# Token

La API del SIE pide un token gratuito de 64 caracteres. Se genera en
<https://www.banxico.org.mx/SieAPIRest/service/v1/token>.

El token identifica tus consultas: si alguien más lo usa, **tu** límite se agota
y Banxico bloquea **tu** token. Por eso la regla es que nunca quede escrito en
un notebook, un script o un repositorio.

## En tu computadora

Una sola vez, desde Python o un notebook:

```python
import banxicolab as sie

sie.guardar_token()
```

Te lo pide sin mostrarlo, lo comprueba con Banxico y lo guarda. Debes ver:

```text
Pega tu token del SIE (no se mostrará en pantalla): ········
Token verificado con Banxico y guardado. Ya puedes descargar series.
```

Queda en `~/.config/banxicolab/token` (en Windows,
`%APPDATA%\banxicolab\token`), en un archivo que solo tu usuario puede leer.
A partir de ahí no hay que hacer nada más: cualquier script o notebook lo
encuentra solo.

Si Banxico rechaza el token, o lo pegaste incompleto, no se guarda nada y el
mensaje explica qué pasó.

Para cambiarlo, vuelve a ejecutar `sie.guardar_token()`. Para eliminarlo:

```python
sie.borrar_token()
```

??? note "Lo mismo desde la terminal"

    ```bash
    banxicolab token
    ```

    ```bash
    banxicolab token --borrar
    ```

    Si la terminal no reconoce el comando `banxicolab`, usa
    `python -m banxicolab token`.

## En Google Colab

Colab borra los archivos al cerrar la sesión, así que `guardar_token()`
funcionaría solo hasta que se reinicie. Lo permanente es usar los *Secrets*:

1. Abre el panel **Secrets** (ícono de llave en la barra izquierda).
2. Pulsa **Add new secret**. En *Name* escribe `BANXICO_TOKEN` y en *Value*
   pega tu token.
3. Activa el interruptor **Notebook access**.

Listo: usa la librería normalmente, sin escribir nada más en el notebook.

Los secretos viven en tu cuenta de Google, no en el archivo `.ipynb`, así que
puedes compartir el notebook sin compartir el token. En cada notebook nuevo hay
que volver a activar *Notebook access*.

## En un servidor o tarea programada

Donde nadie puede responder a una pregunta, define la variable de entorno:

```bash
export BANXICO_TOKEN="pega-aquí-tu-token"
```

!!! warning "Si usas un archivo `.env`"
    Agrégalo a `.gitignore` para que no llegue a tu repositorio.

## Dónde busca el token la librería

En este orden, y se queda con el primero que encuentre:

| # | Fuente | Cuándo conviene |
|---|---|---|
| 1 | Argumento `sie.Banxico(token=...)` | Pruebas; evítalo en código que compartes |
| 2 | Variable de entorno `BANXICO_TOKEN` (o `BMX_TOKEN`) | Servidores, tareas programadas |
| 3 | *Secrets* de Google Colab con ese nombre | Colab |
| 4 | Archivo creado por `sie.guardar_token()` | Tu computadora |
| 5 | Pregunta en el momento, sin guardarlo | Equipos prestados |

Si Banxico rechaza un token, el mensaje de error indica de cuál de estas
fuentes se tomó. Es útil cuando una variable de entorno vieja está tapando al
token que acabas de guardar.

## Qué más hace para protegerlo

- Viaja en el encabezado `Bmx-Token`, no en la URL: no queda en historiales,
  bitácoras de proxy ni mensajes de error.
- `repr(sie.Banxico())` muestra solo `••••` y los últimos 4 caracteres.
- Los mensajes de las excepciones nunca incluyen el token.

Si aun así se expuso (lo subiste a GitHub, lo pegaste en un chat), genera uno
nuevo en la página de Banxico y guárdalo con `sie.guardar_token()`.
