# Inflación

Un análisis completo, de la descarga a la tasa real.

## La tabla de inflación

```python
import banxicolab as sie

tabla = sie.Banxico().inflacion("2018-01-01")
tabla.tail()
```

Descarga el INPC y calcula cuatro lecturas, en %:

| Columna | Definición | Para qué |
|---|---|---|
| `mensual` | contra el mes anterior | el dato del mes; tiene estacionalidad |
| `anual` | contra el mismo mes del año anterior | la que se compara con la meta de 3 % ± 1 |
| `acumulada` | contra diciembre del año anterior | avance en lo que va del año |
| `mensual_anualizada` | mensual capitalizada a 12 meses | ritmo reciente; muy volátil |

Se descargan 13 meses adicionales hacia atrás para que la variación anual
exista desde la fecha de inicio.

Si ya tienes el índice, o quieres otro (subyacente, no subyacente):

```python
indices = sie.descargar(["inpc", "inpc_subyacente", "inpc_no_subyacente"], "2015-01-01")

anual = sie.variacion_anual(indices)  # las tres, de una vez
sie.inflacion(indices["inpc_subyacente"])  # tabla completa de la subyacente
```

## Graficar contra la meta

```python
import matplotlib.pyplot as plt

ax = anual.loc["2018":].plot(figsize=(10, 4), lw=1.6)
ax.axhline(3, ls="--", color="gray", label="Meta 3 %")
ax.axhspan(2, 4, color="gray", alpha=0.1)
ax.set_ylabel("% anual")
ax.legend()
plt.show()
```

## Calculada aquí o calculada por Banxico

Banxico publica la inflación ya calculada; conviene para verificar:

```python
oficial = sie.serie("inflacion_anual", "2018-01-01")
propia = sie.variacion_anual(sie.serie("inpc", "2016-12-01")).loc["2018-01-01":]

(oficial - propia).abs().max()  # diferencias de redondeo
```

La serie oficial viene redondeada a dos decimales; calcularla desde el índice
conserva toda la precisión y permite cualquier horizonte.

## Inflación entre dos fechas

```python
inpc = sie.serie("inpc")

sie.inflacion_entre(inpc, "2018-12-01", "2024-09-01")  # % acumulado en el sexenio
sie.a_pesos_de(1000, "2000-01-01", "2026-01-01", inpc)  # $1,000 de 2000 en pesos de 2026
```

## Tasa de interés real

```python
cetes = sie.a_mensual(sie.serie("cetes_28", "2000-01-01"), "promedio")
inflacion_anual = sie.variacion_anual(inpc)

real = sie.tasa_real(cetes, inflacion_anual).dropna()
(real < 0).mean() * 100  # % de meses con tasa real negativa
```

Es la tasa real **ex-post**: compara el rendimiento con la inflación ya
observada. La ex-ante requeriría expectativas de inflación.

## Salario o cualquier monto en pesos constantes

```python
salario = sie.serie("salario_minimo", "2000-01-01")
salario_real = sie.deflactar(salario, inpc, base=inpc.index[-1])

sie.variacion_anual(salario_real).tail()  # crecimiento real del salario mínimo
```

## ¿La inflación es estacionaria?

```python
sie.prueba_adf(
    {
        "INPC (nivel)": inpc,
        "Inflación mensual": sie.variacion(inpc, log=True),
        "Inflación anual": sie.variacion(inpc, 12, log=True),
    }
)
```

El resultado típico es que el nivel no lo es, la inflación mensual sí, y la
anual queda en la frontera: la diferencia de 12 meses traslapa 11 de cada 12
observaciones consecutivas, lo que induce una persistencia fuerte.
