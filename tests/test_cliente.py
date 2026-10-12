import numpy as np
import pandas as pd
import pytest
import requests
from conftest import TOKEN, Respuesta, SesionFalsa

import banxicolab as sie
from banxicolab.cliente import _resolver_series


def serie_json(id_serie, datos, titulo="Título   con   espacios"):
    return {
        "idSerie": id_serie,
        "titulo": titulo,
        "datos": [{"fecha": f, "dato": d} for f, d in datos],
    }


def bmx(*series):
    return {"bmx": {"series": list(series)}}


def cliente(responder, **kw):
    sesion = SesionFalsa(responder)
    return sie.Banxico(TOKEN, sesion=sesion, **kw), sesion


def test_descarga_limpia_fechas_numeros_y_orden():
    # La API responde en otro orden, con N/E, comas de miles y fechas dd/mm/aaaa
    respuesta = bmx(
        serie_json("SF43707", [("02/01/2015", "193,045.50"), ("03/01/2015", "N/E")]),
        serie_json("SF43718", [("02/01/2015", "14.8290"), ("05/01/2015", "14.9469")]),
    )
    bmx_, sesion = cliente(lambda url, p: respuesta)
    df = bmx_.descargar({"SF43718": "FIX", "reservas": "Reservas"}, "2015-01-01", "2015-01-08")

    assert list(df.columns) == ["FIX", "Reservas"]
    assert df.index.name == "fecha"
    assert df.index[0] == pd.Timestamp("2015-01-02")  # 2 de enero, no 1 de febrero
    assert df.loc["2015-01-02", "Reservas"] == 193045.50
    assert pd.Timestamp("2015-01-03") not in df.index  # fila sin ningún dato
    assert df.dtypes.eq(float).all()
    assert df.attrs["series"]["FIX"] == {"id": "SF43718", "titulo": "Título con espacios"}
    assert sesion.llamadas[0]["url"].endswith("/series/SF43718,SF43707/datos/2015-01-01/2015-01-08")


def test_el_token_va_en_encabezado_y_nunca_en_la_url():
    bmx_, sesion = cliente(lambda url, p: bmx(serie_json("SP1", [("01/01/2020", "105.9")])))
    bmx_.descargar("inpc")
    llamada = sesion.llamadas[0]
    assert llamada["headers"]["Bmx-Token"] == TOKEN
    assert TOKEN not in llamada["url"] and TOKEN not in str(llamada["params"])
    assert TOKEN not in repr(bmx_) and repr(bmx_).endswith("c0de)")


def test_mas_de_20_series_se_parten_en_lotes():
    ids = [f"SF{i}" for i in range(1, 46)]

    def responder(url, p):
        pedidas = url.split("/series/")[1].split("/")[0].split(",")
        assert len(pedidas) <= 20
        return bmx(*[serie_json(i, [("01/01/2020", "1.0")]) for i in pedidas])

    bmx_, sesion = cliente(responder)
    df = bmx_.descargar(ids)
    assert len(sesion.llamadas) == 3 and list(df.columns) == ids


def test_cache_evita_repetir_la_consulta():
    bmx_, sesion = cliente(lambda url, p: bmx(serie_json("SP1", [("01/01/2020", "105.9")])))
    bmx_.descargar("inpc")
    bmx_.descargar("inpc")
    assert len(sesion.llamadas) == 1
    bmx_.limpiar_cache()
    bmx_.descargar("inpc")
    assert len(sesion.llamadas) == 2


def test_serie_sin_datos_avisa_y_todas_vacias_falla():
    respuesta = bmx(
        serie_json("SP1", [("01/01/2020", "105.9")]),
        {"idSerie": "SF43718", "titulo": "FIX"},
    )
    bmx_, _ = cliente(lambda url, p: respuesta)
    with pytest.warns(UserWarning, match="fix"):
        df = bmx_.descargar(["inpc", "fix"])
    assert df["fix"].isna().all() and df["inpc"].notna().all()

    vacio, _ = cliente(lambda url, p: bmx({"idSerie": "SP1", "titulo": "INPC"}))
    with pytest.raises(sie.SinDatos):
        vacio.descargar("inpc")


def test_serie_inexistente():
    bmx_, _ = cliente(lambda url, p: bmx(serie_json("SP1", [("01/01/2020", "1")])))
    with pytest.raises(sie.SerieNoEncontrada, match="SF999"):
        bmx_.descargar(["SP1", "SF999"])


def test_incremento_y_validaciones():
    bmx_, sesion = cliente(lambda url, p: bmx(serie_json("SP1", [("01/01/2020", "3.24")])))
    bmx_.descargar("inpc", incremento="anual")
    assert sesion.llamadas[0]["params"] == {"incremento": "PorcAnual"}
    with pytest.raises(ValueError):
        bmx_.descargar("inpc", incremento="semanal")
    with pytest.raises(ValueError, match="posterior"):
        bmx_.descargar("inpc", "2021-01-01", "2020-01-01")


def test_errores_del_sie():
    invalido, _ = cliente(
        lambda url, p: Respuesta({"error": {"mensaje": "Token inválido", "detalle": "x"}}, 400)
    )
    with pytest.raises(sie.TokenInvalido):
        invalido.descargar("inpc")

    limite = {"error": {"mensaje": "Límite de consultas superado.", "secondsToReset": 250}}
    bloqueado, _ = cliente(lambda url, p: Respuesta(limite, 400))
    with pytest.raises(sie.LimiteExcedido) as info:
        bloqueado.descargar("inpc")
    assert info.value.segundos == 250


def test_limite_corto_espera_y_reintenta():
    respuestas = iter(
        [
            Respuesta({"error": {"mensaje": "Límite superado", "secondsToReset": 5}}, 400),
            Respuesta(bmx(serie_json("SP1", [("01/01/2020", "105.9")]))),
        ]
    )
    bmx_, sesion = cliente(lambda url, p: next(respuestas))
    assert len(bmx_.descargar("inpc")) == 1 and len(sesion.llamadas) == 2


def test_reintenta_fallas_de_red_y_no_filtra_el_token():
    intentos = iter([requests.ConnectionError("caída"), Respuesta({}, 503)])
    ok = bmx(serie_json("SP1", [("01/01/2020", "105.9")]))
    bmx_, sesion = cliente(lambda url, p: next(intentos, ok))
    assert len(bmx_.descargar("inpc")) == 1 and len(sesion.llamadas) == 3

    caido, _ = cliente(lambda url, p: requests.ConnectionError("caída"), reintentos=1)
    with pytest.raises(sie.ErrorDeConexion) as info:
        caido.descargar("inpc")
    assert TOKEN not in str(info.value)


def test_metadatos_y_oportuno():
    meta = bmx(
        {
            "idSerie": "SF43718", "titulo": "FIX", "fechaInicio": "12/11/1991",
            "fechaFin": "29/09/2015", "periodicidad": "Diaria", "cifra": "Tipo de Cambio",
            "unidad": "Pesos por Dólar",
        }
    )  # fmt: skip
    bmx_, _ = cliente(lambda url, p: meta)
    tabla = bmx_.metadatos("fix")
    assert tabla.loc["fix", "inicio"] == pd.Timestamp("1991-11-12")
    assert tabla.loc["fix", "periodicidad"] == "Diaria"

    bmx_, sesion = cliente(lambda url, p: bmx(serie_json("SF43718", [("29/09/2015", "17.0771")])))
    ultimo = bmx_.oportuno("fix")
    assert ultimo.loc["fix", "dato"] == 17.0771
    assert sesion.llamadas[0]["url"].endswith("/datos/oportuno")


def test_buscar_no_usa_token():
    resultados = {"bmx": {"resultados": [
        {"idSerie": "SP74625", "texto": "INPC   Subyacente"},
        {"idSerie": "SP74625", "texto": "repetida"},
    ]}}  # fmt: skip
    sesion = SesionFalsa(lambda url, p: resultados)
    df = sie.Banxico(sesion=sesion).buscar("subyacente")
    assert df.to_dict("records") == [{"id": "SP74625", "descripcion": "INPC Subyacente"}]
    assert "Bmx-Token" not in sesion.llamadas[0]["headers"]

    vacio = sie.Banxico(sesion=SesionFalsa(lambda url, p: {"bmx": {}})).buscar("zzz")
    assert vacio.empty and list(vacio.columns) == ["id", "descripcion"]


def test_inflacion_del_cliente_recorta_al_inicio(inpc):
    datos = [(f.strftime("%d/%m/%Y"), f"{v:.6f}") for f, v in inpc.items()]
    bmx_, sesion = cliente(lambda url, p: bmx(serie_json("SP1", datos)))
    tabla = bmx_.inflacion("2018-01-01")
    assert tabla.index[0] == pd.Timestamp("2018-01-01")
    assert tabla["anual"].notna().all()
    assert "/datos/2016-12-01/" in sesion.llamadas[0]["url"]


def test_resolver_series():
    assert _resolver_series("fix") == {"SF43718": "fix"}
    assert _resolver_series(["sp1", "FIX"]) == {"SP1": "SP1", "SF43718": "fix"}
    assert _resolver_series({"SP1": "INPC"}) == {"SP1": "INPC"}
    with pytest.raises(sie.SerieNoEncontrada, match="inpc"):
        _resolver_series("inpcc")
    with pytest.raises(ValueError, match="repetidos"):
        _resolver_series({"SP1": "x", "SF43718": "x"})


def test_respuesta_parcial_se_vuelve_a_pedir():
    # El SIE a veces devuelve solo una parte de las series; no deben darse por inexistentes
    def responder(url, p):
        pedidas = url.split("/series/")[1].split("/")[0].split(",")
        if len(pedidas) == 3:
            pedidas = pedidas[:1]
        return bmx(*[serie_json(i, [("01/01/2020", "1.0")]) for i in pedidas])

    bmx_, sesion = cliente(responder)
    df = bmx_.descargar(["SF1", "SF2", "SF3"])
    assert list(df.columns) == ["SF1", "SF2", "SF3"] and len(sesion.llamadas) == 2


def test_404_es_serie_inexistente():
    bmx_, _ = cliente(lambda url, p: Respuesta(ValueError("no es JSON"), 404))
    with pytest.raises(sie.SerieNoEncontrada, match="SF999"):
        bmx_.descargar("SF999")


def test_variacion_anual_quincenal():
    fechas = pd.DatetimeIndex(
        [
            f
            for m in pd.date_range("2022-01-01", periods=30, freq="MS")
            for f in (m, m + pd.Timedelta(days=15))
        ]
    )
    s = pd.Series(100 * 1.002 ** np.arange(60), index=fechas)
    assert sie.frecuencia(s) == "Quincenal"
    assert np.allclose(sie.variacion_anual(s).dropna(), (1.002**24 - 1) * 100)


def test_catalogo_por_tema_y_busqueda():
    assert set(sie.catalogo()["tema"]) == set(sie.TEMAS)
    assert sie.catalogo("Tipo de cambio").index.tolist()[0] == "fix"
    assert "inflacion_anual" in sie.catalogo(buscar="INFLACIÓN").index
    assert sie.catalogo("tasas", buscar="cetes").index.tolist() == ["cetes_28", "cetes_91"]
    assert sie.catalogo(buscar="no existe").empty
    with pytest.raises(ValueError, match="precios"):
        sie.catalogo("clima")
    assert len({s.id for s in sie.CATALOGO.values()}) == len(sie.CATALOGO)  # sin claves repetidas


def test_descargar_un_tema():
    def responder(url, p):
        pedidas = url.split("/series/")[1].split("/")[0].split(",")
        return bmx(*[serie_json(i, [("01/01/2020", "1.0")]) for i in pedidas])

    bmx_, _ = cliente(responder)
    assert list(bmx_.descargar(tema="dinero").columns) == ["m1", "m2"]
    with pytest.raises(ValueError, match="no ambos"):
        bmx_.descargar("inpc", tema="dinero")
    with pytest.raises(ValueError, match="serie o un tema"):
        bmx_.descargar()


def test_panel_mensual_usa_la_regla_del_catalogo():
    dias = pd.bdate_range("2020-01-01", "2020-03-31")
    quincenas = [f"{d:02d}/{m:02d}/2020" for m in (1, 2, 3) for d in (1, 16)]
    series = {
        "SP1": [(f"01/{m:02d}/2020", str(100 + m)) for m in (1, 2, 3)],
        "SF43718": [(f.strftime("%d/%m/%Y"), str(18 + i / 100)) for i, f in enumerate(dias)],
        "SF61745": [(f.strftime("%d/%m/%Y"), "7.0" if f.month < 3 else "6.5") for f in dias],
        "SP8664": [(q, str(100 + i)) for i, q in enumerate(quincenas)],
        "SF99": [(f.strftime("%d/%m/%Y"), str(float(i))) for i, f in enumerate(dias)],
    }

    def responder(url, p):
        pedidas = url.split("/series/")[1].split("/")[0].split(",")
        return bmx(*[serie_json(i, series[i]) for i in pedidas])

    bmx_, sesion = cliente(responder)
    tabla = bmx_.panel(["inpc", "fix", "tasa_objetivo", "inpc_quincenal", "SF99"], "2020-01-01")

    assert list(tabla.index) == list(pd.date_range("2020-01-01", periods=3, freq="MS"))
    assert tabla["inpc"].tolist() == [101.0, 102.0, 103.0]
    enero = dias[dias.month == 1]
    assert tabla["fix"].iloc[0] == pytest.approx(18 + (len(enero) - 1) / 100)  # cierre del mes
    assert tabla["tasa_objetivo"].tolist() == [7.0, 7.0, 6.5]  # promedio
    assert tabla["inpc_quincenal"].tolist() == [100.5, 102.5, 104.5]  # promedio de dos quincenas
    assert tabla["SF99"].iloc[0] == len(enero) - 1  # fuera del catálogo: último
    assert tabla.attrs["agregacion"]["tasa_objetivo"] == "promedio"
    assert len(sesion.llamadas) == 1

    propia = bmx_.panel({"SF99": "x"}, "2020-01-01", como={"x": "promedio"})
    assert propia["x"].iloc[0] == pytest.approx((len(enero) - 1) / 2)
    with pytest.raises(ValueError, match="no se pidieron"):
        bmx_.panel("fix", como={"otra": "promedio"})


def test_el_readme_lista_todo_el_catalogo():
    from pathlib import Path

    readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
    for alias, entrada in sie.CATALOGO.items():
        assert f"| `{alias}` | `{entrada.id}` |" in readme, alias


def test_token_rechazado_dice_de_donde_salio_y_no_se_queda_pegado(monkeypatch):
    malo, bueno = "b" * 64, "c" * 64

    def responder(url, p):
        return Respuesta({"error": {"mensaje": "Token inválido", "detalle": "x"}}, 400)

    sesion = SesionFalsa(responder)
    monkeypatch.setenv("BANXICO_TOKEN", malo)
    bmx_ = sie.Banxico(sesion=sesion)
    with pytest.raises(sie.TokenInvalido, match="variable de entorno BANXICO_TOKEN") as info:
        bmx_.descargar("inpc")
    assert malo not in str(info.value) and "guardar_token" in str(info.value)

    # Al corregirlo, el mismo cliente toma el nuevo sin reiniciar la sesión
    monkeypatch.setenv("BANXICO_TOKEN", bueno)
    sesion.responder = lambda url, p: bmx(serie_json("SP1", [("01/01/2020", "105.9")]))
    assert len(bmx_.descargar("inpc")) == 1
    assert sesion.llamadas[-1]["headers"]["Bmx-Token"] == bueno
