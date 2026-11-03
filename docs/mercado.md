# Rendimientos e inflación implícita

Qué inflación descuentan los precios de los bonos del gobierno, calculada desde
los datos diarios de Banxico.

## La idea

Un **Bono M** paga una tasa nominal fija. Un **Udibono** paga una tasa real y
además se ajusta con la inflación observada. La inflación que deja indiferente
a un inversionista entre ambos es la *inflación implícita* (o *breakeven*):

$$\pi^{impl} = \frac{1 + i}{1 + r} - 1$$

## En una línea

```python
import banxicolab as sie

bmx = sie.Banxico()
bei = bmx.inflacion_implicita(10, "2010-01-01")
bei.tail()
```

| Columna | Contenido |
|---|---|
| `nominal` | rendimiento a vencimiento del Bono M, % anual |
| `real` | rendimiento real del Udibono, % anual |
| `implicita` | inflación implícita, % |
| `plazo_nominal`, `plazo_real` | años por vencer de cada título |

Los plazos disponibles son 3, 10, 20 y 30 años, con datos diarios desde 2003
(los más largos empiezan después).

## De dónde salen los rendimientos

Banxico publica cada día el precio limpio, el cupón vigente y los días por
vencer de los títulos de referencia (el «vector de precios *on the run*»), pero
no su rendimiento. La librería lo calcula con la convención del mercado
mexicano: cupones cada 182 días y base 360.

Con $R = y \cdot 182/360$, cupón $C = VN \cdot c \cdot 182/360$, $K$ cupones por
cobrar y $d$ días transcurridos del cupón vigente:

$$P_{sucio} = \frac{C + C\left[\dfrac{1}{R} - \dfrac{1}{R(1+R)^{K-1}}\right] + \dfrac{VN}{(1+R)^{K-1}}}{(1+R)^{1-d/182}}
\qquad P_{limpio} = P_{sucio} - C\,\frac{d}{182}$$

El rendimiento $y$ es la tasa que iguala esa expresión con el precio observado.
El Udibono cotiza en pesos pero su valor nominal son 100 UDIS, así que primero
se divide su precio entre el valor de la UDI.

Las dos funciones se pueden usar por separado, con cualquier bono:

```python
sie.rendimiento_bono(precio_limpio=90.629439, cupon=8.0, plazo_dias=3426)  # 9.517
sie.precio_bono(rendimiento=9.517, cupon=8.0, plazo_dias=3426)  # 90.63
```

!!! success "Cómo se verificó"
    - Los intereses devengados que implica la fórmula coinciden con la
      diferencia entre el precio sucio y el limpio que publica Banxico
      (diferencia mediana de 3 × 10⁻⁷ pesos en más de 2,900 días).
    - Los rendimientos calculados difieren en promedio 0.10 puntos porcentuales
      de la tasa de las subastas primarias de Bonos M a 10 años y 0.06 de las
      de Udibonos, que son otro mercado y otro día.

## Cómo leerla

!!! warning "No es una expectativa pura"
    La inflación implícita incluye dos primas que no se observan por separado:

    - una **prima por riesgo inflacionario**, que la empuja hacia arriba;
    - una **prima de liquidez** de los Udibonos, que la empuja hacia abajo.

    Banxico la llama *compensación por inflación y riesgo inflacionario*. Sirve
    más para ver **cambios** que para leer el nivel como pronóstico.

Otras tres limitaciones de los datos:

- **Los plazos no coinciden.** Los Bonos M de referencia se agrupan por rango
  («7 a 10 años»), y el Udibono «a 10 años» puede vencer uno o dos años después.
  Revisa `plazo_nominal` y `plazo_real`.
- **Hay saltos** cuando Banxico cambia el título de referencia.
- **Hay huecos**: por ejemplo, el vector a 10 años no tiene datos de octubre a
  diciembre de 2014.

## Contra la encuesta de expectativas

```python
inpc = bmx.serie("inpc", "2009-01-01")

comparacion = (
    sie.a_mensual(bei["implicita"], "promedio")
    .to_frame("mercado")
    .assign(
        encuesta=bmx.serie("expectativa_inflacion_12m", "2010-01-01"),
        observada=sie.variacion_anual(inpc),
    )
)
```

La encuesta mensual de Banxico a especialistas está en el catálogo como
`"expectativa_inflacion_12m"`, `"expectativa_inflacion_cierre"` y
`"expectativa_inflacion_cierre_siguiente"` (medianas).

## Implícita forward

Con dos plazos se obtiene la inflación que el mercado descuenta para un periodo
futuro. La de diez años dentro de diez años deja fuera los choques de corto
plazo:

```python
diez = bmx.inflacion_implicita(10, "2018-01-01")["implicita"]
veinte = bmx.inflacion_implicita(20, "2018-01-01")["implicita"]

sie.inflacion_implicita_forward(diez, veinte, plazo_corto=10, plazo_largo=20)
```

Supone que los títulos vencen exactamente a 10 y 20 años, lo que rara vez se
cumple; tómala como aproximación.

## Tres tasas reales

```python
objetivo = sie.a_mensual(bmx.serie("tasa_objetivo", "2010-01-01"), "promedio")

ex_post = sie.tasa_real(objetivo, sie.variacion_anual(inpc))  # inflación ya observada
ex_ante = sie.tasa_real(objetivo, bmx.serie("expectativa_inflacion_12m"))  # inflación esperada
de_mercado = sie.a_mensual(bei["real"], "promedio")  # Udibono
```

La postura de la política monetaria se evalúa con la **ex-ante**; la ex-post
mide lo que efectivamente ganó quien invirtió.

## Curva de rendimientos

Con los Cetes de 28 a 364 días y los Bonos M de referencia de hasta 30 años se
arma la curva del día y se ajusta una curva de Nelson-Siegel:

```python
curva = sie.Banxico().curva_rendimientos()  # o curva_rendimientos("2020-03-13")
sie.graficar_curva(curva)
curva.attrs["curva"]
```

```text
CurvaNS(nivel=9.762, pendiente=-3.332, curvatura=3.865, lam=5.66, error=0.038)
```

La tabla trae, por título, el plazo en años, el rendimiento observado y el
ajustado. La curva se evalúa en cualquier plazo: `curva.attrs["curva"](7)` da
la tasa a siete años.

| Parámetro | Qué mide |
|---|---|
| `nivel` | la tasa de largo plazo |
| `pendiente` | corto menos largo plazo; negativa cuando las tasas largas son mayores |
| `curvatura` | la joroba en los plazos medios |
| `lam` | en qué plazo (años) se ubica la joroba |
| `error` | qué tan bien ajusta, en puntos porcentuales |

Para seguir la curva en el tiempo:

```python
historia = sie.Banxico().curva_historica("2021-01-01")
historia[["3m", "2a", "10a", "30a"]]
```

Ajusta la curva cada día y la evalúa en plazos fijos (3 meses a 30 años, o
los que indiques con `plazos=`), junto con los parámetros. La inversión de
2023, cuando la tasa a 3 meses superó a la de 10 años, se ve con claridad.

!!! note "Qué es y qué no es"
    Son rendimientos a vencimiento de los títulos de referencia, no una curva
    cupón cero. Los Cetes cotizan a tasa de rendimiento y los Bonos M a
    rendimiento con cupones semestrales: convenciones cercanas pero no
    idénticas. La función general es `sie.nelson_siegel(plazos, rendimientos)`.
