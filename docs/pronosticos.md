# Tendencia y pronósticos

Requiere `statsmodels`, incluido en el extra `[analisis]` de la instalación.

## Medidas de tendencia

La inflación anual compara con hace doce meses, así que tarda en mostrar los
cambios de dirección. Lecturas complementarias:

```python
import banxicolab as sie

indices = sie.descargar(["inpc", "inpc_subyacente"], "2005-01-01")

sie.variacion_anual(indices)  # general y subyacente
sie.serie("media_truncada", "2005-01-01")  # calculada por Banxico
sie.impulso(indices["inpc_subyacente"], 3)  # 3m/3m anualizado
```

| Medida | Qué hace | Limitación |
|---|---|---|
| **Subyacente** | excluye agropecuarios, energéticos y tarifas | lo excluido también es inflación |
| **Media truncada** | descarta cada mes los genéricos con variaciones extremas | no se puede reproducir sin los genéricos y sus ponderadores |
| **Impulso** | promedio de los últimos *k* meses contra los *k* previos, desestacionalizado y anualizado | ruidoso; depende del ajuste estacional |

### Persistencia

```python
mensual = sie.variacion(sie.desestacionalizar(indices["inpc_subyacente"]))

sie.persistencia(mensual)  # un número para toda la muestra
sie.persistencia(mensual, ventana=120)  # cómo ha cambiado, en ventanas de 10 años
```

Es la suma de los coeficientes de un AR(12): cerca de 0 los choques se
revierten pronto; cerca de 1 se quedan.

### Inflación quincenal

El INPC quincenal sale unos quince días antes que el mensual:

```python
quincenal = sie.serie("inpc_quincenal", "2020-01-01")
sie.variacion_anual(quincenal)  # detecta la frecuencia: compara contra 24 quincenas atrás
```

## Pronóstico

```python
inpc = sie.serie("inpc", "2000-01-01")

sie.pronosticar_inflacion(inpc, horizonte=12)
```

Devuelve una fila por mes futuro con `indice`, `mensual`, `anual` y el
intervalo `anual_inf`–`anual_sup`.

| `metodo` | Qué supone |
|---|---|
| `"sarima"` (por omisión) | SARIMA sobre el logaritmo del índice. La especificación por omisión, $(0,1,1)(0,1,1)_{12}$, es el «modelo de aerolíneas» |
| `"ingenuo"` | la inflación anual se queda en su último valor |

Otra especificación:

```python
sie.pronosticar_inflacion(inpc, 12, orden=(1, 1, 0), orden_estacional=(1, 0, 0, 12), nivel=0.80)
```

El intervalo se obtiene simulando trayectorias, porque la inflación **anual** de
un mes futuro depende de varios meses pronosticados a la vez. Con `semilla` fija
(por omisión) el resultado es reproducible.

!!! warning "Qué no incluye el intervalo"
    Refleja solo los choques futuros bajo el modelo. No incluye la
    incertidumbre de los parámetros ni la de haber elegido mal el modelo, así
    que es más estrecho que la incertidumbre real. Además, el modelo de
    aerolíneas extrapola la tendencia reciente y no sabe que existe una meta
    de 3 %.

## ¿Qué tan bueno es? Evaluación fuera de muestra

```python
sie.evaluar_pronosticos(inpc, horizontes=(1, 3, 6, 12), desde="2012-01-01", paso=3)
```

Para cada fecha de origen estima el modelo **solo con los datos disponibles
hasta entonces**, pronostica y compara con lo ocurrido. El resultado es la raíz
del error cuadrático medio, en puntos porcentuales de inflación anual. Con el
INPC de 2000 a agosto de 2026:

| Horizonte (meses) | SARIMA | Ingenuo | Pronósticos |
|---|---|---|---|
| 1 | 0.31 | 0.47 | 59 |
| 3 | 0.59 | 0.75 | 58 |
| 6 | 0.95 | 1.11 | 57 |
| 12 | 1.58 | 1.78 | 55 |

Dos lecturas:

- El error crece rápido: a doce meses supera el ±1 del intervalo de
  variabilidad de Banxico.
- La ventaja del SARIMA es clara a un mes (34 %) y se diluye a doce (11 %). Es
  el resultado clásico: a un año es difícil ganarle a «la inflación seguirá
  como está».

Los errores individuales quedan en `tabla.attrs["errores"]`, para graficarlos o
calcular otra métrica. `paso=1` evalúa todos los meses; es más preciso y más
lento, porque cada origen reestima el modelo.

!!! note "Sobre la evaluación"
    Usa el INPC como está publicado hoy. El INPC no se revisa salvo en los
    cambios de base, así que la diferencia con una evaluación en tiempo real es
    pequeña, pero no es cero.
