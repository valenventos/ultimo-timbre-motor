# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T044 — invariante I1: el orden de carga no altera el informe (FR-049, SC-010).

La normalización de `HistoriaDeServicios` hace que esto valga por construcción,
pero el invariante se verifica sobre el informe completo: alcanza con que un
solo campo dependa del orden para que el resultado deje de ser auditable.
"""

from __future__ import annotations

import datetime as dt
import itertools

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso, HistoriaDeServicios
from ultimo_timbre.render import json_out
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

inicios = st.dates(min_value=dt.date(1985, 1, 1), max_value=dt.date(2010, 12, 31))
duraciones = st.integers(min_value=400, max_value=3000)
cargos = st.sampled_from(["maestro_de_grado", "preceptor", "bibliotecario"])


@st.composite
def casos(draw: st.DrawFn) -> Caso:
    cantidad = draw(st.integers(min_value=2, max_value=4))
    periodos = []
    for _ in range(cantidad):
        desde = draw(inicios)
        hasta = desde + dt.timedelta(days=draw(duraciones))
        periodos.append(periodo(draw(cargos), desde=desde.isoformat(), hasta=hasta.isoformat()))
    return caso(
        *periodos,
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-11-02",
    )


def _reordenado(c: Caso, orden: tuple[int, ...]) -> Caso:
    periodos = tuple(c.historia.periodos[i] for i in orden)
    return c.model_copy(update={"historia": HistoriaDeServicios(periodos=periodos)})


@settings(max_examples=60, deadline=None)
@given(c=casos())
def test_la_historia_normalizada_es_la_misma_en_cualquier_orden(c: Caso) -> None:
    n = len(c.historia.periodos)
    for orden in itertools.permutations(range(n)):
        assert _reordenado(c, orden).historia == c.historia


@settings(max_examples=40, deadline=None)
@given(c=casos())
def test_el_informe_es_identico_en_cualquier_orden(c: Caso) -> None:
    referencia = json_out.informe_a_json(calcular(c, reglas=REGLAS))
    n = len(c.historia.periodos)
    for orden in itertools.permutations(range(n)):
        otro = json_out.informe_a_json(calcular(_reordenado(c, orden), reglas=REGLAS))
        assert otro == referencia


@settings(max_examples=60, deadline=None)
@given(c=casos())
def test_los_idx_son_consecutivos_y_no_dependen_del_orden(c: Caso) -> None:
    esperado = list(range(len(c.historia.periodos)))
    assert [p.idx for p in c.historia.periodos] == esperado
    invertido = _reordenado(c, tuple(reversed(esperado)))
    assert [p.cargo for p in invertido.historia.periodos] == [p.cargo for p in c.historia.periodos]
