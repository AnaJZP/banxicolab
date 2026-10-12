"""Importación tardía de dependencias opcionales, con un mensaje útil si faltan."""

from __future__ import annotations


def statsmodels_tsa():
    try:
        import statsmodels.tsa.seasonal  # noqa: F401
        import statsmodels.tsa.stattools  # noqa: F401
        from statsmodels import tsa
    except ImportError as error:
        raise ImportError(
            "Esta función necesita statsmodels. Instálalo con: pip install statsmodels"
        ) from error
    return tsa
