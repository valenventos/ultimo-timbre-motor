# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T022 — `HistoriaDeServicios` normaliza el orden y asigna `idx` (FR-049).

La normalización es lo que hace cumplir FR-049/SC-010 **por construcción**: si
dos historias con los mismos períodos en distinto orden producen el mismo
objeto, el resto del motor ni siquiera puede observar el orden de carga.
"""

from __future__ import annotations

import datetime as dt

from ultimo_timbre.models.caso import Establecimiento, HistoriaDeServicios, PeriodoDeServicio
from ultimo_timbre.models.enums import CajaAportes, SituacionRevista, TipoEstablecimiento

EST = Establecimiento(tipo=TipoEstablecimiento.ESTATAL_DGCYE)


def _p(cargo: str, desde: str, hasta: str | None = None) -> PeriodoDeServicio:
    return PeriodoDeServicio(
        cargo=cargo,
        establecimiento=EST,
        desde=dt.date.fromisoformat(desde),
        hasta=dt.date.fromisoformat(hasta) if hasta else None,
        caja_aportes=CajaAportes.IPS,
        situacion_revista=SituacionRevista.TITULAR,
    )


A = _p("maestro_de_grado", "2000-03-01", "2010-02-28")
B = _p("vicedirector", "2010-03-01", "2018-02-28")
C = _p("director", "2018-03-01", "2026-02-28")


def test_ordena_los_periodos_por_fecha_de_inicio() -> None:
    h = HistoriaDeServicios(periodos=(C, A, B))
    assert [p.cargo for p in h.periodos] == ["maestro_de_grado", "vicedirector", "director"]


def test_asigna_idx_consecutivo_desde_cero() -> None:
    h = HistoriaDeServicios(periodos=(C, A, B))
    assert [p.idx for p in h.periodos] == [0, 1, 2]


def test_el_orden_de_carga_no_cambia_la_historia_normalizada() -> None:
    """FR-049, SC-010: la propiedad completa se verifica en tests/properties."""
    assert HistoriaDeServicios(periodos=(A, B, C)) == HistoriaDeServicios(periodos=(C, B, A))


def test_la_normalizacion_es_estable_con_periodos_de_igual_inicio() -> None:
    """Dos períodos que empiezan el mismo día se ordenan por `hasta` y luego por cargo."""
    x = _p("zcargo", "2010-03-01", "2012-02-28")
    y = _p("acargo", "2010-03-01", "2012-02-28")
    h1 = HistoriaDeServicios(periodos=(x, y))
    h2 = HistoriaDeServicios(periodos=(y, x))
    assert [p.cargo for p in h1.periodos] == [p.cargo for p in h2.periodos]
    assert [p.cargo for p in h1.periodos] == ["acargo", "zcargo"]


def test_un_periodo_en_curso_se_ordena_al_final_de_su_fecha_de_inicio() -> None:
    """`hasta is None` no puede romper el orden."""
    en_curso = _p("director", "2018-03-01", None)
    cerrado = _p("director", "2018-03-01", "2020-02-28")
    h = HistoriaDeServicios(periodos=(en_curso, cerrado))
    assert h.periodos[0].hasta is not None
    assert h.periodos[1].hasta is None


def test_la_historia_es_inmutable() -> None:
    h = HistoriaDeServicios(periodos=(A, B))
    assert isinstance(h.periodos, tuple)


def test_la_historia_conserva_todos_los_periodos() -> None:
    h = HistoriaDeServicios(periodos=(C, A, B))
    assert len(h.periodos) == 3


def test_la_historia_detecta_superposiciones() -> None:
    """La clasificación se prueba en US2; acá solo que se detectan."""
    uno = _p("maestro_de_grado", "2010-03-01", "2016-02-28")
    dos = _p("preceptor", "2012-03-01", "2018-02-28")
    h = HistoriaDeServicios(periodos=(uno, dos))
    assert len(h.superposiciones) == 1
    assert h.superposiciones[0].periodos == (0, 1)


def test_sin_superposicion_no_hay_hallazgos() -> None:
    h = HistoriaDeServicios(periodos=(A, B, C))
    assert h.superposiciones == ()
