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

_FORMATO = re.compile(r"^[0-9A-Za-z]{64}$")


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
    # Al copiar y pegar es fácil arrastrar espacios, saltos de línea o comillas
    token = token.strip().strip("'\"").strip()
    if not _FORMATO.match(token):
        raise TokenInvalido(
            f"El token del SIE tiene 64 letras y números, sin espacios; recibí {len(token)} "
            f"caracteres. Cópialo de nuevo, completo. Se genera en {URL_TOKEN}"
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


_AYUDA = (
    "Para configurarlo, ejecuta una sola vez en Python:\n\n"
    "    import banxicolab as sie\n"
    "    sie.guardar_token()\n\n"
    "Te lo pedirá sin mostrarlo en pantalla y lo guardará para las siguientes sesiones.\n"
    f"Si aún no tienes token, se genera gratis en {URL_TOKEN}"
)


def _preguntar() -> str:
    try:
        return getpass("Pega tu token del SIE (no se mostrará en pantalla): ")
    except (EOFError, KeyboardInterrupt):
        raise
    except Exception as error:  # p. ej. un notebook que se ejecuta sin nadie que responda
        raise TokenNoEncontrado(
            "No hay token del SIE configurado y este entorno no permite preguntarlo.\n" + _AYUDA
        ) from error


def _resolver(token: str | None = None, *, preguntar: bool = True) -> tuple[str, str]:
    """Devuelve ``(token, de dónde salió)``; lo segundo sirve para explicar errores."""
    if token:
        return _validar(token), "argumento token="
    for nombre in VARIABLES_DE_ENTORNO:
        if os.environ.get(nombre):
            return _validar(os.environ[nombre]), f"variable de entorno {nombre}"
    de_colab = _desde_colab()
    if de_colab:
        return _validar(de_colab), "Secrets de Colab"
    de_archivo = _desde_archivo()
    if de_archivo:
        return _validar(de_archivo), f"archivo {ruta_token()}"
    if preguntar and _es_interactivo():
        return _validar(_preguntar()), "lo que escribiste"
    raise TokenNoEncontrado("No hay token del SIE configurado.\n" + _AYUDA)


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
    return _resolver(token, preguntar=preguntar)[0]


def _verificar(token: str) -> bool:
    """Hace una consulta mínima al SIE. ``False`` si no hubo conexión para comprobarlo."""
    from .cliente import Banxico
    from .errores import ErrorDeConexion

    try:
        Banxico(token, reintentos=1, cache=False).oportuno("SF43718")
    except ErrorDeConexion:
        return False
    except TokenInvalido:
        raise TokenInvalido(
            "Banxico rechazó ese token, así que no se guardó. Cópialo de nuevo, completo, "
            f"o genera otro en {URL_TOKEN}"
        ) from None
    return True


def guardar_token(token: str | None = None, *, verificar: bool = True) -> Path:
    """Configura el token: lo pide, lo comprueba con Banxico y lo guarda.

    Es el paso que se hace **una sola vez** por computadora. El token queda en
    un archivo que solo tu usuario puede leer, y a partir de ahí la librería lo
    encuentra sola.

    Parameters
    ----------
    token : str, opcional
        Si se omite (lo recomendable) se pide con ``getpass``, de modo que
        nunca queda escrito en la celda del notebook ni en el historial.
    verificar : bool
        Hace una consulta de prueba antes de guardar. Si Banxico rechaza el
        token no se guarda nada y se lanza :class:`~banxicolab.TokenInvalido`.

    Returns
    -------
    pathlib.Path
        Ruta del archivo escrito.

    Examples
    --------
    >>> import banxicolab as sie
    >>> sie.guardar_token()                       # doctest: +SKIP
    Pega tu token del SIE (no se mostrará en pantalla): ········
    Token verificado con Banxico y guardado. Ya puedes descargar series.
    """
    if token is None:
        token = _preguntar()
    token = _validar(token)
    verificado = _verificar(token) if verificar else None
    ruta = ruta_token()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Se crea ya con permisos 600 para que el token nunca sea legible por otros
    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        archivo.write(token + "\n")
    os.chmod(ruta, 0o600)
    if verificado:
        print("Token verificado con Banxico y guardado. Ya puedes descargar series.")
    elif verificado is False:
        print("Token guardado. No hubo conexión para verificarlo con Banxico.")
    return ruta


def borrar_token() -> bool:
    """Elimina el archivo creado por :func:`guardar_token`. Devuelve si existía."""
    try:
        ruta_token().unlink()
        return True
    except FileNotFoundError:
        return False
