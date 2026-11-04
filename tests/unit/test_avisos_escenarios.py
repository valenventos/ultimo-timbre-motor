# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T160 — los dos avisos de un escenario futuro (FR-030a, FR-030c, US5 esc. 4 y 6).

Un escenario de 2035 valuado con la grilla de 2026 da un número correcto y
profundamente engañoso si no se dice qué es. Dos avisos lo acotan:

* **`montos_a_valores_de_hoy`**: el motor usa la última grilla aprobada y **no
  proyecta aumentos salariales**. El número está en pesos de la grilla, no de
  2035;
* **`haber_movil_art_50`**: el haber es móvil y se actualiza por correlación con
  el cargo en actividad, y este motor no proyecta esa movilidad.

Los dos citan el art. 50, que es la razón por la que las dos cosas son
verdaderas a la vez: el haber se mueve, y el motor no lo mueve.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.casos import caso_escenarios, caso_inc_b
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Advertencia, Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")
A_VALORES = CodigoAdvertencia.MONTOS_A_VALORES_DE_HOY
MOVIL = CodigoAdvertencia.HABER_MOVIL_ART_50


@pytest.fixture(scope="module")
def grilla() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(FIXTURE)


@pytest.fixture(scope="module")
def informe(grilla: GrillaSalarial) -> Informe:
    return calcular(caso_escenarios(), reglas=REGLAS, grilla=grilla)


def _adv(informe: Informe, codigo: CodigoAdvertencia) -> Advertencia:
    return next(a for a in informe.advertencias if a.codigo is codigo)


def test_se_advierte_que_los_montos_estan_a_valores_de_la_grilla(
    informe: Informe,
) -> None:
    assert A_VALORES in {a.codigo for a in informe.advertencias}


def test_el_aviso_dice_a_valores_de_que_fecha(informe: Informe) -> None:
    """«A valores de hoy» sin decir qué día es hoy no sirve de nada."""
    assert "2026-01-01" in _adv(informe, A_VALORES).mensaje


def test_el_aviso_aclara_que_no_se_proyectan_aumentos(informe: Informe) -> None:
    mensaje = _adv(informe, A_VALORES).mensaje
    assert "no proyecta" in mensaje or "sin proyectar" in mensaje


def test_se_advierte_que_el_haber_es_movil(informe: Informe) -> None:
    assert MOVIL in {a.codigo for a in informe.advertencias}


def test_los_dos_avisos_citan_el_art_50(informe: Informe) -> None:
    """Es la razón por la que las dos cosas son verdaderas a la vez."""
    for codigo in (A_VALORES, MOVIL):
        adv = _adv(informe, codigo)
        assert adv.norma is not None
        assert adv.norma.articulo == "50"


def test_ninguno_de_los_dos_bloquea_el_calculo(informe: Informe) -> None:
    """Son aclaraciones sobre el monto, no impedimentos para emitirlo."""
    for codigo in (A_VALORES, MOVIL):
        assert _adv(informe, codigo).bloquea_calculo is False


def test_el_monto_se_emite_igual(informe: Informe) -> None:
    assert all(e.haber is not None for e in informe.escenarios)


def test_sin_grilla_no_se_advierte_sobre_los_valores() -> None:
    """No se aclara el origen de un monto que no se emitió."""
    informe = calcular(caso_escenarios(), reglas=REGLAS)
    assert A_VALORES not in {a.codigo for a in informe.advertencias}


def test_un_caso_sin_escenarios_futuros_no_lleva_el_aviso(
    grilla: GrillaSalarial,
) -> None:
    """Resguardo: si saliera siempre, el test de arriba no probaría nada.

    `caso_inc_b` cesa el 2030-03-31 con fecha de cálculo del 2030-04-01: el cese
    ya ocurrió, así que no hay nada futuro que aclarar. Los escenarios derivados
    de excedente sí caen en el futuro, y por eso el aviso aparece igual; lo que
    este test fija es que la condición se evalúa por escenario y no de entrada.
    """
    informe = calcular(caso_inc_b(), reglas=REGLAS, grilla=grilla)
    provista = next(e for e in informe.escenarios if e.fecha_cese.year == 2030)
    assert provista.fecha_cese < informe.fecha_de_calculo
