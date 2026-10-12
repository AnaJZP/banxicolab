import numpy as np
import pandas as pd
import pytest

import banxicolab as sie
from banxicolab import renta_fija


def test_bono_a_la_par_rinde_su_cupon():
    assert sie.rendimiento_bono(100, 8, 3640) == pytest.approx(8.0, abs=1e-8)
    assert sie.precio_bono(8, 8, 3640) == pytest.approx(100)
    assert sie.precio_bono(0, 8, 364) == pytest.approx(100 + 2 * 8 * 182 / 360)  # sin descuento


def test_caso_real_del_vector_de_banxico():
    # Bono M 7-10 años, 5-oct-2026: limpio 90.629439, sucio 91.340550, cupón 8 %, 3,426 días
    dias, cupon = 3426, 8.0
    transcurridos = 182 - (dias - 182 * (np.ceil(dias / 182) - 1))
    assert cupon * transcurridos / 360 == pytest.approx(91.340550 - 90.629439, abs=1e-6)
    rendimiento = sie.rendimiento_bono(90.629439, cupon, dias)
    assert rendimiento == pytest.approx(9.517, abs=1e-3)
    assert sie.precio_bono(rendimiento, cupon, dias) == pytest.approx(90.629439, abs=1e-9)


def test_ida_y_vuelta_vectorizada_y_faltantes():
    fechas = pd.date_range("2024-01-01", periods=4)
    tasas = pd.Series([4.0, 9.5, 12.0, np.nan], index=fechas)
    dias = pd.Series([400.0, 3426.0, 10900.0, 3000.0], index=fechas)
    precios = sie.precio_bono(tasas, 8.0, dias)
    assert precios.iloc[0] > 100 > precios.iloc[1] > precios.iloc[2]  # precio y tasa van al revés
    recuperadas = sie.rendimiento_bono(precios, 8.0, dias)
    assert recuperadas.index.equals(fechas)
    assert np.allclose(recuperadas.iloc[:3], tasas.iloc[:3]) and np.isnan(recuperadas.iloc[3])


def test_inflacion_implicita_y_forward():
    assert sie.inflacion_implicita(9.5, 5.0) == pytest.approx(4.2857, abs=1e-4)
    # Curva plana: la forward es la misma tasa
    assert sie.inflacion_implicita_forward(4.0, 4.0, 10, 20) == pytest.approx(4.0)
    # (1.04^10 · 1.05^10)^(1/20) es la de 20 años → los segundos diez años rinden 5 %
    larga = ((1.04**10 * 1.05**10) ** (1 / 20) - 1) * 100
    assert sie.inflacion_implicita_forward(4.0, larga, 10, 20) == pytest.approx(5.0)
    with pytest.raises(ValueError):
        sie.inflacion_implicita_forward(4.0, 4.0, 20, 10)


def test_desde_vector_valua_el_udibono_en_udis():
    udi = 8.0
    datos = pd.DataFrame(
        {
            "precio_nominal": sie.precio_bono(9.0, 8.0, 3500),
            "cupon_nominal": 8.0,
            "dias_nominal": 3500.0,
            "precio_real": sie.precio_bono(4.0, 4.0, 3640) * udi,  # cotiza en pesos
            "cupon_real": 4.0,
            "dias_real": 3640.0,
            "udi": [udi, np.nan],
        },
        index=pd.date_range("2026-01-01", periods=2),
    )
    tabla = renta_fija.desde_vector(datos)
    assert len(tabla) == 1  # el día sin UDI se descarta
    fila = tabla.iloc[0]
    assert fila["nominal"] == pytest.approx(9.0) and fila["real"] == pytest.approx(4.0)
    assert fila["implicita"] == pytest.approx((1.09 / 1.04 - 1) * 100)
    assert fila["plazo_real"] == pytest.approx(3640 / 365.25)
