# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T049 — varios incisos cumplidos en fechas distintas (US1 esc. 4, FR-017).

Nacida el 1970-01-10, servicios desde 1990-02-01 al 2025-12-31: al cese tiene
55 años y 35 de servicio, así que cumple el inc. b y el inc. d, habilitados en
fechas distintas. El informe debe señalar cuál es más favorable y por qué.
"""

from __future__ import annotations

import pytest

from tests.casos import caso_incisos_multiples, f
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.informe import Informe, ResultadoInciso
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(caso_incisos_multiples(), reglas=REGLAS)


def _inc(informe: Informe, letra: str) -> ResultadoInciso:
    return next(i for i in informe.elegibilidad.incisos if i.inciso == letra)


def test_cumple_el_inciso_b(informe: Informe) -> None:
    assert _inc(informe, "b").cumple is True


def test_cumple_el_inciso_d(informe: Informe) -> None:
    assert _inc(informe, "d").cumple is True


def test_los_incisos_se_habilitan_en_fechas_distintas(informe: Informe) -> None:
    b = _inc(informe, "b").habilitado_desde
    d = _inc(informe, "d").habilitado_desde
    assert b is not None
    assert d is not None
    assert b != d
    assert b < d


def test_el_inciso_b_se_habilita_en_el_cumpleanios_50(informe: Informe) -> None:
    assert _inc(informe, "b").habilitado_desde == f("2020-01-10")


def test_el_inciso_d_se_habilita_en_el_cumpleanios_55(informe: Informe) -> None:
    assert _inc(informe, "d").habilitado_desde == f("2025-01-10")


def test_el_mas_favorable_es_el_inciso_b(informe: Informe) -> None:
    """El inc. b accede por el art. 43 (75 % de base); el d, por el art. 41 (70 %)."""
    assert informe.elegibilidad.inciso_mas_favorable == "b"


def test_el_desglose_explica_por_que_el_b_es_mas_favorable(informe: Informe) -> None:
    """FR-017: no alcanza con decir cuál, hay que decir por qué."""
    pasos = [p for p in informe.desglose if "favorable" in p.descripcion.lower()]
    assert pasos
    assert any("43" in (p.salida or "") or "43" in p.descripcion for p in pasos)


def test_el_escenario_usa_el_inciso_mas_favorable(informe: Informe) -> None:
    assert all(e.inciso == "b" for e in informe.escenarios if e.hay_derecho)
