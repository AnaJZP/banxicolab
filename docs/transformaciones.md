# Transformaciones

Funciones puras: reciben un `Series` o `DataFrame` con índice de fechas y
devuelven uno nuevo. No dependen de la API, así que sirven con datos de
cualquier fuente.

Los ejemplos suponen:

```python
import banxicolab as sie

inpc = sie.serie("inpc", "2000-01-01")
diarias = sie.descargar(["fix", "tasa_objetivo", "cetes_28"], "2000-01-01")
```

## Conocer los datos primero

```python
sie.diagnostico(diarias)
```

Devuelve por serie: observaciones, cobertura, frecuencia, faltantes, mínimo,
máximo y la razón máx/mín. Si una serie positiva se multiplicó varias veces en
la muestra, su varianza casi seguro crece con el nivel y conviene el logaritmo.

## De diario a mensual

```python
mensual = sie.a_mensual(
    diarias,
    {
        "fix": "ultimo",  # precio → cierre del mes
        "tasa_objetivo": "promedio",  # tasa → promedio del mes
        "cetes_28": "promedio",
    },
)
```

La regla de agregación no es neutral. Promediar un precio suaviza su
volatilidad artificialmente: con el FIX, la desviación estándar del cambio
mensual es notablemente menor sobre promedios que sobre cierres.

| `como` | Úsalo para |
|---|---|
| `"ultimo"` | precios y saldos: tipo de cambio, reservas, índices |
| `"promedio"` | tasas de interés |
| `"suma"` | flujos: remesas, exportaciones |

El resultado queda fechado el día 1 de cada mes, igual que las series mensuales
del SIE, de modo que se une sin desfases:

```python
panel = mensual.join(inpc)
```

La columna `agregacion` de `sie.catalogo()` sugiere la regla para cada alias.

## Números índice

$$I_t = 100 \times \frac{X_t}{X_{t_0}}$$

```python
sie.indice_base(panel, "2018-01-01")  # todas las columnas, base ene-2018 = 100
sie.cambiar_base(indice, "2010-01-01")  # rebasificar sin los datos originales
sie.empalmar(tramo_base_2010, tramo_base_2018)  # unir dos bases
```

Si la fecha exacta no existe se toma el último dato anterior. Un índice permite
comparar series en unidades distintas, pero es un cambio de escala: no altera
tasas de crecimiento ni vuelve estacionaria la serie.

## Tasas de variación

```python
sie.variacion(inpc)  # mensual, en %
sie.variacion(inpc, 12)  # anual
sie.variacion_anual(inpc)  # igual, detectando la frecuencia
sie.variacion(inpc, log=True)  # diferencia de logaritmos
sie.anualizar(sie.variacion(inpc))  # (1 + r)^12 − 1
```

- La variación **logarítmica** es aditiva en el tiempo (la suma de las mensuales
  es exactamente la del periodo), pero solo se parece a la simple para cambios
  pequeños: a 10 % ya difieren medio punto.
- **Anualizar** multiplicando por 12 subestima; `anualizar` capitaliza.
- Los faltantes no se rellenan: una variación junto a un `NaN` es `NaN`.

## Precios constantes

```python
sie.deflactar(salario_nominal, inpc, base="2018-07-01")  # serie en pesos de jul-2018
sie.a_pesos_de(1000, "2010-01-01", "2026-01-01", inpc)  # un monto entre dos fechas
sie.tasa_real(mensual["cetes_28"], sie.variacion_anual(inpc))  # Fisher exacta
```

`deflactar` necesita que la serie nominal y el índice tengan la misma
frecuencia. `tasa_real` usa por omisión la fórmula exacta
$(1+i)/(1+\pi)-1$; con `exacta=False` devuelve $i-\pi$, que siempre
sobreestima y se degrada justo cuando la inflación es alta.

!!! warning "Esto no es el tipo de cambio real"
    Deflactar el FIX con el INPC lo expresa en pesos constantes, pero el tipo de
    cambio real bilateral también incorpora los precios de Estados Unidos:
    $E_t P^*_t / P_t$.

## Cambio de unidades

```python
sie.estandarizar(panel)  # (x − media) / desviación
sie.min_max(panel)  # al intervalo [0, 1]
sie.escalar_robusto(panel)  # (x − mediana) / rango intercuartílico
```

Las tres son transformaciones afines: cambian media y dispersión, pero no el
sesgo, la curtosis ni la raíz unitaria.

### Sin fuga de información

Si vas a evaluar un modelo fuera de muestra, los parámetros del escalamiento
deben salir **solo** del conjunto de entrenamiento:

```python
corte = int(len(serie) * 0.75)
entrenamiento, prueba = serie.iloc[:corte], serie.iloc[corte:]

prueba_z = sie.estandarizar(prueba, referencia=entrenamiento)
```

Con `min_max(..., referencia=entrenamiento)` los datos de prueba pueden salir
de `[0, 1]`. No es un error: es la señal de que el futuro salió del rango
histórico.

## Estacionalidad

```python
igae = sie.serie("igae")  # serie original
igae_sa = sie.desestacionalizar(igae)  # descomposición clásica
```

`desestacionalizar` usa medias móviles (`statsmodels`). Sirve para explorar y
enseñar, pero no reproduce las cifras oficiales, que usan X-13ARIMA-SEATS con
efectos de calendario. Cuando exista la serie oficial ajustada, como
`"igae_desestacionalizado"`, es preferible.

!!! note "`SR17693` ya está desestacionalizada"
    En el SIE, `SR17692` es el IGAE original y `SR17693` el desestacionalizado.
    Por eso el alias `"igae"` apunta a `SR17692`.

La variación anual (`variacion_anual`) también cancela la estacionalidad
estable sin necesidad de ajustar.

## Verificar: ¿quedó estacionaria?

```python
sie.prueba_adf(
    {
        "nivel": inpc,
        "z-score": sie.estandarizar(inpc),
        "Δ ln": sie.variacion(inpc, log=True),
        "Δ12 ln": sie.variacion(inpc, 12, log=True),
    }
)
```

Devuelve el estadístico Dickey–Fuller Aumentado, el valor crítico al 5 %, el
p-valor y una columna `estacionaria`. Las filas de nivel y z-score tendrán el
mismo estadístico: escalar nunca cambia la conclusión.
