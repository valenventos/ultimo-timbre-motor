# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T096 — el haber depende de la escala de antigüedad (US2 esc. 3, Cuestión #1).

El escenario de la spec dice: «un caso cuyo haber depende de la escala de
bonificación por antigüedad» sale marcado no definitivo por la regla
`NO_VERIFICADA` correspondiente, explicando qué falta verificar.

**Alcance de lo que se puede verificar en la US2**: el cálculo del haber llega
con la US4 (T139 en adelante). Lo que sí se verifica acá es que, en cuanto el
motor entra al camino del monto —es decir, en cuanto recibe una grilla—, las
tres reglas que condicionan cualquier haber aparecen como condicionantes y el
informe sale provisional. El monto en sí se prueba en la US4.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.casos import caso_inc_b
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import ClaseCondicionante, EstadoResultado
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Condicionante, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")
GRILLA_FICTICIA = "tests/fixtures/grilla-ficticia-test.yaml"
REGLA_ANTIGUEDAD = "antiguedad.escala_y_tope"


@pytest.fixture(scope="module")
def grilla() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(Path(GRILLA_FICTICIA))


@pytest.fixture(scope="module")
def informe(grilla: GrillaSalarial) -> Informe:
    return calcular(caso_inc_b(), reglas=REGLAS, grilla=grilla)


def _cond(informe: Informe, referencia: str) -> Condicionante:
    return next(c for c in informe.condicionantes if c.referencia == referencia)


def test_la_grilla_usada_es_la_ficticia(grilla: GrillaSalarial) -> None:
    """Resguardo: ningún test de monto corre sobre importes que parezcan reales."""
    assert grilla.ficticia is True


def test_con_grilla_el_informe_declara_su_version(informe: Informe) -> None:
    assert informe.version_grilla == "ficticia-test"


def test_la_escala_de_antiguedad_condiciona_el_resultado(informe: Informe) -> None:
    cond = _cond(informe, REGLA_ANTIGUEDAD)
    assert cond.clase is ClaseCondicionante.REGLA_NO_VERIFICADA


def test_el_condicionante_cita_el_decreto_818_13(informe: Informe) -> None:
    """La escala aplicada es la del decreto, no la original del Estatuto.

    La Ley 10.579, art. 33, queda como lectura alternativa a la baja: su escala
    está cargada aparte, en `antiguedad.escala_ley_10579`.
    """
    cond = _cond(informe, REGLA_ANTIGUEDAD)
    assert cond.norma is not None
    assert cond.norma.ley == "Decreto 818/13"
    assert cond.norma.articulo == "Anexo Único"
    assert cond.norma.enlace == "https://normas.gba.gob.ar/documentos/BgAzqgfp.html"


def test_el_condicionante_explica_que_falta_verificar(informe: Informe) -> None:
    """Cuestión abierta #1: lo que falta es la **vigencia**, no los valores.

    Los once tramos están transcriptos del Anexo Único del Decreto 818/13. Lo
    que no se pudo verificar es que ninguna norma posterior los haya
    modificado, y eso es lo que el condicionante tiene que decir.
    """
    cond = _cond(informe, REGLA_ANTIGUEDAD)
    assert "vigente" in cond.que_falta_verificar or "sigue siendo" in cond.que_falta_verificar
    assert "120" in cond.que_falta_verificar


def test_el_condicionante_declara_la_magnitud(informe: Informe) -> None:
    """FR-046b: la dirección sola no alcanza; hace falta cuánto."""
    cond = _cond(informe, REGLA_ANTIGUEDAD)
    assert cond.magnitud_estimada is not None
    assert "125" in cond.magnitud_estimada
    assert "120" in cond.magnitud_estimada


def test_tambien_condicionan_la_remuneracion_y_el_redondeo(informe: Informe) -> None:
    """Las tres Cuestiones que afectan a cualquier monto: #1, #2 y #6."""
    refs = {c.referencia for c in informe.condicionantes}
    assert "remuneracion.conceptos_del_cargo" in refs
    assert "redondeo.politica_ips" in refs


def test_el_informe_con_grilla_es_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_sin_grilla_las_reglas_del_monto_no_condicionan() -> None:
    """No se condiciona lo que no se calcula: la US1 no emite montos."""
    informe = calcular(caso_inc_b(), reglas=REGLAS)
    refs = {c.referencia for c in informe.condicionantes}
    assert REGLA_ANTIGUEDAD not in refs
    assert informe.estado_general is EstadoResultado.DEFINITIVO
