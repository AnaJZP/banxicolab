# banxicolab

Series del **Sistema de Información Económica (SIE) de Banco de México**
directamente en un `DataFrame` de pandas, con herramientas para analizar
inflación, tipo de cambio y tasas de interés.

!!! note "Librería no oficial"
    No está afiliada ni respaldada por Banco de México. Los datos son de Banxico
    y están sujetos a sus términos de uso.

## Primeros pasos

Sigue los cuatro pasos **en este orden**. Los tres primeros se hacen una sola
vez por computadora; después, basta con importar y descargar.

### 1. Instala la librería

=== "Jupyter o Google Colab"

    En una celda del notebook:

    ```python
    %pip install banxicolab
    ```

=== "Terminal"

    ```bash
    pip install banxicolab
    ```

Requiere Python 3.10 o posterior. Con eso se instala todo lo necesario,
incluidas las librerías que usan los pronósticos y las gráficas.

### 2. Impórtala

```python
import banxicolab as sie

print(sie.__version__)
```

Si aparece el número de versión, la instalación quedó bien. Si sale
`ModuleNotFoundError`, ve a [Si algo falla](#si-algo-falla).

### 3. Configura tu token

La API de Banxico pide un token personal y gratuito de 64 caracteres.

**a) Consíguelo.** Entra a
<https://www.banxico.org.mx/SieAPIRest/service/v1/token>, sigue las
instrucciones de la página y copia el token completo.

**b) Guárdalo.** Ejecuta:

```python
sie.guardar_token()
```

Aparecerá un cuadro para escribir (en VS Code sale arriba, al centro de la
ventana). Pega el token y presiona Enter; no se muestra en pantalla mientras lo
pegas. Debes ver:

```text
Pega tu token del SIE (no se mostrará en pantalla): ········
Token verificado con Banxico y guardado. Ya puedes descargar series.
```

La librería comprueba el token con Banxico antes de guardarlo. Si lo copiaste
incompleto o Banxico lo rechaza, te lo dice ahí mismo y no guarda nada: vuelve
a copiarlo y repite el paso.

!!! tip "Solo una vez"
    El token queda en un archivo privado de tu computadora y la librería lo
    encuentra sola en adelante. No vuelvas a ejecutar `guardar_token()` ni
    escribas el token dentro de tu código: así puedes compartir tus notebooks
    sin exponerlo.

!!! info "En Google Colab"
    Colab borra los archivos al cerrar la sesión, así que habría que repetir
    este paso cada vez. Para evitarlo, guarda el token en los *Secrets* de
    Colab; está explicado en [Token](token.md#en-google-colab).

### 4. Descarga tus primeras series

```python
datos = sie.panel(["inpc", "fix", "tasa_objetivo"], inicio="2026-04-01", fin="2026-08-31")
datos
```

```text
               inpc     fix  tasa_objetivo
fecha
2026-04-01  145.831  17.512          6.750
2026-05-01  145.527  17.350          6.556
2026-06-01  145.131  17.469          6.500
2026-07-01  145.169  17.329          6.500
2026-08-01  145.462  17.015          6.500
```

Si ves una tabla como esta, todo funciona. `panel` descargó el INPC (mensual),
el tipo de cambio FIX y la tasa objetivo (diarios) y los dejó en frecuencia
mensual.

## Ahora sí, a analizar

Con las series descargadas, cada análisis es una línea:

```python
inpc = sie.serie("inpc", "2015-01-01")

sie.inflacion(inpc).tail()  # mensual, anual, acumulada y anualizada
sie.pronosticar_inflacion(inpc, 12)  # pronóstico a 12 meses con intervalo
sie.Banxico().inflacion_implicita(10)  # la que descuentan Bonos M y Udibonos
```

<div class="grid cards" markdown>

-   **[Descargar series](descarga.md)**

    Por clave del SIE, por alias o un tema completo. Paneles mensuales, último
    dato y búsqueda de series.

-   **[Catálogo](catalogo.md)**

    Las 35 series con nombre corto: `"inpc"`, `"fix"`, `"cetes_28"`,
    `"tasa_objetivo"`…

-   **[Transformaciones](transformaciones.md)**

    Índices, variaciones, deflactar, tasa real, escalamientos y
    estacionalidad.

-   **[Inflación](inflacion.md)**

    Un análisis completo, del índice a la tasa de interés real.

-   **[Tendencia y pronósticos](pronosticos.md)**

    Impulso, persistencia y pronósticos SARIMA evaluados fuera de muestra.

-   **[Rendimientos e inflación implícita](mercado.md)**

    Qué inflación descuentan los precios de los bonos del gobierno.

</div>

## Si algo falla

| Mensaje | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'banxicolab'` | Se instaló en otro Python, o falta reiniciar | En el notebook instala con `%pip` (no con `!pip`) y reinicia el kernel |
| `TokenNoEncontrado` | Aún no configuras el token | Ejecuta `sie.guardar_token()` (paso 3) |
| `TokenInvalido: … recibí 40 caracteres` | Token copiado incompleto | Cópialo de nuevo; son 64 caracteres |
| `TokenInvalido: Banxico rechazó el token` | Token equivocado o dado de baja | Genera otro y repite el paso 3. El mensaje dice de dónde se tomó el token rechazado |
| `SerieNoEncontrada` | Clave o alias mal escrito | Revisa el [catálogo](catalogo.md) o usa `sie.buscar("texto")` |
| `LimiteExcedido` | Más de 200 consultas en 5 minutos | Espera los segundos que indica el mensaje |
| No aparece dónde pegar el token | El notebook se ejecuta sin interacción | Ejecuta la celda a mano, o define la variable de entorno `BANXICO_TOKEN` |

## Qué resuelve

| Al usar la API directamente… | Con la librería |
|---|---|
| El token termina pegado en el notebook | Se guarda aparte y nunca aparece en el código, las URLs ni los errores |
| Fechas `dd/mm/aaaa` que pandas puede leer al revés | Se leen con formato explícito |
| `N/E` y comas de miles (`"193,045.50"`) que se vuelven `NaN` en silencio | Limpieza numérica correcta |
| Máximo 20 series por consulta | La consulta se parte en lotes |
| Límite de 200 consultas cada 5 minutos | Caché en memoria y espera automática si el bloqueo es corto |
| Series diarias y mensuales que no se alinean | `panel` las lleva a frecuencia mensual con la regla correcta |
| Hay que memorizar `SF43718` | Alias (`"fix"`), temas y buscador de series |
