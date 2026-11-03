"""Gráficas listas para presentar, con la fuente citada."""

from __future__ import annotations

import pandas as pd

PALETA = ["#800020", "#0F7173", "#C9A227", "#646464", "#D98C9A", "#3B5B92", "#8C6D46"]
_GUINDA, _GRIS = PALETA[0], "#646464"


def graficar(
    datos: pd.Series | pd.DataFrame,
    titulo: str | None = None,
    *,
    unidad: str | None = None,
    meta: bool = False,
    cero: bool = False,
    fuente: str | bool = True,
    ax=None,
    **opciones,
):
    """Grafica una o varias series con un estilo limpio y la fuente al pie.

    Parameters
    ----------
    datos : Series o DataFrame
        Una línea por columna. Los nombres de las columnas aparecen en la
        leyenda.
    titulo : str, opcional
        Título, alineado a la izquierda.
    unidad : str, opcional
        Etiqueta del eje vertical, por ejemplo ``"%"`` o ``"Pesos por dólar"``.
    meta : bool
        Dibuja la meta de inflación de Banxico (3 %) y su intervalo de
        variabilidad (2 % a 4 %).
    cero : bool
        Dibuja una línea en cero (útil para tasas reales o variaciones).
    fuente : str o bool
        ``True`` cita al SIE de Banco de México con las claves de las series
        si se descargaron con la librería; un texto lo sustituye; ``False`` la
        omite.
    ax : matplotlib.axes.Axes, opcional
        Eje donde dibujar; si se omite se crea una figura nueva.
    **opciones
        Se pasan a ``Axes.plot`` (por ejemplo ``lw=1`` o ``ls="--"``).

    Returns
    -------
    matplotlib.axes.Axes

    Examples
    --------
    >>> import banxicolab as sie
    >>> inpc = sie.serie("inpc", "2015-01-01")                       # doctest: +SKIP
    >>> sie.graficar(sie.variacion_anual(inpc), "Inflación anual",
    ...              unidad="%", meta=True)                           # doctest: +SKIP
    """
    import matplotlib.pyplot as plt

    tabla = datos.to_frame() if isinstance(datos, pd.Series) else datos
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4.2))
    opciones.setdefault("lw", 1.8)
    for k, columna in enumerate(tabla.columns):
        ax.plot(
            tabla.index,
            tabla[columna],
            color=PALETA[k % len(PALETA)],
            label=str(columna),
            **opciones,
        )

    if meta:
        ax.axhspan(2, 4, color=_GRIS, alpha=0.10, lw=0, label="Intervalo de variabilidad")
        ax.axhline(3, color=_GRIS, ls="--", lw=1, label="Meta de 3 %")
    if cero:
        ax.axhline(0, color=_GRIS, lw=0.9)

    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.spines["left"].set_color("#C8C8C8")
    ax.spines["bottom"].set_color("#C8C8C8")
    ax.grid(True, color="#EDEDED", lw=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("")
    if unidad:
        ax.set_ylabel(unidad)
    if titulo:
        ax.set_title(titulo, loc="left", fontweight="bold", fontsize=12, color="#1F1F1F")
    if len(tabla.columns) > 1 or meta:
        ax.legend(frameon=False, fontsize=9, ncols=min(len(tabla.columns) + 2 * meta, 4))

    texto = _fuente(datos) if fuente is True else (fuente or "")
    if texto:
        ax.annotate(
            texto, xy=(0, 0), xycoords="axes fraction", xytext=(0, -26), textcoords="offset points",
            fontsize=8, color=_GRIS, ha="left", va="top",
        )  # fmt: skip
    return ax


def _fuente(datos) -> str:
    series = getattr(datos, "attrs", {}).get("series", {})
    claves = ", ".join(sorted({ficha["id"] for ficha in series.values()}))
    return "Fuente: Banco de México, SIE" + (f" ({claves})" if claves else "") + "."
