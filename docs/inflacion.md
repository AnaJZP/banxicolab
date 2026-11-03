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
sie.graficar(anual.loc["2018":], "Inflación anual", unidad="%", meta=True)
```

`meta=True` dibuja la meta de 3 % y el intervalo de 2 % a 4 %; la fuente, con
las claves de las series, se agrega sola al pie. Ver [Gráficas](graficas.md).

## ¿Qué componentes la empujan?

```python
bmx = sie.Banxico()
aportes = bmx.contribuciones_inflacion("2019-01-01")
aportes.tail()
```

Reparte la inflación anual, en puntos porcentuales, entre **mercancías,
servicios, agropecuarios y energéticos y tarifas**; con
`desglose="subyacente"`, entre subyacente y no subyacente. Con `periodos=1`
reparte la mensual.

| Columna | Contenido |
|---|---|
| un componente por columna | su aportación en puntos porcentuales |
| `total` | la inflación del periodo |
| `residuo` | lo que la suma no explica |

**Cómo funciona.** Dentro de cada periodo con ponderadores fijos, el INPC es
una suma exacta de sus componentes. Los coeficientes de esa suma se estiman de
los propios datos, así que no hace falta conocer los ponderadores oficiales.
Los periodos que cruzan un cambio de ponderadores se encadenan en el mes de
enlace. Con datos de 2000 a 2026 el residuo nunca pasa de 0.02 puntos.

Los cambios de ponderadores se identificaron en los datos (julio de 2002,
enero de 2011, febrero de 2013, agosto de 2018 y agosto de 2024). Si INEGI
hace uno nuevo, la función avisa que el total dejó de ser una suma exacta y
que las contribuciones son aproximadas.

Para usar otros índices, la versión general es
`sie.contribuciones(total, componentes)`.

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
