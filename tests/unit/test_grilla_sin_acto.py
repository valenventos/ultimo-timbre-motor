# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Una grilla con fuente oficial y sin acto aprobatorio (FR-008, FR-046b).

El caso real que esto resuelve: el Ministerio de Economía de la Provincia
publica la escala salarial de la Ley 10.579 mes a mes, y **ninguna de las
publicaciones cita el decreto ni el acta paritaria que la aprueba**. Son dos
salidas malas y una intermedia:

* **rechazar la grilla** deja al motor sin poder valuar nada con la única
  fuente oficial disponible;
* **darla por firme** le presta al monto una certeza que no tiene: no se puede
  descartar que la escala haya sido modificada o que rija otra;
* **admitirla marcada** es lo que hace el motor. El profesional ve el número y
  ve de qué carece, que es la decisión Q3 aplicada a este caso.

`norma` sigue siendo obligatoria: declara la **fuente** de los valores.
`acto_aprobatorio` es el acto que les dio fuerza, que es otra cosa y puede
faltar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.casos import caso_inc_b
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    CodigoAdvertencia,
    EstadoResultado,
    SentidoImpacto,
)
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")
CODIGO = CodigoAdvertencia.GRILLA_SIN_ACTO_APROBATORIO


@pytest.fixture(scope="module")
def con_acto() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(FIXTURE)


@pytest.fixture(scope="module")
def sin_acto(con_acto: GrillaSalarial) -> GrillaSalarial:
    return con_acto.model_copy(update={"acto_aprobatorio": None})


def _informe(grilla: GrillaSalarial) -> Informe:
    return calcular(caso_inc_b(), reglas=REGLAS, grilla=grilla)


# ---------------------------------------------------------------------------
# El modelo
# ---------------------------------------------------------------------------


def test_el_acto_aprobatorio_puede_faltar(sin_acto: GrillaSalarial) -> None:
    """Que falte no invalida la grilla: la condiciona."""
    assert sin_acto.acto_aprobatorio is None
    assert sin_acto.tiene_acto_aprobatorio is False


def test_la_norma_sigue_siendo_obligatoria(sin_acto: GrillaSalarial) -> None:
    """Son dos cosas distintas: la fuente de los valores y el acto que los aprueba."""
    assert sin_acto.norma.texto


def test_una_grilla_con_acto_lo_declara(con_acto: GrillaSalarial) -> None:
    assert con_acto.tiene_acto_aprobatorio is True
    assert con_acto.acto_aprobatorio is not None


# ---------------------------------------------------------------------------
# El efecto sobre el informe
# ---------------------------------------------------------------------------


def test_sin_acto_se_advierte(sin_acto: GrillaSalarial) -> None:
    codigos = {a.codigo for a in _informe(sin_acto).advertencias}
    assert CODIGO in codigos


def test_la_advertencia_no_bloquea_el_calculo(sin_acto: GrillaSalarial) -> None:
    """El monto se emite: lo que falta es el acto, no los valores."""
    adv = next(a for a in _informe(sin_acto).advertencias if a.codigo is CODIGO)
    assert adv.bloquea_calculo is False


def test_el_condicionante_es_una_situacion_del_caso(sin_acto: GrillaSalarial) -> None:
    """No es una regla NO_VERIFICADA: la duda no es normativa, es de la fuente."""
    cond = next(c for c in _informe(sin_acto).condicionantes if c.referencia == CODIGO.value)
    assert cond.clase is ClaseCondicionante.SITUACION_DEL_CASO
    assert cond.norma is None


def test_el_sentido_del_impacto_es_indeterminado(sin_acto: GrillaSalarial) -> None:
    """No se sabe si la escala fue modificada ni en qué dirección."""
    cond = next(c for c in _informe(sin_acto).condicionantes if c.referencia == CODIGO.value)
    assert cond.sentido_impacto is SentidoImpacto.INDETERMINADO


def test_el_condicionante_explica_que_falta(sin_acto: GrillaSalarial) -> None:
    cond = next(c for c in _informe(sin_acto).condicionantes if c.referencia == CODIGO.value)
    assert "acta paritaria" in cond.que_falta_verificar or "decreto" in cond.que_falta_verificar


def test_el_informe_queda_provisional(sin_acto: GrillaSalarial) -> None:
    assert _informe(sin_acto).estado_general is EstadoResultado.PROVISIONAL


def test_con_acto_no_aparece_el_condicionante(con_acto: GrillaSalarial) -> None:
    """Resguardo: si apareciera siempre, el test de arriba no probaría nada."""
    informe = _informe(con_acto)
    assert CODIGO not in {a.codigo for a in informe.advertencias}
    assert CODIGO.value not in {c.referencia for c in informe.condicionantes}


def test_sin_grilla_tampoco_aparece() -> None:
    """No se condiciona lo que no se calcula."""
    informe = calcular(caso_inc_b(), reglas=REGLAS)
    assert CODIGO not in {a.codigo for a in informe.advertencias}
