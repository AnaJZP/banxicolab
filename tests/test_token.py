import os
import stat

import pytest
from conftest import TOKEN

import banxicolab as sie
from banxicolab import token as modulo


def test_orden_de_busqueda(monkeypatch):
    with pytest.raises(sie.TokenNoEncontrado, match="guardar_token"):
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


def test_guardar_no_escribe_un_token_que_banxico_rechaza(monkeypatch, capsys):
    def rechazar(token):
        raise sie.TokenInvalido("rechazado")

    monkeypatch.setattr(modulo, "_verificar", rechazar)
    with pytest.raises(sie.TokenInvalido):
        sie.guardar_token(TOKEN)
    assert not modulo.ruta_token().exists()

    monkeypatch.setattr(modulo, "_verificar", lambda token: False)  # sin conexión: se guarda
    assert sie.guardar_token(TOKEN).exists()
    assert "No hubo conexión" in capsys.readouterr().out

    monkeypatch.setattr(modulo, "_verificar", lambda token: True)
    sie.guardar_token(TOKEN)
    assert "verificado" in capsys.readouterr().out
    assert TOKEN not in capsys.readouterr().out


def test_tolera_comillas_y_espacios_al_pegar():
    assert sie.obtener_token(f' "{TOKEN}" \n') == TOKEN


def test_token_incompleto_dice_cuantos_caracteres_llegaron():
    with pytest.raises(sie.TokenInvalido, match="recibí 40 caracteres"):
        sie.guardar_token(TOKEN[:40])
    assert not modulo.ruta_token().exists()


def test_sin_token_y_sin_forma_de_preguntar_explica_que_hacer(monkeypatch):
    def sin_entrada(mensaje):
        raise RuntimeError("getpass was called, but this frontend does not support input requests")

    monkeypatch.setattr(modulo, "getpass", sin_entrada)
    monkeypatch.setattr(modulo, "_es_interactivo", lambda: True)
    with pytest.raises(sie.TokenNoEncontrado, match=r"sie\.guardar_token\(\)"):
        sie.obtener_token()
