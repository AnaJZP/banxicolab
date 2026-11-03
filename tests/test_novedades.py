"""Pruebas de la versión 0.4: caché en disco, anticipación, contribuciones, curva y gráficas."""

import os
import time
import warnings

import matplotlib
import numpy as np
import pandas as pd
import pytest
from conftest import TOKEN, SesionFalsa

import banxicolab as sie
from banxicolab import renta_fija

matplotlib.use("Agg")


def bmx_json(*series):
    return {"bmx": {"series": list(series)}}


def una_serie(id_serie, datos):
    return {
        "idSerie": id_serie,
        "titulo": id_serie,
        "datos": [{"fecha": f, "dato": d} for f, d in datos],
    }


# ── Caché en disco ───────────────────────────────────────────────────────────


def test_cache_en_disco_sobrevive_a_un_cliente_nuevo(tmp_path):
    respuesta = bmx_json(una_serie("SP1", [("01/01/2020", "105.9")]))
    primero = SesionFalsa(lambda url, p: respuesta)
    sie.Banxico(TOKEN, sesion=primero, cache="disco", carpeta_cache=tmp_path).descargar("inpc")
    assert len(primero.llamadas) == 1 and len(list(tmp_path.glob("*.json"))) == 1
    assert TOKEN not in next(tmp_path.glob("*.json")).read_text()  # el token nunca se guarda

    segundo = SesionFalsa(lambda url, p: respuesta)
    otro = sie.Banxico(TOKEN, sesion=segundo, cache="disco", carpeta_cache=tmp_path)
    assert otro.descargar("inpc")["inpc"].iloc[0] == 105.9
    assert len(segundo.llamadas) == 0

    otro.limpiar_cache()
    assert not list(tmp_path.glob("*.json"))


def test_cache_en_disco_caduca_y_no_guarda_el_ultimo_dato(tmp_path):
    respuesta = bmx_json(una_serie("SF43718", [("01/01/2020", "18.5")]))
    sesion = SesionFalsa(lambda url, p: respuesta)
    sie.Banxico(TOKEN, sesion=sesion, cache="disco", carpeta_cache=tmp_path).descargar("fix")
    viejo = time.time() - 13 * 3600
    for archivo in tmp_path.glob("*.json"):
        os.utime(archivo, (viejo, viejo))
    nuevo = sie.Banxico(TOKEN, sesion=sesion, cache="disco", carpeta_cache=tmp_path)
    nuevo.descargar("fix")
    assert len(sesion.llamadas) == 2  # la guardada ya había caducado (12 horas)

    nuevo.oportuno("fix")
    assert len(list(tmp_path.glob("*.json"))) == 1  # el último dato no se escribe en disco
    with pytest.raises(ValueError):
        sie.Banxico(cache="nube")


def test_configurar_reemplaza_el_cliente_compartido(tmp_path):
    from banxicolab import cliente

    anterior = cliente._compartido
    try:
        bmx = sie.configurar(cache="disco", carpeta_cache=tmp_path, vigencia_cache=1)
        assert cliente._compartido is bmx and bmx._disco.vigencia == 3600
    finally:
        cliente._compartido = anterior


# ── Anticipar la inflación con la primera quincena ───────────────────────────


def indice_quincenal(meses=60, completo=False):
    """Primera quincena crece 0.3 % al mes; la segunda queda 0.1 % arriba (o 0.4 % en junio)."""
    fechas, valores = [], []
    nivel = 100.0
    for mes in pd.date_range("2018-01-01", periods=meses, freq="MS"):
        nivel *= 1.003
        fechas.append(mes)
        valores.append(nivel)
        if completo or mes != pd.date_range("2018-01-01", periods=meses, freq="MS")[-1]:
            fechas.append(mes + pd.Timedelta(days=15))
            valores.append(nivel * (1.004 if mes.month == 6 else 1.001))
    return pd.Series(valores, index=pd.DatetimeIndex(fechas))


def test_anticipa_con_el_patron_del_mismo_mes():
    q = indice_quincenal()
    tabla = sie.anticipar_inflacion(q)
    assert len(tabla) == 1 and tabla.index[0] == pd.Timestamp("2022-12-01")
    q1 = q.iloc[-1]
    mensual_real = (q1 * 1.0005) / ((q.iloc[-3] + q.iloc[-2]) / 2) - 1  # q2 = q1 · 1.001
    assert tabla["mensual"].iloc[0] == pytest.approx(mensual_real * 100)
    assert tabla["mensual_inf"].iloc[0] <= tabla["mensual"].iloc[0] <= tabla["mensual_sup"].iloc[0]


def test_anticipar_historial_y_validaciones():
    q = indice_quincenal(completo=True)
    with pytest.raises(ValueError, match="ya tiene sus dos quincenas"):
        sie.anticipar_inflacion(q)
    historial = sie.anticipar_inflacion(q, historial=True)
    assert {"mensual_observada", "anual_observada"} <= set(historial.columns)
    # Con un patrón estacional exacto, la estimación coincide con lo observado
    assert np.allclose(historial["mensual"], historial["mensual_observada"])
    assert np.allclose(historial["anual"], historial["anual_observada"])
    with pytest.raises(ValueError, match="quincenal"):
        sie.anticipar_inflacion(q.resample("MS").last())


# ── Contribuciones ───────────────────────────────────────────────────────────


def componentes_sinteticos(cambio="2021-01-01"):
    rng = np.random.default_rng(3)
    fechas = pd.date_range("2018-01-01", periods=60, freq="MS")
    comp = pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0.003, 0.004, (60, 3)), axis=0)),
        index=fechas,
        columns=["a", "b", "c"],
    )
    antes = comp @ np.array([0.5, 0.3, 0.2])
    # Cambio de ponderadores encadenado: el índice nuevo empata con el viejo en el mes de enlace
    enlace = pd.Timestamp(cambio) - pd.DateOffset(months=1)
    pesos = np.array([0.2, 0.3, 0.5])
    nuevo = antes[enlace] * (comp / comp.loc[enlace]) @ pesos
    total = antes.where(fechas < pd.Timestamp(cambio), nuevo)
    return total, comp


def test_contribuciones_suman_la_inflacion_aun_con_cambio_de_ponderadores():
    total, comp = componentes_sinteticos()
    tabla = sie.contribuciones(total, comp, 12, cambios=["2021-01-01"])
    assert list(tabla.columns) == ["a", "b", "c", "total", "residuo"]
    assert np.allclose(tabla["total"], (total / total.shift(12) - 1).dropna() * 100)
    assert tabla["residuo"].abs().max() < 1e-9  # incluso en los meses que cruzan el cambio
    mensual = sie.contribuciones(total, comp, 1, cambios=["2021-01-01"])
    assert mensual["residuo"].abs().max() < 1e-9


def test_contribuciones_avisan_si_falta_un_cambio_de_ponderadores():
    total, comp = componentes_sinteticos()
    with pytest.warns(UserWarning, match="ponderadores"):
        tabla = sie.contribuciones(total, comp, 12, cambios=[])
    assert tabla["residuo"].abs().max() > 1e-6


# ── Curva de rendimientos ────────────────────────────────────────────────────


def test_nelson_siegel_recupera_la_curva():
    plazos = np.array([0.08, 0.25, 0.5, 1, 3, 5, 9, 16, 28])
    verdad = renta_fija.CurvaNS(9.5, -3.0, 1.5, 2.0, 0.0)
    curva = sie.nelson_siegel(plazos, verdad(plazos))
    assert np.allclose(curva(plazos), verdad(plazos), atol=1e-3)
    assert isinstance(curva(10), float) and curva.error < 1e-3
    assert set(curva.parametros()) == {"nivel", "pendiente", "curvatura", "lam", "error"}
    with pytest.raises(ValueError, match="4 plazos"):
        sie.nelson_siegel([1, 2, 3], [5, 6, 7])


def test_puntos_de_curva_desde_el_vector():
    dia = pd.to_datetime(["2026-10-30"])
    datos = {}
    for nombre in renta_fija.VECTOR_CETES:
        dias = int(nombre.split()[1])
        datos[f"{nombre}|tasa"], datos[f"{nombre}|dias"] = [7.0], [dias]
    for nombre in renta_fija.VECTOR_BONOS:
        datos[f"{nombre}|precio"] = [sie.precio_bono(9.0, 8.0, 3640)]
        datos[f"{nombre}|cupon"], datos[f"{nombre}|dias"] = [8.0], [3640]
    tabla = pd.DataFrame(datos, index=dia)
    tabla.iloc[0, tabla.columns.get_loc("Bono M 5-7 años|precio")] = np.nan  # rango sin precio
    puntos = renta_fija.puntos_de_curva(tabla)
    assert len(puntos) == 4 + 5 and puntos["plazo"].is_monotonic_increasing
    bonos = puntos[puntos["titulo"].str.startswith("Bono")]
    assert np.allclose(bonos["rendimiento"], 9.0)


def test_etiquetas_de_plazo():
    from banxicolab.cliente import _etiqueta_plazo

    assert [_etiqueta_plazo(p) for p in (0.25, 0.5, 1, 2.5, 10)] == [
        "3m",
        "6m",
        "1a",
        "2.5a",
        "10a",
    ]


# ── Gráficas ─────────────────────────────────────────────────────────────────


def test_graficar_cita_la_fuente_y_dibuja_la_meta():
    datos = pd.DataFrame(
        {"General": [3.5, 4.0, 3.2], "Subyacente": [3.8, 3.9, 3.7]},
        index=pd.date_range("2026-01-01", periods=3, freq="MS"),
    )
    datos.attrs["series"] = {"General": {"id": "SP1"}, "Subyacente": {"id": "SP74625"}}
    ax = sie.graficar(datos, "Inflación", unidad="%", meta=True)
    textos = [t.get_text() for t in ax.texts]
    assert any("SP1, SP74625" in t for t in textos)
    assert ax.get_title(loc="left") == "Inflación" and ax.get_ylabel() == "%"
    assert len(ax.lines) == 3  # dos series y la línea de la meta
    assert [linea.get_color() for linea in ax.lines[:2]] == sie.PALETA[:2]

    sin_fuente = sie.graficar(datos["General"], fuente=False)
    assert not sin_fuente.texts
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        sie.graficar(datos, fuente="Fuente: propia", cero=True)
    import matplotlib.pyplot as plt

    plt.close("all")
