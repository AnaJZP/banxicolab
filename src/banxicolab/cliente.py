"""Cliente de la API REST del Sistema de Información Económica (SIE)."""

from __future__ import annotations

import re
import time
import warnings
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd
import requests

from . import alias as _catalogo
from ._cache import CacheDisco
from .errores import (
    BanxicoError,
    ErrorDeConexion,
    LimiteExcedido,
    SerieNoEncontrada,
    SinDatos,
    TokenInvalido,
)
from .token import _resolver as _resolver_token
from .token import enmascarar

URL_BASE = "https://www.banxico.org.mx/SieAPIRest/service/v1"
MAX_SERIES_POR_CONSULTA = 20  # límite documentado por Banxico
INCREMENTOS = {
    "mensual": "PorcObsAnt",  # respecto a la observación anterior
    "anual": "PorcAnual",  # respecto a la misma observación del año anterior
    "acumulado": "PorcAcumAnual",  # respecto a la última observación del año anterior
}

Series = str | Iterable[str] | Mapping[str, str]
Fecha = str | pd.Timestamp | Any


def _resolver_series(series: Series | None, tema: str | None = None) -> dict[str, str]:
    """Normaliza la entrada del usuario a ``{id_serie: nombre_de_columna}``."""
    if tema is not None:
        if series is not None:
            raise ValueError("Indica series o tema, no ambos.")
        series = _catalogo.de_tema(tema)
    if series is None:
        raise ValueError("Debes indicar al menos una serie o un tema.")
    if isinstance(series, str):
        pares: Iterable[tuple[str, str | None]] = [(series, None)]
    elif isinstance(series, Mapping):
        pares = list(series.items())
    else:
        pares = [(s, None) for s in series]

    resueltas: dict[str, str] = {}
    for clave, nombre in pares:
        id_serie, por_defecto = _catalogo.resolver(clave)
        resueltas.setdefault(id_serie, nombre or por_defecto)
    if not resueltas:
        raise ValueError("Debes indicar al menos una serie.")
    repetidos = {n for n in resueltas.values() if list(resueltas.values()).count(n) > 1}
    if repetidos:
        raise ValueError(f"Nombres de columna repetidos: {sorted(repetidos)}")
    return resueltas


def _fecha(valor: Fecha) -> str:
    return pd.Timestamp(valor).strftime("%Y-%m-%d")


def _a_numero(datos: pd.Series) -> pd.Series:
    # El SIE manda texto: 'N/E' cuando no hay dato y comas como separador de miles
    # ('1,234.56'). Sin quitar las comas, to_numeric los volvería NaN en silencio.
    limpio = datos.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(limpio, errors="coerce")


def _limpiar_titulo(titulo: str) -> str:
    return re.sub(r"\s+", " ", titulo or "").strip()


class Banxico:
    """Cliente del SIE de Banco de México.

    Parameters
    ----------
    token : str, opcional
        Token de consulta. Lo normal es **no** pasarlo y dejar que se resuelva
        desde el entorno; ver :func:`banxicolab.obtener_token`.
    timeout : float
        Segundos de espera por petición.
    reintentos : int
        Reintentos ante fallas de red o errores 5xx (con espera creciente).
    cache : {True, "disco", False}
        ``True`` guarda las respuestas en memoria mientras dura la sesión.
        ``"disco"`` además las guarda en un archivo local, de modo que volver a
        ejecutar un notebook o un script no gasta consultas. ``False`` no
        guarda nada. Banxico recomienda expresamente cachear.
    vigencia_cache : float
        Horas que una respuesta guardada en disco se considera vigente.
    carpeta_cache : str o Path, opcional
        Dónde guardar la caché en disco; por omisión ``~/.cache/banxicolab``.
    espera_maxima : float
        Si se supera el límite de consultas y el desbloqueo ocurre en menos de
        estos segundos, se espera y se reintenta; si no, se lanza
        :class:`~banxicolab.LimiteExcedido`.
    sesion : requests.Session, opcional
        Sesión propia (proxies, certificados corporativos, pruebas).

    Examples
    --------
    >>> import banxicolab as sie
    >>> bmx = sie.Banxico()                                   # doctest: +SKIP
    >>> bmx.descargar(["inpc", "fix"], inicio="2015-01-01")   # doctest: +SKIP
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: float = 30,
        reintentos: int = 3,
        cache: bool | str = True,
        vigencia_cache: float = 12,
        carpeta_cache=None,
        espera_maxima: float = 60,
        sesion: requests.Session | None = None,
    ):
        self._token_explicito = token
        self._token: str | None = None
        # Describe de dónde salió el token (no es el token)
        self._origen_token = ""  # nosec B105
        self.timeout = timeout
        self.reintentos = reintentos
        self.espera_maxima = espera_maxima
        self._sesion = sesion or requests.Session()
        if cache not in (True, False, "disco"):
            raise ValueError('cache debe ser True, False o "disco"')
        self._cache: dict[tuple, Any] | None = {} if cache else None
        self._disco = CacheDisco(carpeta_cache, vigencia_cache) if cache == "disco" else None

    def __repr__(self) -> str:
        token = enmascarar(self._token) if self._token else "sin resolver"
        return f"Banxico(token={token})"

    # ── Infraestructura ──────────────────────────────────────────────────────

    def limpiar_cache(self) -> None:
        """Olvida las respuestas guardadas, en memoria y en disco (p. ej. tras una publicación)."""
        if self._cache is not None:
            self._cache.clear()
        if self._disco is not None:
            self._disco.limpiar()

    def _pedir(self, ruta: str, params: dict | None = None, *, con_token: bool = True) -> dict:
        llave = (ruta, tuple(sorted((params or {}).items())))
        if self._cache is not None and llave in self._cache:
            return self._cache[llave]
        # El último dato publicado cambia a diario: no se guarda en disco
        en_disco = self._disco is not None and not ruta.endswith("/oportuno")
        if en_disco:
            guardado = self._disco.obtener(llave)
            if guardado is not None:
                self._cache[llave] = guardado
                return guardado

        # El token viaja en un encabezado, nunca en la URL: así no aparece en
        # mensajes de error, bitácoras ni historiales.
        encabezados = {"Accept": "application/json"}
        if con_token:
            if self._token is None:
                self._token, self._origen_token = _resolver_token(self._token_explicito)
            encabezados["Bmx-Token"] = self._token

        espero_limite = False
        intento = 0
        while True:
            try:
                resp = self._sesion.get(
                    f"{URL_BASE}/{ruta}", params=params, headers=encabezados, timeout=self.timeout
                )
            except requests.RequestException as error:
                if intento >= self.reintentos:
                    raise ErrorDeConexion(
                        f"No se pudo conectar con el SIE ({type(error).__name__})."
                    ) from error
                intento += 1
                time.sleep(min(2**intento, 30))
                continue

            if resp.status_code >= 500 and intento < self.reintentos:
                intento += 1
                time.sleep(min(2**intento, 30))
                continue

            try:
                cuerpo = resp.json()
            except ValueError:
                if resp.status_code == 404 and ruta.startswith("series/"):
                    claves = ruta.split("/")[1].split(",")
                    raise SerieNoEncontrada(f"El SIE no reconoce estas series: {claves}") from None
                raise BanxicoError(
                    f"El SIE respondió algo que no es JSON (HTTP {resp.status_code})."
                ) from None

            error = cuerpo.get("error") if isinstance(cuerpo, dict) else None
            if error:
                segundos = error.get("secondsToReset")
                if segundos is not None and not espero_limite and segundos <= self.espera_maxima:
                    espero_limite = True
                    time.sleep(float(segundos) + 1)
                    continue
                try:
                    self._lanzar(error)
                except TokenInvalido as rechazo:
                    origen = self._origen_token
                    self._token = None  # para que un token corregido se tome sin reiniciar
                    raise TokenInvalido(
                        f"Banxico rechazó el token (origen: {origen}). Revisa que esté "
                        "completo y guarda uno nuevo con banxicolab.guardar_token()."
                    ) from rechazo
            if resp.status_code >= 400:
                raise BanxicoError(f"El SIE respondió HTTP {resp.status_code}.")
            break

        if self._cache is not None:
            self._cache[llave] = cuerpo
        if en_disco:
            self._disco.guardar(llave, cuerpo)
        return cuerpo

    @staticmethod
    def _lanzar(error: dict) -> None:
        mensaje = error.get("mensaje", "Error del SIE")
        detalle = error.get("detalle", "")
        texto = f"{mensaje} {detalle}".strip()
        if error.get("secondsToReset") is not None:
            raise LimiteExcedido(texto, int(error["secondsToReset"]))
        if "token" in mensaje.lower():
            raise TokenInvalido(texto)
        raise BanxicoError(texto)

    def _por_lotes(self, ids: list[str], sufijo: str, params: dict | None = None) -> dict:
        """Pide las series de 20 en 20 y devuelve ``{id_serie: objeto}``."""
        objetos: dict[str, dict] = {}
        for i in range(0, len(ids), MAX_SERIES_POR_CONSULTA):
            lote = ids[i : i + MAX_SERIES_POR_CONSULTA]
            cuerpo = self._pedir(f"series/{','.join(lote)}{sufijo}", params)
            objetos.update({o["idSerie"]: o for o in cuerpo.get("bmx", {}).get("series", [])})
            # El SIE a veces responde con solo una parte de las series pedidas; antes
            # de darlas por inexistentes se piden otra vez, solas.
            faltan = [c for c in lote if c not in objetos]
            if faltan and len(faltan) < len(lote):
                try:
                    cuerpo = self._pedir(f"series/{','.join(faltan)}{sufijo}", params)
                except SerieNoEncontrada:
                    continue
                objetos.update({o["idSerie"]: o for o in cuerpo.get("bmx", {}).get("series", [])})
        return objetos

    # ── Consultas ────────────────────────────────────────────────────────────

    def descargar(
        self,
        series: Series | None = None,
        inicio: Fecha | None = None,
        fin: Fecha | None = None,
        *,
        tema: str | None = None,
        incremento: str | None = None,
    ) -> pd.DataFrame:
        """Descarga una o varias series y las devuelve alineadas por fecha.

        Hay tres formas de decir qué se quiere: por clave del SIE, por alias
        del catálogo o un tema completo.

        Parameters
        ----------
        series : str, lista o dict
            Identificadores del SIE (``"SF43718"``), alias del catálogo
            (``"fix"``) o un diccionario ``{clave: nombre_de_columna}``. No hay
            límite de 20 series: la consulta se parte en lotes automáticamente.
        tema : str, opcional
            En lugar de ``series``, todas las del catálogo de un tema
            (``"tasas"``, ``"tipo_de_cambio"``…); ver :func:`banxicolab.catalogo`.
        inicio, fin : fecha, opcional
            Cualquier cosa que entienda ``pandas.Timestamp``. Si se omiten ambas
            se descarga la historia completa; si falta ``fin`` se usa hoy.
        incremento : {"mensual", "anual", "acumulado"}, opcional
            Pide a Banxico la variación porcentual ya calculada en lugar del
            nivel: respecto a la observación anterior, al mismo periodo del año
            anterior, o al cierre del año anterior.

        Returns
        -------
        pandas.DataFrame
            ``DatetimeIndex`` llamado ``fecha``, una columna por serie y valores
            ``float`` (``NaN`` donde el SIE reporta ``N/E``). Las fechas sin
            ningún dato se descartan. Los títulos oficiales quedan en
            ``df.attrs["series"]``.

        Raises
        ------
        SerieNoEncontrada
            Si alguna clave no existe en el SIE.
        SinDatos
            Si ninguna serie tiene observaciones en el periodo.
        """
        nombres = _resolver_series(series, tema)
        params = {}
        if incremento is not None:
            if incremento not in INCREMENTOS:
                raise ValueError(f"incremento debe ser uno de {sorted(INCREMENTOS)}")
            params["incremento"] = INCREMENTOS[incremento]

        if inicio is None and fin is None:
            sufijo = "/datos"
        else:
            desde = _fecha(inicio) if inicio is not None else "1900-01-01"
            hasta = _fecha(fin) if fin is not None else _fecha(pd.Timestamp.today())
            if desde > hasta:
                raise ValueError(f"inicio ({desde}) es posterior a fin ({hasta})")
            sufijo = f"/datos/{desde}/{hasta}"

        objetos = self._por_lotes(list(nombres), sufijo, params or None)
        faltantes = [i for i in nombres if i not in objetos]
        if faltantes:
            raise SerieNoEncontrada(f"El SIE no reconoce estas series: {faltantes}")

        columnas, info, vacias = {}, {}, []
        for id_serie, nombre in nombres.items():
            objeto = objetos[id_serie]
            info[nombre] = {"id": id_serie, "titulo": _limpiar_titulo(objeto.get("titulo", ""))}
            datos = objeto.get("datos")
            if not datos:
                vacias.append(f"{nombre} ({id_serie})")
                columnas[nombre] = pd.Series(dtype=float)
                continue
            tabla = pd.DataFrame(datos)
            # Formato explícito: las fechas vienen dd/mm/aaaa y adivinar el orden
            # convertiría el 03/01 en 1 de marzo sin avisar.
            indice = pd.to_datetime(tabla["fecha"], format="%d/%m/%Y")
            columnas[nombre] = pd.Series(_a_numero(tabla["dato"]).to_numpy(), index=indice)

        if len(vacias) == len(nombres):
            raise SinDatos("Ninguna serie tiene datos en el periodo solicitado.")
        if vacias:
            warnings.warn(
                f"Sin datos en el periodo para: {', '.join(vacias)}. La columna queda en NaN.",
                stacklevel=2,
            )

        df = pd.DataFrame(columnas).sort_index().dropna(how="all")
        df = df.reindex(columns=list(nombres.values())).astype(float)
        df.index.name = "fecha"
        df.attrs["series"] = info
        return df

    def panel(
        self,
        series: Series | None = None,
        inicio: Fecha | None = None,
        fin: Fecha | None = None,
        *,
        tema: str | None = None,
        como: Mapping[str, str] | None = None,
    ) -> pd.DataFrame:
        """Panel **mensual** listo para analizar, aunque las series tengan frecuencias distintas.

        Descarga las series y lleva a frecuencia mensual las diarias, semanales
        y quincenales, cada una con la regla que le corresponde según el
        catálogo: último dato para precios y saldos, promedio para tasas, suma
        para flujos. Evita tener que descargar por grupos y agregar a mano.

        Parameters
        ----------
        series, inicio, fin, tema
            Igual que en :meth:`descargar`.
        como : dict, opcional
            ``{columna: regla}`` para cambiar la regla de alguna serie o fijar
            la de una clave que no está en el catálogo (por omisión,
            ``"ultimo"``). Reglas: ``"ultimo"``, ``"promedio"``, ``"suma"``,
            ``"primero"``.

        Returns
        -------
        pandas.DataFrame
            Indexado al primer día de cada mes. La regla aplicada a cada columna
            queda en ``df.attrs["agregacion"]``.

        Examples
        --------
        >>> import banxicolab as sie
        >>> sie.panel(["inpc", "fix", "tasa_objetivo"], "2015-01-01")   # doctest: +SKIP
        """
        from .transformaciones import a_mensual, frecuencia

        nombres = _resolver_series(series, tema)
        como = dict(como or {})
        sobran = set(como) - set(nombres.values())
        if sobran:
            raise ValueError(f"`como` menciona columnas que no se pidieron: {sorted(sobran)}")
        datos = self.descargar(nombres, inicio, fin)

        columnas, reglas = {}, {}
        for id_serie, nombre in nombres.items():
            s = datos[nombre].dropna()
            conocida = _catalogo.POR_ID.get(id_serie)
            regla = como.get(nombre) or (conocida.agregacion if conocida else "ultimo")
            if conocida:
                periodicidad = conocida.periodicidad
            else:
                periodicidad = frecuencia(s) if len(s) >= 3 else "Mensual"
            if periodicidad in ("Mensual", "Trimestral", "Anual") and nombre not in como:
                regla = "ultimo"  # ya hay a lo más un dato por mes: solo se alinea la fecha
            columnas[nombre] = a_mensual(s, regla) if len(s) else s
            reglas[nombre] = regla
        tabla = pd.DataFrame(columnas).dropna(how="all")
        tabla.index.name = "fecha"
        tabla.attrs["series"] = datos.attrs["series"]
        tabla.attrs["agregacion"] = reglas
        return tabla

    def serie(
        self,
        clave: str,
        inicio: Fecha | None = None,
        fin: Fecha | None = None,
        *,
        incremento: str | None = None,
    ) -> pd.Series:
        """Como :meth:`descargar`, pero para una sola serie y sin valores faltantes."""
        df = self.descargar(clave, inicio, fin, incremento=incremento)
        return df.iloc[:, 0].dropna()

    def metadatos(self, series: Series) -> pd.DataFrame:
        """Título, periodicidad, unidad y cobertura de cada serie.

        Conviene revisarlo **antes** de transformar: indica si la serie es un
        índice, una tasa o un saldo, y desde cuándo existe.
        """
        nombres = _resolver_series(series)
        objetos = self._por_lotes(list(nombres), "")
        faltantes = [i for i in nombres if i not in objetos]
        if faltantes:
            raise SerieNoEncontrada(f"El SIE no reconoce estas series: {faltantes}")
        filas = []
        for id_serie, nombre in nombres.items():
            o = objetos[id_serie]
            filas.append(
                {
                    "serie": nombre,
                    "id": id_serie,
                    "titulo": _limpiar_titulo(o.get("titulo", "")),
                    "periodicidad": o.get("periodicidad"),
                    "cifra": o.get("cifra"),
                    "unidad": o.get("unidad"),
                    "inicio": pd.to_datetime(o.get("fechaInicio"), format="%d/%m/%Y"),
                    "fin": pd.to_datetime(o.get("fechaFin"), format="%d/%m/%Y"),
                }
            )
        return pd.DataFrame(filas).set_index("serie")

    def oportuno(self, series: Series) -> pd.DataFrame:
        """Último dato publicado de cada serie (consulta barata: 80 por minuto)."""
        nombres = _resolver_series(series)
        objetos = self._por_lotes(list(nombres), "/datos/oportuno")
        filas = []
        for id_serie, nombre in nombres.items():
            o = objetos.get(id_serie)
            if o is None:
                raise SerieNoEncontrada(f"El SIE no reconoce la serie {id_serie}")
            dato = (o.get("datos") or [{}])[-1]
            filas.append(
                {
                    "serie": nombre,
                    "id": id_serie,
                    "fecha": pd.to_datetime(dato.get("fecha"), format="%d/%m/%Y"),
                    "dato": _a_numero(pd.Series([dato.get("dato", np.nan)])).iloc[0],
                    "titulo": _limpiar_titulo(o.get("titulo", "")),
                }
            )
        return pd.DataFrame(filas).set_index("serie")

    def buscar(self, texto: str, limite: int | None = 30) -> pd.DataFrame:
        """Busca series por texto en el catálogo público del SIE. No usa token.

        Notes
        -----
        Se apoya en el buscador de la página del catálogo, que no forma parte
        de la API documentada: funciona mejor con una o dos palabras
        (``"subyacente"``, ``"cetes"``) y podría cambiar sin aviso.
        """
        cuerpo = self._pedir("cat/series", {"q": texto}, con_token=False)
        resultados = cuerpo.get("bmx", {}).get("resultados", [])
        df = pd.DataFrame(
            [{"id": r["idSerie"], "descripcion": _limpiar_titulo(r["texto"])} for r in resultados],
            columns=["id", "descripcion"],
        ).drop_duplicates("id")
        return df.head(limite).reset_index(drop=True)

    def info(self, clave: str) -> dict:
        """Ficha de una serie desde el catálogo público. No usa token ni gasta consultas."""
        id_serie, _ = _catalogo.resolver(clave)
        series = self._pedir(f"cat/series/{id_serie}", con_token=False).get("bmx", {}).get("series")
        if not series:
            raise SerieNoEncontrada(f"El SIE no reconoce la serie {id_serie}")
        ficha = series[0]
        return {
            "id": ficha["idSerie"],
            "titulo": _limpiar_titulo(ficha.get("titulo", "")),
            "periodicidad": ficha.get("periodicidad"),
            "cifra": ficha.get("cifra"),
            "unidad": ficha.get("unidad"),
        }

    def inflacion(
        self, inicio: Fecha | None = None, fin: Fecha | None = None, *, indice: str = "inpc"
    ) -> pd.DataFrame:
        """Tabla de inflación calculada a partir del índice de precios.

        Descarga 13 meses extra hacia atrás para que la variación anual exista
        desde ``inicio``. Ver :func:`banxicolab.inflacion` para las columnas.
        """
        from .precios import inflacion as _tabla

        desde = None if inicio is None else pd.Timestamp(inicio) - pd.DateOffset(months=13)
        tabla = _tabla(self.serie(indice, desde, fin))
        return tabla if inicio is None else tabla.loc[pd.Timestamp(inicio) :]

    def inflacion_implicita(
        self, plazo: int = 10, inicio: Fecha | None = None, fin: Fecha | None = None
    ) -> pd.DataFrame:
        """Inflación implícita diaria en los precios de Bonos M y Udibonos.

        Descarga el vector de precios de Banxico, calcula el rendimiento a
        vencimiento de cada título y los compara. Ver
        :func:`banxicolab.inflacion_implicita` para la interpretación.

        Parameters
        ----------
        plazo : {3, 10, 20, 30}
            Plazo de referencia en años.

        Returns
        -------
        pandas.DataFrame
            ``nominal`` (Bono M) y ``real`` (Udibono) en % anual, ``implicita``
            en %, y el plazo efectivo en años de cada título (``plazo_nominal``,
            ``plazo_real``), que rara vez coinciden exactamente.
        """
        from . import renta_fija

        if plazo not in renta_fija.VECTOR:
            raise ValueError(f"plazo debe ser uno de {sorted(renta_fija.VECTOR)}")
        claves = renta_fija.VECTOR[plazo]
        datos = self.descargar({**claves, "SP68257": "udi"}, inicio, fin)
        return renta_fija.desde_vector(datos)

    def anticipar_inflacion(self, *, anios: int = 8, historial: bool = False) -> pd.DataFrame:
        """Anticipa la inflación del mes con su primera quincena ya publicada.

        Descarga el INPC quincenal. Ver :func:`banxicolab.anticipar_inflacion`.
        """
        from .precios import anticipar_inflacion as _anticipar

        inicio = None if historial else pd.Timestamp.today() - pd.DateOffset(years=anios + 3)
        return _anticipar(self.serie("inpc_quincenal", inicio), anios=anios, historial=historial)

    def contribuciones_inflacion(
        self,
        inicio: Fecha | None = None,
        fin: Fecha | None = None,
        *,
        periodos: int = 12,
        desglose: str = "componentes",
    ) -> pd.DataFrame:
        """Aportación de cada componente a la inflación, en puntos porcentuales.

        El método está descrito en :func:`banxicolab.contribuciones`.

        Parameters
        ----------
        periodos : int
            12 para la inflación anual; 1 para la mensual.
        desglose : {"componentes", "subyacente"}
            ``"componentes"``: mercancías, servicios, agropecuarios y
            energéticos y tarifas. ``"subyacente"``: subyacente y no subyacente.
        """
        from .precios import contribuciones as _contribuciones

        partes = {
            "componentes": [
                "inpc_mercancias",
                "inpc_servicios",
                "inpc_agropecuarios",
                "inpc_energeticos",
            ],
            "subyacente": ["inpc_subyacente", "inpc_no_subyacente"],
        }
        if desglose not in partes:
            raise ValueError(f"desglose debe ser uno de {sorted(partes)}")
        # Siempre desde 2000: los coeficientes se estiman con cada tramo completo
        nombres = {a: a.removeprefix("inpc_") for a in partes[desglose]}
        datos = self.descargar({"inpc": "inpc", **nombres}, "2000-01-01", fin)
        tabla = _contribuciones(datos["inpc"], datos[list(nombres.values())], periodos)
        return tabla if inicio is None else tabla.loc[pd.Timestamp(inicio) :]

    def _vector_de_curva(self, inicio: Fecha | None, fin: Fecha | None) -> pd.DataFrame:
        from .renta_fija import VECTOR_BONOS, VECTOR_CETES

        claves = {}
        for nombre, (tasa, dias) in VECTOR_CETES.items():
            claves[tasa], claves[dias] = f"{nombre}|tasa", f"{nombre}|dias"
        for nombre, (precio, cupon, dias) in VECTOR_BONOS.items():
            claves[precio], claves[cupon] = f"{nombre}|precio", f"{nombre}|cupon"
            claves[dias] = f"{nombre}|dias"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # algún rango de bonos puede no tener datos
            return self.descargar(claves, inicio, fin)

    def curva_rendimientos(self, fecha: Fecha | None = None) -> pd.DataFrame:
        """Curva de rendimientos de Cetes y Bonos M de un día, con su ajuste Nelson-Siegel.

        Parameters
        ----------
        fecha : fecha, opcional
            Por omisión, el último día con datos. Si la fecha no tuvo
            operaciones se toma el día hábil anterior.

        Returns
        -------
        pandas.DataFrame
            Una fila por título: ``titulo``, ``plazo`` (años), ``rendimiento``
            observado y ``ajustado`` por la curva (% anual). La curva queda en
            ``df.attrs["curva"]`` y se puede evaluar en cualquier plazo:
            ``df.attrs["curva"](10)``.

        Notes
        -----
        Son rendimientos a vencimiento de los títulos de referencia del vector
        de precios de Banxico, no una curva cupón cero. Los Cetes cotizan a
        tasa de rendimiento y los Bonos M a rendimiento con cupones
        semestrales, así que la curva mezcla convenciones cercanas pero no
        idénticas.
        """
        from .renta_fija import nelson_siegel, puntos_de_curva

        hasta = pd.Timestamp(fecha) if fecha is not None else pd.Timestamp.today()
        puntos = puntos_de_curva(self._vector_de_curva(hasta - pd.Timedelta(days=14), hasta))
        dias = puntos.groupby("fecha").size()
        completos = dias[dias >= 4]
        if completos.empty:
            raise SinDatos("No hay suficientes títulos con precio en esas fechas.")
        dia = completos.index.max()
        tabla = puntos[puntos["fecha"] == dia].drop(columns="fecha").reset_index(drop=True)
        curva = nelson_siegel(tabla["plazo"], tabla["rendimiento"])
        tabla["ajustado"] = curva(tabla["plazo"].to_numpy())
        tabla.attrs.update({"curva": curva, "fecha": dia})
        return tabla

    def curva_historica(
        self,
        inicio: Fecha,
        fin: Fecha | None = None,
        *,
        plazos=(0.25, 1, 2, 5, 10, 20, 30),
    ) -> pd.DataFrame:
        """Curva de rendimientos ajustada cada día, evaluada en plazos fijos.

        Returns
        -------
        pandas.DataFrame
            Una fila por día: el rendimiento ajustado a cada plazo (columnas
            ``"3m"``, ``"1a"``, ``"10a"``…) y los parámetros de Nelson-Siegel
            (``nivel``, ``pendiente``, ``curvatura``, ``lam``, ``error``).
            ``pendiente`` negativa significa tasas largas mayores que las cortas.
        """
        from .renta_fija import nelson_siegel, puntos_de_curva

        puntos = puntos_de_curva(self._vector_de_curva(inicio, fin))
        filas = {}
        for dia, grupo in puntos.groupby("fecha"):
            if len(grupo) < 4:
                continue
            curva = nelson_siegel(grupo["plazo"], grupo["rendimiento"])
            valores = dict(zip(map(_etiqueta_plazo, plazos), curva(list(plazos)), strict=True))
            filas[dia] = {**valores, **curva.parametros()}
        tabla = pd.DataFrame.from_dict(filas, orient="index")
        tabla.index.name = "fecha"
        return tabla


def _etiqueta_plazo(anios: float) -> str:
    return f"{round(anios * 12)}m" if anios < 1 else f"{anios:g}a"


_compartido: Banxico | None = None


def configurar(
    *,
    cache: bool | str = True,
    vigencia_cache: float = 12,
    carpeta_cache=None,
    token: str | None = None,
) -> Banxico:
    """Ajusta el cliente que usan las funciones del módulo (``sie.descargar``…).

    Examples
    --------
    Para que volver a ejecutar un notebook no gaste consultas:

    >>> import banxicolab as sie
    >>> sie.configurar(cache="disco")      # doctest: +SKIP
    """
    global _compartido
    _compartido = Banxico(
        token, cache=cache, vigencia_cache=vigencia_cache, carpeta_cache=carpeta_cache
    )
    return _compartido


def _cliente() -> Banxico:
    """Cliente compartido que usan las funciones de módulo (``sie.descargar``…)."""
    global _compartido
    if _compartido is None:
        _compartido = Banxico()
    return _compartido


def descargar(
    series: Series | None = None,
    inicio: Fecha | None = None,
    fin: Fecha | None = None,
    *,
    tema: str | None = None,
    incremento: str | None = None,
) -> pd.DataFrame:
    """Atajo de :meth:`Banxico.descargar` con el cliente compartido."""
    return _cliente().descargar(series, inicio, fin, tema=tema, incremento=incremento)


def panel(
    series: Series | None = None,
    inicio: Fecha | None = None,
    fin: Fecha | None = None,
    *,
    tema: str | None = None,
    como: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Atajo de :meth:`Banxico.panel` con el cliente compartido."""
    return _cliente().panel(series, inicio, fin, tema=tema, como=como)


def serie(
    clave: str,
    inicio: Fecha | None = None,
    fin: Fecha | None = None,
    *,
    incremento: str | None = None,
) -> pd.Series:
    """Atajo de :meth:`Banxico.serie` con el cliente compartido."""
    return _cliente().serie(clave, inicio, fin, incremento=incremento)


def metadatos(series: Series) -> pd.DataFrame:
    """Atajo de :meth:`Banxico.metadatos` con el cliente compartido."""
    return _cliente().metadatos(series)


def oportuno(series: Series) -> pd.DataFrame:
    """Atajo de :meth:`Banxico.oportuno` con el cliente compartido."""
    return _cliente().oportuno(series)


def buscar(texto: str, limite: int | None = 30) -> pd.DataFrame:
    """Atajo de :meth:`Banxico.buscar`. No requiere token."""
    return _cliente().buscar(texto, limite)


def info(clave: str) -> dict:
    """Atajo de :meth:`Banxico.info`. No requiere token."""
    return _cliente().info(clave)
