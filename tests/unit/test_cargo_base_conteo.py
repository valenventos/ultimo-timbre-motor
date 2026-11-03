# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T117 — racha de meses consecutivos y cardinalidad de alternados (FR-019, FR-004a).

El conteo de los 36/60 meses se resuelve sobre un **conjunto de meses
calendario**, no sobre deltas de días (research R2): «60 alternados» es la
cardinalidad del conjunto y «36 consecutivos» es la racha máxima en la
secuencia ordenada. Eso hace el conteo exacto y permite exponer qué meses
concretos sustentan el cargo base, que es lo que exige FR-020.

El invariante I9 vive acá: los meses se cuentan sobre la **unión**. Dos cargos
simultáneos durante un mismo mes aportan ese mes una vez, no dos.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, f, periodo
from ultimo_timbre.engine import cargo_base
from ultimo_timbre.models.caso import MesCalendario


def _meses(*pares: str) -> frozenset[MesCalendario]:
    return frozenset(
        MesCalendario(anio=int(p.split("-")[0]), mes=int(p.split("-")[1])) for p in pares
    )


def test_racha_de_meses_contiguos() -> None:
    assert cargo_base.racha_maxima(_meses("2020-01", "2020-02", "2020-03")) == 3


def test_el_corte_de_anio_no_interrumpe_la_racha() -> None:
    """Diciembre y enero son consecutivos: el ordinal es absoluto, no por año."""
    assert cargo_base.racha_maxima(_meses("2020-11", "2020-12", "2021-01")) == 3


def test_un_hueco_corta_la_racha() -> None:
    meses = _meses("2020-01", "2020-02", "2020-03", "2020-06", "2020-07")
    assert cargo_base.racha_maxima(meses) == 3
    assert len(meses) == 5


def test_la_racha_toma_la_mas_larga_no_la_primera() -> None:
    meses = _meses("2020-01", "2020-02", "2020-05", "2020-06", "2020-07", "2020-08")
    assert cargo_base.racha_maxima(meses) == 4


def test_el_conjunto_vacio_no_tiene_racha() -> None:
    assert cargo_base.racha_maxima(frozenset()) == 0


def test_un_mes_solo_es_racha_de_uno() -> None:
    assert cargo_base.racha_maxima(_meses("2020-01")) == 1


# ---------------------------------------------------------------------------
# I9 / FR-004a — los meses se cuentan sobre la unión
# ---------------------------------------------------------------------------


def test_dos_periodos_simultaneos_del_mismo_cargo_no_duplican_meses() -> None:
    """Invariante I9: unión, nunca suma de duraciones superpuestas."""
    c = caso(
        periodo(desde="2020-01-01", hasta="2021-12-31"),
        periodo(desde="2021-01-01", hasta="2022-12-31"),
        nacimiento="1970-01-10",
        ceses=["2022-12-31"],
    )
    meses = cargo_base.meses_del_cargo(c.historia, f("2022-12-31"), "maestro_de_grado")
    # 2020-01 a 2022-12 son 36 meses; sumar duraciones daría 24 + 24 = 48
    assert len(meses) == 36
    assert cargo_base.racha_maxima(meses) == 36


def test_los_meses_se_recortan_a_la_fecha_de_cese() -> None:
    """FR-018: el cómputo cierra en el cese, no en el fin del período."""
    c = caso(
        periodo(desde="2020-01-01", hasta="2025-12-31"),
        nacimiento="1970-01-10",
        ceses=["2021-06-30"],
    )
    meses = cargo_base.meses_del_cargo(c.historia, f("2021-06-30"), "maestro_de_grado")
    assert len(meses) == 18
    assert max(meses) == MesCalendario(anio=2021, mes=6)


def test_solo_cuenta_los_meses_del_cargo_pedido() -> None:
    c = caso(
        periodo("maestro_de_grado", desde="2020-01-01", hasta="2020-12-31"),
        periodo("director_primera", desde="2021-01-01", hasta="2021-12-31"),
        nacimiento="1970-01-10",
        ceses=["2021-12-31"],
    )
    assert len(cargo_base.meses_del_cargo(c.historia, f("2021-12-31"), "maestro_de_grado")) == 12
    assert len(cargo_base.meses_del_cargo(c.historia, f("2021-12-31"), "director_primera")) == 12


@pytest.mark.parametrize("cargo", ["inexistente", ""])
def test_un_cargo_que_no_esta_en_la_historia_no_tiene_meses(cargo: str) -> None:
    c = caso(periodo(), nacimiento="1970-01-10", ceses=["2026-02-28"])
    assert cargo_base.meses_del_cargo(c.historia, f("2026-02-28"), cargo) == frozenset()
