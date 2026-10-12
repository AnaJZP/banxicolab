# Descargar series

Todas las funciones existen en dos formas equivalentes: como función del módulo
(`sie.descargar(...)`, usa un cliente compartido) o como método de un cliente
propio (`sie.Banxico().descargar(...)`), útil para ajustar tiempos de espera o
proxies.

## `descargar`

```python
import banxicolab as sie

# Una serie, historia completa
sie.descargar("inpc")

# Varias, por alias o por identificador del SIE, en un rango de fechas
sie.descargar(["inpc", "SR17692"], "2000-01-01", "2026-12-31")

# Eligiendo el nombre de las columnas
sie.descargar({"SF43718": "FIX", "SF61745": "Objetivo"}, inicio="2020-01-01")
```

El resultado es un `DataFrame` con:

- índice `DatetimeIndex` llamado `fecha`, ordenado;
- una columna `float` por serie, en el orden en que las pediste;
- `NaN` donde el SIE reporta `N/E`; las fechas sin ningún dato se descartan;
- los títulos oficiales en `df.attrs["series"]`.

Las fechas aceptan cualquier formato que entienda pandas (`"2020"`,
`"2020-03"`, `datetime.date`, `pd.Timestamp`). Si omites `fin` se usa hoy.

!!! tip "Mezclar frecuencias"
    Puedes pedir series diarias y mensuales juntas, pero la tabla tendrá `NaN`
    en los días sin dato mensual. Lo más limpio es descargarlas por separado y
    unirlas después de [`a_mensual`](transformaciones.md#de-diario-a-mensual).

### Un tema completo

```python
sie.descargar(tema="tipo_de_cambio", inicio="2020-01-01")
```

Los temas son `precios`, `expectativas`, `tipo_de_cambio`, `tasas`, `actividad`,
`externo` y `dinero`; ver el [catálogo](catalogo.md).

### Variaciones calculadas por Banxico

```python
sie.descargar("inpc", "2020-01-01", incremento="anual")
```

| `incremento` | Variación porcentual respecto a… |
|---|---|
| `"mensual"` | la observación anterior |
| `"anual"` | la misma observación del año anterior |
| `"acumulado"` | la última observación del año anterior |

## Panel mensual

`panel` descarga y deja todo en frecuencia mensual, fechado al día 1:

```python
sie.panel(["inpc", "igae", "fix", "tasa_objetivo", "cetes_28"], "2000-01-01")
```

Cada serie se agrega con la regla de su ficha en el catálogo: `ultimo` para
precios y saldos, `promedio` para tasas, y promedio de las dos quincenas para
los índices quincenales (así se define el INPC mensual). Las series que ya son
mensuales solo se alinean.

Para una clave que no está en el catálogo la regla por omisión es `ultimo`; con
`como` se cambia la de cualquier columna:

```python
sie.panel({"SF43718": "FIX", "SF43773": "fondeo"}, como={"fondeo": "promedio"})
```

La regla aplicada queda en `df.attrs["agregacion"]`.

### `serie`

Para una sola serie, devuelve un `pandas.Series` sin faltantes:

```python
fix = sie.serie("fix", "2020-01-01")
```

## Antes de descargar: qué es cada serie

```python
sie.catalogo()  # alias incluidos en la librería
sie.catalogo("tasas")  # solo un tema
sie.catalogo(buscar="cetes")  # por texto
sie.buscar("subyacente")  # busca en el catálogo de Banxico; no usa token
sie.info("SP74625")  # ficha de una serie; no usa token
sie.metadatos(["inpc", "fix"])  # incluye fecha de inicio y fin; usa token
```

`metadatos` responde lo que hay que saber antes de transformar: periodicidad,
si es índice, tasa o saldo, la unidad y la cobertura.

!!! info "Sobre `buscar`"
    Usa el buscador de la página del catálogo del SIE, que no es parte de la API
    documentada. Funciona mejor con una o dos palabras (`"cetes"`, `"remesas"`)
    y podría cambiar sin aviso. Si deja de funcionar, el catálogo se puede
    consultar en <https://www.banxico.org.mx/SieAPIRest/service/v1/doc/catalogoSeries>.

## Último dato publicado

```python
sie.oportuno(["fix", "tasa_objetivo", "udis"])
```

Es la consulta indicada para tableros o revisiones diarias: tiene un límite más
holgado (80 por minuto) que la histórica.

## Límites de consulta

Banxico limita cada token a:

| Tipo | Ventana | Diario |
|---|---|---|
| Históricas (`descargar`) | 200 cada 5 minutos | 10,000 |
| Oportunas y metadatos | 80 por minuto | 40,000 |

La librería ayuda de tres formas:

1. **Lotes**: 45 series son 3 consultas, no 45.
2. **Caché en memoria**: repetir la misma descarga en la misma sesión no gasta
   consultas. `sie.Banxico().limpiar_cache()` la vacía; `Banxico(cache=False)`
   la desactiva.
3. **Espera**: si el token queda bloqueado por menos de `espera_maxima`
   segundos (60 por omisión), espera y reintenta; si es más, lanza
   `LimiteExcedido` con los segundos restantes en `.segundos`.

## Errores

Todas heredan de `sie.BanxicoError`.

| Excepción | Significa |
|---|---|
| `TokenNoEncontrado` | No hay token configurado |
| `TokenInvalido` | Banxico rechazó el token |
| `SerieNoEncontrada` | La clave no existe (trae sugerencias si es un alias mal escrito) |
| `SinDatos` | Ninguna serie tiene observaciones en el periodo |
| `LimiteExcedido` | Se agotó el límite de consultas |
| `ErrorDeConexion` | Falló la red después de los reintentos |

Si solo *algunas* series vienen vacías en el periodo, no es un error: se emite
una advertencia y esas columnas quedan en `NaN`.

## Desde la terminal

```bash
banxicolab descargar inpc fix --inicio 2020-01-01 -o datos.csv
```

```bash
banxicolab descargar --tema tasas --mensual --inicio 2015-01-01 -o tasas.csv
```

```bash
banxicolab catalogo precios
```

```bash
banxicolab buscar remesas
```

```bash
banxicolab metadatos inpc SF43718
```
