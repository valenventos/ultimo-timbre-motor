# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T050 — unión de tramos y meses cubiertos (FR-004a, invariante I9)."""

from __future__ import annotations

from tests.casos import f, periodo
from ultimo_timbre.engine import calendario
from ultimo_timbre.models.caso import HistoriaDeServicios, PeriodoDeServicio


def historia(*ps: PeriodoDeServicio) -> HistoriaDeServicios:
    return HistoriaDeServicios(periodos=tuple(ps))


def test_tramos_disjuntos_se_mantienen_separados() -> None:
    h = historia(
        periodo(desde="2000-03-01", hasta="2005-02-28"),
        periodo(desde="2010-03-01", hasta="2015-02-28"),
    )
    assert len(calendario.tramos_unidos(h, f("2026-02-28"))) == 2


def test_tramos_contiguos_se_fusionan() -> None:
    """Un día de diferencia no abre un hueco real en la carrera."""
    h = historia(
        periodo(desde="2000-03-01", hasta="2005-02-28"),
        periodo(desde="2005-03-01", hasta="2010-02-28"),
    )
    tramos = calendario.tramos_unidos(h, f("2026-02-28"))
    assert len(tramos) == 1
    assert tramos[0].desde == f("2000-03-01")
    assert tramos[0].hasta == f("2010-02-28")


def test_tramos_superpuestos_se_fusionan_en_uno() -> None:
    h = historia(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2010-02-28"),
        periodo("preceptor", desde="2005-03-01", hasta="2015-02-28"),
    )
    tramos = calendario.tramos_unidos(h, f("2026-02-28"))
    assert len(tramos) == 1
    assert tramos[0].hasta == f("2015-02-28")


def test_los_meses_cubiertos_no_se_cuentan_dos_veces() -> None:
    """Dos cargos simultáneos durante 2015 aportan el año 2015 una sola vez."""
    h = historia(
        periodo("maestro_de_grado", desde="2015-01-01", hasta="2015-12-31"),
        periodo("preceptor", desde="2015-01-01", hasta="2015-12-31"),
    )
    assert len(calendario.meses_cubiertos(h, f("2026-02-28"))) == 12


def test_un_periodo_de_un_dia_cubre_su_mes() -> None:
    h = historia(periodo(desde="2015-06-15", hasta="2015-06-15"))
    assert len(calendario.meses_cubiertos(h, f("2026-02-28"))) == 1


def test_la_duracion_de_un_tramo_exacto_de_anios() -> None:
    h = historia(periodo(desde="2000-03-01", hasta="2010-02-28"))
    d = calendario.servicio_total(h, f("2026-02-28"))
    assert d.anios == 10
    assert d.meses == 0


def test_la_duracion_suma_tramos_disjuntos() -> None:
    h = historia(
        periodo(desde="2000-03-01", hasta="2005-02-28"),
        periodo(desde="2010-03-01", hasta="2015-02-28"),
    )
    assert calendario.servicio_total(h, f("2026-02-28")).anios == 10


def test_la_duracion_de_tramos_superpuestos_no_suma_duraciones() -> None:
    """Invariante I9: la unión, nunca la suma."""
    h = historia(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2010-02-28"),
        periodo("preceptor", desde="2000-03-01", hasta="2010-02-28"),
    )
    assert calendario.servicio_total(h, f("2026-02-28")).anios == 10


def test_los_meses_se_normalizan_a_anios() -> None:
    h = historia(
        periodo(desde="2000-01-01", hasta="2000-07-31"),
        periodo(desde="2001-01-01", hasta="2001-07-31"),
    )
    d = calendario.servicio_total(h, f("2026-02-28"))
    assert (d.anios, d.meses) == (1, 2)


def test_la_duracion_es_comparable_contra_un_umbral() -> None:
    h = historia(periodo(desde="2000-03-01", hasta="2025-02-28"))
    d = calendario.servicio_total(h, f("2026-02-28"))
    assert d.cumple_anios(25)
    assert not d.cumple_anios(26)


def test_servicio_filtrado_por_condicion() -> None:
    """Los años al frente de alumnos son un subconjunto de los de servicio."""
    # 2020 es bisiesto: para que el tramo unido dé 20 años exactos hay que
    # llegar al 29 de febrero, no al 28. Esta es justamente la clase de
    # aproximación que el Principio II prohíbe dar por buena.
    h = historia(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2010-02-28"),
        periodo("administrativo", desde="2010-03-01", hasta="2020-02-29"),
    )
    total = calendario.servicio_total(h, f("2026-02-28"))
    solo_primero = calendario.servicio_total(h, f("2026-02-28"), idx_incluidos={0})
    assert total.anios == 20
    assert solo_primero.anios == 10


def test_un_dia_menos_no_completa_el_anio() -> None:
    """Hasta el 28 de febrero de un año bisiesto falta un día para los 20 años."""
    h = historia(periodo(desde="2000-03-01", hasta="2020-02-28"))
    d = calendario.servicio_total(h, f("2026-02-28"))
    assert (d.anios, d.meses, d.dias) == (19, 11, 28)
    assert not d.cumple_anios(20)


def test_sin_periodos_vigentes_la_duracion_es_cero() -> None:
    h = historia(periodo(desde="2030-03-01", hasta="2035-02-28"))
    d = calendario.servicio_total(h, f("2026-02-28"))
    assert (d.anios, d.meses, d.dias) == (0, 0, 0)


def test_horas_catedra_simultaneas_suma_los_periodos_superpuestos() -> None:
    h = historia(
        periodo(
            "horas_catedra_secundario",
            desde="2010-03-01",
            hasta="2020-02-28",
            horas_catedra=12,
        ),
        periodo(
            "horas_catedra_secundario",
            desde="2012-03-01",
            hasta="2018-02-28",
            horas_catedra=10,
        ),
    )
    # en 2015 los dos períodos están activos; en 2019 ya solo el primero
    assert calendario.horas_catedra_simultaneas(h, 0, f("2015-01-01")) == 22
    assert calendario.horas_catedra_simultaneas(h, 0, f("2019-01-01")) == 12
    # lo que el motor usa es el máximo alcanzado durante el período
    assert calendario.max_horas_catedra_simultaneas(h, 0, f("2026-02-28")) == 22


def test_horas_catedra_simultaneas_ignora_los_periodos_disjuntos() -> None:
    h = historia(
        periodo(
            "horas_catedra_secundario",
            desde="2010-03-01",
            hasta="2012-02-28",
            horas_catedra=12,
        ),
        periodo(
            "horas_catedra_secundario",
            desde="2015-03-01",
            hasta="2018-02-28",
            horas_catedra=10,
        ),
    )
    assert calendario.horas_catedra_simultaneas(h, 0, f("2011-01-01")) == 12


def test_la_fecha_al_alcanzar_un_umbral_de_servicio() -> None:
    """Lo que `habilitado_desde` necesita: cuándo se alcanzaron los N años."""
    h = historia(periodo(desde="2000-03-01", hasta="2030-02-28"))
    fecha = calendario.fecha_al_alcanzar_servicio(h, 25, limite=f("2030-02-28"))
    assert fecha == f("2025-02-28")


def test_la_fecha_al_alcanzar_un_umbral_no_alcanzado_es_none() -> None:
    h = historia(periodo(desde="2000-03-01", hasta="2010-02-28"))
    assert calendario.fecha_al_alcanzar_servicio(h, 25, limite=f("2010-02-28")) is None
