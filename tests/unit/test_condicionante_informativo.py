# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Un condicionante sobre un inciso que no se eligió es informativo (FR-046b).

La regla está documentada en `engine/condicionantes.py`, sección
«Condicionantes informativos»: la sensibilidad de un inciso que **no** es el más
favorable no vuelve provisional ni la elegibilidad ni el estado general, salvo
que, de darse vuelta, pudiera cambiar si hay derecho o cuál es el inciso más
favorable.

El motivo: marcar provisional un resultado por una duda que no puede moverlo
gasta la marca. Si todo sale provisional, «provisional» deja de informar.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import EstadoResultado
from ultimo_timbre.models.informe import Informe, ResultadoInciso
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
REGLA_CONVENCION = "computo.convencion_de_conteo"


def _inciso(informe: Informe, letra: str) -> ResultadoInciso:
    return next(i for i in informe.elegibilidad.incisos if i.inciso == letra)


# ---------------------------------------------------------------------------
# (a) inc. b holgado + inc. d sensible → elegibilidad definitiva
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def holgado_en_b() -> Informe:
    """30 años exactos de servicio y 56 de edad.

    El inc. d queda justo en su umbral de 30 años —es sensible a la convención—
    pero el inc. b se cumple con 5 años de sobra y paga más (art. 43, 75 %
    contra el 70 % del art. 41). Que el inc. d caiga o no es indiferente.
    """
    return calcular(
        caso(
            periodo(desde="1996-03-01", hasta="2026-02-28"),
            nacimiento="1970-01-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=REGLAS,
    )


def test_a_el_inciso_mas_favorable_es_el_b(holgado_en_b: Informe) -> None:
    assert holgado_en_b.elegibilidad.inciso_mas_favorable == "b"


def test_a_el_inciso_d_es_sensible_a_la_convencion(holgado_en_b: Informe) -> None:
    """El dato sigue estando: se informa, no se esconde."""
    inc_d = _inciso(holgado_en_b, "d")
    assert inc_d.estado is EstadoResultado.PROVISIONAL
    assert any(r.margen_dias == 0 for r in inc_d.requisitos)


def test_a_el_inciso_b_no_es_sensible(holgado_en_b: Informe) -> None:
    assert _inciso(holgado_en_b, "b").estado is EstadoResultado.DEFINITIVO


def test_a_la_elegibilidad_queda_definitiva(holgado_en_b: Informe) -> None:
    assert holgado_en_b.elegibilidad.estado is EstadoResultado.DEFINITIVO


def test_a_el_estado_general_queda_definitivo(holgado_en_b: Informe) -> None:
    assert holgado_en_b.estado_general is EstadoResultado.DEFINITIVO


def test_a_no_se_registra_el_condicionante_de_convencion(holgado_en_b: Informe) -> None:
    """Invariante I5: sin condicionantes no hay nada marcado como provisional."""
    assert REGLA_CONVENCION not in {c.referencia for c in holgado_en_b.condicionantes}


# ---------------------------------------------------------------------------
# (b) inc. b sensible, cuya caída dejaría al inc. c como más favorable
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sensible_en_b() -> Informe:
    """25 años exactos de servicio, todos al frente, y 52 de edad.

    El inc. b queda justo en su umbral de 25 años al frente y es el más
    favorable. Si la convención lo dejara en 24 años y 364 días, el derecho no
    desaparecería —el inc. c pide 25 de servicio con 10 al frente— pero el
    inciso más favorable pasaría a ser el c, con otro artículo y otro
    porcentaje. Eso sí hay que marcarlo.
    """
    return calcular(
        caso(
            periodo(desde="2001-03-01", hasta="2026-02-28"),
            nacimiento="1974-01-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=REGLAS,
    )


def test_b_el_inciso_mas_favorable_es_el_b(sensible_en_b: Informe) -> None:
    assert sensible_en_b.elegibilidad.inciso_mas_favorable == "b"


def test_b_el_inciso_b_es_sensible(sensible_en_b: Informe) -> None:
    assert _inciso(sensible_en_b, "b").estado is EstadoResultado.PROVISIONAL


def test_b_el_inciso_c_tambien_se_cumple(sensible_en_b: Informe) -> None:
    """Es lo que haría que el derecho no se caiga, solo cambie de inciso."""
    assert _inciso(sensible_en_b, "c").cumple is True


def test_b_la_elegibilidad_queda_provisional(sensible_en_b: Informe) -> None:
    assert sensible_en_b.elegibilidad.estado is EstadoResultado.PROVISIONAL


def test_b_el_estado_general_queda_provisional(sensible_en_b: Informe) -> None:
    assert sensible_en_b.estado_general is EstadoResultado.PROVISIONAL


def test_b_el_condicionante_de_convencion_esta_registrado(sensible_en_b: Informe) -> None:
    """FR-046b: y explica qué falta verificar."""
    cond = next(c for c in sensible_en_b.condicionantes if c.referencia == REGLA_CONVENCION)
    assert cond.norma is not None
    assert cond.que_falta_verificar
