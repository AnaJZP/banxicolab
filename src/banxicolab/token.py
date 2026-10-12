"""Manejo del token del SIE sin escribirlo nunca en el código.

El token se busca, en este orden:

1. El argumento ``token=`` (útil en pruebas; evítalo en notebooks compartidos).
2. Las variables de entorno ``BANXICO_TOKEN`` o ``BMX_TOKEN``.
3. Los *Secrets* de Google Colab con esos mismos nombres.
4. El archivo local creado por :func:`guardar_token` (permisos ``600``).
5. Una pregunta interactiva con ``getpass`` (no se muestra en pantalla).
"""

from __future__ import annotations

import os
import re
import sys
from getpass import getpass
from pathlib import Path

from .errores import TokenInvalido, TokenNoEncontrado

VARIABLES_DE_ENTORNO = ("BANXICO_TOKEN", "BMX_TOKEN")
URL_TOKEN = "https://www.banxico.org.mx/SieAPIRest/service/v1/token"

_FORMATO = re.compile(r"^[0-9A-Za-z]{16,128}$")


def ruta_token() -> Path:
    """Ruta del archivo donde :func:`guardar_token` deja el token."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "banxicolab" / "token"


def enmascarar(token: str) -> str:
    """Versión del token segura para imprimir: ``'••••c0de'``."""
    return "••••" + token[-4:] if len(token) >= 8 else "••••"


def _validar(token: str) -> str:
    token = token.strip()
    if not _FORMATO.match(token):
        raise TokenInvalido(
            "El token no tiene el formato esperado (solo letras y números, sin espacios). "
            f"Puedes generar uno en {URL_TOKEN}"
        )
    return token


def _desde_colab() -> str | None:
    if "google.colab" not in sys.modules:
        return None
    try:
        from google.colab import userdata  # type: ignore[import-not-found]
    except Exception:
        return None
    for nombre in VARIABLES_DE_ENTORNO:
        try:
            valor = userdata.get(nombre)
        except Exception:  # el secreto no existe o el notebook no tiene acceso
            continue
        if valor:
            return valor
    return None


def _desde_archivo() -> str | None:
    try:
        return ruta_token().read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _es_interactivo() -> bool:
    if "ipykernel" in sys.modules or "google.colab" in sys.modules:
        return True
    return bool(sys.stdin and sys.stdin.isatty())


def obtener_token(token: str | None = None, *, preguntar: bool = True) -> str:
    """Resuelve el token siguiendo el orden descrito en el módulo.

    Parameters
    ----------
    token : str, opcional
        Token explícito. Si se da, solo se valida su formato.
    preguntar : bool
        Si no se encuentra en ninguna fuente y la sesión es interactiva,
        pedirlo con ``getpass``.

    Raises
    ------
    TokenNoEncontrado
        Si no hay token y no se puede preguntar.
    TokenInvalido
        Si el token encontrado tiene un formato imposible.
    """
    if token:
        return _validar(token)
    for nombre in VARIABLES_DE_ENTORNO:
        if os.environ.get(nombre):
            return _validar(os.environ[nombre])
    encontrado = _desde_colab() or _desde_archivo()
    if encontrado:
        return _validar(encontrado)
    if preguntar and _es_interactivo():
        return _validar(getpass("Pega tu token del SIE (no se mostrará en pantalla): "))
    raise TokenNoEncontrado(
        "No encontré un token del SIE. Opciones:\n"
        "  • define la variable de entorno BANXICO_TOKEN,\n"
        "  • ejecuta `banxicolab token` (o banxicolab.guardar_token()) una sola vez,\n"
        "  • en Colab, agrégalo en Secrets con el nombre BANXICO_TOKEN.\n"
        f"Si aún no tienes uno, se genera gratis en {URL_TOKEN}"
    )


def guardar_token(token: str | None = None) -> Path:
    """Guarda el token en un archivo local que solo tu usuario puede leer.

    Si no se pasa ``token`` se pide con ``getpass``, de modo que nunca queda
    en el historial de la terminal ni en la celda del notebook.

    Returns
    -------
    pathlib.Path
        Ruta del archivo escrito.
    """
    if token is None:
        token = getpass("Pega tu token del SIE (no se mostrará en pantalla): ")
    token = _validar(token)
    ruta = ruta_token()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Se crea ya con permisos 600 para que el token nunca sea legible por otros
    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        archivo.write(token + "\n")
    os.chmod(ruta, 0o600)
    return ruta


def borrar_token() -> bool:
    """Elimina el archivo creado por :func:`guardar_token`. Devuelve si existía."""
    try:
        ruta_token().unlink()
        return True
    except FileNotFoundError:
        return False
