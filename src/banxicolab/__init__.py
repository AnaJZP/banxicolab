"""banxicolab: series del SIE de Banco de México listas para analizar.

>>> import banxicolab as sie
>>> df = sie.descargar(["inpc", "fix"], inicio="2015-01-01")   # doctest: +SKIP
>>> sie.inflacion(df["inpc"]).tail()                            # doctest: +SKIP

Librería no oficial; no está afiliada a Banco de México.
"""

from .alias import CATALOGO, TEMAS, catalogo
from .cliente import (
    Banxico,
    buscar,
    descargar,
    info,
    metadatos,
    oportuno,
    panel,
    serie,
)
from .diagnostico import diagnostico, prueba_adf
from .errores import (
    BanxicoError,
    ErrorDeConexion,
    LimiteExcedido,
    SerieNoEncontrada,
    SinDatos,
    TokenInvalido,
    TokenNoEncontrado,
)
from .precios import impulso, inflacion, inflacion_entre, persistencia
from .pronostico import evaluar_pronosticos, pronosticar_inflacion
from .renta_fija import (
    inflacion_implicita,
    inflacion_implicita_forward,
    precio_bono,
    rendimiento_bono,
)
from .token import borrar_token, guardar_token, obtener_token
from .transformaciones import (
    a_mensual,
    a_pesos_de,
    anualizar,
    cambiar_base,
    deflactar,
    desestacionalizar,
    empalmar,
    escalar_robusto,
    estandarizar,
    frecuencia,
    indice_base,
    min_max,
    tasa_real,
    valor_en,
    variacion,
    variacion_anual,
)

__version__ = "0.3.1"

__all__ = [
    "TEMAS",
    "panel",
    "rendimiento_bono",
    "precio_bono",
    "inflacion_implicita_forward",
    "inflacion_implicita",
    "pronosticar_inflacion",
    "evaluar_pronosticos",
    "persistencia",
    "impulso",
    "CATALOGO",
    "Banxico",
    "BanxicoError",
    "ErrorDeConexion",
    "LimiteExcedido",
    "SerieNoEncontrada",
    "SinDatos",
    "TokenInvalido",
    "TokenNoEncontrado",
    "a_mensual",
    "a_pesos_de",
    "anualizar",
    "borrar_token",
    "buscar",
    "cambiar_base",
    "catalogo",
    "deflactar",
    "descargar",
    "desestacionalizar",
    "diagnostico",
    "empalmar",
    "escalar_robusto",
    "estandarizar",
    "frecuencia",
    "guardar_token",
    "indice_base",
    "inflacion",
    "inflacion_entre",
    "info",
    "metadatos",
    "min_max",
    "obtener_token",
    "oportuno",
    "prueba_adf",
    "serie",
    "tasa_real",
    "valor_en",
    "variacion",
    "variacion_anual",
]
