"""Conocer los datos antes de transformarlos, y verificar después."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from .transformaciones import frecuencia


def diagnostico(datos: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Resumen mínimo por serie: cobertura, frecuencia, faltantes y rango.

    La columna ``razon_max_min`` orienta sobre el logaritmo: si una serie
    positiva se multiplicó varias veces, su varianza casi seguro crece con el
    nivel.

    ``faltantes`` cuenta los huecos entre la primera y la última observación de
    cada columna, así que diagnostica por separado las series de frecuencias
    distintas: al juntarlas en una tabla, los días sin dato mensual contarían
    como faltantes.
    """
    df = datos.to_frame() if isinstance(datos, pd.Series) else datos
    filas = []
    for columna in df.columns:
        s = df[columna].dropna()
        if len(s) < 3:
            continue
        interior = df[columna].loc[s.index.min() : s.index.max()]
        filas.append(
            {
                "serie": columna,
                "obs": len(s),
                "inicio": s.index.min().date(),
                "fin": s.index.max().date(),
                "frecuencia": frecuencia(s),
                "faltantes": int(interior.isna().sum()),
                "min": s.min(),
                "max": s.max(),
                "razon_max_min": s.max() / s.min() if s.min() > 0 else np.nan,
            }
        )
    return pd.DataFrame(filas).set_index("serie")


def _adf(adfuller, serie: pd.Series) -> tuple:
    # statsmodels está migrando de devolver una tupla a un objeto de resultados
    try:
        r = adfuller(serie, autolag="AIC", result_object=True)
    except TypeError:  # statsmodels < 0.15
        return adfuller(serie, autolag="AIC")[:5]
    return r.statistic, r.pvalue, r.lags, r.nobs, r.critical_values


def prueba_adf(
    datos: pd.Series | pd.DataFrame | Mapping[str, pd.Series], alfa: float = 0.05
) -> pd.DataFrame:
    """Prueba Dickey–Fuller Aumentada para una o varias series.

    Acepta un diccionario ``{nombre: serie}``, ideal para comparar la misma
    variable bajo distintas transformaciones. H0: la serie tiene raíz unitaria;
    se rechaza (``estacionaria = True``) cuando ``p_valor < alfa``.

    Requiere ``statsmodels`` (``pip install statsmodels``).
    """
    from ._opcionales import statsmodels_tsa

    adfuller = statsmodels_tsa().stattools.adfuller
    if isinstance(datos, pd.Series):
        datos = {datos.name or "serie": datos}
    elif isinstance(datos, pd.DataFrame):
        datos = {c: datos[c] for c in datos.columns}

    filas = []
    for nombre, s in datos.items():
        estadistico, p, rezagos, n, criticos = _adf(adfuller, s.dropna())
        filas.append(
            {
                "serie": nombre,
                "estadistico": estadistico,
                "critico_5%": criticos["5%"],
                "p_valor": p,
                "rezagos": rezagos,
                "obs": n,
                "estacionaria": bool(p < alfa),
            }
        )
    return pd.DataFrame(filas).set_index("serie")
