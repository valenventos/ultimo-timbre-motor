# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T090 — establecimiento de gestión privada (US2 esc. 4, FR-045).

El Alcance de la v1 cubre establecimientos estatales de la DGCyE. Un tramo
privado se detecta y se informa; no se computa ni se aproxima (Principio X).
"""

from __future__ import annotations

import pytest

from tests.casos import caso_privado
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(caso_privado(), reglas=REGLAS)


def test_detecta_el_establecimiento_privado(informe: Informe) -> None:
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO in codigos


def test_la_advertencia_bloquea_el_calculo(informe: Informe) -> None:
    adv = next(
        a for a in informe.advertencias if a.codigo is CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO
    )
    assert adv.bloquea_calculo is True
    assert adv.periodo_idx == 0


def test_el_tramo_privado_no_se_computa(informe: Informe) -> None:
    requisito = next(
        r
        for i in informe.elegibilidad.incisos
        if i.inciso == "b"
        for r in i.requisitos
        if r.nombre == "años de servicio"
    )
    assert requisito.valor_alcanzado == "20"


def test_no_se_calcula_haber(informe: Informe) -> None:
    assert all(e.haber is None for e in informe.escenarios)


def test_el_informe_igual_se_emite(informe: Informe) -> None:
    assert informe.elegibilidad.incisos
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_el_informe_declara_el_bloqueo(informe: Informe) -> None:
    assert informe.tiene_bloqueos is True
