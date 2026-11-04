# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T046 — invariante I9: la unión, nunca la suma (FR-004a, SC-014).

Es el invariante que protege contra el error clásico del dominio: sumar
duraciones de períodos superpuestos y producir una carrera de 40 años sobre una
de 25. El test genera solapamientos a propósito.
"""

from __future__ import annotations

import datetime as dt
import itertools

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.casos import periodo
from ultimo_timbre.engine import calendario
from ultimo_timbre.models.caso import HistoriaDeServicios

HORIZONTE = dt.date(2040, 12, 31)

inicios = st.dates(min_value=dt.date(1980, 1, 1), max_value=dt.date(2015, 12, 31))
duraciones = st.integers(min_value=30, max_value=4000)
cargos = st.sampled_from(["maestro_de_grado", "preceptor", "bibliotecario_ensenanza_superior"])


@st.composite
def historias(draw: st.DrawFn, minimo: int = 1, maximo: int = 4) -> HistoriaDeServicios:
    cantidad = draw(st.integers(min_value=minimo, max_value=maximo))
    periodos = []
    for _ in range(cantidad):
        desde = draw(inicios)
        hasta = desde + dt.timedelta(days=draw(duraciones))
        periodos.append(periodo(draw(cargos), desde=desde.isoformat(), hasta=hasta.isoformat()))
    return HistoriaDeServicios(periodos=tuple(periodos))


@settings(max_examples=120, deadline=None)
@given(h=historias())
def test_los_tramos_unidos_son_disjuntos_y_ordenados(h: HistoriaDeServicios) -> None:
    tramos = calendario.tramos_unidos(h, HORIZONTE)
    for anterior, siguiente in itertools.pairwise(tramos):
        assert anterior.hasta < siguiente.desde
        # y no contiguos: si lo fueran, se habrían fusionado
        assert (siguiente.desde - anterior.hasta).days > 1


@settings(max_examples=120, deadline=None)
@given(h=historias())
def test_los_dias_cubiertos_nunca_superan_la_suma_de_duraciones(
    h: HistoriaDeServicios,
) -> None:
    """La unión es siempre menor o igual que la suma. La igualdad solo sin solape."""
    suma = sum(
        (t.dias for p in h.periodos if (t := p.tramo_a(HORIZONTE)) is not None),
        0,
    )
    assert calendario.dias_cubiertos(h, HORIZONTE) <= suma


@settings(max_examples=120, deadline=None)
@given(h=historias())
def test_los_meses_cubiertos_nunca_superan_la_suma_de_meses(
    h: HistoriaDeServicios,
) -> None:
    suma = sum(
        (len(t.meses()) for p in h.periodos if (t := p.tramo_a(HORIZONTE)) is not None),
        0,
    )
    assert len(calendario.meses_cubiertos(h, HORIZONTE)) <= suma


@settings(max_examples=120, deadline=None)
@given(h=historias())
def test_duplicar_un_periodo_no_cambia_el_computo(h: HistoriaDeServicios) -> None:
    """Dos cargos idénticos en el mismo tramo aportan ese tramo una sola vez."""
    duplicada = HistoriaDeServicios(periodos=(*h.periodos, *h.periodos))
    assert calendario.dias_cubiertos(duplicada, HORIZONTE) == calendario.dias_cubiertos(
        h, HORIZONTE
    )
    assert calendario.servicio_total(duplicada, HORIZONTE) == calendario.servicio_total(
        h, HORIZONTE
    )


@settings(max_examples=120, deadline=None)
@given(h=historias())
def test_los_meses_cubiertos_coinciden_con_los_de_los_tramos_unidos(
    h: HistoriaDeServicios,
) -> None:
    desde_tramos = {m for t in calendario.tramos_unidos(h, HORIZONTE) for m in t.meses()}
    assert calendario.meses_cubiertos(h, HORIZONTE) == frozenset(desde_tramos)


@settings(max_examples=80, deadline=None)
@given(h=historias(minimo=2))
def test_el_servicio_total_no_supera_el_tramo_que_lo_abarca(
    h: HistoriaDeServicios,
) -> None:
    """Cota superior independiente: de la primera fecha a la última."""
    tramos = calendario.tramos_unidos(h, HORIZONTE)
    if not tramos:
        return
    abarcador = (tramos[-1].hasta - tramos[0].desde).days + 1
    assert calendario.dias_cubiertos(h, HORIZONTE) <= abarcador
