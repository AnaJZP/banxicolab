# Cambios

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
