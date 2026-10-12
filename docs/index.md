# banxicolab

Series del **Sistema de Información Económica (SIE) de Banco de México** en un
`DataFrame`, con el token fuera del código y las transformaciones habituales
para analizar inflación, tipo de cambio y tasas.

!!! note "Librería no oficial"
    No está afiliada ni respaldada por Banco de México. Los datos son de Banxico
    y están sujetos a sus términos de uso.

## En un minuto

```bash
pip install "banxicolab[analisis]"
banxicolab token               # guarda tu token una sola vez, sin mostrarlo
```

```python
import banxicolab as sie

df = sie.descargar(["inpc", "fix", "tasa_objetivo"], inicio="2015-01-01")
sie.inflacion(df["inpc"]).tail()
```

## Qué resuelve

| Problema al usar la API directamente | Qué hace la librería |
|---|---|
| El token termina pegado en el notebook | Lo lee del entorno, de Colab Secrets o de un archivo privado; nunca aparece en URLs, errores ni `repr` |
| Fechas `dd/mm/aaaa` que pandas puede leer al revés | Formato explícito |
| `N/E` y comas de miles (`"193,045.50"`) que se vuelven `NaN` en silencio | Limpieza numérica correcta |
| Máximo 20 series por consulta | Parte la consulta en lotes |
| Límite de 200 consultas cada 5 minutos | Caché en memoria, espera automática si el bloqueo es corto y un error claro si no |
| Una serie mal escrita falla sin explicación | `SerieNoEncontrada` con sugerencias |
| Hay que memorizar `SF43718` | Alias (`"fix"`) y buscador de series |

## Por dónde seguir

- [Token](token.md): configurarlo en tu computadora, en Colab o en un servidor.
- [Descargar series](descarga.md): todas las formas de pedir datos.
- [Transformaciones](transformaciones.md): índices, variaciones, deflactar, escalar, estacionalidad.
- [Inflación](inflacion.md): un análisis completo de principio a fin.
- [Tendencia y pronósticos](pronosticos.md): impulso, persistencia, SARIMA y su evaluación fuera de muestra.
- [Rendimientos e inflación implícita](mercado.md): qué inflación descuentan los Bonos M y Udibonos.
- [Referencia](referencia.md): cada función con sus parámetros.
