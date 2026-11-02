# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T109 — cargo base por 36 meses consecutivos (US3 esc. 1, FR-019, FR-020).

`[DL 9650/80, art. 41 (texto Ley 13968); Res. IPS 14/10]`

Director ejercido 40 meses consecutivos frente a Maestro ejercido 25 años: el
motor elige el de mayor jerarquía entre los que alcanzan el requisito temporal,
y enumera los meses que lo sustentan.

**Por qué este test usa jerarquía ficticia**: con `rules/v1/cargos.yaml` la
jerarquía es `null` en todos los cargos y la respuesta correcta es el empate
(ver `tests/unit/test_empate_jerarquia.py`). Lo que se verifica acá es la
mecánica del ranking, con el mismo criterio con que `grilla-ficticia-test.yaml`
verifica la mecánica del monto.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, periodo
from tests.catalogos import con_jerarquia_ficticia
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import ViaCargoBase
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = con_jerarquia_ficticia(versiones.cargar_reglas("v1"))


def _caso() -> Caso:
    """Maestra 1996-2021 y directora 2021-09 a 2024-12 (40 meses corridos)."""
    return caso(
        periodo("maestro_de_grado", desde="1996-03-01", hasta="2021-08-31"),
        periodo("director", desde="2021-09-01", hasta="2024-12-31"),
        nacimiento="1970-01-10",
        ceses=["2024-12-31"],
        fecha_de_calculo="2025-01-02",
    )


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(_caso(), reglas=REGLAS)


def test_elige_el_cargo_de_mayor_jerarquia(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "director"


def test_califica_por_los_36_meses_consecutivos(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.via is ViaCargoBase.CONSECUTIVOS_36


def test_enumera_los_meses_que_lo_sustentan(informe: Informe) -> None:
    """FR-020: qué meses concretos, no cuántos."""
    assert informe.cargo_base is not None
    meses = informe.cargo_base.meses_que_lo_sustentan
    assert len(meses) == 40
    assert meses[0] == "2021-09"
    assert meses[-1] == "2024-12"


def test_descarta_el_maestro_por_menor_jerarquia(informe: Informe) -> None:
    """FR-021: el descarte lleva su razón."""
    assert informe.cargo_base is not None
    descartado = next(d for d in informe.cargo_base.descartados if d.cargo == "maestro_de_grado")
    assert "jerarquía" in descartado.razon
    assert descartado.meses_alcanzados == 306


def test_no_hubo_descenso_al_cargo_inferior(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.descenso_desde is None


def test_cita_el_art_41(informe: Informe) -> None:
    """Principio I: la elección del cargo base tiene fuente."""
    assert informe.cargo_base is not None
    assert informe.cargo_base.norma.articulo == "41"
    assert "Ley 13968" in informe.cargo_base.norma.texto


def test_el_desglose_explica_la_eleccion(informe: Informe) -> None:
    """Principio IV: auditable paso a paso."""
    pasos = [p for p in informe.desglose if "cargo base" in p.descripcion.lower()]
    assert pasos
    assert all(p.norma.texto for p in pasos)
