# Cambios

## 0.4.1 — 2026-11-03

- Gráficas interactivas con Plotly y paleta en escala de azules. `graficar` devuelve una figura
  de Plotly (con `interactivo=False`, una gráfica fija de matplotlib).
- Funciones de una línea para las gráficas más laboriosas: `graficar_contribuciones`,
  `graficar_curva` y `graficar_pronostico`.
- Corrige un docstring que impedía publicar la documentación de la 0.4.0.

## 0.4.0 — 2026-11-03

- `anticipar_inflacion`: estima la inflación del mes con su primera quincena ya publicada, con
  rango y validación histórica (`historial=True`).
- `contribuciones` y `Banxico.contribuciones_inflacion`: aportación de cada componente a la
  inflación, exacta dentro de cada periodo de ponderadores y encadenada entre periodos.
- `nelson_siegel`, `Banxico.curva_rendimientos` y `Banxico.curva_historica`: curva de
  rendimientos de Cetes y Bonos M.
- `graficar` y `PALETA`: gráficas con estilo propio y la fuente citada.
- Caché en disco: `Banxico(cache="disco")` o `configurar(cache="disco")`.
- Alias nuevos: `inpc_mercancias`, `inpc_servicios`, `inpc_agropecuarios`, `inpc_energeticos`.
- Notebooks de ejemplo que se abren en Google Colab e instalan la librería solos.
- Revisión semanal automática contra la API de Banxico y archivo de cita (`CITATION.cff`).

## 0.3.3 — 2026-10-12

- Se elimina el extra `[analisis]`, que ya no hacía falta.

## 0.3.2 — 2026-10-12

- La instalación es simplemente `pip install banxicolab`: `statsmodels` y `matplotlib` pasan a
  instalarse siempre.

## 0.3.1 — 2026-10-12

- `guardar_token()` comprueba el token con Banxico antes de guardarlo y confirma el resultado.
- Mensajes de error más claros: qué hacer cuando falta el token, cuántos caracteres llegaron si
  está incompleto y de dónde salió el token que Banxico rechazó.
- Un token rechazado ya no se queda en memoria: al corregirlo no hace falta reiniciar.
- Se toleran comillas y espacios al pegar el token.
- `python -m banxicolab` como alternativa cuando el comando no está en el PATH.
- Documentación: página de inicio reescrita como guía paso a paso.

## 0.3.0 — 2026-10-12

Primera versión en PyPI. El paquete se llama `banxicolab` (antes `siebanxico`, nombre que PyPI
rechazó por parecerse a otro paquete existente).

- `panel`: descarga y deja las series en frecuencia mensual con la regla de agregación del catálogo.
- `descargar(tema=...)` y `panel(tema=...)`: un tema completo del catálogo.
- `catalogo(tema, buscar=...)`: el catálogo ahora está organizado por temas y se puede filtrar.
- Los índices quincenales se agregan a mensual por promedio, como define el INPC.
- Terminal: `banxicolab catalogo [tema]`, `banxicolab descargar --tema ... --mensual`.

## 0.2.0 — 2026-10-06

- `Banxico.inflacion_implicita`: rendimientos diarios de Bonos M y Udibonos e inflación implícita.
- `rendimiento_bono`, `precio_bono`, `inflacion_implicita`, `inflacion_implicita_forward`.
- `pronosticar_inflacion` (SARIMA e ingenuo) y `evaluar_pronosticos` (origen móvil).
- `impulso` y `persistencia`.
- Alias nuevos: INPC quincenal, media truncada, expectativas de la encuesta, subastas a 10 años.
- `variacion_anual` acepta series quincenales.
- El cliente vuelve a pedir las series que falten en una respuesta parcial del SIE, y una clave
  inexistente (HTTP 404) se reporta como `SerieNoEncontrada`.

## 0.1.0 — 2026-10-06

Primera versión.

- Cliente `Banxico`: `descargar`, `serie`, `metadatos`, `oportuno`, `buscar`, `info`, `inflacion`.
- Manejo del token fuera del código (entorno, Colab Secrets, archivo privado, `getpass`).
- Catálogo de alias para las series más usadas.
- Transformaciones: índices, variaciones, deflactar, tasa real, escalamientos, ajuste estacional.
- Diagnóstico y prueba ADF.
- Comando `banxicolab` para la terminal.
