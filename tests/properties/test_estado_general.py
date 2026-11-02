# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T060 — invariante I6: `estado_general` definitivo ⟺ nada provisional (FR-046c).

El campo se **deriva**, no se acepta como entrada, para que no pueda quedar
inconsistente con sus componentes. Lo que el test fija es la equivalencia en los
dos sentidos, y que un informe provisional nunca salga sin condicionantes.
"""

from __future__ import annotations

import datetime as dt

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.casos import ESTATAL, caso, caso_inc_b, periodo
from ultimo_timbre.engine import calcular, estado_de
from ultimo_timbre.models.caso import Caso, Licencia
from ultimo_timbre.models.enums import EstadoResultado, SituacionRevista, TipoLicencia
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

# cargos que condicionan y cargos que no, para cubrir los dos lados
LIMPIOS = ["maestro_de_grado", "preceptor", "bibliotecario"]
CONDICIONANTES = ["director", "vicedirector", "horas_catedra_secundario", "inexistente"]


@st.composite
def casos(draw: st.DrawFn) -> Caso:
    cargo = draw(st.sampled_from(LIMPIOS + CONDICIONANTES))
    revista = draw(st.sampled_from(list(SituacionRevista)))
    en_curso = draw(st.booleans())
    return caso(
        periodo(
            cargo,
            desde="1995-03-01",
            hasta=None if en_curso else "2026-02-28",
            situacion_revista=revista,
        ),
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-11-02",
    )


def _componentes_provisionales(informe: Informe) -> bool:
    if informe.elegibilidad.estado is EstadoResultado.PROVISIONAL:
        return True
    if informe.cargo_base is not None and informe.cargo_base.estado is EstadoResultado.PROVISIONAL:
        return True
    return any(
        e.haber is not None and e.haber.estado is EstadoResultado.PROVISIONAL
        for e in informe.escenarios
    )


@settings(max_examples=120, deadline=None)
@given(c=casos())
def test_la_equivalencia_i6(c: Caso) -> None:
    informe = calcular(c, reglas=REGLAS)
    definitivo = informe.estado_general is EstadoResultado.DEFINITIVO
    assert definitivo == (not _componentes_provisionales(informe))


@settings(max_examples=120, deadline=None)
@given(c=casos())
def test_un_informe_provisional_siempre_declara_sus_condicionantes(c: Caso) -> None:
    """FR-046a: una marca sin explicación no sirve a quien lee el informe."""
    informe = calcular(c, reglas=REGLAS)
    if informe.estado_general is EstadoResultado.PROVISIONAL:
        assert informe.condicionantes


@settings(max_examples=120, deadline=None)
@given(c=casos())
def test_un_informe_definitivo_no_tiene_condicionantes(c: Caso) -> None:
    informe = calcular(c, reglas=REGLAS)
    if informe.estado_general is EstadoResultado.DEFINITIVO:
        assert informe.condicionantes == ()


@settings(max_examples=120, deadline=None)
@given(c=casos())
def test_todo_condicionante_declara_su_sentido_y_que_falta(c: Caso) -> None:
    """FR-046b."""
    for cond in calcular(c, reglas=REGLAS).condicionantes:
        assert cond.sentido_impacto is not None
        assert cond.que_falta_verificar


def test_un_cargo_condicionado_vuelve_provisional_la_elegibilidad() -> None:
    c = caso(
        periodo("director", desde="1995-03-01", hasta="2026-02-28"),
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
    )
    informe = calcular(c, reglas=REGLAS)
    assert informe.estado_general is EstadoResultado.PROVISIONAL
    assert informe.elegibilidad.estado is EstadoResultado.PROVISIONAL


def test_una_historia_limpia_es_definitiva() -> None:
    c = caso(
        periodo("maestro_de_grado", desde="1995-03-01", hasta="2026-02-28"),
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
    )
    assert calcular(c, reglas=REGLAS).estado_general is EstadoResultado.DEFINITIVO


def test_una_licencia_vuelve_provisional_el_computo() -> None:
    """Cuestión abierta #5: cómo cuentan las licencias no está verificado."""
    c = caso(
        periodo(
            "maestro_de_grado",
            desde="1995-03-01",
            hasta="2026-02-28",
            licencias=(
                Licencia(
                    tipo=TipoLicencia.SIN_GOCE,
                    desde=dt.date(2010, 3, 1),
                    hasta=dt.date(2011, 2, 28),
                ),
            ),
            establecimiento=ESTATAL,
        ),
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
    )
    assert calcular(c, reglas=REGLAS).estado_general is EstadoResultado.PROVISIONAL


def test_una_situacion_de_revista_no_titular_vuelve_provisional_el_computo() -> None:
    """Cuestión abierta #5 ampliada: el art. 41 habla del cargo «de que era titular»."""
    c = caso(
        periodo(
            "maestro_de_grado",
            desde="1995-03-01",
            hasta="2026-02-28",
            situacion_revista=SituacionRevista.SUPLENTE,
        ),
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
    )
    assert calcular(c, reglas=REGLAS).estado_general is EstadoResultado.PROVISIONAL


def test_el_atajo_estado_de_devuelve_lo_mismo_que_el_informe() -> None:
    """FR-046c: la interfaz de librería no puede divergir del informe.

    `estado_de` existe para que un consumidor no tenga que recordar dónde vive
    el estado. Si devolviera otra cosa que `informe.estado_general`, habría dos
    respuestas posibles a la misma pregunta, que es justo lo que I6 impide.
    """
    informe = calcular(caso_inc_b(), reglas=REGLAS)
    assert estado_de(informe) is informe.estado_general
