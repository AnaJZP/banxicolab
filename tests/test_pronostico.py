import numpy as np
import pandas as pd
import pytest

import banxicolab as sie


@pytest.fixture(scope="module")
def indice():
    """Inflación de 4 % anual con estacionalidad y ruido pequeño."""
    rng = np.random.default_rng(11)
    fechas = pd.date_range("2008-01-01", periods=180, freq="MS")
    mensual = np.log(1.04) / 12 + 0.002 * np.sin(2 * np.pi * fechas.month / 12)
    return pd.Series(100 * np.exp(np.cumsum(mensual + rng.normal(0, 0.0008, 180))), index=fechas)


def test_impulso_de_un_crecimiento_constante():
    fechas = pd.date_range("2015-01-01", periods=48, freq="MS")
    s = pd.Series(100 * 1.005 ** np.arange(48), index=fechas)
    resultado = sie.impulso(s, 3, ajustar=False)
    assert resultado.first_valid_index() == fechas[5]
    assert np.allclose(resultado.dropna(), (1.005**12 - 1) * 100)


def test_persistencia_recupera_el_coeficiente():
    rng = np.random.default_rng(5)
    x = np.zeros(3000)
    for t in range(1, 3000):
        x[t] = 0.7 * x[t - 1] + rng.normal()
    serie = pd.Series(x, index=pd.date_range("1800-01-01", periods=3000, freq="MS"))
    assert sie.persistencia(serie, rezagos=4) == pytest.approx(0.7, abs=0.06)
    movil = sie.persistencia(serie.iloc[:400], rezagos=2, ventana=200)
    assert len(movil) == 201 and movil.index[-1] == serie.index[399]
    with pytest.raises(ValueError):
        sie.persistencia(serie.iloc[:20], rezagos=12)


def test_pronostico_ingenuo_mantiene_la_inflacion_anual(indice):
    tabla = sie.pronosticar_inflacion(indice, 18, metodo="ingenuo")
    ultima = (indice.iloc[-1] / indice.iloc[-13] - 1) * 100
    assert np.allclose(tabla["anual"], ultima)
    assert tabla.index[0] == indice.index[-1] + pd.DateOffset(months=1)
    assert "anual_inf" not in tabla


def test_pronostico_sarima(indice):
    pytest.importorskip("statsmodels")
    tabla = sie.pronosticar_inflacion(indice, 12, simulaciones=300)
    assert len(tabla) == 12 and tabla["anual"].between(3.0, 5.0).all()
    assert (tabla["anual_inf"] < tabla["anual"]).all() and (
        tabla["anual"] < tabla["anual_sup"]
    ).all()
    ancho = tabla["anual_sup"] - tabla["anual_inf"]
    assert ancho.iloc[-1] > ancho.iloc[0]  # la incertidumbre crece con el horizonte
    # Coherencia interna: índice, mensual y anual cuentan la misma historia
    completo = pd.concat([indice, tabla["indice"]])
    assert np.allclose(completo.pct_change(12).iloc[-12:] * 100, tabla["anual"])
    assert np.allclose(completo.pct_change().iloc[-12:] * 100, tabla["mensual"])
    assert tabla.equals(sie.pronosticar_inflacion(indice, 12, simulaciones=300))  # semilla fija


def test_evaluacion_fuera_de_muestra(indice):
    pytest.importorskip("statsmodels")
    tabla = sie.evaluar_pronosticos(indice, (1, 6), desde="2020-01-01", paso=6)
    assert list(tabla.columns) == ["sarima", "ingenuo", "n"] and list(tabla.index) == [1, 6]
    assert (tabla[["sarima", "ingenuo"]] > 0).all().all()
    assert tabla.loc[1, "sarima"] < tabla.loc[6, "sarima"]
    errores = tabla.attrs["errores"]
    assert errores["origen"].min() >= pd.Timestamp("2019-12-01")
    assert tabla.loc[1, "n"] == (errores.query("metodo == 'sarima' and horizonte == 1")).shape[0]


def test_validaciones(indice):
    with pytest.raises(ValueError, match="metodo"):
        sie.pronosticar_inflacion(indice, metodo="magia")
    with pytest.raises(ValueError, match="60 meses"):
        sie.pronosticar_inflacion(indice.iloc[:30])
    with pytest.raises(ValueError, match="mensual"):
        sie.pronosticar_inflacion(pd.Series(1.0, index=pd.bdate_range("2020-01-01", periods=90)))
