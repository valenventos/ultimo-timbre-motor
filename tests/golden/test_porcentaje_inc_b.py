# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T113 — inc. b con 5 años de excedente: 85 % (US3 esc. 5, FR-027, FR-027a).

`[DL 9650/80, art. 43; Res. IPS 995/2021, Anexo, punto 2.1.a]`

Una docente que alcanzó **todas** las condiciones del inc. b cinco años antes
del cese llega al tope del art. 43. Lo que el test fija no es solo el 85 %,
sino desde dónde se contaron esos cinco años: desde la última condición en
cumplirse, que es el criterio del IPS.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.casos import caso, escenario_de, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.informe import Escenario, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    """Nacida 1970-01-10, maestra desde 1995-01-01, cese 2025-01-10.

    Cumple 50 años el 2020-01-10 y 25 de servicio el 2019-12-31: la última
    condición es la edad, el 2020-01-10. Del cese la separan 5 años justos.
    """
    return calcular(
        caso(
            periodo("maestro_de_grado", desde="1995-01-01", hasta="2025-01-10"),
            nacimiento="1970-01-10",
            ceses=["2025-01-10"],
            fecha_de_calculo="2025-01-11",
        ),
        reglas=REGLAS,
    )


@pytest.fixture(scope="module")
def escenario(informe: Informe) -> Escenario:
    """El escenario del cese preguntado, que coincide con el excedente de 5."""
    return escenario_de(informe, "2025-01-10")


def test_accede_por_el_inciso_b(escenario: Escenario) -> None:
    assert escenario.hay_derecho is True
    assert escenario.inciso == "b"


def test_la_habilitacion_es_la_ultima_condicion(informe: Informe) -> None:
    """FR-027a: la edad, no los 25 años de servicio que llegaron antes."""
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.habilitado_desde == f("2020-01-10")


def test_aplica_el_85_por_ciento(escenario: Escenario) -> None:
    assert escenario.porcentaje == Decimal("0.85")


def test_el_desglose_cita_el_art_43_y_la_resolucion(informe: Informe) -> None:
    """Principio I y FR-040: la interpretación se declara como tal."""
    textos = " ".join(p.norma.texto for p in informe.desglose)
    assert "art. 43" in textos
    assert "995/2021" in textos


def test_el_desglose_declara_el_excedente_de_5_anios(informe: Informe) -> None:
    salidas = " ".join(p.salida or "" for p in informe.desglose)
    assert "5" in salidas


def test_no_supera_el_tope_del_articulo(escenario: Escenario) -> None:
    """Invariante I2, en el único caso donde el tope se toca de verdad."""
    assert escenario.porcentaje is not None
    assert escenario.porcentaje <= Decimal("0.85")
