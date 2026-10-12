# Token

La API del SIE pide un token gratuito de 64 caracteres. Se genera en
<https://www.banxico.org.mx/SieAPIRest/service/v1/token>.

El token identifica tus consultas: si alguien más lo usa, **tu** límite se agota
y Banxico bloquea **tu** token. Por eso la regla es que nunca quede escrito en
un notebook, un script o un repositorio.

## Dónde lo busca la librería

En este orden, y se queda con el primero que encuentre:

| # | Fuente | Cuándo conviene |
|---|---|---|
| 1 | Argumento `Banxico(token=...)` | Pruebas; evítalo en código que compartes |
| 2 | Variable de entorno `BANXICO_TOKEN` (o `BMX_TOKEN`) | Servidores, tareas programadas, CI |
| 3 | *Secrets* de Google Colab con ese nombre | Colab |
| 4 | Archivo guardado con `banxicolab token` | Tu computadora |
| 5 | Pregunta con `getpass` | Primera vez, o equipos prestados |

## En tu computadora

```bash
banxicolab token
```

Lo pide sin mostrarlo y lo guarda en `~/.config/banxicolab/token` (en Windows,
`%APPDATA%\banxicolab\token`) con permisos `600`: solo tu usuario puede leerlo.
Desde Python es equivalente a `sie.guardar_token()`.

Para eliminarlo:

```bash
banxicolab token --borrar
```

## En Google Colab

1. Abre el panel **Secrets** (ícono de llave en la barra izquierda).
2. Crea un secreto llamado `BANXICO_TOKEN` y activa *Notebook access*.
3. Usa la librería normalmente; no hay que escribir nada más.

Los secretos viven en tu cuenta, no en el archivo `.ipynb`, así que puedes
compartir el notebook sin compartir el token.

## Con variable de entorno

```bash
export BANXICO_TOKEN="pega-aquí-tu-token"
```

!!! warning "Si usas un archivo `.env`"
    Agrégalo a `.gitignore`. El de este proyecto ya lo incluye.

## Qué más hace para protegerlo

- Viaja en el encabezado `Bmx-Token`, no en la URL: no queda en historiales,
  bitácoras de proxy ni mensajes de error.
- `repr(sie.Banxico())` muestra solo `••••` y los últimos 4 caracteres.
- Los mensajes de las excepciones nunca incluyen el token.

Si aun así se expuso (lo subiste a GitHub, lo pegaste en un chat), genera uno
nuevo y deja de usar el anterior.
