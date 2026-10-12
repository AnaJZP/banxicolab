"""Transformaciones habituales de series económicas y financieras.

Todas son funciones puras: reciben un ``Series`` (o ``DataFrame``, columna por
columna) con ``DatetimeIndex`` y devuelven un objeto nuevo. Ninguna descarga
datos, así que sirven con cualquier fuente.

Recordatorio: cambiar de escala (índice, z-score, min–max) **no** vuelve
estacionaria una serie; para eso están las diferencias y las tasas de variación.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

import numpy as np
import pandas as pd

Datos = TypeVar("Datos", pd.Series, pd.DataFrame)

_AGREGACIONES = {"ultimo": "last", "promedio": "mean", "suma": "sum", "primero": "first"}
_PERIODOS = {"Quincenal": 24, "Mensual": 12, "Trimestral": 4, "Anual": 1}


# ── Utilidades ───────────────────────────────────────────────────────────────


def frecuencia(serie: pd.Series | pd.DataFrame) -> str:
    """Frecuencia aproximada según la separación mediana entre observaciones.

    Returns
    -------
    str
        ``"Diaria"``, ``"Semanal"``, ``"Quincenal"``, ``"Mensual"``,
        ``"Trimestral"`` o ``"Anual"``.
    """
    indice = (
        serie.dropna(how="all").index if isinstance(serie, pd.DataFrame) else serie.dropna().index
    )
    if len(indice) < 3:
        raise ValueError("Se necesitan al menos 3 observaciones para inferir la frecuencia.")
    dias = pd.Series(indice).diff().dt.days.median()
    for limite, nombre in [(4, "Diaria"), (10, "Semanal"), (20, "Quincenal"),
                           (45, "Mensual"), (135, "Trimestral")]:  # fmt: skip
        if dias <= limite:
            return nombre
    return "Anual"


def valor_en(serie: pd.Series, fecha) -> float:
    """Último valor disponible en o antes de ``fecha``.

    Evita el ``KeyError`` cuando la fecha exacta no existe (fines de semana,
    series mensuales fechadas el día 1, etc.).
    """
    valor = serie.dropna().sort_index().asof(pd.Timestamp(fecha))
    if pd.isna(valor):
        raise ValueError(f"No hay datos en o antes de {pd.Timestamp(fecha).date()}")
    return float(valor)


def _por_columna(funcion, datos, *args, **kwargs):
    if isinstance(datos, pd.DataFrame):
        return datos.apply(lambda columna: funcion(columna, *args, **kwargs))
    return funcion(datos, *args, **kwargs)


# ── Frecuencia ───────────────────────────────────────────────────────────────


def a_mensual(datos: Datos, como: str | Mapping[str, str] = "ultimo") -> Datos:
    """Lleva una serie de alta frecuencia a frecuencia mensual.

    Parameters
    ----------
    datos : Series o DataFrame
        Serie diaria o semanal.
    como : {"ultimo", "promedio", "suma", "primero"} o dict
        Regla de agregación. La elección no es neutral: ``"ultimo"`` para
        precios y saldos (tipo de cambio, reservas), ``"promedio"`` para tasas
        de interés, ``"suma"`` para flujos. Promediar un precio reduce
        artificialmente su volatilidad. Con un ``DataFrame`` puede darse un
        diccionario ``{columna: regla}``.

    Returns
    -------
    Series o DataFrame
        Indexado al **primer día de cada mes**, igual que las series mensuales
        del SIE, para que se puedan unir sin desfases.
    """
    if isinstance(como, Mapping):
        if not isinstance(datos, pd.DataFrame):
            raise TypeError("Un diccionario de reglas solo aplica a un DataFrame.")
        faltan = set(datos.columns) - set(como)
        if faltan:
            raise ValueError(f"Falta la regla de agregación para: {sorted(faltan)}")
        return pd.DataFrame({c: a_mensual(datos[c], como[c]) for c in datos.columns})
    if como not in _AGREGACIONES:
        raise ValueError(f"como debe ser uno de {sorted(_AGREGACIONES)}")
    # min_count evita que un mes sin datos sume 0 en lugar de quedar vacío
    extra = {"min_count": 1} if como == "suma" else {}
    return getattr(datos.resample("MS"), _AGREGACIONES[como])(**extra)


# ── Números índice ───────────────────────────────────────────────────────────


def indice_base(datos: Datos, base=None, valor: float = 100) -> Datos:
    """Convierte a número índice: ``valor × X_t / X_base``.

    Parameters
    ----------
    base : fecha, opcional
        Periodo base. Se toma el último dato en o antes de esa fecha; si se
        omite, la primera observación válida.
    valor : float
        Valor del índice en la base (100 por convención).
    """

    def _uno(s: pd.Series) -> pd.Series:
        referencia = s.dropna().iloc[0] if base is None else valor_en(s, base)
        return valor * s / referencia

    return _por_columna(_uno, datos)


def cambiar_base(indice: Datos, base, valor: float = 100) -> Datos:
    """Rebasifica un índice ya construido, sin volver a los datos originales."""
    return indice_base(indice, base, valor)


def empalmar(anterior: pd.Series, nueva: pd.Series, traslape=None) -> pd.Series:
    """Une dos tramos de un índice con bases distintas en una sola serie.

    El tramo ``anterior`` se reescala para que coincida con ``nueva`` en la
    fecha de traslape; de ahí en adelante se usa ``nueva`` tal cual. Las tasas
    de variación de ambos tramos se conservan intactas.

    Parameters
    ----------
    traslape : fecha, opcional
        Fecha común en la que se igualan. Por omisión, la primera fecha de
        ``nueva`` que también existe en ``anterior``.
    """
    anterior, nueva = anterior.dropna().sort_index(), nueva.dropna().sort_index()
    if traslape is None:
        comunes = nueva.index.intersection(anterior.index)
        if comunes.empty:
            raise ValueError("Los tramos no comparten ninguna fecha: no hay cómo empalmarlos.")
        traslape = comunes[0]
    traslape = pd.Timestamp(traslape)
    if traslape not in anterior.index or traslape not in nueva.index:
        raise ValueError(f"Ambos tramos deben tener dato en {traslape.date()}")
    factor = nueva.loc[traslape] / anterior.loc[traslape]
    previo = anterior.loc[anterior.index < traslape] * factor
    return pd.concat([previo, nueva.loc[traslape:]]).rename(nueva.name)


# ── Tasas de variación ───────────────────────────────────────────────────────


def variacion(
    datos: Datos, periodos: int = 1, *, log: bool = False, porcentaje: bool = True
) -> Datos:
    """Tasa de variación respecto a ``periodos`` observaciones atrás.

    Parameters
    ----------
    periodos : int
        1 para la variación periodo a periodo; 12 para la anual de una serie
        mensual (ver también :func:`variacion_anual`).
    log : bool
        Si es ``True`` devuelve la diferencia de logaritmos, que es aditiva en
        el tiempo. Se aproxima a la variación simple solo para cambios pequeños.
    porcentaje : bool
        Multiplica por 100.
    """
    if log:
        resultado = np.log(datos.where(datos > 0)).diff(periodos)
    else:
        resultado = datos.pct_change(periodos, fill_method=None)
    return resultado * 100 if porcentaje else resultado


def variacion_anual(datos: Datos, *, log: bool = False, porcentaje: bool = True) -> Datos:
    """Variación contra el mismo periodo del año anterior.

    Detecta sola si la serie es quincenal, mensual, trimestral o anual. Al comparar cada
    mes con el mismo mes del año previo, cancela la estacionalidad estable.
    """
    nombre = frecuencia(datos)
    if nombre not in _PERIODOS:
        raise ValueError(
            f"La serie parece {nombre.lower()}; llévala primero a mensual con a_mensual()."
        )
    return variacion(datos, _PERIODOS[nombre], log=log, porcentaje=porcentaje)


def anualizar(tasa: Datos, periodos_por_anio: int = 12, *, porcentaje: bool = True) -> Datos:
    """Anualiza una tasa por capitalización compuesta: ``(1 + r)^k − 1``.

    Multiplicar por ``k`` subestima el resultado; el error crece con la tasa.

    Parameters
    ----------
    tasa : Series, DataFrame o número
        Tasa por periodo (en % si ``porcentaje=True``).
    periodos_por_anio : int
        12 para una tasa mensual, 4 para trimestral.
    """
    r = tasa / 100 if porcentaje else tasa
    anual = (1 + r) ** periodos_por_anio - 1
    return anual * 100 if porcentaje else anual


# ── Precios constantes ───────────────────────────────────────────────────────


def deflactar(nominal: Datos, precios: pd.Series, base=None) -> Datos:
    """Expresa una serie monetaria en pesos constantes.

    Parameters
    ----------
    nominal : Series o DataFrame
        Montos en pesos corrientes.
    precios : Series
        Índice de precios (normalmente el INPC) **con la misma frecuencia y
        fechas** que ``nominal``.
    base : fecha, opcional
        Los resultados quedan en pesos de esa fecha. Si se omite se usa la base
        propia del índice (se divide entre ``precios / 100``).
    """
    referencia = 100.0 if base is None else valor_en(precios, base)
    deflactor = precios.reindex(nominal.index) / referencia
    if isinstance(nominal, pd.DataFrame):
        return nominal.div(deflactor, axis=0)
    return nominal / deflactor


def a_pesos_de(monto: float, origen, destino, precios: pd.Series) -> float:
    """Convierte un monto de la fecha ``origen`` a pesos de la fecha ``destino``.

    Examples
    --------
    >>> import pandas as pd
    >>> inpc = pd.Series([100.0, 110.0], index=pd.to_datetime(["2020-01-01", "2021-01-01"]))
    >>> a_pesos_de(1000, "2020-01-01", "2021-01-01", inpc)
    1100.0
    """
    return monto * valor_en(precios, destino) / valor_en(precios, origen)


def tasa_real(nominal: Datos, inflacion: Datos, *, exacta: bool = True) -> Datos:
    """Tasa de interés real ex-post (ecuación de Fisher), en %.

    Parameters
    ----------
    nominal, inflacion : Series
        Ambas en % anual y con el mismo índice.
    exacta : bool
        ``True``: ``(1 + i) / (1 + π) − 1``. ``False``: la aproximación
        ``i − π``, que siempre sobreestima y empeora cuando la inflación es alta.
    """
    if not exacta:
        return nominal - inflacion
    return ((1 + nominal / 100) / (1 + inflacion / 100) - 1) * 100


# ── Cambio de unidades ───────────────────────────────────────────────────────


def estandarizar(datos: Datos, referencia: Datos | None = None) -> Datos:
    """Puntaje z: ``(x − media) / desviación estándar``.

    Parameters
    ----------
    referencia : Series o DataFrame, opcional
        Muestra de la que se calculan media y desviación. Al evaluar un modelo
        pasa aquí **solo el conjunto de entrenamiento** para no filtrar
        información del futuro (*data leakage*).
    """
    ref = datos if referencia is None else referencia
    return (datos - ref.mean()) / ref.std()


def min_max(datos: Datos, a: float = 0, b: float = 1, referencia: Datos | None = None) -> Datos:
    """Reescala linealmente al intervalo ``[a, b]``.

    Muy sensible a valores atípicos. Con ``referencia`` (entrenamiento) los
    datos nuevos pueden salir de ``[a, b]``: eso es información, no un error.
    """
    ref = datos if referencia is None else referencia
    return a + (b - a) * (datos - ref.min()) / (ref.max() - ref.min())


def escalar_robusto(datos: Datos, referencia: Datos | None = None) -> Datos:
    """``(x − mediana) / rango intercuartílico``: resistente a valores atípicos."""
    ref = datos if referencia is None else referencia
    return (datos - ref.median()) / (ref.quantile(0.75) - ref.quantile(0.25))


# ── Estacionalidad ───────────────────────────────────────────────────────────


def desestacionalizar(
    serie: pd.Series, modelo: str = "multiplicativo", periodo: int | None = None
) -> pd.Series:
    """Ajuste estacional sencillo por descomposición clásica (medias móviles).

    Sirve para explorar y enseñar. **No** reproduce las cifras oficiales, que
    usan X-13ARIMA-SEATS con efectos de calendario; si existe la serie
    desestacionalizada oficial (p. ej. ``"igae_desestacionalizado"``), úsala.

    Requiere ``statsmodels`` (``pip install statsmodels``).

    Parameters
    ----------
    modelo : {"multiplicativo", "aditivo"}
    periodo : int, opcional
        Observaciones por ciclo; por omisión 12 o 4 según la frecuencia.
    """
    from ._opcionales import statsmodels_tsa

    modelos = {"multiplicativo": "multiplicative", "aditivo": "additive"}
    if modelo not in modelos:
        raise ValueError(f"modelo debe ser uno de {sorted(modelos)}")
    s = serie.dropna()
    if periodo is None:
        periodo = _PERIODOS.get(frecuencia(s))
        if periodo in (None, 1):
            raise ValueError("Indica periodo=: no se puede inferir un ciclo estacional.")
    # extrapolate_trend completa la tendencia en los extremos de la muestra
    estacional = (
        statsmodels_tsa()
        .seasonal.seasonal_decompose(
            s, model=modelos[modelo], period=periodo, extrapolate_trend=periodo - 1
        )
        .seasonal
    )
    return s / estacional if modelo == "multiplicativo" else s - estacional
