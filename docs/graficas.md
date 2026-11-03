# Gráficas

```python
import banxicolab as sie

indices = sie.descargar(["inpc", "inpc_subyacente"], "2015-01-01")
anual = sie.variacion_anual(indices).rename(
    columns={"inpc": "General", "inpc_subyacente": "Subyacente"}
)
sie.graficar(anual.loc["2018":], "Inflación anual", unidad="%", meta=True)
```

`graficar` dibuja una línea por columna con la paleta de la librería, el título
alineado a la izquierda, una cuadrícula discreta y la fuente al pie:
*Fuente: Banco de México, SIE (SP1, SP74625).* Las claves salen de los datos
descargados con la librería.

| Parámetro | Para qué |
|---|---|
| `titulo` | título de la gráfica |
| `unidad` | etiqueta del eje vertical (`"%"`, `"Pesos por dólar"`) |
| `meta=True` | meta de inflación de 3 % e intervalo de 2 % a 4 % |
| `cero=True` | línea en cero, para tasas reales o variaciones |
| `fuente` | `True` (automática), un texto propio o `False` |
| `ax` | dibujar en un eje existente, por ejemplo en una figura con varios paneles |

Devuelve el eje de matplotlib, así que se puede seguir ajustando:

```python
ax = sie.graficar(anual, "Inflación anual", unidad="%")
ax.set_ylim(0, 10)
ax.figure.savefig("inflacion.png", dpi=200, bbox_inches="tight")
```

La paleta está en `sie.PALETA`, por si quieres usarla en tus propias gráficas.
