# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T111 — descenso al cargo inferior (US3 esc. 3, FR-020a, FR-021).

`[DL 9650/80, art. 41]`

Directora 20 meses y Vicedirectora 48 consecutivos: el art. 41 no permite
regular por el cargo superior que no alcanzó los plazos, y considera a la
persona comprendida en el inferior que sí los alcanza. El motor descarta
Director, regula por Vicedirector y **explica el descenso** —que es la parte
que un expediente necesita para no parecer un error—.

Usa jerarquía ficticia por lo mismo que `test_cargo_base_36.py`: sin un orden
de jerarquía no hay «superior» ni «inferior» que determinar.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, periodo
from tests.catalogos import con_jerarquia_ficticia
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import ViaCargoBase
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = con_jerarquia_ficticia(versiones.cargar_reglas("v1"))


@pytest.fixture(scope="module")
def informe() -> Informe:
    """Maestra 1996-2016, vicedirectora 2017-2020 (48 meses), directora 20 meses."""
    return calcular(
        caso(
            periodo("maestro_de_grado", desde="1996-03-01", hasta="2016-12-31"),
            periodo("vicedirector", desde="2017-01-01", hasta="2020-12-31"),
            periodo("director", desde="2021-01-01", hasta="2022-08-31"),
            nacimiento="1970-01-10",
            ceses=["2022-08-31"],
            fecha_de_calculo="2022-09-01",
        ),
        reglas=REGLAS,
    )


def test_regula_por_el_vicedirector(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "vicedirector"


def test_la_via_es_el_descenso_al_cargo_inferior(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.via is ViaCargoBase.CARGO_INFERIOR


def test_declara_desde_que_cargo_descendio(informe: Informe) -> None:
    """FR-020a: sin esto el informe parece haber ignorado el cargo de Director."""
    assert informe.cargo_base is not None
    assert informe.cargo_base.descenso_desde == "director"


def test_descarta_el_director_por_no_alcanzar_los_plazos(informe: Informe) -> None:
    """FR-021: con los meses que sí alcanzó, para que la cuenta sea auditable."""
    assert informe.cargo_base is not None
    descartado = next(d for d in informe.cargo_base.descartados if d.cargo == "director")
    assert descartado.meses_alcanzados == 20
    assert "36" in descartado.razon
    assert "60" in descartado.razon


def test_los_48_meses_del_vicedirector_lo_sustentan(informe: Informe) -> None:
    assert informe.cargo_base is not None
    meses = informe.cargo_base.meses_que_lo_sustentan
    assert len(meses) == 48
    assert meses[0] == "2017-01"
    assert meses[-1] == "2020-12"


def test_el_desglose_explica_el_descenso(informe: Informe) -> None:
    """Principio IV y VIII: dicho en castellano, con su norma."""
    pasos = [p for p in informe.desglose if "inferior" in p.descripcion.lower()]
    assert pasos
    assert pasos[0].norma.articulo == "41"
