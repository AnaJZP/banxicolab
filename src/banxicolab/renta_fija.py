"""Rendimientos de bonos gubernamentales e inflación implícita.

Banxico publica cada día el precio, el cupón y los días por vencer de los Bonos M
y Udibonos de referencia, pero no su rendimiento. Este módulo lo calcula con la
convención del mercado mexicano (cupones cada 182 días, base 360) y de ahí
obtiene la inflación implícita.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Vector de precios «on the run» del SIE, por plazo de referencia en años.
# Los Bonos M se agrupan por rango de vencimiento, no por plazo exacto.
VECTOR: dict[int, dict[str, str]] = {
    3: {
        "SF45448": "precio_nominal", "SF45475": "cupon_nominal", "SF45427": "dias_nominal",
        "SF61785": "precio_real", "SF61787": "cupon_real", "SF61784": "dias_real",
    },
    10: {
        "SF45454": "precio_nominal", "SF45478": "cupon_nominal", "SF45430": "dias_nominal",
        "SF45458": "precio_real", "SF45480": "cupon_real", "SF45432": "dias_real",
    },
    20: {
        "SF45456": "precio_nominal", "SF45479": "cupon_nominal", "SF45431": "dias_nominal",
        "SF50765": "precio_real", "SF50763": "cupon_real", "SF50761": "dias_real",
    },
    30: {
        "SF60721": "precio_nominal", "SF60723": "cupon_nominal", "SF60720": "dias_nominal",
        "SF50767": "precio_real", "SF50764": "cupon_real", "SF50762": "dias_real",
    },
}  # fmt: skip


def precio_bono(rendimiento, cupon, plazo_dias, valor_nominal: float = 100, dias_cupon: int = 182):
    """Precio limpio de un bono a tasa fija con la convención mexicana.

    Parameters
    ----------
    rendimiento : número o Series
        Rendimiento a vencimiento, en % anual.
    cupon : número o Series
        Tasa cupón, en % anual.
    plazo_dias : número o Series
        Días por vencer.
    valor_nominal : float
        100 pesos en los Bonos M; 100 UDIS en los Udibonos.
    dias_cupon : int
        Días entre cupones (182).

    Notes
    -----
    Con ``R = rendimiento × 182/360``, cupón ``C = VN × cupón × 182/360``, ``K``
    cupones por cobrar y ``d`` días transcurridos del cupón vigente:

    ``precio sucio = [C + C·(1/R − 1/(R(1+R)^(K−1))) + VN/(1+R)^(K−1)] / (1+R)^(1−d/182)``

    y el precio limpio descuenta los intereses devengados ``C·d/182``.
    """
    y, c, n = (np.asarray(x, dtype=float) for x in (rendimiento, cupon, plazo_dias))
    tasa = y / 100 * dias_cupon / 360
    pago = valor_nominal * c / 100 * dias_cupon / 360
    cupones = np.ceil(n / dias_cupon)
    al_siguiente = n - dias_cupon * (cupones - 1)
    transcurridos = dias_cupon - al_siguiente

    with np.errstate(divide="ignore", invalid="ignore"):
        factor = (1 + tasa) ** (cupones - 1)
        anualidad = np.where(np.abs(tasa) < 1e-12, cupones - 1, (1 - 1 / factor) / tasa)
        sucio = (pago + pago * anualidad + valor_nominal / factor) / (1 + tasa) ** (
            al_siguiente / dias_cupon
        )
    limpio = sucio - pago * transcurridos / dias_cupon
    return _como(rendimiento, cupon, plazo_dias, valor=limpio)


def rendimiento_bono(
    precio_limpio, cupon, plazo_dias, valor_nominal: float = 100, dias_cupon: int = 182
):
    """Rendimiento a vencimiento (% anual) a partir del precio limpio.

    Inversa de :func:`precio_bono`, resuelta por bisección. Para un Udibono, el
    precio debe estar en UDIS (precio en pesos entre el valor de la UDI) y el
    resultado es un rendimiento **real**.

    Examples
    --------
    >>> round(float(rendimiento_bono(100, 8, 3640)), 4)   # a la par rinde su cupón
    8.0
    """
    p, c, n = np.broadcast_arrays(
        *(np.asarray(x, dtype=float) for x in (precio_limpio, cupon, plazo_dias))
    )
    bajo, alto = np.full(p.shape, -20.0), np.full(p.shape, 200.0)
    for _ in range(60):  # el precio decrece con el rendimiento
        medio = (bajo + alto) / 2
        caro = np.asarray(precio_bono(medio, c, n, valor_nominal, dias_cupon)) > p
        bajo, alto = np.where(caro, medio, bajo), np.where(caro, alto, medio)
    resultado = np.where(
        np.isnan(p) | np.isnan(c) | np.isnan(n) | (n <= 0), np.nan, (bajo + alto) / 2
    )
    return _como(precio_limpio, cupon, plazo_dias, valor=resultado)


def _como(*entradas, valor):
    """Devuelve ``valor`` con el índice de la primera entrada que sea un Series."""
    for entrada in entradas:
        if isinstance(entrada, pd.Series):
            return pd.Series(valor, index=entrada.index)
    return valor if np.ndim(valor) else float(valor)


def inflacion_implicita(nominal, real):
    """Inflación implícita (*breakeven*): ``(1 + i) / (1 + r) − 1``, en %.

    Es la inflación promedio que iguala el rendimiento de un bono nominal con el
    de uno indexado a la inflación del mismo plazo.

    Parameters
    ----------
    nominal : número o Series
        Rendimiento nominal (Bono M, Cetes), en % anual.
    real : número o Series
        Rendimiento real (Udibono), en % anual.

    Notes
    -----
    **No es una expectativa pura.** Incluye una prima por riesgo inflacionario
    (la sube) y una prima de liquidez de los Udibonos (la baja). Banxico la
    llama «compensación por inflación y riesgo inflacionario». Compárala con las
    expectativas de la encuesta (``"expectativa_inflacion_12m"``) antes de
    interpretarla.

    Examples
    --------
    >>> round(inflacion_implicita(9.5, 5.0), 4)
    4.2857
    """
    return ((1 + nominal / 100) / (1 + real / 100) - 1) * 100


def inflacion_implicita_forward(corta, larga, plazo_corto: float, plazo_largo: float):
    """Inflación implícita entre dos plazos futuros, en % anual.

    Con las implícitas a 10 y 20 años, por ejemplo, devuelve la que el mercado
    descuenta para los diez años que empiezan dentro de diez («10a10a»). Aísla
    el largo plazo de los choques de corto plazo.

    Parameters
    ----------
    corta, larga : número o Series
        Inflación implícita al plazo corto y al largo, en %.
    plazo_corto, plazo_largo : float
        Plazos en años.
    """
    if plazo_largo <= plazo_corto:
        raise ValueError("plazo_largo debe ser mayor que plazo_corto")
    acumulada = (1 + larga / 100) ** plazo_largo / (1 + corta / 100) ** plazo_corto
    return (acumulada ** (1 / (plazo_largo - plazo_corto)) - 1) * 100


def desde_vector(datos: pd.DataFrame) -> pd.DataFrame:
    """Rendimientos e inflación implícita desde el vector de precios del SIE.

    ``datos`` debe traer las columnas ``precio_``, ``cupon_`` y ``dias_`` con
    sufijo ``nominal`` y ``real``, más ``udi``. Es lo que usa
    :meth:`banxicolab.Banxico.inflacion_implicita`.
    """
    d = datos.dropna(subset=["precio_nominal", "precio_real", "udi"])
    nominal = rendimiento_bono(d["precio_nominal"], d["cupon_nominal"], d["dias_nominal"])
    # El Udibono cotiza en pesos pero paga en UDIS: se valúa en UDIS
    real = rendimiento_bono(d["precio_real"] / d["udi"], d["cupon_real"], d["dias_real"])
    return pd.DataFrame(
        {
            "nominal": nominal,
            "real": real,
            "implicita": inflacion_implicita(nominal, real),
            "plazo_nominal": d["dias_nominal"] / 365.25,
            "plazo_real": d["dias_real"] / 365.25,
        }
    )


# ── Curva de rendimientos ────────────────────────────────────────────────────

# Vector de precios: Cetes (tasa de rendimiento y días por vencer) y Bonos M por
# rango de vencimiento (precio limpio, cupón y días por vencer).
VECTOR_CETES: dict[str, tuple[str, str]] = {
    "Cetes 28": ("SF45470", "SF45422"),
    "Cetes 91": ("SF45471", "SF45423"),
    "Cetes 182": ("SF45472", "SF45424"),
    "Cetes 364": ("SF45473", "SF45425"),
}
VECTOR_BONOS: dict[str, tuple[str, str, str]] = {
    "Bono M 0-3 años": ("SF45448", "SF45475", "SF45427"),
    "Bono M 3-5 años": ("SF45450", "SF45476", "SF45428"),
    "Bono M 5-7 años": ("SF45452", "SF45477", "SF45429"),
    "Bono M 7-10 años": ("SF45454", "SF45478", "SF45430"),
    "Bono M 10-20 años": ("SF45456", "SF45479", "SF45431"),
    "Bono M 20-30 años": ("SF60721", "SF60723", "SF60720"),
}


def _cargas(plazos: np.ndarray, lam: float) -> np.ndarray:
    x = plazos / lam
    pendiente = (1 - np.exp(-x)) / x
    return np.column_stack([np.ones_like(plazos), pendiente, pendiente - np.exp(-x)])


class CurvaNS:
    """Curva de Nelson-Siegel ajustada: ``nivel``, ``pendiente``, ``curvatura`` y ``lam``.

    Se evalúa como función: ``curva(10)`` da el rendimiento a 10 años, en %.
    """

    def __init__(self, nivel: float, pendiente: float, curvatura: float, lam: float, error: float):
        self.nivel, self.pendiente, self.curvatura, self.lam = nivel, pendiente, curvatura, lam
        self.error = error  # raíz del error cuadrático medio del ajuste, en puntos porcentuales

    def __call__(self, plazos):
        p = np.atleast_1d(np.asarray(plazos, dtype=float))
        valores = _cargas(p, self.lam) @ np.array([self.nivel, self.pendiente, self.curvatura])
        return valores if np.ndim(plazos) else float(valores[0])

    def __repr__(self) -> str:
        return (
            f"CurvaNS(nivel={self.nivel:.3f}, pendiente={self.pendiente:.3f}, "
            f"curvatura={self.curvatura:.3f}, lam={self.lam:.2f}, error={self.error:.3f})"
        )

    def parametros(self) -> dict:
        return {
            "nivel": self.nivel,
            "pendiente": self.pendiente,
            "curvatura": self.curvatura,
            "lam": self.lam,
            "error": self.error,
        }


def nelson_siegel(plazos, rendimientos) -> CurvaNS:
    """Ajusta una curva de Nelson-Siegel a rendimientos observados.

    .. math::

        y(\\tau) = \\beta_0 + \\beta_1 \\, g(\\tau)
                  + \\beta_2 \\left(g(\\tau) - e^{-\\tau/\\lambda}\\right),
        \\qquad g(\\tau) = \\frac{1-e^{-\\tau/\\lambda}}{\\tau/\\lambda}

    ``nivel`` (:math:`\\beta_0`) es la tasa de largo plazo; ``pendiente``
    (:math:`\\beta_1`), la diferencia entre el corto y el largo plazo (negativa
    cuando la curva tiene pendiente positiva); ``curvatura`` (:math:`\\beta_2`),
    la joroba en los plazos medios; y ``lam`` (:math:`\\lambda`), en años, dónde
    se ubica esa joroba.

    Para cada :math:`\\lambda` de una rejilla, los tres coeficientes se obtienen
    por mínimos cuadrados; se elige el :math:`\\lambda` con menor error. Es
    determinista y no depende de valores iniciales.

    Parameters
    ----------
    plazos : arreglo
        Plazos en años.
    rendimientos : arreglo
        Rendimientos en % anual.
    """
    p = np.asarray(plazos, dtype=float)
    y = np.asarray(rendimientos, dtype=float)
    validos = np.isfinite(p) & np.isfinite(y) & (p > 0)
    p, y = p[validos], y[validos]
    if len(p) < 4:
        raise ValueError("Se necesitan al menos 4 plazos para ajustar la curva.")
    mejor = None
    for lam in np.geomspace(0.1, 15, 150):
        x = _cargas(p, lam)
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        error = float(np.sqrt(np.mean((y - x @ beta) ** 2)))
        if mejor is None or error < mejor[0]:
            mejor = (error, lam, beta)
    error, lam, beta = mejor
    return CurvaNS(float(beta[0]), float(beta[1]), float(beta[2]), float(lam), error)


def puntos_de_curva(datos: pd.DataFrame) -> pd.DataFrame:
    """Plazo y rendimiento de cada título del vector, por día (formato largo).

    ``datos`` trae las columnas que arma :meth:`banxicolab.Banxico.curva_rendimientos`.
    Los Cetes se cotizan a tasa de rendimiento; para los Bonos M se calcula el
    rendimiento a vencimiento con :func:`rendimiento_bono`.
    """
    partes = []
    for nombre in VECTOR_CETES:
        partes.append(
            pd.DataFrame(
                {
                    "titulo": nombre,
                    "plazo": datos[f"{nombre}|dias"] / 365.25,
                    "rendimiento": datos[f"{nombre}|tasa"],
                }
            )
        )
    for nombre in VECTOR_BONOS:
        rendimiento = rendimiento_bono(
            datos[f"{nombre}|precio"], datos[f"{nombre}|cupon"], datos[f"{nombre}|dias"]
        )
        partes.append(
            pd.DataFrame(
                {
                    "titulo": nombre,
                    "plazo": datos[f"{nombre}|dias"] / 365.25,
                    "rendimiento": rendimiento,
                }
            )
        )
    largo = pd.concat(partes).dropna()
    largo.index.name = "fecha"
    return largo.reset_index().sort_values(["fecha", "plazo"]).reset_index(drop=True)
