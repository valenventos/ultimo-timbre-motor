# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T051 — el cese recorta, no rechaza (FR-018, FR-018a)."""

from __future__ import annotations

from tests.casos import f, periodo
from ultimo_timbre.engine import calendario
from ultimo_timbre.models.caso import HistoriaDeServicios


def test_un_periodo_posterior_al_cese_no_se_rechaza_se_recorta() -> None:
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta="2030-02-28"),))
    tramos = calendario.tramos_unidos(h, f("2020-02-29"))
    assert tramos[0].hasta == f("2020-02-29")


def test_cada_fecha_de_cese_recorta_de_forma_independiente() -> None:
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta="2030-02-28"),))
    assert calendario.servicio_total(h, f("2010-02-28")).anios == 10
    assert calendario.servicio_total(h, f("2020-02-29")).anios == 20


def test_no_se_computan_servicios_posteriores_al_cese() -> None:
    """FR-018, arts. 71 y 72: el cómputo cierra en el cese."""
    h = HistoriaDeServicios(
        periodos=(
            periodo(desde="2000-03-01", hasta="2010-02-28"),
            periodo(desde="2015-03-01", hasta="2025-02-28"),
        )
    )
    assert calendario.servicio_total(h, f("2012-02-29")).anios == 10


def test_el_recorte_se_reporta() -> None:
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta="2030-02-28"),))
    assert h.periodos_recortados_a(f("2020-02-29")) == (0,)
    assert h.periodos_recortados_a(f("2030-02-28")) == ()


def test_un_periodo_que_empieza_despues_del_cese_no_aporta_tramo() -> None:
    h = HistoriaDeServicios(periodos=(periodo(desde="2030-03-01", hasta="2035-02-28"),))
    assert calendario.tramos_unidos(h, f("2026-02-28")) == ()
