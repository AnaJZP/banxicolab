# Gráficas

Todas las gráficas de la librería son **interactivas** (Plotly): al pasar el
cursor se ven los valores, se puede arrastrar para acercar y los botones de
arriba eligen el periodo. Cada una se hace con una sola línea.

```python
import banxicolab as sie

indices = sie.descargar(["inpc", "inpc_subyacente"], "2010-01-01")
anual = sie.variacion_anual(indices).rename(
    columns={"inpc": "General", "inpc_subyacente": "Subyacente"}
)
sie.graficar(anual, "Inflación anual", unidad="%", meta=True)
```

<iframe src="../assets/graficas/inflacion.html" width="100%" height="470" style="border:none"></iframe>

## Las cuatro funciones

| Función | Qué dibuja |
|---|---|
| `sie.graficar(datos, ...)` | Una o varias series de tiempo, en líneas o barras |
| `sie.graficar_contribuciones(aportes)` | Lo que aporta cada componente a la inflación, en barras apiladas |
| `sie.graficar_curva(curva)` | La curva de rendimientos del día, con su ajuste Nelson-Siegel |
| `sie.graficar_pronostico(historia, pronostico)` | La inflación observada y su pronóstico con la banda de incertidumbre |

```python
bmx = sie.Banxico()

sie.graficar_contribuciones(bmx.contribuciones_inflacion("2019-01-01"))
sie.graficar_curva(bmx.curva_rendimientos())

inpc = sie.serie("inpc", "2000-01-01")
sie.graficar_pronostico(sie.variacion_anual(inpc).loc["2021":], sie.pronosticar_inflacion(inpc, 12))
```

<iframe src="../assets/graficas/contribuciones.html" width="100%" height="470" style="border:none"></iframe>

## Opciones de `graficar`

| Parámetro | Para qué |
|---|---|
| `titulo` | título de la gráfica |
| `unidad` | etiqueta del eje vertical (`"%"`, `"Pesos por dólar"`) |
| `meta=True` | meta de inflación de 3 % e intervalo de 2 % a 4 % |
| `cero=True` | línea en cero, para tasas reales o variaciones |
| `tipo="barras"` | barras en lugar de líneas |
| `fuente` | `True` cita al SIE con las claves de las series; también acepta un texto propio o `False` |
| `interactivo=False` | gráfica fija de matplotlib, para documentos impresos |

La fuente se agrega sola al pie con las claves de las series descargadas, por
ejemplo *Fuente: Banco de México, SIE (SP1, SP74625).*

## Ajustar, combinar y guardar

Cada función devuelve una figura de Plotly, que se puede seguir modificando:

```python
fig = sie.graficar(anual, "Inflación anual", unidad="%")
fig.add_scatter(x=otra.index, y=otra, name="Otra serie")  # agregar una línea
fig.update_yaxes(range=[0, 10])  # fijar el eje
fig.write_html("inflacion.html")  # página web interactiva
```

Para una imagen fija (PNG o PDF), lo más sencillo es la versión de matplotlib:

```python
ax = sie.graficar(anual, "Inflación anual", unidad="%", interactivo=False)
ax.figure.savefig("inflacion.png", dpi=200, bbox_inches="tight")
```

La paleta, en escala de azules, está en `sie.PALETA`.

!!! note "Notebooks en GitHub"
    GitHub no muestra las gráficas interactivas al previsualizar un notebook.
    Se ven al ejecutarlo en Jupyter, VS Code o Google Colab.
