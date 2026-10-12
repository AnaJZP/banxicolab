import os
import stat

import pytest
from conftest import TOKEN

import banxicolab as sie
from banxicolab import token as modulo


def test_orden_de_busqueda(monkeypatch):
    with pytest.raises(sie.TokenNoEncontrado, match="BANXICO_TOKEN"):
        sie.obtener_token(preguntar=False)

    sie.guardar_token("b" * 64)
    assert sie.obtener_token(preguntar=False) == "b" * 64  # archivo
    monkeypatch.setenv("BMX_TOKEN", "c" * 64)
    assert sie.obtener_token(preguntar=False) == "c" * 64  # el entorno gana al archivo
    assert sie.obtener_token(f"  {TOKEN}\n") == TOKEN  # el argumento gana a todo


def test_archivo_solo_legible_por_el_usuario():
    ruta = sie.guardar_token(TOKEN)
    if os.name != "nt":
        assert stat.S_IMODE(ruta.stat().st_mode) == 0o600
    assert sie.borrar_token() is True
    assert sie.borrar_token() is False


def test_guardar_pide_con_getpass(monkeypatch):
    monkeypatch.setattr(modulo, "getpass", lambda mensaje: TOKEN)
    assert sie.guardar_token().read_text().strip() == TOKEN


def test_formato_invalido_no_repite_el_token():
    malo = "esto no es un token"
    with pytest.raises(sie.TokenInvalido) as info:
        sie.obtener_token(malo)
    assert malo not in str(info.value)


def test_enmascarar():
    assert modulo.enmascarar(TOKEN) == "••••c0de"
    assert modulo.enmascarar("abc") == "••••"
