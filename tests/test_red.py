"""Pruebas contra Banxico. No corren por omisión:

pytest -m red      # catálogo público, sin token
pytest -m token    # requiere BANXICO_TOKEN_PRUEBA con un token real
"""

import os

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
