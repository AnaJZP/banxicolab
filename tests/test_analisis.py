import numpy as np
import pandas as pd
import pytest

import banxicolab as sie


def test_tabla_de_inflacion():
    fechas = pd.date_range("2019-12-01", periods=14, freq="MS")
    indice = pd.Series(100 * 1.01 ** np.arange(14), index=fechas)
    tabla = sie.inflacion(indice)

    assert list(tabla.columns) == ["mensual", "anual", "acumulada", "mensual_anualizada"]
    assert np.allclose(tabla["mensual"].dropna(), 1.0)
    assert np.isclose(tabla.loc["2020-12-01", "anual"], (1.01**12 - 1) * 100)
    # En diciembre el acumulado del año coincide con la anual
    assert np.isclose(tabla.loc["2020-12-01", "acumulada"], tabla.loc["2020-12-01", "anual"])
    assert np.isclose(tabla.loc["2020-03-01", "acumulada"], (1.01**3 - 1) * 100)
    assert np.isclose(tabla.loc["2021-01-01", "acumulada"], 1.0)  # reinicia cada enero
    assert np.isnan(tabla.loc["2019-12-01", "acumulada"])  # sin diciembre previo
    assert np.isclose(tabla["mensual_anualizada"].iloc[-1], (1.01**12 - 1) * 100)


def test_inflacion_exige_frecuencia_mensual():
    diaria = pd.Series(1.0, index=pd.bdate_range("2020-01-01", periods=30))
    with pytest.raises(ValueError, match="mensual"):
        sie.inflacion(diaria)


def test_inflacion_entre(inpc):
    assert sie.inflacion_entre(inpc, "2015-01-01", "2016-01-01") == pytest.approx(
        (1.005**12 - 1) * 100
    )


def test_diagnostico(inpc):
    diaria = pd.Series(np.linspace(10, 20, 60), index=pd.bdate_range("2015-01-01", periods=60))
    diaria.iloc[5] = np.nan
    mensual = sie.diagnostico(inpc)
    assert mensual.loc["inpc", "frecuencia"] == "Mensual" and mensual.loc["inpc", "obs"] == 96
    assert mensual.loc["inpc", "faltantes"] == 0
    tabla = sie.diagnostico(diaria.rename("fix").to_frame())
    assert tabla.loc["fix", "frecuencia"] == "Diaria" and tabla.loc["fix", "faltantes"] == 1
    assert tabla.loc["fix", "razon_max_min"] == pytest.approx(2.0)


def test_escalar_no_cambia_la_prueba_adf():
    pytest.importorskip("statsmodels")
    choques = np.random.default_rng(7).normal(0.004, 0.003, 240)
    inpc = pd.Series(
        100 * np.exp(np.cumsum(choques)), index=pd.date_range("2005-01-01", periods=240, freq="MS")
    )
    tabla = sie.prueba_adf(
        {
            "nivel": inpc,
            "z": sie.estandarizar(inpc),
            "indice": sie.indice_base(inpc, "2018-01-01"),
            "dlog": sie.variacion(inpc, log=True),
        }
    )
    assert np.allclose(tabla.loc[["z", "indice"], "estadistico"], tabla.loc["nivel", "estadistico"])
    assert not tabla.loc["nivel", "estacionaria"]
    assert tabla.loc["dlog", "estacionaria"]
