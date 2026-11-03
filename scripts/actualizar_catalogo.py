"""Regenera las tablas del catálogo en README.md y docs/catalogo.md.

Uso:  python scripts/actualizar_catalogo.py
"""

from pathlib import Path

import banxicolab as sie
from banxicolab.alias import TEMAS

RAIZ = Path(__file__).resolve().parents[1]


def tablas(nivel: int) -> str:
    catalogo = sie.catalogo().reset_index()
    partes = []
    for tema, titulo in TEMAS.items():
        partes += [f"{'#' * nivel} {titulo}\n", f'`tema="{tema}"`\n']
        partes += ["| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |"]
        partes += ["|---|---|---|---|---|---|"]
        for fila in catalogo[catalogo["tema"] == tema].itertuples():
            partes.append(
                f"| `{fila.alias}` | `{fila.id}` | {fila.descripcion} | {fila.periodicidad} "
                f"| {fila.unidad} | {fila.agregacion} |"
            )
        partes.append("")
    return "\n".join(partes)


def reemplazar(ruta: Path, inicio: str, fin: str, contenido: str) -> None:
    texto = ruta.read_text(encoding="utf-8")
    a, b = texto.index(inicio), texto.index(fin)
    ruta.write_text(texto[:a] + contenido + texto[b:], encoding="utf-8")


total = len(sie.CATALOGO)
reemplazar(
    RAIZ / "README.md",
    "## Catálogo",
    "## Analizar",
    f"## Catálogo\n\nLas {total} series con alias. La columna *A mensual* es la regla que usa "
    "`panel`.\nCualquier otra clave del SIE funciona directamente con `descargar`.\n\n"
    + tablas(3)
    + "\n",
)
reemplazar(RAIZ / "docs" / "catalogo.md", "## ", "## ¿Falta una serie?", tablas(2) + "\n")
print(f"Catálogo actualizado: {total} series")
