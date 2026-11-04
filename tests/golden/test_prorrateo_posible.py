# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T091 — el prorrateo como vía posible `[DL 9650/80, art. 27]` (US2 esc. 5, FR-015a).

Con 16 años docentes la docente no alcanza ningún inciso, pero tiene 14 años no
docentes aportados al IPS. El prorrateo del art. 27 está fuera del Alcance de la
v1, así que no se computa — pero decir «no cumple» sin mencionar que esa vía
existe sería engañoso: el profesional tomaría una decisión de cese sobre una
negativa que podría revertirse.
"""

from __future__ import annotations

import pytest

from tests.casos import caso_no_cumple, caso_prorrateo_posible
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado, SentidoImpacto
from ultimo_timbre.models.informe import Advertencia, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(caso_prorrateo_posible(), reglas=REGLAS)


def _adv(informe: Informe, codigo: CodigoAdvertencia) -> Advertencia:
    return next(a for a in informe.advertencias if a.codigo is codigo)


def test_ningun_inciso_se_cumple_con_los_servicios_docentes(informe: Informe) -> None:
    assert all(not i.cumple for i in informe.elegibilidad.incisos)


def test_advierte_los_servicios_no_docentes_sin_computar(informe: Informe) -> None:
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.SERVICIOS_NO_DOCENTES_SIN_COMPUTAR in codigos


def test_advierte_que_el_prorrateo_podria_completar_los_requisitos(
    informe: Informe,
) -> None:
    """FR-015a: la advertencia que vuelve honesto el «no cumple»."""
    adv = _adv(informe, CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS)
    assert adv.norma is not None
    assert adv.norma.articulo == "27"


def test_la_advertencia_de_prorrateo_tiene_impacto_al_alza(informe: Informe) -> None:
    adv = _adv(informe, CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS)
    assert adv.sentido_impacto is SentidoImpacto.AL_ALZA


def test_la_elegibilidad_no_es_definitiva(informe: Informe) -> None:
    """FR-015a: el resultado de elegibilidad queda no definitivo."""
    assert informe.elegibilidad.estado is EstadoResultado.PROVISIONAL
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_el_condicionante_nombra_el_prorrateo(informe: Informe) -> None:
    refs = {c.referencia for c in informe.condicionantes}
    assert CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS.value in refs


def test_los_no_docentes_no_se_computan(informe: Informe) -> None:
    requisito = next(
        r
        for i in informe.elegibilidad.incisos
        if i.inciso == "b"
        for r in i.requisitos
        if r.nombre == "años de servicio"
    )
    assert requisito.valor_alcanzado == "16"


def test_sin_no_docentes_no_se_advierte_el_prorrateo() -> None:
    informe = calcular(caso_no_cumple(), reglas=REGLAS)
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS not in codigos
