"""Pruebas contra Banxico. No corren por omisión:

pytest -m red      # catálogo público, sin token
pytest -m token    # requiere BANXICO_TOKEN_PRUEBA con un token real
"""

import os

import numpy as np
import pytest

import banxicolab as sie


@pytest.mark.red
def test_los_alias_del_catalogo_existen_y_coinciden():
    bmx = sie.Banxico()
    for alias, entrada in sie.CATALOGO.items():
        ficha = bmx.info(alias)
        assert ficha["id"] == entrada.id
        assert ficha["periodicidad"] == entrada.periodicidad, alias


@pytest.mark.red
def test_buscar():
    assert "SP74625" in set(sie.Banxico().buscar("subyacente", limite=None)["id"])


@pytest.mark.token
def test_descarga_real():
    token = os.environ.get("BANXICO_TOKEN_PRUEBA")
    if not token:
        pytest.skip("define BANXICO_TOKEN_PRUEBA")
    bmx = sie.Banxico(token)
    df = bmx.descargar(["inpc", "fix", "reservas"], "2020-01-01", "2020-12-31")
    assert df["inpc"].count() == 12 and df["fix"].count() > 240
    assert df["reservas"].min() > 100_000  # las comas de miles se interpretaron bien
    assert bmx.inflacion("2020-01-01", "2020-12-31")["anual"].notna().all()


@pytest.mark.token
def test_novedades_con_datos_reales():
    token = os.environ.get("BANXICO_TOKEN_PRUEBA")
    if not token:
        pytest.skip("define BANXICO_TOKEN_PRUEBA")
    bmx = sie.Banxico(token)
    contribuciones = bmx.contribuciones_inflacion("2020-01-01")
    assert contribuciones["residuo"].abs().max() < 0.05
    historial = bmx.anticipar_inflacion(historial=True).loc["2015":]
    error = historial["mensual"] - historial["mensual_observada"]
    assert np.sqrt((error**2).mean()) < 0.15
    curva = bmx.curva_rendimientos()
    assert len(curva) >= 4 and curva.attrs["curva"].error < 0.3
