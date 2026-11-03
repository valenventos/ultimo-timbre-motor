# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T115 — inc. d sin excedente: 70 % (US3 esc. 7, FR-025).

`[DL 9650/80, art. 41]`

Quien accede por el inc. d va por el art. 41, cuya base es el 70 %. Para que el
inc. d sea el más favorable hace falta que los incs. b y c **no** se cumplan, y
eso exige una carrera sin años al frente de alumnos.

En el catálogo de la v1 todo camino hacia «no al frente» pasa por director o
vicedirector, que están condicionados por la extensión discutida de la Ley
13469 (Cuestión abierta #8). Así que este caso sale provisional, y es correcto
que salga así: si esa extensión aplicara, la docente accedería por el inc. b.
El impacto exacto lo verifica `test_ley_13469.py`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.casos import caso, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.informe import Escenario, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    """Nacida 1969-01-10, directora desde 1995-01-01, cese 2025-01-10.

    Cumple 55 años el 2024-01-10 y 30 de servicio el 2024-12-31: la última
    condición es el servicio, a 10 días del cese. Excedente 0.
    """
    return calcular(
        caso(
            periodo("director_primera", desde="1995-01-01", hasta="2025-01-10"),
            nacimiento="1969-01-10",
            ceses=["2025-01-10"],
            fecha_de_calculo="2025-01-11",
        ),
        reglas=REGLAS,
    )


@pytest.fixture(scope="module")
def escenario(informe: Informe) -> Escenario:
    return informe.escenarios[0]


def test_no_cumple_los_incisos_que_piden_frente_de_alumnos(informe: Informe) -> None:
    """Resguardo del escenario: si el inc. b se cumpliera, el 70 % no se probaría."""
    incisos = {i.inciso: i for i in informe.elegibilidad.incisos}
    assert incisos["b"].cumple is False
    assert incisos["c"].cumple is False


def test_accede_por_el_inciso_d(escenario: Escenario) -> None:
    assert escenario.hay_derecho is True
    assert escenario.inciso == "d"


def test_la_habilitacion_es_la_ultima_condicion(informe: Informe) -> None:
    inc_d = next(i for i in informe.elegibilidad.incisos if i.inciso == "d")
    assert inc_d.habilitado_desde == f("2024-12-31")


def test_aplica_el_70_por_ciento(escenario: Escenario) -> None:
    assert escenario.porcentaje == Decimal("0.70")


def test_el_desglose_cita_el_art_41(informe: Informe) -> None:
    pasos = [p for p in informe.desglose if "porcentaje" in p.descripcion.lower()]
    assert pasos
    assert any(p.norma.articulo == "41" for p in pasos)
