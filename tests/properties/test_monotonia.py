# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T046 — invariante I4: monotonía **acotada**.

Agregar períodos **estatales de la DGCyE con aportes al IPS** nunca retrasa la
habilitación ni reduce el servicio computado.

La restricción al alcance no es un detalle: sin ella el invariante es falso.
Agregar un período en otra caja o en un establecimiento privado no mejora el
resultado, lo saca de alcance (FR-044, FR-045). Por eso el generador produce
únicamente períodos en alcance.
"""

from __future__ import annotations

import datetime as dt

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.casos import ESTATAL, caso, periodo
from ultimo_timbre.engine import calcular, calendario
from ultimo_timbre.models.caso import Caso, HistoriaDeServicios, PeriodoDeServicio
from ultimo_timbre.models.enums import CajaAportes
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
CESE = dt.date(2026, 2, 28)

inicios = st.dates(min_value=dt.date(1985, 1, 1), max_value=dt.date(2015, 12, 31))
duraciones = st.integers(min_value=100, max_value=3000)
cargos = st.sampled_from(["maestro_de_grado", "preceptor", "bibliotecario"])


@st.composite
def periodos_en_alcance(draw: st.DrawFn) -> PeriodoDeServicio:
    desde = draw(inicios)
    hasta = desde + dt.timedelta(days=draw(duraciones))
    p = periodo(draw(cargos), desde=desde.isoformat(), hasta=hasta.isoformat())
    # el generador solo produce períodos en alcance: es la cota del invariante
    assert p.establecimiento == ESTATAL
    assert p.caja_aportes is CajaAportes.IPS
    return p


@st.composite
def casos(draw: st.DrawFn) -> Caso:
    cantidad = draw(st.integers(min_value=1, max_value=3))
    periodos = [draw(periodos_en_alcance()) for _ in range(cantidad)]
    return caso(
        *periodos,
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-11-02",
    )


def _con(c: Caso, extra: PeriodoDeServicio) -> Caso:
    return c.model_copy(
        update={"historia": HistoriaDeServicios(periodos=(*c.historia.periodos, extra))}
    )


@settings(max_examples=100, deadline=None)
@given(c=casos(), extra=periodos_en_alcance())
def test_agregar_servicio_nunca_reduce_el_computo(c: Caso, extra: PeriodoDeServicio) -> None:
    antes = calendario.servicio_total(c.historia, CESE)
    despues = calendario.servicio_total(_con(c, extra).historia, CESE)
    assert despues >= antes


@settings(max_examples=100, deadline=None)
@given(c=casos(), extra=periodos_en_alcance())
def test_agregar_servicio_nunca_reduce_los_meses_cubiertos(
    c: Caso,
    extra: PeriodoDeServicio,
) -> None:
    antes = calendario.meses_cubiertos(c.historia, CESE)
    despues = calendario.meses_cubiertos(_con(c, extra).historia, CESE)
    assert antes <= despues


@settings(max_examples=60, deadline=None)
@given(c=casos(), extra=periodos_en_alcance())
def test_agregar_servicio_nunca_retrasa_la_habilitacion(c: Caso, extra: PeriodoDeServicio) -> None:
    antes = {i.inciso: i.habilitado_desde for i in calcular(c, reglas=REGLAS).elegibilidad.incisos}
    despues = {
        i.inciso: i.habilitado_desde
        for i in calcular(_con(c, extra), reglas=REGLAS).elegibilidad.incisos
    }
    for inciso, fecha_antes in antes.items():
        fecha_despues = despues[inciso]
        if fecha_antes is None:
            continue  # antes no cumplía: cualquier resultado posterior es mejora
        assert fecha_despues is not None, inciso
        assert fecha_despues <= fecha_antes, inciso


@settings(max_examples=60, deadline=None)
@given(c=casos(), extra=periodos_en_alcance())
def test_agregar_servicio_nunca_quita_un_inciso_cumplido(c: Caso, extra: PeriodoDeServicio) -> None:
    antes = {i.inciso for i in calcular(c, reglas=REGLAS).elegibilidad.incisos if i.cumple}
    despues = {
        i.inciso for i in calcular(_con(c, extra), reglas=REGLAS).elegibilidad.incisos if i.cumple
    }
    assert antes <= despues
