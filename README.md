# banxicolab

[![PyPI](https://img.shields.io/pypi/v/banxicolab)](https://pypi.org/project/banxicolab/)
[![Pruebas](https://github.com/AnaJZP/banxicolab/actions/workflows/pruebas.yml/badge.svg)](https://github.com/AnaJZP/banxicolab/actions/workflows/pruebas.yml)
[![Documentación](https://img.shields.io/badge/docs-anajzp.github.io-800020)](https://anajzp.github.io/banxicolab/)

Series del **Sistema de Información Económica (SIE) de Banco de México** en un
`DataFrame`, con el token fuera del código y las transformaciones habituales
para analizar inflación, tipo de cambio y tasas.

> Librería **no oficial**. No está afiliada ni respaldada por Banco de México.

## Primeros pasos

En este orden. Los tres primeros pasos se hacen una sola vez.

**1. Instala** (en un notebook o en Colab, usa `%pip` en lugar de `pip`):

```bash
pip install banxicolab
```

**2. Importa:**

```python
import banxicolab as sie
```

**3. Configura tu token.** Es gratuito y se genera en
<https://www.banxico.org.mx/SieAPIRest/service/v1/token>. Guárdalo con:

```python
sie.guardar_token()
```

Pégalo cuando te lo pida (no se muestra en pantalla). La librería lo comprueba
con Banxico y lo guarda en un archivo privado; no hay que volver a escribirlo
ni ponerlo en el código. En Google Colab conviene usar los *Secrets*: ver
[Token](https://anajzp.github.io/banxicolab/token/).

**4. Descarga y analiza:**

```python
datos = sie.panel(["inpc", "fix", "tasa_objetivo"], inicio="2015-01-01")
sie.inflacion(datos["inpc"]).tail()
```

La guía completa, con la solución a los errores más comunes, está en
**<https://anajzp.github.io/banxicolab/>**.

Requiere Python ≥ 3.10. La instalación incluye lo necesario para todos los
análisis (`pandas`, `statsmodels`, `matplotlib`).

## Descargar

Hay tres formas de pedir datos; se pueden mezclar en la misma llamada.

```python
import banxicolab as sie

# 1. Por clave del SIE: cualquier serie de Banxico, esté o no en el catálogo
sie.descargar("SF43718")
sie.descargar({"SF43718": "FIX", "SF61745": "Objetivo"}, inicio="2020-01-01")

# 2. Por alias del catálogo: sin memorizar claves
sie.descargar(["inpc", "fix", "tasa_objetivo"], "2000-01-01", "2026-12-31")

# 3. Un tema completo del catálogo
sie.descargar(tema="tasas", inicio="2020-01-01")
```

`descargar` devuelve un `DataFrame` con `DatetimeIndex` y valores `float`. Se
encarga de lo que suele fallar en silencio: fechas `dd/mm/aaaa`, `N/E`, comas
de miles, más de 20 series por consulta, reintentos y límite de consultas.

### Panel mensual en un paso

Las series del SIE vienen en frecuencias distintas. `panel` las descarga y las
lleva a frecuencia mensual, cada una con la regla que indica el catálogo
(último dato para precios y saldos, promedio para tasas):

```python
sie.panel(["inpc", "igae", "fix", "tasa_objetivo", "cetes_28"], "2000-01-01")
sie.panel(tema="tasas", inicio="2015-01-01")
sie.panel({"SF43718": "FIX"}, como={"FIX": "promedio"})  # cambiar la regla
```

### Encontrar una serie

```python
sie.catalogo()  # todos los alias
sie.catalogo("precios")  # los de un tema
sie.catalogo(buscar="cetes")  # por texto, en el catálogo de la librería
sie.buscar("remesas")  # en todo el SIE de Banxico (sin token)
sie.metadatos(["inpc", "fix"])  # periodicidad, unidad, cobertura
sie.oportuno(["fix", "tasa_objetivo"])  # último dato publicado
```

## Catálogo

Las 35 series con alias. La columna *A mensual* es la regla que usa `panel`.
Cualquier otra clave del SIE funciona directamente con `descargar`.

### Precios

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

### Expectativas de inflación (encuesta de Banxico, mediana)

`tema="expectativas"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `expectativa_inflacion_12m` | `SR14195` | Expectativa de inflación general, próximos 12 meses | Mensual | % | ultimo |
| `expectativa_inflacion_cierre` | `SR14139` | Expectativa de inflación general, cierre del año en curso | Mensual | % | ultimo |
| `expectativa_inflacion_cierre_siguiente` | `SR14146` | Expectativa de inflación general, cierre del año siguiente | Mensual | % | ultimo |

### Tipo de cambio

`tema="tipo_de_cambio"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `fix` | `SF43718` | Tipo de cambio FIX, fecha de determinación | Diaria | MXN/USD | ultimo |
| `fix_liquidacion` | `SF60653` | Tipo de cambio FIX, fecha de liquidación | Diaria | MXN/USD | ultimo |
| `fix_promedio_mensual` | `SF17908` | Tipo de cambio FIX, promedio del mes | Mensual | MXN/USD | ultimo |
| `euro` | `SF46410` | Pesos por euro | Diaria | MXN/EUR | ultimo |

### Tasas de interés

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

### Actividad y salarios

`tema="actividad"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `igae` | `SR17692` | IGAE base 2018, serie original | Mensual | Índice | ultimo |
| `igae_desestacionalizado` | `SR17693` | IGAE base 2018, serie desestacionalizada | Mensual | Índice | ultimo |
| `salario_minimo` | `SL11298` | Salario mínimo general | Mensual | Pesos por día | ultimo |

### Sector externo

`tema="externo"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `reservas` | `SF43707` | Reserva internacional | Diaria | Millones de USD | ultimo |
| `remesas` | `SE27803` | Remesas familiares, total | Mensual | Millones de USD | suma |

### Agregados monetarios

`tema="dinero"`

| Alias | Clave SIE | Serie | Periodicidad | Unidad | A mensual |
|---|---|---|---|---|---|
| `m1` | `SF311408` | Agregado monetario M1 | Mensual | Miles de pesos | ultimo |
| `m2` | `SF311418` | Agregado monetario M2 | Mensual | Miles de pesos | ultimo |

## Analizar

```python
diarias = sie.descargar(["fix", "tasa_objetivo", "cetes_28"], "2000-01-01")
mensual = sie.a_mensual(
    diarias, {"fix": "ultimo", "tasa_objetivo": "promedio", "cetes_28": "promedio"}
)
inpc = sie.serie("inpc", "2000-01-01")

sie.inflacion(inpc)  # mensual, anual, acumulada, anualizada
sie.a_pesos_de(1000, "2010-01-01", "2026-01-01", inpc)  # poder adquisitivo
sie.deflactar(mensual["fix"], inpc, base="2018-07-01")  # pesos constantes
sie.tasa_real(mensual["cetes_28"], sie.variacion_anual(inpc))  # Fisher exacta
sie.indice_base(mensual, "2018-01-01")  # base 100 para comparar
sie.prueba_adf({"nivel": inpc, "Δln": sie.variacion(inpc, log=True)})
```

## Inflación: mercado y pronósticos

```python
bmx = sie.Banxico()

bmx.inflacion_implicita(10, "2015-01-01")  # rendimiento de Bono M y Udibono, e implícita
sie.rendimiento_bono(90.63, cupon=8.0, plazo_dias=3426)  # convención mexicana 182/360

sie.impulso(sie.serie("inpc_subyacente"), 3)  # 3m/3m anualizado
sie.pronosticar_inflacion(inpc, 12)  # SARIMA con intervalo
sie.evaluar_pronosticos(inpc, desde="2012-01-01")  # error fuera de muestra vs. método ingenuo
```

## Documentación

La guía completa y la referencia de cada función están en
**<https://anajzp.github.io/banxicolab/>**.

Para verla en tu computadora mientras la editas:

```bash
pip install -e ".[docs]"
mkdocs serve
```

## Ejemplos

- `examples/inicio_rapido.ipynb`: descarga, inflación y tasa real en pocas celdas.
- `examples/seminario_transformaciones.ipynb`: el seminario completo de
  transformaciones, con cada una justificada y verificada con la prueba ADF.
- `examples/inflacion_mercado_y_pronosticos.ipynb`: medidas de tendencia, inflación
  implícita en Bonos M y Udibonos, y pronósticos evaluados fuera de muestra.

## Desarrollo

```bash
pip install -e ".[dev]"
pytest              # pruebas sin red
pytest -m red       # verifica el catálogo de alias contra Banxico (sin token)
```

## Autoría

Ana Lorena Jiménez Preciado · Escuela Superior de Economía, Instituto Politécnico Nacional.

## Datos

Los datos pertenecen a Banco de México y están sujetos a sus
[términos de uso](https://www.banxico.org.mx/SieAPIRest/service/v1/doc/salvedad).
