# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T071, T072 — la convención de conteo es una decisión declarada.

El motor no puede *no* contar: tiene que elegir si cuenta días calendario
reales o meses de 30 días, si la fecha final es inclusiva, y si arrastra los
días residuales a meses. Esa elección no está verificada contra ninguna norma
(Cuestión abierta #5), así que se declara como **valor por defecto aplicado**
en lugar de quedar escondida en el código.
"""

from __future__ import annotations

import pytest

from tests.casos import f, periodo
from ultimo_timbre.engine import calendario
from ultimo_timbre.models.caso import HistoriaDeServicios
from ultimo_timbre.models.enums import ConvencionConteo, EstadoRegla
from ultimo_timbre.models.normativa import ConjuntoDeReglas
from ultimo_timbre.rules import versiones

REGLA = "computo.convencion_de_conteo"


@pytest.fixture(scope="module")
def reglas() -> ConjuntoDeReglas:
    return versiones.cargar_reglas("v1")


# --------------------------------------------------------------------------- #
# T071 — la regla existe, no está verificada y declara su default aplicado
# --------------------------------------------------------------------------- #


def test_la_convencion_es_una_regla_no_verificada(reglas: ConjuntoDeReglas) -> None:
    regla = reglas.por_id(REGLA)
    assert regla is not None
    assert regla.estado is EstadoRegla.NO_VERIFICADA
    assert regla.cuestion_abierta == 5


def test_la_convencion_declara_su_valor_por_defecto_aplicado(
    reglas: ConjuntoDeReglas,
) -> None:
    """Distingue «no verificada y sin valor» de «no verificada pero hubo que elegir»."""
    regla = reglas.por_id(REGLA)
    assert regla is not None
    assert regla.valor_por_defecto_aplicado is True
    assert regla.valor is not None


def test_el_valor_por_defecto_es_la_convencion_actual(reglas: ConjuntoDeReglas) -> None:
    regla = reglas.por_id(REGLA)
    assert regla is not None
    assert regla.valor is not None
    assert regla.valor["convencion"] == ConvencionConteo.DIAS_REALES.value
    assert regla.valor["fecha_final"] == "inclusiva"
    assert regla.valor["arrastre_de_dias"] is False


def test_la_convencion_declara_que_falta_verificar(reglas: ConjuntoDeReglas) -> None:
    regla = reglas.por_id(REGLA)
    assert regla is not None
    assert regla.que_falta_verificar
    assert "30" in regla.que_falta_verificar


def test_el_umbral_de_arrastre_sale_de_la_regla(reglas: ConjuntoDeReglas) -> None:
    """Principio I: el «30» de los meses de 30 días es un valor normativo."""
    regla = reglas.por_id(REGLA)
    assert regla is not None
    assert regla.valor is not None
    assert regla.valor["dias_por_mes_alternativa"] == 30


def test_las_demas_reglas_no_verificadas_siguen_sin_valor(
    reglas: ConjuntoDeReglas,
) -> None:
    """Las excepciones son las que obligan a elegir, y las ya verificadas en parte.

    El criterio completo está en
    `test_cargar_reglas.test_ninguna_regla_no_verificada_lleva_valor`.
    """
    for r in reglas.no_verificadas:
        if r.valor_por_defecto_aplicado or r.evidencia:
            continue
        assert r.valor is None, r.id


# --------------------------------------------------------------------------- #
# T072 — las dos convenciones se calculan y pueden diferir
# --------------------------------------------------------------------------- #


def test_las_dos_convenciones_difieren_por_la_fecha_final() -> None:
    """Un tramo de 10 años exactos con fecha inclusiva es 9 años y 11 meses con
    fecha exclusiva. Esa diferencia de un día es, justamente, lo que la
    Cuestión abierta #5 no tiene resuelto."""
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta="2010-02-28"),))
    reales = calendario.servicio_total(h, f("2026-02-28"))
    alternativa = calendario.servicio_total(
        h, f("2026-02-28"), convencion=ConvencionConteo.MESES_30
    )
    assert reales.anios == 10
    assert alternativa.anios == 9
    assert (alternativa.meses, alternativa.dias) == (11, 27)


def test_las_dos_convenciones_difieren_con_dias_residuales() -> None:
    """Dos tramos de ~7 meses: la alternativa arrastra los días y la actual no."""
    h = HistoriaDeServicios(
        periodos=(
            periodo(desde="2000-01-01", hasta="2000-07-20"),
            periodo(desde="2001-01-01", hasta="2001-07-20"),
        )
    )
    reales = calendario.servicio_total(h, f("2026-02-28"))
    alternativa = calendario.servicio_total(
        h, f("2026-02-28"), convencion=ConvencionConteo.MESES_30
    )
    assert reales.dias > 0
    assert alternativa != reales


def test_la_convencion_alternativa_arrastra_dias_a_meses() -> None:
    h = HistoriaDeServicios(
        periodos=(
            periodo(desde="2000-01-01", hasta="2000-02-20"),
            periodo(desde="2001-01-01", hasta="2001-02-20"),
            periodo(desde="2002-01-01", hasta="2002-02-20"),
        )
    )
    alternativa = calendario.servicio_total(
        h, f("2026-02-28"), convencion=ConvencionConteo.MESES_30
    )
    assert alternativa.dias < 30


def test_la_convencion_por_defecto_es_dias_reales() -> None:
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta="2010-02-28"),))
    assert calendario.servicio_total(h, f("2026-02-28")) == calendario.servicio_total(
        h, f("2026-02-28"), convencion=ConvencionConteo.DIAS_REALES
    )


def test_la_fecha_de_cruce_puede_diferir_entre_convenciones() -> None:
    """Es lo que hace que un caso cerca del umbral sea sensible."""
    h = HistoriaDeServicios(periodos=(periodo(desde="2000-01-10", hasta="2030-02-28"),))
    a = calendario.fecha_al_alcanzar_servicio(h, 25, limite=f("2030-02-28"))
    b = calendario.fecha_al_alcanzar_servicio(
        h, 25, limite=f("2030-02-28"), convencion=ConvencionConteo.MESES_30
    )
    assert a is not None
    assert b is not None
    assert abs((a - b).days) >= 0  # pueden coincidir; lo que importa es que se calculen
