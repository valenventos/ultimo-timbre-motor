# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T116 — la extensión discutida de la Ley 13469 (US3 esc. 8, FR-002c).

`[Ley 13469 — NO_VERIFICADA; SCBA causa A 74801 (2020); Cuestión abierta #8]`

La Ley 13469 asimiló expresamente a preceptores y bibliotecarios al frente de
alumnos. Si esa asimilación se extiende a otros cargos del escalafón —lo que la
SCBA trató en A 74801— está discutido. Para una directora con 30 años de
carrera la diferencia no es académica:

* sin la extensión: ningún año al frente → accede por el inc. d → **70 %**;
* con la extensión: 30 años al frente → accede por el inc. b → **75 %**.

El motor aplica la letra del art. 24 inc. b, que no la enumera, y marca el
resultado provisional declarando el impacto al alza. Lo que no hace es elegir
en silencio una de las dos lecturas.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado, SentidoImpacto
from ultimo_timbre.models.informe import Condicionante, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")
REGLA = "al_frente.ley_13469.extension"


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(
        caso(
            periodo("director_primera", desde="1995-01-01", hasta="2025-01-10"),
            nacimiento="1969-01-10",
            ceses=["2025-01-10"],
            fecha_de_calculo="2025-01-11",
        ),
        reglas=REGLAS,
    )


def _cond(informe: Informe) -> Condicionante:
    return next(c for c in informe.condicionantes if c.referencia == REGLA)


def test_el_resultado_es_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_el_condicionante_es_la_extension_de_la_ley_13469(informe: Informe) -> None:
    assert _cond(informe) is not None


def test_el_impacto_declarado_es_al_alza(informe: Informe) -> None:
    """Si la extensión aplicara, la docente pasaría del inc. d al inc. b."""
    assert _cond(informe).sentido_impacto is SentidoImpacto.AL_ALZA


def test_el_condicionante_explica_que_falta_verificar(informe: Informe) -> None:
    """FR-046b, con los dos porcentajes en juego."""
    falta = _cond(informe).que_falta_verificar
    assert "13469" in falta or "extensión" in falta.lower()


def test_se_advierte_la_regla_sin_verificar(informe: Informe) -> None:
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.REGLA_NO_VERIFICADA in codigos


def test_el_porcentaje_aplicado_es_el_de_la_letra_del_art_24(informe: Informe) -> None:
    """70 % por el inc. d: el motor no adelanta el resultado del pleito."""
    assert informe.escenarios[0].porcentaje == Decimal("0.70")
    assert informe.escenarios[0].inciso == "d"


def test_el_impacto_posible_es_de_70_a_75(informe: Informe) -> None:
    """La magnitud declarada tiene que ser la que el profesional discute."""
    cond = _cond(informe)
    assert cond.magnitud_estimada is not None
    assert "70" in cond.magnitud_estimada
    assert "75" in cond.magnitud_estimada
