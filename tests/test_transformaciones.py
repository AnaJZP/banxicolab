import numpy as np
import pandas as pd
import pytest

import banxicolab as sie

P = pd.Series(
    [100.0, 108.0, 102.0, 115.0, 110.0], index=pd.date_range("2020-01-01", periods=5, freq="MS")
)


def test_indice_y_cambio_de_base():
    base0 = sie.indice_base(P)
    assert base0.iloc[0] == 100
    base2 = sie.cambiar_base(base0, "2020-03-01")
    assert np.allclose(base2, 100 * P / P.iloc[2])  # no hace falta la serie original
    assert np.isclose(base0.iloc[3] / base0.iloc[1], base2.iloc[3] / base2.iloc[1])
    assert sie.indice_base(P, "2020-03-20").iloc[2] == 100  # fecha inexistente → dato previo
    with pytest.raises(ValueError):
        sie.indice_base(P, "2019-01-01")


def test_indice_en_dataframe_con_inicios_distintos():
    df = pd.DataFrame({"a": P, "b": P.shift(1)})
    resultado = sie.indice_base(df)
    assert resultado["a"].iloc[0] == 100 and resultado["b"].iloc[1] == 100


def test_empalme_reconstruye_la_serie(inpc):
    viejo = sie.indice_base(inpc.loc[:"2018-06-01"], "2015-01-01")
    nuevo = sie.indice_base(inpc.loc["2018-01-01":], "2018-01-01")
    empalmada = sie.empalmar(viejo, nuevo)
    assert np.allclose(empalmada, sie.indice_base(inpc, "2018-01-01"))
    assert empalmada.index.is_unique
    with pytest.raises(ValueError):
        sie.empalmar(viejo.loc[:"2017-01-01"], nuevo)


def test_variaciones():
    simple, log = sie.variacion(P), sie.variacion(P, log=True)
    assert np.isclose(simple.iloc[1], 8.0)
    assert np.isclose(log.sum(), np.log(110 / 100) * 100)  # aditividad temporal
    assert np.isclose(sie.variacion(P, porcentaje=False).iloc[1], 0.08)


def test_variacion_no_rellena_faltantes():
    s = P.copy()
    s.iloc[2] = np.nan
    assert sie.variacion(s).iloc[2:4].isna().all()


def test_variacion_anual_detecta_frecuencia(inpc):
    assert np.allclose(sie.variacion_anual(inpc).dropna(), (1.005**12 - 1) * 100)
    trimestral = inpc.resample("QS").last()
    assert sie.variacion_anual(trimestral).first_valid_index() == trimestral.index[4]
    diaria = pd.Series(1.0, index=pd.bdate_range("2020-01-01", periods=30))
    with pytest.raises(ValueError, match="a_mensual"):
        sie.variacion_anual(diaria)


def test_anualizar():
    assert np.isclose(sie.anualizar(0.5), (1.005**12 - 1) * 100)
    assert np.isclose(sie.anualizar(0.02, 4, porcentaje=False), 1.02**4 - 1)


def test_deflactar_y_poder_adquisitivo():
    idx = pd.date_range("2020-01-01", periods=3, freq="YS")
    salario = pd.Series([5000.0, 5150.0, 5400.0], index=idx)
    precios = pd.Series([100.0, 104.0, 110.0], index=idx)
    real = sie.deflactar(salario, precios)
    assert np.isclose((real.iloc[-1] / real.iloc[0] - 1) * 100, -1.8182, atol=1e-4)
    assert np.isclose(sie.deflactar(salario, precios, base="2022-01-01").iloc[-1], 5400)
    assert sie.a_pesos_de(1000, "2020-01-01", "2022-01-01", precios) == pytest.approx(1100)
    df = sie.deflactar(pd.DataFrame({"a": salario, "b": salario * 2}), precios)
    assert np.allclose(df["b"], 2 * real)


def test_tasa_real_fisher():
    assert sie.tasa_real(10.0, 6.0) == pytest.approx(3.7736, abs=1e-4)
    assert sie.tasa_real(10.0, 6.0, exacta=False) == 4.0


def test_escalamientos_y_fuga_de_informacion():
    z = sie.estandarizar(P)
    assert np.isclose(z.mean(), 0) and np.isclose(z.std(), 1)
    assert sie.min_max(P).agg(["min", "max"]).tolist() == [0, 1]
    assert np.isclose(sie.escalar_robusto(P).median(), 0)
    assert np.isclose(z.skew(), P.skew())  # la forma de la distribución no cambia

    entrenamiento, prueba = P.iloc[:3], P.iloc[3:]
    sin_fuga = sie.estandarizar(prueba, referencia=entrenamiento)
    assert np.allclose(sin_fuga, (prueba - entrenamiento.mean()) / entrenamiento.std())
    assert sie.min_max(prueba, referencia=entrenamiento).max() > 1  # el futuro salió del rango


def test_a_mensual():
    dias = pd.bdate_range("2020-01-01", "2020-03-31")
    df = pd.DataFrame({"fix": np.arange(len(dias), dtype=float), "tasa": 7.0}, index=dias)
    mensual = sie.a_mensual(df, {"fix": "ultimo", "tasa": "promedio"})
    assert list(mensual.index) == list(pd.date_range("2020-01-01", periods=3, freq="MS"))
    assert mensual["fix"].iloc[0] == df.loc["2020-01", "fix"].iloc[-1]
    assert (mensual["tasa"] == 7).all()
    assert sie.a_mensual(df["fix"], "promedio").iloc[0] == df.loc["2020-01", "fix"].mean()
    with pytest.raises(ValueError):
        sie.a_mensual(df, {"fix": "ultimo"})
    with pytest.raises(ValueError):
        sie.a_mensual(df, "mediana")


def test_frecuencia(inpc):
    assert sie.frecuencia(inpc) == "Mensual"
    assert (
        sie.frecuencia(pd.Series(1.0, index=pd.bdate_range("2020-01-01", periods=30))) == "Diaria"
    )
    assert sie.frecuencia(inpc.resample("QS").last()) == "Trimestral"
    assert sie.frecuencia(inpc.resample("YS").last()) == "Anual"


def test_desestacionalizar_quita_el_patron(inpc):
    pytest.importorskip("statsmodels")
    ajustada = sie.desestacionalizar(inpc)
    perfil = lambda s: sie.variacion(s).groupby(s.index.month).mean()  # noqa: E731
    assert perfil(ajustada).std() < perfil(inpc).std() / 5
