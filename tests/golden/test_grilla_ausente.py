# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T140 — la grilla vigente al cese no está cargada (US4 esc. 2, FR-034).

Pasa siempre que se evalúa un cese futuro, que es el caso normal de este motor:
nadie consulta por un cese que ya ocurrió. La grilla vigente a 2030 no existe en
2026, así que el motor valúa con la última disponible.

Lo que FR-034 exige es que **se diga**: advertencia, con qué grilla se calculó,
y el monto marcado. Un haber a valores de cuatro años atrás presentado como
definitivo es exactamente la clase de número convincente y equivocado que el
Principio X existe para impedir.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from tests.casos import caso_inc_b
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")
CODIGO = CodigoAdvertencia.GRILLA_AUSENTE


@pytest.fixture(scope="module")
def informe() -> Informe:
    """El caso del inc. b cesa en 2030 y la grilla deja de regir antes.

    La grilla ficticia no declara `vigencia_hasta`, así que por sí sola seguiría
    vigente para siempre: una grilla sin fecha de fin es la última aprobada y
    sigue en vigor. Para probar FR-034 hace falta justamente lo contrario, una
    que haya dejado de regir, y por eso se le pone fin con `model_copy`.
    """
    grilla: GrillaSalarial = versiones.cargar_grilla_de_prueba(FIXTURE)
    caduca = grilla.model_copy(update={"vigencia_hasta": dt.date(2026, 12, 31)})
    return calcular(caso_inc_b(), reglas=REGLAS, grilla=caduca)


def test_se_advierte_que_la_grilla_no_rige_a_la_fecha_de_cese(informe: Informe) -> None:
    assert CODIGO in {a.codigo for a in informe.advertencias}


def test_la_advertencia_dice_con_que_grilla_se_calculo(informe: Informe) -> None:
    """FR-034: «no es la vigente» sin decir cuál se usó no sirve de nada."""
    adv = next(a for a in informe.advertencias if a.codigo is CODIGO)
    assert "ficticia-test" in adv.mensaje


def test_la_advertencia_no_bloquea_el_calculo(informe: Informe) -> None:
    """El monto se emite marcado: es mejor que ninguno, si se dice qué es."""
    assert next(a for a in informe.advertencias if a.codigo is CODIGO).bloquea_calculo is False


def test_el_monto_igual_se_emite(informe: Informe) -> None:
    assert informe.escenarios[0].haber is not None


def test_el_monto_queda_provisional(informe: Informe) -> None:
    haber = informe.escenarios[0].haber
    assert haber is not None
    assert haber.estado is EstadoResultado.PROVISIONAL
    assert CODIGO.value in {c.referencia for c in haber.condicionantes}


def test_el_informe_queda_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_el_monto_declara_a_valores_de_que_fecha(informe: Informe) -> None:
    """FR-030a: sin esto, el número no se puede interpretar."""
    haber = informe.escenarios[0].haber
    assert haber is not None
    assert haber.a_valores_de < informe.escenarios[0].fecha_cese
