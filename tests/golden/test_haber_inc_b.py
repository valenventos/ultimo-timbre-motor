# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T147 — el haber estimado con la grilla ficticia (US4 esc. 1, FR-030, FR-031a).

Es el primer informe del motor que lleva un número de plata. Con la grilla
ficticia, el maestro de grado vale $100.000 bonificables más $50.000 de suma
fija, los dos remunerativos: $150.000 de remuneración. Accediendo por el inc. b
sin excedente el porcentaje es 75 %, así que el haber es $112.500.

Lo que el test fija además del número: que el monto **nunca** aparezca sin su
estado, su versión de grilla y sus condicionantes (FR-046a, invariante I5), y
que el desglose explique de dónde salió cada parte.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tests.casos import caso_inc_b
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import EstadoResultado
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe, Monto
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


@pytest.fixture(scope="module")
def grilla() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(FIXTURE)


@pytest.fixture(scope="module")
def informe(grilla: GrillaSalarial) -> Informe:
    return calcular(caso_inc_b(), reglas=REGLAS, grilla=grilla)


@pytest.fixture(scope="module")
def monto(informe: Informe) -> Monto:
    haber = informe.escenarios[0].haber
    assert haber is not None, "el escenario tiene que traer haber"
    return haber


def test_la_grilla_usada_es_la_ficticia(grilla: GrillaSalarial) -> None:
    """Resguardo: ningún test de monto corre sobre importes que parezcan reales."""
    assert grilla.ficticia is True


def test_el_cargo_base_es_el_maestro(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "maestro_de_grado"


def test_el_porcentaje_es_el_del_art_43(informe: Informe) -> None:
    assert informe.escenarios[0].porcentaje == Decimal("0.75")


def test_el_haber_es_el_porcentaje_sobre_la_remuneracion_mas_antiguedad(
    informe: Informe, monto: Monto
) -> None:
    """La cuenta completa, con la antigüedad del Decreto 818/13.

    Remuneración 150.000 por la letra del art. 40 (los dos componentes, ninguno
    excluido). La docente tiene 26 años de servicio, así que entra en el último
    tramo de la escala, 125 %, **sobre la base bonificable de 100.000** y no
    sobre el total: 125.000 de adicional. (150.000 + 125.000) por 75 % =
    206.250.

    Si la antigüedad se aplicara sobre el total daría 262.500 de adicional y un
    haber de 309.375: la diferencia de 103.125 es lo que FR-031b evita.
    """
    assert informe.escenarios[0].antiguedad_anios == 26
    assert monto.valor == Decimal("206250.00")


def test_la_antiguedad_no_se_aplico_sobre_el_total(monto: Monto) -> None:
    """El resguardo explícito del error caro (FR-031b)."""
    sobre_el_total = (Decimal("150000.00") * Decimal("2.25")) * Decimal("0.75")
    assert monto.valor != sobre_el_total


def test_el_monto_declara_la_version_de_grilla(monto: Monto) -> None:
    assert monto.grilla_version == "ficticia-test"


def test_el_monto_declara_a_que_valores_esta(monto: Monto) -> None:
    """FR-030a: los montos se expresan a valores de la fecha de la grilla."""
    assert monto.a_valores_de is not None


def test_el_monto_nunca_viene_sin_su_estado_ni_sus_condicionantes(monto: Monto) -> None:
    """FR-046a e invariante I5, a nivel de tipo."""
    assert monto.estado is EstadoResultado.PROVISIONAL
    assert monto.condicionantes


def test_el_monto_arrastra_las_tres_cuestiones_del_haber(monto: Monto) -> None:
    """Antigüedad (#1), remuneración del cargo (#2) y redondeo (#6)."""
    refs = {c.referencia for c in monto.condicionantes}
    assert "antiguedad.escala_y_tope" in refs
    assert "remuneracion.conceptos_del_cargo" in refs
    assert "redondeo.politica_ips" in refs


def test_el_informe_declara_la_version_de_grilla(informe: Informe) -> None:
    assert informe.version_grilla == "ficticia-test"


def test_el_desglose_explica_la_valuacion(informe: Informe) -> None:
    descripciones = " ".join(p.descripcion.lower() for p in informe.desglose)
    assert "remuneración" in descripciones
    assert "antigüedad" in descripciones
    assert "haber" in descripciones


def test_el_desglose_cita_el_decreto_818_13_para_la_antiguedad(informe: Informe) -> None:
    """Principio I: la escala aplicada tiene fuente, con su anexo."""
    paso = next(p for p in informe.desglose if p.regla_id == "antiguedad.escala_y_tope")
    assert paso.norma.ley == "Decreto 818/13"
    assert paso.norma.articulo == "Anexo Único"
    assert "1.25" in (paso.salida or "")


def test_el_desglose_cita_la_escala_alternativa_de_la_ley_10579(informe: Informe) -> None:
    """FR-032: la otra escala se informa, con su sentido y su monto."""
    paso = next(p for p in informe.desglose if p.regla_id == "antiguedad.escala_ley_10579")
    assert paso.norma.ley == "Ley 10579"
    assert paso.norma.articulo == "33"
    # 120 % sobre 100.000 de base bonificable.
    assert "120000.00" in (paso.salida or "")
    assert "a_la_baja" in (paso.salida or "")


def test_el_desglose_cita_el_art_41_para_el_haber(informe: Informe) -> None:
    pasos = [p for p in informe.desglose if "haber" in p.descripcion.lower()]
    assert pasos
    assert any(p.norma.articulo in {"41", "40"} for p in pasos)


def test_sin_grilla_no_hay_haber() -> None:
    """Resguardo del contraste: la US1 a la US3 no emiten montos."""
    informe = calcular(caso_inc_b(), reglas=REGLAS)
    assert all(e.haber is None for e in informe.escenarios)
