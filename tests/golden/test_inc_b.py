# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T050 — caso dorado del inciso b `[DL 9650/80, art. 24 inc. b]` (US1 esc. 1).

Docente nacida el 1980-03-15 con 26 años al frente de alumnos al 2030-03-31:
cumple el art. 24 inc. b (50 años de edad y 25 de servicios al frente), y la
fecha de habilitación es la del cumpleaños 50, porque los 25 años de servicio
ya estaban alcanzados antes.

Caso **sintético**, no una resolución real del IPS: el caso dorado real es
T119, marcado `[PENDIENTE-DATOS]`.
"""

from __future__ import annotations

import pytest

from tests.casos import caso_inc_b, f
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import EstadoResultado, TipoEscenario
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(caso_inc_b(), reglas=REGLAS)


def test_cumple_el_inciso_b(informe: Informe) -> None:
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.cumple is True
    assert inc_b.norma.texto.startswith("DL 9650/80, art. 24 inc. b")


def test_la_habilitacion_es_el_cumpleanios_50(informe: Informe) -> None:
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.habilitado_desde == f("2030-03-15")


def test_el_inciso_b_es_el_mas_favorable(informe: Informe) -> None:
    assert informe.elegibilidad.inciso_mas_favorable == "b"


def test_no_cumple_el_inciso_d_por_edad(informe: Informe) -> None:
    inc_d = next(i for i in informe.elegibilidad.incisos if i.inciso == "d")
    assert inc_d.cumple is False
    assert inc_d.falta is not None
    assert inc_d.falta.anios_edad > 0


def test_cumple_el_minimo_de_22_anios(informe: Informe) -> None:
    assert informe.elegibilidad.minimo_22_anios.cumple is True


def test_hay_derecho_en_el_escenario_del_cese_provisto(informe: Informe) -> None:
    escenario = next(e for e in informe.escenarios if e.tipo is TipoEscenario.PROVISTA)
    assert escenario.fecha_cese == f("2030-03-31")
    assert escenario.hay_derecho is True
    assert escenario.inciso == "b"


def test_sin_grilla_no_hay_haber(informe: Informe) -> None:
    """La US1 entrega elegibilidad sin montos: el haber llega con la US4."""
    assert all(e.haber is None for e in informe.escenarios)
    assert informe.version_grilla is None


def test_el_informe_declara_la_version_de_reglas(informe: Informe) -> None:
    assert informe.version_reglas == "v1"


def test_el_informe_lleva_los_avisos_obligatorios(informe: Informe) -> None:
    """FR-042 y FR-030c."""
    assert "estimación orientativa" in informe.aviso_estimacion
    assert "art. 50" in informe.aviso_movilidad


def test_el_resultado_es_definitivo(informe: Informe) -> None:
    """Historia limpia: titular, sin licencias, cargo verificado en el catálogo."""
    assert informe.estado_general is EstadoResultado.DEFINITIVO
    assert informe.condicionantes == ()


def test_lejos_del_umbral_la_convencion_no_decide(informe: Informe) -> None:
    """T074: 26 años contra 25 requeridos. Ninguna convención de conteo cambia
    ese resultado, así que el requisito sigue siendo definitivo."""
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.estado is EstadoResultado.DEFINITIVO
    for requisito in inc_b.requisitos:
        assert requisito.estado is EstadoResultado.DEFINITIVO, requisito.nombre


def test_el_desglose_cita_el_art_24_inc_b(informe: Informe) -> None:
    citas = {p.norma.texto for p in informe.desglose}
    assert any("art. 24 inc. b" in c for c in citas)


def test_la_condicion_al_frente_queda_en_la_procedencia(informe: Informe) -> None:
    """FR-039: el dato se derivó del catálogo, no lo cargó el usuario."""
    procedencias = [p for p in informe.procedencias if "al_frente" in p.dato]
    assert procedencias
    assert procedencias[0].origen.value == "derivado"
    assert procedencias[0].derivado_de is not None
