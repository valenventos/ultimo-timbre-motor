# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T087 — invariante I7: una advertencia bloqueante impide el haber (FR-044, FR-045).

Es la garantía que vuelve seguro el informe parcial de FR-045a: el motor puede
entregar todo el análisis que sostiene, pero **nunca** un monto sobre un caso
que detectó fuera de alcance.
"""

from __future__ import annotations

import datetime as dt

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.casos import ESTATAL, PRIVADO, caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import CajaAportes
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

inicios = st.dates(min_value=dt.date(1990, 1, 1), max_value=dt.date(2010, 12, 31))
duraciones = st.integers(min_value=400, max_value=4000)
cargos = st.sampled_from(["maestro_de_grado", "preceptor", "bibliotecario"])
cajas = st.sampled_from(list(CajaAportes))
establecimientos = st.sampled_from([ESTATAL, PRIVADO])


@st.composite
def casos(draw: st.DrawFn) -> Caso:
    """Genera casos que **pueden** estar fuera de alcance, a propósito."""
    cantidad = draw(st.integers(min_value=1, max_value=3))
    periodos = []
    for _ in range(cantidad):
        desde = draw(inicios)
        hasta = desde + dt.timedelta(days=draw(duraciones))
        periodos.append(
            periodo(
                draw(cargos),
                desde=desde.isoformat(),
                hasta=hasta.isoformat(),
                caja_aportes=draw(cajas),
                establecimiento=draw(establecimientos),
            )
        )
    return caso(
        *periodos,
        nacimiento="1965-04-15",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-11-02",
    )


@settings(max_examples=150, deadline=None)
@given(c=casos())
def test_con_bloqueo_ningun_escenario_lleva_haber(c: Caso) -> None:
    informe = calcular(c, reglas=REGLAS)
    if informe.tiene_bloqueos:
        assert all(e.haber is None for e in informe.escenarios)


@settings(max_examples=150, deadline=None)
@given(c=casos())
def test_toda_advertencia_bloqueante_llega_al_escenario(c: Caso) -> None:
    """Si el informe bloquea, el escenario tiene que decirlo: la CLI mira ahí."""
    informe = calcular(c, reglas=REGLAS)
    bloqueo_global = any(a.bloquea_calculo for a in informe.advertencias)
    if bloqueo_global:
        for escenario in informe.escenarios:
            assert any(a.bloquea_calculo for a in escenario.advertencias)


@settings(max_examples=150, deadline=None)
@given(c=casos())
def test_un_caso_fuera_de_alcance_siempre_devuelve_informe(c: Caso) -> None:
    """FR-045a: no hay excepción por casos de usuario."""
    informe = calcular(c, reglas=REGLAS)
    assert informe.elegibilidad is not None
    assert len(informe.elegibilidad.incisos) == 3


@settings(max_examples=150, deadline=None)
@given(c=casos())
def test_un_periodo_fuera_de_alcance_implica_bloqueo(c: Caso) -> None:
    """La detección no se puede saltear ningún período."""
    informe = calcular(c, reglas=REGLAS)
    hay_fuera = any(p.fuera_de_alcance for p in c.historia.periodos)
    assert informe.tiene_bloqueos == hay_fuera


@settings(max_examples=150, deadline=None)
@given(c=casos())
def test_toda_advertencia_bloqueante_declara_su_periodo(c: Caso) -> None:
    """FR-054: el índice anónimo es lo único que identifica al período."""
    informe = calcular(c, reglas=REGLAS)
    for adv in informe.advertencias:
        if adv.bloquea_calculo:
            assert adv.periodo_idx is not None
            assert 0 <= adv.periodo_idx < len(c.historia.periodos)


@settings(max_examples=100, deadline=None)
@given(c=casos())
def test_sin_bloqueo_el_computo_usa_todos_los_periodos(c: Caso) -> None:
    informe = calcular(c, reglas=REGLAS)
    if not informe.tiene_bloqueos:
        assert all(not p.fuera_de_alcance for p in c.historia.periodos)
