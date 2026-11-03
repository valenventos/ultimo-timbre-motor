# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T094 — condicionantes de clase `regla_no_verificada` (FR-046, FR-046b).

Toda regla sin verificar que **interviene** en el resultado tiene que aparecer
como condicionante, con su norma y su sentido de impacto. Una regla que no
interviene no aparece: si apareciera, el informe condicionaría todo con todo y
la marca dejaría de significar algo.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.engine import condicionantes as cond
from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    EstadoRegla,
    SentidoImpacto,
    SituacionRevista,
)
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def _informe(cargo: str = "maestro_de_grado", **kw: object) -> Informe:
    return calcular(
        caso(
            periodo(cargo, desde="1995-03-01", hasta="2026-02-28", **kw),
            nacimiento="1970-06-20",
            ceses=["2026-02-28"],
        ),
        reglas=REGLAS,
    )


def test_el_constructor_de_condicionante_de_regla() -> None:
    regla = REGLAS.por_id("antiguedad.escala_y_tope")
    assert regla is not None
    c = cond.de_regla(regla)
    assert c is not None
    assert c.clase is ClaseCondicionante.REGLA_NO_VERIFICADA
    assert c.referencia == "antiguedad.escala_y_tope"
    assert c.norma is not None
    assert c.sentido_impacto is regla.impacto_si_no_verificada
    assert c.que_falta_verificar == regla.que_falta_verificar


def test_una_regla_verificada_no_produce_condicionante() -> None:
    regla = REGLAS.por_id("haber.art41.base")
    assert regla is not None
    assert regla.estado is EstadoRegla.VERIFICADO
    assert cond.de_regla(regla) is None


def test_un_cargo_condicionado_produce_el_condicionante_de_su_regla() -> None:
    """Cuestión abierta #8: director no está en la enumeración del inc. b."""
    informe = _informe("director_primera")
    c = next(x for x in informe.condicionantes if x.referencia == "al_frente.ley_13469.extension")
    assert c.clase is ClaseCondicionante.REGLA_NO_VERIFICADA
    assert c.sentido_impacto is SentidoImpacto.AL_ALZA
    assert c.norma is not None
    assert c.norma.ley == "Ley 13469"


def test_una_situacion_de_revista_produce_el_condicionante_del_computo() -> None:
    informe = _informe(situacion_revista=SituacionRevista.SUPLENTE)
    refs = {c.referencia for c in informe.condicionantes}
    assert "computo.licencias_suplencias_y_revista" in refs


def test_una_historia_limpia_no_produce_condicionantes_de_regla() -> None:
    """Si todo interviene, la marca deja de significar algo."""
    informe = _informe()
    assert informe.condicionantes == ()


def test_todo_condicionante_de_regla_declara_norma_y_sentido() -> None:
    informe = _informe("director_primera", situacion_revista=SituacionRevista.SUPLENTE)
    reglas = [
        c for c in informe.condicionantes if c.clase is ClaseCondicionante.REGLA_NO_VERIFICADA
    ]
    assert reglas
    for c in reglas:
        assert c.norma is not None
        assert c.sentido_impacto is not None
        assert c.que_falta_verificar


def test_los_condicionantes_no_se_repiten() -> None:
    """La misma regla puede intervenir en varios pasos; aparece una sola vez."""
    informe = calcular(
        caso(
            periodo("director_primera", desde="1995-03-01", hasta="2010-02-28"),
            periodo("vicedirector_primera", desde="2010-03-01", hasta="2026-02-28"),
            nacimiento="1970-06-20",
            ceses=["2026-02-28"],
        ),
        reglas=REGLAS,
    )
    refs = [c.referencia for c in informe.condicionantes]
    assert refs.count("al_frente.ley_13469.extension") == 1


def test_los_condicionantes_salen_en_orden_estable() -> None:
    """SC-003: sin orden estable el informe no es comparable byte a byte."""
    uno = _informe("director_primera", situacion_revista=SituacionRevista.SUPLENTE)
    otro = _informe("director_primera", situacion_revista=SituacionRevista.SUPLENTE)
    assert [c.referencia for c in uno.condicionantes] == [c.referencia for c in otro.condicionantes]


def test_las_reglas_que_condicionan_todo_monto_se_listan() -> None:
    """Las Cuestiones #1, #2 y #6 condicionan cualquier haber (listo para la US4)."""
    refs = {c.referencia for c in cond.del_monto(REGLAS)}
    assert "antiguedad.escala_y_tope" in refs
    assert "remuneracion.conceptos_del_cargo" in refs
    assert "redondeo.politica_ips" in refs


@pytest.mark.parametrize(
    "regla_id",
    [
        "antiguedad.escala_y_tope",
        "remuneracion.conceptos_del_cargo",
        "horas_catedra.como_carrera",
        "jerarquia.criterio_comparacion",
        "computo.licencias_suplencias_y_revista",
        "redondeo.politica_ips",
    ],
)
def test_toda_regla_no_verificada_puede_volverse_condicionante(regla_id: str) -> None:
    regla = REGLAS.por_id(regla_id)
    assert regla is not None
    c = cond.de_regla(regla)
    assert c is not None
    assert c.referencia == regla_id
