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
