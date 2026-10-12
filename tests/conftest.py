import numpy as np
import pandas as pd
import pytest

TOKEN = "a" * 60 + "c0de"


class Respuesta:
    def __init__(self, cuerpo, status=200):
        self._cuerpo, self.status_code = cuerpo, status

    def json(self):
        if isinstance(self._cuerpo, Exception):
            raise self._cuerpo
        return self._cuerpo


class SesionFalsa:
    """Sustituye a requests.Session: responde con una función y registra las llamadas."""

    def __init__(self, responder):
        self.responder = responder
        self.llamadas = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.llamadas.append({"url": url, "params": params, "headers": headers})
        resultado = self.responder(url, params)
        if isinstance(resultado, Exception):
            raise resultado
        return resultado if isinstance(resultado, Respuesta) else Respuesta(resultado)


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch, tmp_path):
    """Ninguna prueba debe ver (ni tocar) el token real de quien las corre."""
    for variable in ("BANXICO_TOKEN", "BMX_TOKEN"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("banxicolab.token._verificar", lambda token: True)


@pytest.fixture
def inpc():
    """Índice mensual sintético: 0.5 % mensual con un patrón estacional."""
    fechas = pd.date_range("2015-01-01", periods=96, freq="MS")
    tendencia = 100 * 1.005 ** np.arange(96)
    estacional = 1 + 0.01 * np.sin(2 * np.pi * fechas.month / 12)
    return pd.Series(tendencia * estacional, index=fechas, name="inpc")
