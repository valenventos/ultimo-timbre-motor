# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T052 — período en curso: proyección bajo supuesto de continuidad (FR-002e)."""

from __future__ import annotations

from tests.casos import caso, f, periodo
from ultimo_timbre.engine import calcular, calendario
from ultimo_timbre.models.caso import Caso, HistoriaDeServicios
from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    CodigoAdvertencia,
    EstadoResultado,
)
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def _caso_en_curso() -> Caso:
    return caso(
        periodo(desde="2000-03-01", hasta=None),
        nacimiento="1974-01-10",
        ceses=["2026-02-28"],
    )


def test_un_periodo_en_curso_se_proyecta_hasta_el_cese() -> None:
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta=None),))
    assert calendario.servicio_total(h, f("2020-02-29")).anios == 20


def test_cada_cese_proyecta_de_forma_independiente() -> None:
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta=None),))
    assert calendario.servicio_total(h, f("2010-02-28")).anios == 10
    assert calendario.servicio_total(h, f("2025-02-28")).anios == 25


def test_el_periodo_en_curso_se_reporta() -> None:
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta=None),))
    assert h.periodos_en_curso() == (0,)


def test_el_informe_advierte_el_supuesto_de_continuidad() -> None:
    informe = calcular(_caso_en_curso(), reglas=REGLAS)
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.SUPUESTO_CONTINUIDAD in codigos


def test_el_supuesto_queda_en_la_procedencia() -> None:
    informe = calcular(_caso_en_curso(), reglas=REGLAS)
    assert any("continuidad" in p.dato for p in informe.procedencias)


def test_el_supuesto_condiciona_el_resultado() -> None:
    """FR-046b: es una situación del caso, no una regla sin verificar."""
    informe = calcular(_caso_en_curso(), reglas=REGLAS)
    assert informe.estado_general is EstadoResultado.PROVISIONAL
    clases = {c.clase for c in informe.condicionantes}
    assert ClaseCondicionante.SITUACION_DEL_CASO in clases


def test_el_condicionante_nombra_el_supuesto() -> None:
    informe = calcular(_caso_en_curso(), reglas=REGLAS)
    refs = {c.referencia for c in informe.condicionantes}
    assert CodigoAdvertencia.SUPUESTO_CONTINUIDAD.value in refs


def test_sin_periodos_en_curso_no_hay_advertencia_de_continuidad() -> None:
    c = caso(
        periodo(desde="2000-03-01", hasta="2026-02-28"),
        nacimiento="1974-01-10",
        ceses=["2026-02-28"],
    )
    informe = calcular(c, reglas=REGLAS)
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.SUPUESTO_CONTINUIDAD not in codigos
