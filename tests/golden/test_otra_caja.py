# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T089 — servicios en otra caja `[DL 9650/80, arts. 66 y 67]` (US2 esc. 2, FR-044).

20 años con aportes al IPS y 10 a ANSES. El motor no computa los de ANSES, lo
advierte con su norma, y **igual entrega el análisis** de los 20 que sí son del
IPS: negar el informe entero le quitaría al profesional información que el
motor ya tenía (FR-045a, Principio IV).
"""

from __future__ import annotations

import pytest

from tests.casos import caso_otra_caja
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado, SentidoImpacto
from ultimo_timbre.models.informe import Advertencia, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(caso_otra_caja(), reglas=REGLAS)


def _adv(informe: Informe, codigo: CodigoAdvertencia) -> Advertencia:
    return next(a for a in informe.advertencias if a.codigo is codigo)


def test_advierte_los_servicios_en_otra_caja(informe: Informe) -> None:
    adv = _adv(informe, CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA)
    assert adv.periodo_idx == 0


def test_la_advertencia_cita_los_arts_66_y_67(informe: Informe) -> None:
    """Principio I: la exclusión tiene fuente."""
    adv = _adv(informe, CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA)
    assert adv.norma is not None
    assert adv.norma.articulo == "66-67"


def test_la_advertencia_bloquea_el_calculo(informe: Informe) -> None:
    assert _adv(informe, CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA).bloquea_calculo


def test_los_anios_de_anses_no_se_computan(informe: Informe) -> None:
    """Solo los 20 años del IPS entran al cómputo, no los 30 totales."""
    requisito = next(
        r
        for i in informe.elegibilidad.incisos
        if i.inciso == "b"
        for r in i.requisitos
        if r.nombre == "años de servicio"
    )
    assert requisito.valor_alcanzado == "20"


def test_el_informe_igual_entrega_la_elegibilidad(informe: Informe) -> None:
    """FR-045a: análisis parcial, no una negativa seca."""
    assert len(informe.elegibilidad.incisos) == 3
    assert informe.desglose


def test_no_se_emite_haber(informe: Informe) -> None:
    """Invariante I7: con advertencia bloqueante no hay monto."""
    assert all(e.haber is None for e in informe.escenarios)


def test_el_escenario_lleva_la_advertencia_bloqueante(informe: Informe) -> None:
    assert any(a.bloquea_calculo for e in informe.escenarios for a in e.advertencias)


def test_el_informe_declara_que_tiene_bloqueos(informe: Informe) -> None:
    """FR-045b: de acá sale el exit 3 de la CLI."""
    assert informe.tiene_bloqueos is True


def test_el_resultado_es_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_no_se_lanza_excepcion() -> None:
    """FueraDeAlcance quedó para errores de programación, no para casos."""
    assert calcular(caso_otra_caja(), reglas=REGLAS) is not None


def test_el_sentido_del_impacto_es_indeterminado(informe: Informe) -> None:
    """No es «al alza»: por el art. 67 computar la otra caja puede empeorar el caso.

    La caja otorgante es la de mayor tiempo con aportes, así que sumar los 10
    años de ANSES no agrega antigüedad a *este* cálculo: puede desplazar el
    otorgamiento a ANSES, con otro régimen, otros requisitos y otro haber.
    """
    adv = _adv(informe, CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA)
    assert adv.sentido_impacto is SentidoImpacto.INDETERMINADO

    cond = next(
        c
        for c in informe.condicionantes
        if c.referencia == CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA.value
    )
    assert cond.sentido_impacto is SentidoImpacto.INDETERMINADO


def test_la_advertencia_explica_el_desplazamiento_de_la_caja_otorgante(
    informe: Informe,
) -> None:
    """FR-046b: el motivo tiene que estar dicho, no deducible."""
    adv = _adv(informe, CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA)
    assert "art. 67" in adv.mensaje
    assert "otorgante" in adv.mensaje

    cond = next(
        c
        for c in informe.condicionantes
        if c.referencia == CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA.value
    )
    assert "art. 67" in cond.que_falta_verificar
    assert "otorgante" in cond.que_falta_verificar
