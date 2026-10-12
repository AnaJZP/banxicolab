"""Catálogo de alias para las series más usadas del SIE.

Permite escribir ``descargar("inpc")`` en lugar de recordar ``"SP1"``, pedir un
tema completo (``descargar(tema="tasas")``) y armar paneles mensuales sin
indicar cómo agregar cada serie. Todas las claves fueron contrastadas con el
catálogo público del SIE; ``tests/test_red.py`` repite esa verificación.

El campo ``agregacion`` indica cómo llevar la serie a frecuencia mensual:
``"ultimo"`` para precios y saldos (el promedio suaviza artificialmente la
volatilidad), ``"promedio"`` para tasas de interés y ``"suma"`` para flujos.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

import pandas as pd

from .errores import SerieNoEncontrada

_ID = re.compile(r"^S[A-Z]\d+$", re.IGNORECASE)


@dataclass(frozen=True)
class Serie:
    """Entrada del catálogo de alias."""

    id: str
    descripcion: str
    periodicidad: str
    unidad: str
    agregacion: str = "ultimo"
    tema: str = ""


TEMAS: dict[str, str] = {
    "precios": "Precios",
    "expectativas": "Expectativas de inflación (encuesta de Banxico, mediana)",
    "tipo_de_cambio": "Tipo de cambio",
    "tasas": "Tasas de interés",
    "actividad": "Actividad y salarios",
    "externo": "Sector externo",
    "dinero": "Agregados monetarios",
}

# (alias, clave SIE, descripción, periodicidad, unidad, agregación mensual)
_POR_TEMA: dict[str, list[tuple[str, str, str, str, str, str]]] = {
    "precios": [
        ("inpc", "SP1", "INPC, índice general", "Mensual", "Índice", "ultimo"),
        ("inpc_subyacente", "SP74625", "INPC subyacente", "Mensual", "Índice", "ultimo"),
        ("inpc_no_subyacente", "SP74630", "INPC no subyacente", "Mensual", "Índice", "ultimo"),
        ("inflacion_mensual", "SP30577", "INPC, variación mensual", "Mensual", "%", "ultimo"),
        ("inflacion_anual", "SP30578", "INPC, variación anual", "Mensual", "%", "ultimo"),
        (
            "inflacion_acumulada",
            "SP30579",
            "INPC, variación acumulada en el año",
            "Mensual",
            "%",
            "ultimo",
        ),
        (
            "inflacion_subyacente_anual",
            "SP74662",
            "Inflación subyacente anual",
            "Mensual",
            "%",
            "ultimo",
        ),
        (
            "inflacion_no_subyacente_anual",
            "SP74665",
            "Inflación no subyacente anual",
            "Mensual",
            "%",
            "ultimo",
        ),
        (
            "inpc_quincenal",
            "SP8664",
            "INPC quincenal, índice general",
            "Quincenal",
            "Índice",
            "promedio",
        ),
        (
            "inpc_subyacente_quincenal",
            "SP74632",
            "INPC subyacente quincenal",
            "Quincenal",
            "Índice",
            "promedio",
        ),
        (
            "inflacion_anual_quincenal",
            "SP74833",
            "INPC quincenal, variación anual",
            "Quincenal",
            "%",
            "ultimo",
        ),
        (
            "media_truncada",
            "SP74831",
            "Indicador de media truncada, general (anual)",
            "Mensual",
            "%",
            "ultimo",
        ),
        (
            "media_truncada_subyacente",
            "SP74832",
            "Indicador de media truncada, subyacente (anual)",
            "Mensual",
            "%",
            "ultimo",
        ),
        ("udis", "SP68257", "Valor de la UDI", "Diaria", "Pesos por UDI", "ultimo"),
    ],
    "expectativas": [
        (
            "expectativa_inflacion_12m",
            "SR14195",
            "Expectativa de inflación general, próximos 12 meses",
            "Mensual",
            "%",
            "ultimo",
        ),
        (
            "expectativa_inflacion_cierre",
            "SR14139",
            "Expectativa de inflación general, cierre del año en curso",
            "Mensual",
            "%",
            "ultimo",
        ),
        (
            "expectativa_inflacion_cierre_siguiente",
            "SR14146",
            "Expectativa de inflación general, cierre del año siguiente",
            "Mensual",
            "%",
            "ultimo",
        ),
    ],
    "tipo_de_cambio": [
        (
            "fix",
            "SF43718",
            "Tipo de cambio FIX, fecha de determinación",
            "Diaria",
            "MXN/USD",
            "ultimo",
        ),
        (
            "fix_liquidacion",
            "SF60653",
            "Tipo de cambio FIX, fecha de liquidación",
            "Diaria",
            "MXN/USD",
            "ultimo",
        ),
        (
            "fix_promedio_mensual",
            "SF17908",
            "Tipo de cambio FIX, promedio del mes",
            "Mensual",
            "MXN/USD",
            "ultimo",
        ),
        ("euro", "SF46410", "Pesos por euro", "Diaria", "MXN/EUR", "ultimo"),
    ],
    "tasas": [
        ("tasa_objetivo", "SF61745", "Tasa objetivo de Banxico", "Diaria", "% anual", "promedio"),
        (
            "tiie_fondeo",
            "SF331451",
            "TIIE de fondeo a un día hábil",
            "Diaria",
            "% anual",
            "promedio",
        ),
        ("tiie_28", "SF43783", "TIIE a 28 días", "Diaria", "% anual", "promedio"),
        (
            "cetes_28",
            "SF60633",
            "Cetes a 28 días, subasta semanal",
            "Diaria",
            "% anual",
            "promedio",
        ),
        (
            "cetes_91",
            "SF60634",
            "Cetes a 91 días, subasta semanal",
            "Diaria",
            "% anual",
            "promedio",
        ),
        (
            "bono_10a",
            "SF44071",
            "Bono M a 10 años, tasa de la subasta",
            "Diaria",
            "% anual",
            "promedio",
        ),
        (
            "udibono_10a",
            "SF43924",
            "Udibono a 10 años, tasa real de la subasta",
            "Diaria",
            "% anual",
            "promedio",
        ),
    ],
    "actividad": [
        ("igae", "SR17692", "IGAE base 2018, serie original", "Mensual", "Índice", "ultimo"),
        (
            "igae_desestacionalizado",
            "SR17693",
            "IGAE base 2018, serie desestacionalizada",
            "Mensual",
            "Índice",
            "ultimo",
        ),
        (
            "salario_minimo",
            "SL11298",
            "Salario mínimo general",
            "Mensual",
            "Pesos por día",
            "ultimo",
        ),
    ],
    "externo": [
        ("reservas", "SF43707", "Reserva internacional", "Diaria", "Millones de USD", "ultimo"),
        ("remesas", "SE27803", "Remesas familiares, total", "Mensual", "Millones de USD", "suma"),
    ],
    "dinero": [
        ("m1", "SF311408", "Agregado monetario M1", "Mensual", "Miles de pesos", "ultimo"),
        ("m2", "SF311418", "Agregado monetario M2", "Mensual", "Miles de pesos", "ultimo"),
    ],
}

CATALOGO: dict[str, Serie] = {
    alias: Serie(clave, descripcion, periodicidad, unidad, agregacion, tema)
    for tema, filas in _POR_TEMA.items()
    for alias, clave, descripcion, periodicidad, unidad, agregacion in filas
}
POR_ID: dict[str, Serie] = {serie.id: serie for serie in CATALOGO.values()}


def es_id(clave: str) -> bool:
    """``True`` si ``clave`` tiene forma de identificador del SIE (``SF43718``)."""
    return bool(_ID.match(clave.strip()))


def resolver(clave: str) -> tuple[str, str]:
    """Convierte un alias o un identificador en ``(id_serie, nombre_de_columna)``.

    Raises
    ------
    SerieNoEncontrada
        Si no es un identificador válido ni un alias del catálogo.
    """
    limpia = clave.strip()
    if limpia.lower() in CATALOGO:
        return CATALOGO[limpia.lower()].id, limpia.lower()
    if es_id(limpia):
        return limpia.upper(), limpia.upper()
    parecidas = difflib.get_close_matches(limpia.lower(), CATALOGO, n=3, cutoff=0.5)
    pista = f" ¿Quisiste decir {', '.join(map(repr, parecidas))}?" if parecidas else ""
    raise SerieNoEncontrada(
        f"{clave!r} no es un identificador del SIE (p. ej. 'SF43718') ni un alias conocido."
        f"{pista} Consulta banxicolab.catalogo() o usa banxicolab.buscar('texto')."
    )


def _sin_acentos(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in normal if not unicodedata.combining(c))


def de_tema(tema: str) -> list[str]:
    """Alias que pertenecen a un tema del catálogo."""
    clave = _sin_acentos(tema.strip()).replace(" ", "_")
    if clave not in _POR_TEMA:
        raise ValueError(f"Tema desconocido: {tema!r}. Opciones: {', '.join(TEMAS)}")
    return [fila[0] for fila in _POR_TEMA[clave]]


def catalogo(tema: str | None = None, *, buscar: str | None = None) -> pd.DataFrame:
    """Tabla con los alias disponibles.

    Parameters
    ----------
    tema : str, opcional
        Filtra por tema: ``"precios"``, ``"expectativas"``, ``"tipo_de_cambio"``,
        ``"tasas"``, ``"actividad"``, ``"externo"`` o ``"dinero"``.
    buscar : str, opcional
        Texto a buscar en el alias o la descripción, sin distinguir mayúsculas
        ni acentos (``buscar="inflacion"``).

    Examples
    --------
    >>> catalogo("tipo_de_cambio").index.tolist()
    ['fix', 'fix_liquidacion', 'fix_promedio_mensual', 'euro']
    >>> catalogo(buscar="cetes")["id"].tolist()
    ['SF60633', 'SF60634']
    """
    elegidos = set(de_tema(tema)) if tema else set(CATALOGO)
    aguja = _sin_acentos(buscar) if buscar else ""
    filas = [
        {
            "alias": alias,
            "id": s.id,
            "descripcion": s.descripcion,
            "tema": s.tema,
            "periodicidad": s.periodicidad,
            "unidad": s.unidad,
            "agregacion": s.agregacion,
        }
        for alias, s in CATALOGO.items()
        if alias in elegidos and aguja in _sin_acentos(f"{alias} {s.descripcion}")
    ]
    columnas = ["alias", "id", "descripcion", "tema", "periodicidad", "unidad", "agregacion"]
    return pd.DataFrame(filas, columns=columnas).set_index("alias")
