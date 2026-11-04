# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T158 — la antigüedad se proyecta a cada escenario (FR-030b, US5 esc. 5).

FR-030b pide aplicar «la antigüedad que la persona tendría a la fecha del
escenario», no la de hoy, y que el crecimiento aparezca en el desglose.

## Un hallazgo del régimen que este test deja asentado

El escenario 5 de la US5 —«la bonificación por antigüedad crece respecto del
escenario de habilitación»— **no puede ocurrirle a nadie que califique**, y no
por un error del motor:

* el art. 24 exige como mínimo **25 años** de servicio (incs. b y c) o 30 (inc. d);
* la escala del **Decreto 818/13** topa en su tramo de **24 años**, con 125 %.

Quien se habilita ya está, necesariamente, en el tramo más alto. La antigüedad
en años sigue creciendo entre escenarios —26, 29, 31— y el motor la proyecta y
la informa, pero el **porcentaje** no se mueve.

Eso haría falsa una promesa del tipo «esperá y te sube la antigüedad». Lo que
sube entre escenarios es el porcentaje del art. 43, no la bonificación.

Los tests de abajo verifican las dos mitades por separado: que la proyección
funcione y crezca cuando hay tramos por recorrer (unitario, con antigüedades
que no califican), y que en un caso real salga saturada con su razón.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tests.casos import caso_escenarios
from ultimo_timbre.engine import calcular, haber
from ultimo_timbre.models.enums import TipoEscenario
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


@pytest.fixture(scope="module")
def informe() -> Informe:
    grilla: GrillaSalarial = versiones.cargar_grilla_de_prueba(FIXTURE)
    return calcular(caso_escenarios(), reglas=REGLAS, grilla=grilla)


# ---------------------------------------------------------------------------
# La proyección: la antigüedad es la de cada fecha, no la de hoy
# ---------------------------------------------------------------------------


def test_cada_escenario_declara_su_propia_antiguedad(informe: Informe) -> None:
    for escenario in informe.escenarios:
        assert escenario.antiguedad_anios is not None, escenario.tipo


def test_la_antiguedad_crece_con_la_fecha_del_escenario(informe: Informe) -> None:
    """26 años al habilitarse, 29 a los 3 y 31 a los 5."""
    por_tipo = {e.tipo: e.antiguedad_anios for e in informe.escenarios}
    assert por_tipo[TipoEscenario.HABILITACION] == 26
    assert por_tipo[TipoEscenario.EXCEDENTE_3] == 29
    assert por_tipo[TipoEscenario.EXCEDENTE_5] == 31


def test_la_antiguedad_no_es_la_de_la_fecha_de_calculo(informe: Informe) -> None:
    """Resguardo de FR-030b: si fuera la de hoy, serían todas iguales."""
    antiguedades = {e.antiguedad_anios for e in informe.escenarios}
    assert len(antiguedades) > 1


def test_el_desglose_declara_la_antiguedad_usada(informe: Informe) -> None:
    pasos = [p for p in informe.desglose if p.regla_id == "antiguedad.escala_y_tope"]
    assert pasos
    assert "años de antigüedad" in (pasos[0].entrada or "")


# ---------------------------------------------------------------------------
# La saturación: por qué el porcentaje no crece
# ---------------------------------------------------------------------------


def test_el_porcentaje_de_antiguedad_sale_saturado_en_todos_los_escenarios(
    informe: Informe,
) -> None:
    """Quien califica ya está en el tramo de 24 años: el art. 24 pide 25."""
    for escenario in informe.escenarios:
        assert escenario.antiguedad_anios is not None
        assert haber.porcentaje_de_antiguedad(escenario.antiguedad_anios, reglas=REGLAS) == Decimal(
            "1.25"
        )


def test_el_minimo_del_art_24_supera_el_ultimo_tramo_de_la_escala() -> None:
    """La razón estructural, afirmada sobre las reglas y no sobre un comentario.

    Si alguna de las dos cambiara —un inciso con menos años de servicio, o una
    escala con tramos más altos— este test falla y hay que revisar si el
    escenario 5 de la US5 pasó a ser alcanzable.
    """
    minimo_servicio = min(
        valor
        for regla_id in ("requisitos.art24.inc_b", "requisitos.art24.inc_c")
        if (regla := REGLAS.por_id(regla_id)) is not None and regla.valor is not None
        if isinstance(valor := regla.valor.get("anios_servicio"), int)
    )
    escala = REGLAS.por_id("antiguedad.escala_y_tope")
    assert escala is not None
    assert escala.valor is not None
    tramos = escala.valor["escala"]
    assert isinstance(tramos, list)
    ultimo_tramo = max(
        t["anios"] for t in tramos if isinstance(t, dict) and isinstance(t["anios"], int)
    )

    assert minimo_servicio == 25
    assert ultimo_tramo == 24
    assert minimo_servicio > ultimo_tramo, (
        "si el mínimo del art. 24 dejó de superar el último tramo de la escala, "
        "la antigüedad puede crecer entre escenarios y el escenario 5 de la US5 "
        "pasó a ser alcanzable"
    )


# ---------------------------------------------------------------------------
# El mecanismo de crecimiento, donde sí hay tramos por recorrer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("antes", "despues", "crece"),
    [
        (10, 12, True),
        (12, 15, True),
        (22, 24, True),
        (24, 30, False),
        (30, 40, False),
    ],
)
def test_el_porcentaje_crece_mientras_queden_tramos(antes: int, despues: int, crece: bool) -> None:
    """El mecanismo funciona; lo que no ocurre es el caso que lo necesitaría."""
    pa = haber.porcentaje_de_antiguedad(antes, reglas=REGLAS)
    pd = haber.porcentaje_de_antiguedad(despues, reglas=REGLAS)
    assert pa is not None
    assert pd is not None
    assert (pd > pa) is crece
