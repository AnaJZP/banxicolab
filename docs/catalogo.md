# Catálogo de alias

Nombres cortos para las series más usadas. Sirven en cualquier función que
reciba series: `sie.descargar("fix")` equivale a `sie.descargar("SF43718")`.

```python
sie.catalogo()  # todos
sie.catalogo("tasas")  # un tema
sie.catalogo(buscar="cetes")  # por texto, sin distinguir acentos
sie.descargar(tema="tasas")  # descargar un tema completo
```

Todas las claves están verificadas contra el catálogo público del SIE
(`pytest -m red` repite la verificación). La columna *A mensual* es la regla que
aplica [`panel`](descarga.md#panel-mensual) al llevar la serie a frecuencia
mensual.

## Precios

`tema="precios"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `inpc` | `SP1` | INPC, índice general | Mensual | Índice | ultimo |
| `inpc_subyacente` | `SP74625` | INPC subyacente | Mensual | Índice | ultimo |
| `inpc_no_subyacente` | `SP74630` | INPC no subyacente | Mensual | Índice | ultimo |
| `inflacion_mensual` | `SP30577` | INPC, variación mensual | Mensual | % | ultimo |
| `inflacion_anual` | `SP30578` | INPC, variación anual | Mensual | % | ultimo |
| `inflacion_acumulada` | `SP30579` | INPC, variación acumulada en el año | Mensual | % | ultimo |
| `inflacion_subyacente_anual` | `SP74662` | Inflación subyacente anual | Mensual | % | ultimo |
| `inflacion_no_subyacente_anual` | `SP74665` | Inflación no subyacente anual | Mensual | % | ultimo |
| `inpc_quincenal` | `SP8664` | INPC quincenal, índice general | Quincenal | Índice | promedio |
| `inpc_subyacente_quincenal` | `SP74632` | INPC subyacente quincenal | Quincenal | Índice | promedio |
| `inflacion_anual_quincenal` | `SP74833` | INPC quincenal, variación anual | Quincenal | % | ultimo |
| `media_truncada` | `SP74831` | Indicador de media truncada, general (anual) | Mensual | % | ultimo |
| `media_truncada_subyacente` | `SP74832` | Indicador de media truncada, subyacente (anual) | Mensual | % | ultimo |
| `udis` | `SP68257` | Valor de la UDI | Diaria | Pesos por UDI | ultimo |

## Expectativas de inflación (encuesta de Banxico, mediana)

`tema="expectativas"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `expectativa_inflacion_12m` | `SR14195` | Expectativa de inflación general, próximos 12 meses | Mensual | % | ultimo |
| `expectativa_inflacion_cierre` | `SR14139` | Expectativa de inflación general, cierre del año en curso | Mensual | % | ultimo |
| `expectativa_inflacion_cierre_siguiente` | `SR14146` | Expectativa de inflación general, cierre del año siguiente | Mensual | % | ultimo |

## Tipo de cambio

`tema="tipo_de_cambio"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `fix` | `SF43718` | Tipo de cambio FIX, fecha de determinación | Diaria | MXN/USD | ultimo |
| `fix_liquidacion` | `SF60653` | Tipo de cambio FIX, fecha de liquidación | Diaria | MXN/USD | ultimo |
| `fix_promedio_mensual` | `SF17908` | Tipo de cambio FIX, promedio del mes | Mensual | MXN/USD | ultimo |
| `euro` | `SF46410` | Pesos por euro | Diaria | MXN/EUR | ultimo |

## Tasas de interés

`tema="tasas"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `tasa_objetivo` | `SF61745` | Tasa objetivo de Banxico | Diaria | % anual | promedio |
| `tiie_fondeo` | `SF331451` | TIIE de fondeo a un día hábil | Diaria | % anual | promedio |
| `tiie_28` | `SF43783` | TIIE a 28 días | Diaria | % anual | promedio |
| `cetes_28` | `SF60633` | Cetes a 28 días, subasta semanal | Diaria | % anual | promedio |
| `cetes_91` | `SF60634` | Cetes a 91 días, subasta semanal | Diaria | % anual | promedio |
| `bono_10a` | `SF44071` | Bono M a 10 años, tasa de la subasta | Diaria | % anual | promedio |
| `udibono_10a` | `SF43924` | Udibono a 10 años, tasa real de la subasta | Diaria | % anual | promedio |

## Actividad y salarios

`tema="actividad"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `igae` | `SR17692` | IGAE base 2018, serie original | Mensual | Índice | ultimo |
| `igae_desestacionalizado` | `SR17693` | IGAE base 2018, serie desestacionalizada | Mensual | Índice | ultimo |
| `salario_minimo` | `SL11298` | Salario mínimo general | Mensual | Pesos por día | ultimo |

## Sector externo

`tema="externo"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `reservas` | `SF43707` | Reserva internacional | Diaria | Millones de USD | ultimo |
| `remesas` | `SE27803` | Remesas familiares, total | Mensual | Millones de USD | suma |

## Agregados monetarios

`tema="dinero"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `m1` | `SF311408` | Agregado monetario M1 | Mensual | Miles de pesos | ultimo |
| `m2` | `SF311418` | Agregado monetario M2 | Mensual | Miles de pesos | ultimo |

## ¿Falta una serie?

Cualquier clave del SIE funciona directamente, esté o no en esta tabla:

```python
sie.buscar("cetes")  # encuentra la clave
sie.descargar({"SF282": "cetes_28_mensual"})  # y úsala con el nombre que quieras
```

Para agregar un alias permanente, añade una fila al tema que corresponda en
`_POR_TEMA`, dentro de `src/banxicolab/alias.py`.
