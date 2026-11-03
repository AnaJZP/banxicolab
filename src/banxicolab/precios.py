"""Análisis de inflación a partir de un índice de precios."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .transformaciones import anualizar, frecuencia, valor_en, variacion


def inflacion(indice: pd.Series) -> pd.DataFrame:
    """Las cuatro lecturas habituales de la inflación, en %.

    Parameters
    ----------
    indice : Series
        Índice de precios **mensual** (INPC, subyacente, etc.).

    Returns
    -------
    pandas.DataFrame
        - ``mensual``: variación respecto al mes anterior.
        - ``anual``: respecto al mismo mes del año anterior (la que se compara
          con la meta de 3 % de Banxico).
        - ``acumulada``: respecto a diciembre del año anterior.
        - ``mensual_anualizada``: la mensual capitalizada a 12 meses; muy
          volátil y afectada por la estacionalidad.

    Examples
    --------
    >>> import banxicolab as sie
    >>> sie.inflacion(sie.serie("inpc", "2020-01-01")).tail()   # doctest: +SKIP
    """
    s = indice.dropna().sort_index()
    if frecuencia(s) != "Mensual":
        raise ValueError("inflacion() espera un índice mensual.")
    mensual = variacion(s)

    # Diciembre de cada año es la base del acumulado del año siguiente
    diciembres = s[s.index.month == 12]
    cierre_previo = pd.Series(diciembres.to_numpy(), index=diciembres.index.year + 1)
    base = pd.Series(s.index.year, index=s.index).map(cierre_previo)

    return pd.DataFrame(
        {
            "mensual": mensual,
            "anual": variacion(s, 12),
            "acumulada": (s / base - 1) * 100,
            "mensual_anualizada": anualizar(mensual, 12),
        }
    )


def inflacion_entre(indice: pd.Series, inicio, fin) -> float:
    """Inflación acumulada (en %) entre dos fechas.

    Examples
    --------
    >>> import pandas as pd
    >>> inpc = pd.Series([100.0, 110.0], index=pd.to_datetime(["2020-01-01", "2021-01-01"]))
    >>> round(inflacion_entre(inpc, "2020-01-01", "2021-01-01"), 2)
    10.0
    """
    return (valor_en(indice, fin) / valor_en(indice, inicio) - 1) * 100


def impulso(indice: pd.Series, meses: int = 3, *, ajustar: bool = True) -> pd.Series:
    """Ritmo reciente de la inflación: promedio móvil contra el previo, anualizado.

    Compara el promedio del índice en los últimos ``meses`` con el de los
    ``meses`` anteriores y anualiza el resultado (el «3m/3m anualizado» de los
    reportes de bancos centrales). Detecta los cambios de tendencia varios meses
    antes que la variación anual, que arrastra lo ocurrido hace un año.

    Parameters
    ----------
    indice : Series
        Índice de precios mensual.
    meses : int
        Tamaño de la ventana (3 o 6 son los habituales).
    ajustar : bool
        Desestacionaliza antes con :func:`banxicolab.desestacionalizar`.
        Sin ajuste, el resultado refleja sobre todo
        el calendario.

    Returns
    -------
    Series
        En % anualizado.
    """
    s = indice.dropna().sort_index()
    if frecuencia(s) != "Mensual":
        raise ValueError("impulso() espera un índice mensual.")
    if ajustar:
        from .transformaciones import desestacionalizar

        s = desestacionalizar(s)
    media = s.rolling(meses).mean()
    return ((media / media.shift(meses)) ** (12 / meses) - 1) * 100


def persistencia(serie: pd.Series, rezagos: int = 12, ventana: int | None = None):
    """Persistencia de la inflación: suma de los coeficientes de un AR(p).

    Cerca de 1, los choques tardan mucho en disiparse (la inflación se comporta
    casi como una caminata aleatoria); cerca de 0, se revierten pronto.

    Parameters
    ----------
    serie : Series
        Inflación mensual (idealmente desestacionalizada) u otra serie
        estacionaria.
    rezagos : int
        Orden ``p`` del autorregresivo, estimado por mínimos cuadrados.
    ventana : int, opcional
        Si se indica, estima en ventanas móviles de ese tamaño y devuelve un
        ``Series`` para ver cómo cambia en el tiempo; si no, un solo número.
    """
    s = serie.dropna()

    def _suma(valores: np.ndarray) -> float:
        y = valores[rezagos:]
        x = np.column_stack(
            [np.ones(len(y))] + [valores[rezagos - k : -k] for k in range(1, rezagos + 1)]
        )
        return float(np.linalg.lstsq(x, y, rcond=None)[0][1:].sum())

    if ventana is None:
        if len(s) <= 2 * rezagos + 1:
            raise ValueError("Muy pocas observaciones para ese número de rezagos.")
        return _suma(s.to_numpy())
    if ventana <= 2 * rezagos + 1:
        raise ValueError("La ventana debe ser mayor que 2 × rezagos + 1.")
    valores = s.to_numpy()
    resultado = [_suma(valores[i - ventana : i]) for i in range(ventana, len(valores) + 1)]
    return pd.Series(resultado, index=s.index[ventana - 1 :], name="persistencia")


def _quincenas(quincenal: pd.Series) -> pd.DataFrame:
    s = quincenal.dropna().sort_index()
    if frecuencia(s) != "Quincenal":
        raise ValueError("Se espera un índice de precios quincenal (fechado los días 1 y 16).")
    tabla = pd.DataFrame({"q1": s[s.index.day == 1]})
    segunda = s[s.index.day == 16]
    tabla["q2"] = pd.Series(segunda.to_numpy(), index=segunda.index - pd.Timedelta(days=15))
    tabla.index.name = "mes"
    return tabla


def anticipar_inflacion(
    quincenal: pd.Series, *, anios: int = 8, historial: bool = False
) -> pd.DataFrame:
    """Anticipa la inflación de un mes con solo su primera quincena publicada.

    El INPC mensual es, por construcción, el promedio de sus dos índices
    quincenales. Cuando INEGI publica la primera quincena (unos quince días
    antes que el dato mensual), solo falta la segunda. Se estima con el cambio
    típico entre la primera y la segunda quincena **de ese mismo mes** en los
    años anteriores, lo que captura la estacionalidad (por ejemplo, las tarifas
    eléctricas de temporada cálida).

    Parameters
    ----------
    quincenal : Series
        INPC quincenal (alias ``"inpc_quincenal"``) u otro índice quincenal.
    anios : int
        Años previos de los que se toma el cambio típico entre quincenas.
    historial : bool
        Si es ``True``, repite la estimación para cada mes pasado usando solo
        la información disponible en su momento, y la compara con lo
        observado. Sirve para juzgar qué tan confiable es.

    Returns
    -------
    pandas.DataFrame
        Una fila por mes con ``mensual`` y ``anual`` estimadas (en %) y su
        rango (``_inf``, ``_sup``), que es el mínimo y el máximo de lo que
        habría dado cada uno de los años de referencia. Con ``historial=True``
        se agregan ``mensual_observada`` y ``anual_observada``.

    Notes
    -----
    Con el INPC de 2012 a 2026, el error típico (raíz del error cuadrático
    medio) fue de 0.09 puntos en la inflación mensual y anual, y el dato
    observado cayó dentro del rango en tres de cada cuatro meses.
    """
    q = _quincenas(quincenal)
    q["cambio"] = q["q2"] / q["q1"] - 1
    mensual = (q["q1"] + q["q2"]) / 2

    meses = q.index if historial else q.index[q["q2"].isna() & q["q1"].notna()]
    if not historial and len(meses) == 0:
        raise ValueError(
            "El último mes ya tiene sus dos quincenas, así que su inflación ya se conoce: "
            "usa banxicolab.inflacion() con el INPC mensual."
        )
    filas = []
    for mes in meses:
        previos = q.loc[: mes - pd.DateOffset(months=1)].dropna(subset=["cambio"])
        mismos = previos[previos.index.month == mes.month]["cambio"].tail(anios)
        anterior = mensual.get(mes - pd.DateOffset(months=1))
        hace_un_anio = mensual.get(mes - pd.DateOffset(months=12))
        if (
            len(mismos) < 3
            or pd.isna(anterior)
            or pd.isna(hace_un_anio)
            or pd.isna(q.at[mes, "q1"])
        ):
            continue
        q1 = q.at[mes, "q1"]
        estimado = {
            nombre: (q1 + q1 * (1 + cambio)) / 2
            for nombre, cambio in [
                ("", mismos.median()),
                ("_inf", mismos.min()),
                ("_sup", mismos.max()),
            ]
        }
        fila = {"mes": mes, "primera_quincena": q1}
        for sufijo, indice in estimado.items():
            fila[f"mensual{sufijo}"] = (indice / anterior - 1) * 100
            fila[f"anual{sufijo}"] = (indice / hace_un_anio - 1) * 100
        if historial:
            fila["mensual_observada"] = (mensual[mes] / anterior - 1) * 100
            fila["anual_observada"] = (mensual[mes] / hace_un_anio - 1) * 100
        filas.append(fila)
    if not filas:
        raise ValueError("Hace falta más historia: al menos 3 años previos del índice quincenal.")
    columnas = ["mensual", "mensual_inf", "mensual_sup", "anual", "anual_inf", "anual_sup"]
    tabla = pd.DataFrame(filas).set_index("mes")
    orden = ["primera_quincena", *columnas]
    if historial:
        tabla = tabla.dropna(subset=["mensual_observada"])
        orden += ["mensual_observada", "anual_observada"]
    return tabla[orden]


# Meses en que entra en vigor una nueva estructura de ponderadores del INPC. Se
# identificaron en los datos: dentro de cada tramo el índice general es una suma
# fija de sus cuatro componentes con un error menor a 0.001 puntos de índice.
CAMBIOS_DE_PONDERADORES = ("2002-07-01", "2011-01-01", "2013-02-01", "2018-08-01", "2024-08-01")


def contribuciones(
    total: pd.Series,
    componentes: pd.DataFrame,
    periodos: int = 12,
    *,
    cambios=CAMBIOS_DE_PONDERADORES,
) -> pd.DataFrame:
    """Cuántos puntos porcentuales aporta cada componente a la inflación.

    Dentro de cada periodo de ponderadores fijos, el índice general es una
    combinación lineal exacta de sus componentes. Los coeficientes se estiman
    de los propios datos (no hace falta conocer los ponderadores oficiales) y
    con ellos el cambio del índice general se reparte entre los componentes.
    Cuando el periodo comparado cruza un cambio de ponderadores, el cálculo se
    encadena en el mes de enlace.

    Parameters
    ----------
    total : Series
        Índice general mensual (INPC).
    componentes : DataFrame
        Índices de los componentes que suman el total, uno por columna.
    periodos : int
        12 para la inflación anual; 1 para la mensual.
    cambios : lista de fechas
        Meses en que cambian los ponderadores.

    Returns
    -------
    pandas.DataFrame
        Una columna por componente con su aportación en puntos porcentuales,
        más ``total`` (la inflación del periodo) y ``residuo`` (lo que no
        explica la suma; cercano a cero si la descomposición es exacta).

    Warns
    -----
    UserWarning
        Si en algún tramo el total deja de ser una suma exacta de los
        componentes, lo que suele indicar un cambio de ponderadores reciente
        que aún no está en ``cambios``.
    """
    import warnings

    datos = pd.concat({"__total__": total}, axis=1).join(componentes, how="inner").dropna()
    nombres = list(componentes.columns)
    cortes = [
        datos.index.min(),
        *[pd.Timestamp(c) for c in cambios if pd.Timestamp(c) > datos.index.min()],
    ]
    cortes = sorted(set(cortes)) + [datos.index.max() + pd.DateOffset(months=1)]

    tramos = []
    for inicio, fin in zip(cortes[:-1], cortes[1:], strict=True):
        parte = datos.loc[(datos.index >= inicio) & (datos.index < fin)]
        if len(parte) <= len(nombres):
            continue
        coef, *_ = np.linalg.lstsq(
            parte[nombres].to_numpy(), parte["__total__"].to_numpy(), rcond=None
        )
        error = float(
            np.abs(parte["__total__"].to_numpy() - parte[nombres].to_numpy() @ coef).max()
        )
        if error > 0.05:  # puntos de índice; por debajo es redondeo de los datos publicados
            warnings.warn(
                f"Entre {inicio:%Y-%m} y {parte.index.max():%Y-%m} el índice general no es "
                f"una suma exacta de los componentes (error máximo {error:.3f}); puede haber "
                "un cambio de ponderadores no considerado. Las contribuciones son aproximadas.",
                stacklevel=2,
            )
        tramos.append((inicio, fin, coef))

    def coeficientes(fecha):
        for inicio, fin, coef in tramos:
            if inicio <= fecha < fin:
                return coef
        return None

    fechas = datos.index
    filas = {}
    for k in range(periodos, len(fechas)):
        desde, hasta = fechas[k - periodos], fechas[k]
        if hasta - pd.DateOffset(months=periodos) != desde:
            continue  # hay meses faltantes
        # Puntos de enlace: el último mes de cada tramo que queda dentro del periodo
        puntos = [desde]
        for inicio, _, _ in tramos:
            enlace = inicio - pd.DateOffset(months=1)
            if desde < enlace < hasta:
                puntos.append(enlace)
        puntos.append(hasta)
        base = datos.at[desde, "__total__"]
        aporte = np.zeros(len(nombres))
        for a, b in zip(puntos[:-1], puntos[1:], strict=True):
            coef = coeficientes(a + pd.DateOffset(months=1))  # tramo en el que cae (a, b]
            if coef is None:
                aporte[:] = np.nan
                break
            aporte += (
                coef * (datos.loc[b, nombres].to_numpy() - datos.loc[a, nombres].to_numpy()) / base
            )
        filas[hasta] = aporte * 100
    tabla = pd.DataFrame.from_dict(filas, orient="index", columns=nombres)
    tabla.index.name = "fecha"
    tabla["total"] = (datos["__total__"] / datos["__total__"].shift(periodos) - 1).reindex(
        tabla.index
    ) * 100
    tabla["residuo"] = tabla["total"] - tabla[nombres].sum(axis=1)
    return tabla
