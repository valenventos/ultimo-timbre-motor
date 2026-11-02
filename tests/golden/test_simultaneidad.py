# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T088 — simultaneidad de cargos `[DL 9650/80, art. 47; Res. IPS 995/2021]`.

US2 esc. 1, FR-043. Dos cargos distintos superpuestos casi 10 años: el motor lo
clasifica como computable por el art. 47, advierte su impacto posible en el
haber, y **no calcula el incremento** — eso está fuera del Alcance de la v1.

A diferencia de un tramo en otra caja, la simultaneidad **no bloquea** el
cálculo: los servicios sí se computan (sobre la unión), lo que queda sin
calcular es el incremento.
"""

from __future__ import annotations

import pytest

from tests.casos import caso_simultaneidad, caso_simultaneidad_breve
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado
from ultimo_timbre.models.informe import Advertencia, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(caso_simultaneidad(), reglas=REGLAS)


def _adv(informe: Informe, codigo: CodigoAdvertencia) -> Advertencia:
    return next(a for a in informe.advertencias if a.codigo is codigo)


def test_clasifica_la_simultaneidad_como_computable(informe: Informe) -> None:
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47 in codigos


def test_la_advertencia_cita_el_art_47_y_la_resolucion(informe: Informe) -> None:
    adv = _adv(informe, CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47)
    assert adv.norma is not None
    assert adv.norma.articulo == "47"
    assert "995/2021" in adv.norma.texto


def test_la_advertencia_declara_el_impacto_posible(informe: Informe) -> None:
    """FR-043: se advierte el impacto, no se calcula el incremento."""
    adv = _adv(informe, CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47)
    assert adv.sentido_impacto is not None


def test_la_simultaneidad_no_bloquea_el_computo_de_servicios(informe: Informe) -> None:
    """Los servicios se computan sobre la unión; lo que falta es el incremento."""
    adv = _adv(informe, CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47)
    assert adv.bloquea_calculo is False


def test_los_servicios_se_computan_sobre_la_union(informe: Informe) -> None:
    """30 años de carrera, no 40: el solapamiento no se cuenta dos veces (I9)."""
    requisito = next(
        r
        for i in informe.elegibilidad.incisos
        if i.inciso == "b"
        for r in i.requisitos
        if r.nombre == "años de servicio"
    )
    assert requisito.valor_alcanzado == "30"


def test_el_resultado_es_provisional_por_la_simultaneidad(informe: Informe) -> None:
    """El incremento del art. 47 podría cambiar el haber."""
    assert informe.estado_general is EstadoResultado.PROVISIONAL
    refs = {c.referencia for c in informe.condicionantes}
    assert CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47.value in refs


def test_el_condicionante_explica_que_falta(informe: Informe) -> None:
    cond = next(
        c
        for c in informe.condicionantes
        if c.referencia == CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47.value
    )
    assert "art. 47" in cond.que_falta_verificar


def test_un_solapamiento_breve_no_llega_al_art_47() -> None:
    informe = calcular(caso_simultaneidad_breve(), reglas=REGLAS)
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47 not in codigos
    assert CodigoAdvertencia.SIMULTANEIDAD_NO_COMPUTABLE in codigos
