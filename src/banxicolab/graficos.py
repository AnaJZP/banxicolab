"""Gráficas interactivas (Plotly) listas para presentar, con la fuente citada.

Cada función resuelve una gráfica completa en una línea: series de tiempo,
contribuciones a la inflación, curva de rendimientos y pronósticos. Devuelven
una figura de Plotly que se puede seguir ajustando (``fig.update_layout(...)``)
o guardar como página web (``fig.write_html("grafica.html")``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Escala de azules, ordenada para que las series consecutivas se distingan bien
PALETA = ["#0B3C5D", "#328CC1", "#8FC1E3", "#5B7083", "#1B5E8C", "#B8D8EE", "#2E2E2E"]
_GRIS = "#7A7A7A"
_NOMBRES = {  # columnas de contribuciones_inflacion, con acentos para la leyenda
    "mercancias": "Mercancías",
    "servicios": "Servicios",
    "agropecuarios": "Agropecuarios",
    "energeticos": "Energéticos y tarifas",
    "subyacente": "Subyacente",
    "no_subyacente": "No subyacente",
}
_FECHAS = [  # formatos numéricos, para no depender del idioma del navegador
    {"dtickrange": [None, 86400000 * 31], "value": "%d/%m/%Y"},
    {"dtickrange": [86400000 * 31, 86400000 * 365], "value": "%m/%Y"},
    {"dtickrange": [86400000 * 365, None], "value": "%Y"},
]


def _fuente(datos) -> str:
    series = getattr(datos, "attrs", {}).get("series", {})
    claves = ", ".join(sorted({ficha["id"] for ficha in series.values()}))
    return "Fuente: Banco de México, SIE" + (f" ({claves})" if claves else "") + "."


def _texto_fuente(datos, fuente) -> str:
    return _fuente(datos) if fuente is True else (fuente or "")


def _estilo(fig, titulo, unidad, fuente, *, fechas=True, rango=False):
    fig.update_layout(
        template="simple_white",
        title={"text": f"<b>{titulo}</b>" if titulo else None, "x": 0.01, "xanchor": "left"},
        font={"family": "Arial, sans-serif", "size": 13, "color": "#1F1F1F"},
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "x": 0, "title": None},
        margin={"l": 60, "r": 20, "t": 80, "b": 85 if fuente else 45},
        separators=".,",
        yaxis={"title": unidad, "gridcolor": "#EDEDED", "showgrid": True, "zeroline": False},
        xaxis={"gridcolor": "#EDEDED"},
    )
    if fechas:
        fig.update_xaxes(tickformatstops=_FECHAS, hoverformat="%d/%m/%Y")
    if rango:
        fig.update_xaxes(
            rangeselector={
                "buttons": [
                    {"count": 1, "label": "1 año", "step": "year", "stepmode": "backward"},
                    {"count": 5, "label": "5 años", "step": "year", "stepmode": "backward"},
                    {"count": 10, "label": "10 años", "step": "year", "stepmode": "backward"},
                    {"step": "all", "label": "Todo"},
                ],
                "x": 1,
                "xanchor": "right",
                "y": 1.02,
                "yanchor": "bottom",
            }
        )
    if fuente:
        fig.add_annotation(
            text=fuente, xref="paper", yref="paper", x=0, y=0, xanchor="left", yanchor="top",
            yshift=-45, showarrow=False, font={"size": 11, "color": _GRIS},
        )  # fmt: skip
    return fig


def _referencias(fig, meta: bool, cero: bool) -> None:
    if meta:
        fig.add_hrect(y0=2, y1=4, fillcolor=_GRIS, opacity=0.10, line_width=0, layer="below")
        fig.add_hline(
            y=3, line={"color": _GRIS, "dash": "dash", "width": 1},
            annotation_text="Meta 3 %", annotation_position="top left",
            annotation_font={"size": 11, "color": _GRIS},
        )  # fmt: skip
    if cero:
        fig.add_hline(y=0, line={"color": _GRIS, "width": 1})


def graficar(
    datos: pd.Series | pd.DataFrame,
    titulo: str | None = None,
    *,
    unidad: str | None = None,
    meta: bool = False,
    cero: bool = False,
    fuente: str | bool = True,
    tipo: str = "lineas",
    interactivo: bool = True,
    ax=None,
    **opciones,
):
    """Grafica una o varias series con estilo limpio y la fuente al pie.

    Parameters
    ----------
    datos : Series o DataFrame
        Una serie por columna; los nombres de las columnas van a la leyenda.
    titulo : str, opcional
        Título de la gráfica.
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
    tipo : {"lineas", "barras"}
        Forma de dibujar las series.
    interactivo : bool
        ``True`` (por omisión) devuelve una figura de Plotly: se puede hacer
        acercamiento, ver los valores al pasar el cursor y elegir el periodo
        con los botones de la parte superior. ``False`` devuelve una gráfica
        fija de matplotlib, cómoda para documentos impresos.
    ax : matplotlib.axes.Axes, opcional
        Solo con ``interactivo=False``: eje donde dibujar.
    **opciones
        Con matplotlib se pasan a ``Axes.plot`` (por ejemplo ``lw=1``).

    Returns
    -------
    plotly.graph_objects.Figure o matplotlib.axes.Axes

    Examples
    --------
    >>> import banxicolab as sie
    >>> inpc = sie.serie("inpc", "2015-01-01")                       # doctest: +SKIP
    >>> sie.graficar(sie.variacion_anual(inpc), "Inflación anual",
    ...              unidad="%", meta=True)                           # doctest: +SKIP
    """
    if tipo not in ("lineas", "barras"):
        raise ValueError('tipo debe ser "lineas" o "barras"')
    tabla = datos.to_frame() if isinstance(datos, pd.Series) else datos
    texto = _texto_fuente(datos, fuente)
    if not interactivo:
        return _graficar_estatico(tabla, titulo, unidad, meta, cero, texto, tipo, ax, opciones)

    import plotly.graph_objects as go

    fig = go.Figure()
    formato = "%{y:,.2f}" + (f" {unidad}" if unidad in ("%", "pp") else "")
    for k, columna in enumerate(tabla.columns):
        color = PALETA[k % len(PALETA)]
        comunes = {"x": tabla.index, "y": tabla[columna], "name": str(columna)}
        comunes["hovertemplate"] = formato + f"<extra>{columna}</extra>"
        if tipo == "barras":
            fig.add_trace(go.Bar(marker_color=color, **comunes))
        else:
            fig.add_trace(go.Scatter(mode="lines", line={"color": color, "width": 2}, **comunes))
    _referencias(fig, meta, cero)
    es_fecha = isinstance(tabla.index, pd.DatetimeIndex)
    largo = es_fecha and len(tabla) > 1 and (tabla.index.max() - tabla.index.min()).days > 3 * 365
    fig.update_layout(showlegend=len(tabla.columns) > 1)
    return _estilo(fig, titulo, unidad, texto, fechas=es_fecha, rango=largo)


def _graficar_estatico(tabla, titulo, unidad, meta, cero, texto, tipo, ax, opciones):
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4.2))
    opciones.setdefault("lw", 1.8)
    for k, columna in enumerate(tabla.columns):
        color = PALETA[k % len(PALETA)]
        if tipo == "barras":
            ax.bar(tabla.index, tabla[columna], color=color, label=str(columna))
        else:
            ax.plot(tabla.index, tabla[columna], color=color, label=str(columna), **opciones)
    if meta:
        ax.axhspan(2, 4, color=_GRIS, alpha=0.10, lw=0, label="Intervalo de variabilidad")
        ax.axhline(3, color=_GRIS, ls="--", lw=1, label="Meta de 3 %")
    if cero:
        ax.axhline(0, color=_GRIS, lw=0.9)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#C8C8C8")
    ax.grid(True, color="#EDEDED", lw=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("")
    if unidad:
        ax.set_ylabel(unidad)
    if titulo:
        ax.set_title(titulo, loc="left", fontweight="bold", fontsize=12, color="#1F1F1F")
    if len(tabla.columns) > 1 or meta:
        ax.legend(frameon=False, fontsize=9, ncols=min(len(tabla.columns) + 2 * meta, 4))
    if texto:
        ax.annotate(
            texto, xy=(0, 0), xycoords="axes fraction", xytext=(0, -26), textcoords="offset points",
            fontsize=8, color=_GRIS, ha="left", va="top",
        )  # fmt: skip
    return ax


def graficar_contribuciones(
    aportes: pd.DataFrame,
    titulo: str = "Contribución a la inflación",
    *,
    meta: bool = True,
    fuente: str | bool = True,
):
    """Barras apiladas con lo que aporta cada componente, y la inflación total.

    Parameters
    ----------
    aportes : DataFrame
        El resultado de :meth:`banxicolab.Banxico.contribuciones_inflacion` o
        de :func:`banxicolab.contribuciones`.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    import plotly.graph_objects as go

    componentes = [c for c in aportes.columns if c not in ("total", "residuo")]
    fig = go.Figure()
    for k, columna in enumerate(componentes):
        fig.add_trace(
            go.Bar(
                x=aportes.index, y=aportes[columna],
                name=_NOMBRES.get(columna, str(columna).replace("_", " ").capitalize()),
                marker_color=PALETA[k % len(PALETA)], hovertemplate="%{y:.2f} pp",
            )
        )  # fmt: skip
    if "total" in aportes:
        fig.add_trace(
            go.Scatter(
                x=aportes.index, y=aportes["total"], name="Inflación", mode="lines",
                line={"color": "#111111", "width": 2}, hovertemplate="%{y:.2f} %",
            )
        )  # fmt: skip
    fig.update_layout(barmode="relative", bargap=0.15)
    _referencias(fig, meta, cero=True)
    texto = "Fuente: Banco de México, SIE." if fuente is True else (fuente or "")
    return _estilo(fig, titulo, "Puntos porcentuales", texto, rango=len(aportes) > 36)


def graficar_curva(curva: pd.DataFrame, titulo: str | None = None, *, fuente: str | bool = True):
    """Curva de rendimientos: títulos observados y la curva Nelson-Siegel ajustada.

    Parameters
    ----------
    curva : DataFrame
        El resultado de :meth:`banxicolab.Banxico.curva_rendimientos`.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    import plotly.graph_objects as go

    ajuste = curva.attrs.get("curva")
    fecha = curva.attrs.get("fecha")
    if titulo is None:
        titulo = "Curva de rendimientos" + (f" al {fecha:%d/%m/%Y}" if fecha is not None else "")
    fig = go.Figure()
    if ajuste is not None:
        plazos = np.linspace(min(0.05, curva["plazo"].min()), curva["plazo"].max(), 300)
        fig.add_trace(
            go.Scatter(
                x=plazos, y=ajuste(plazos), name="Nelson-Siegel", mode="lines",
                line={"color": PALETA[0], "width": 2.5},
                hovertemplate="%{x:.1f} años: %{y:.2f} %<extra>Ajuste</extra>",
            )
        )  # fmt: skip
    fig.add_trace(
        go.Scatter(
            x=curva["plazo"], y=curva["rendimiento"], name="Cetes y Bonos M", mode="markers+text",
            text=curva["titulo"].str.replace("Bono M ", ""), textposition="bottom right",
            textfont={"size": 10, "color": _GRIS}, marker={"color": PALETA[1], "size": 10},
            hovertemplate="%{text}: %{y:.2f} %<extra></extra>",
        )
    )  # fmt: skip
    fig.update_layout(hovermode="closest")
    texto = "Fuente: Banco de México, vector de precios de valores gubernamentales."
    fig = _estilo(fig, titulo, "% anual", texto if fuente is True else (fuente or ""), fechas=False)
    fig.update_xaxes(title="Plazo (años)")
    return fig


def graficar_pronostico(
    historia: pd.Series,
    pronostico: pd.DataFrame,
    titulo: str = "Inflación anual: observada y pronóstico",
    *,
    meta: bool = True,
    fuente: str | bool = True,
):
    """Inflación observada y su pronóstico con la banda de incertidumbre.

    Parameters
    ----------
    historia : Series
        Inflación anual observada (por ejemplo ``sie.variacion_anual(inpc)``).
    pronostico : DataFrame
        El resultado de :func:`banxicolab.pronosticar_inflacion`; usa las
        columnas ``anual`` y, si existen, ``anual_inf`` y ``anual_sup``.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=historia.index, y=historia, name="Observada", mode="lines",
            line={"color": PALETA[3], "width": 2}, hovertemplate="%{y:.2f} %",
        )
    )  # fmt: skip
    if {"anual_inf", "anual_sup"} <= set(pronostico.columns):
        fig.add_trace(
            go.Scatter(
                x=list(pronostico.index) + list(pronostico.index[::-1]),
                y=list(pronostico["anual_sup"]) + list(pronostico["anual_inf"][::-1]),
                fill="toself", fillcolor="rgba(50,140,193,0.20)", line={"width": 0},
                name="Intervalo", hoverinfo="skip",
            )
        )  # fmt: skip
    fig.add_trace(
        go.Scatter(
            x=pronostico.index, y=pronostico["anual"], name="Pronóstico", mode="lines",
            line={"color": PALETA[0], "width": 2.5}, hovertemplate="%{y:.2f} %",
        )
    )  # fmt: skip
    _referencias(fig, meta, cero=False)
    texto = "Fuente: Banco de México, SIE; pronóstico con banxicolab." if fuente is True else fuente
    return _estilo(fig, titulo, "%", texto or "")
