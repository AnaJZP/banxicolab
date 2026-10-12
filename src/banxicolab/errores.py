"""Excepciones de la librería.

Todas heredan de :class:`BanxicoError`, así que basta un solo ``except`` para
atrapar cualquier fallo relacionado con el SIE.
"""

from __future__ import annotations


class BanxicoError(Exception):
    """Error base de la librería."""


class TokenNoEncontrado(BanxicoError):
    """No se encontró un token en ninguna de las fuentes soportadas."""


class TokenInvalido(BanxicoError):
    """El SIE rechazó el token (o tiene un formato imposible)."""


class LimiteExcedido(BanxicoError):
    """Se superó el límite de consultas del token.

    Attributes
    ----------
    segundos : int | None
        Segundos que faltan para que Banxico desbloquee el token.
    """

    def __init__(self, mensaje: str, segundos: int | None = None):
        super().__init__(mensaje)
        self.segundos = segundos


class SerieNoEncontrada(BanxicoError):
    """La clave no existe en el SIE ni en el catálogo de alias."""


class SinDatos(BanxicoError):
    """La consulta fue válida pero no devolvió ninguna observación."""


class ErrorDeConexion(BanxicoError):
    """No fue posible comunicarse con el servidor del SIE."""
