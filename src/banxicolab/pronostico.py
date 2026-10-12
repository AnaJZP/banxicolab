"""Pronósticos de inflación de referencia y su evaluación fuera de muestra.

Son modelos univariados sencillos: sirven como punto de comparación, no como
sustituto de un modelo estructural ni del juicio de quien analiza.
Requieren ``statsmodels`` (``pip install statsmodels``).
"""

from __future__ import annotations

import inspect
import warnings

import numpy as np
import pandas as pd

from .transformaciones import frecuencia

METODOS = ("sarima", "ingenuo")


def _preparar(indice: pd.Series) -> pd.Series:
    s = indice.dropna().sort_index()
    if frecuencia(s) != "Mensual":
        raise ValueError("Se espera un índice de precios mensual.")
    if len(s) < 60:
        raise ValueError("Se necesitan al menos 60 meses de historia.")
    s.index = pd.DatetimeIndex(s.index).to_period("M").to_timestamp()
    return s.asfreq("MS")


def _ajustar_sarima(log_indice: pd.Series, orden, orden_estacional):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return SARIMAX(log_indice, order=orden, seasonal_order=orden_estacional).fit(disp=False)


def _simular(modelo, horizonte: int, repeticiones: int, semilla) -> np.ndarray:
    # statsmodels renombró el argumento de la semilla (random_state → rng) en la 0.15
    nombre = "rng" if "rng" in inspect.signature(modelo.simulate).parameters else "random_state"
    opciones = {"repetitions": repeticiones, "anchor": "end", nombre: semilla}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        caminos = modelo.simulate(horizonte, **opciones)
    return np.asarray(caminos).reshape(horizonte, -1)


def _ingenuo(log_indice: np.ndarray, horizonte: int) -> np.ndarray:
    """La inflación anual se queda donde está: p[t+h] = p[t+h-12] + (p[t] - p[t-12])."""
    anual = log_indice[-1] - log_indice[-13]
    camino = list(log_indice[-12:])
    for _ in range(horizonte):
        camino.append(camino[-12] + anual)
    return np.array(camino[12:])


def _anual(historia: np.ndarray, futuro: np.ndarray) -> np.ndarray:
    """Inflación anual (%) de los meses pronosticados; ``futuro`` puede ser 2-D."""
    previo = np.broadcast_to(historia[-12:, None], (12, futuro.shape[1]))
    completo = np.vstack([previo, futuro])
    return (np.exp(completo[12:] - completo[:-12]) - 1) * 100


def pronosticar_inflacion(
    indice: pd.Series,
    horizonte: int = 12,
    *,
    metodo: str = "sarima",
    nivel: float = 0.90,
    orden: tuple = (0, 1, 1),
    orden_estacional: tuple = (0, 1, 1, 12),
    simulaciones: int = 2000,
    semilla: int | None = 0,
) -> pd.DataFrame:
    """Pronostica la inflación a partir del índice de precios.

    Parameters
    ----------
    indice : Series
        Índice de precios mensual (INPC, subyacente…), al menos 5 años.
    horizonte : int
        Meses a pronosticar.
    metodo : {"sarima", "ingenuo"}
        - ``"sarima"``: SARIMA sobre el logaritmo del índice. El valor por
          omisión, ``(0,1,1)(0,1,1)₁₂``, es el «modelo de aerolíneas», la
          referencia habitual para series mensuales con estacionalidad.
        - ``"ingenuo"``: la inflación anual se mantiene en su último valor. Es
          sorprendentemente difícil de superar a 12 meses; todo modelo debería
          compararse contra él.
    nivel : float
        Cobertura del intervalo (0.90 → de 5 % a 95 %). Solo con ``"sarima"``.
    orden, orden_estacional : tuple
        Especificación del SARIMA.
    simulaciones : int
        Trayectorias simuladas para construir el intervalo de la inflación
        anual, que depende de varios meses pronosticados a la vez.
    semilla : int, opcional
        Fija las simulaciones para que el resultado sea reproducible.

    Returns
    -------
    pandas.DataFrame
        Una fila por mes futuro: ``indice``, ``mensual``, ``anual`` y, con
        SARIMA, ``anual_inf`` y ``anual_sup``. Todo en % salvo el índice.

    Notes
    -----
    El intervalo refleja solo la incertidumbre de los choques futuros bajo el
    modelo; no incluye la de los parámetros ni la de haber elegido mal el
    modelo, así que es más estrecho que la incertidumbre real.
    """
    if metodo not in METODOS:
        raise ValueError(f"metodo debe ser uno de {METODOS}")
    s = _preparar(indice)
    logs = np.log(s)
    fechas = pd.date_range(s.index[-1], periods=horizonte + 1, freq="MS")[1:]

    bandas = {}
    if metodo == "ingenuo":
        camino = _ingenuo(logs.to_numpy(), horizonte)
    else:
        modelo = _ajustar_sarima(logs, orden, orden_estacional)
        camino = np.asarray(modelo.forecast(horizonte))
        simulado = _simular(modelo, horizonte, simulaciones, semilla)
        anual_sim = _anual(logs.to_numpy(), simulado)
        cola = (1 - nivel) / 2
        bandas = {
            "anual_inf": np.quantile(anual_sim, cola, axis=1),
            "anual_sup": np.quantile(anual_sim, 1 - cola, axis=1),
        }

    completo = np.concatenate([logs.to_numpy()[-1:], camino])
    return pd.DataFrame(
        {
            "indice": np.exp(camino),
            "mensual": (np.exp(np.diff(completo)) - 1) * 100,
            "anual": _anual(logs.to_numpy(), camino[:, None])[:, 0],
            **bandas,
        },
        index=fechas.rename("fecha"),
    )


def evaluar_pronosticos(
    indice: pd.Series,
    horizontes: tuple[int, ...] = (1, 3, 6, 12),
    *,
    desde=None,
    paso: int = 3,
    metodos: tuple[str, ...] = METODOS,
    orden: tuple = (0, 1, 1),
    orden_estacional: tuple = (0, 1, 1, 12),
) -> pd.DataFrame:
    """Compara los métodos con pronósticos fuera de muestra de origen móvil.

    Para cada fecha de origen se estima el modelo **solo con los datos
    disponibles hasta entonces**, se pronostica la inflación anual y se compara
    con lo que realmente ocurrió.

    Parameters
    ----------
    horizontes : tuple de int
        Meses hacia adelante a evaluar.
    desde : fecha, opcional
        Primer origen. Por omisión, el último tercio de la muestra.
    paso : int
        Meses entre orígenes consecutivos. 1 es lo más preciso y lo más lento
        (cada origen reestima el SARIMA).

    Returns
    -------
    pandas.DataFrame
        Raíz del error cuadrático medio, en puntos porcentuales de inflación
        anual, por horizonte (filas) y método (columnas), más ``n`` pronósticos
        evaluados. Los errores individuales quedan en ``.attrs["errores"]``.
    """
    desconocidos = set(metodos) - set(METODOS)
    if desconocidos:
        raise ValueError(f"Métodos desconocidos: {sorted(desconocidos)}")
    s = _preparar(indice)
    logs = np.log(s)
    observada = (np.exp(logs - logs.shift(12)) - 1) * 100
    maximo = max(horizontes)
    primero = len(s) * 2 // 3 if desde is None else int(s.index.searchsorted(pd.Timestamp(desde)))
    primero = max(primero, 60)

    filas = []
    for corte in range(primero, len(s) - min(horizontes) + 1, paso):
        historia = logs.iloc[:corte]
        for metodo in metodos:
            if metodo == "ingenuo":
                camino = _ingenuo(historia.to_numpy(), maximo)
            else:
                modelo = _ajustar_sarima(historia, orden, orden_estacional)
                camino = np.asarray(modelo.forecast(maximo))
            anual = _anual(historia.to_numpy(), camino[:, None])[:, 0]
            for h in horizontes:
                if corte + h - 1 < len(s):
                    filas.append(
                        {
                            "origen": s.index[corte - 1],
                            "metodo": metodo,
                            "horizonte": h,
                            "error": anual[h - 1] - observada.iloc[corte + h - 1],
                        }
                    )
    if not filas:
        raise ValueError("No hay suficientes datos después de `desde` para evaluar.")
    errores = pd.DataFrame(filas)
    tabla = (
        errores.assign(cuadrado=errores["error"] ** 2)
        .pivot_table(index="horizonte", columns="metodo", values="cuadrado", aggfunc="mean")
        .pow(0.5)
        .reindex(columns=list(metodos))
    )
    tabla.columns.name = None
    tabla["n"] = errores[errores["metodo"] == metodos[0]].groupby("horizonte").size()
    tabla.attrs["errores"] = errores
    return tabla
