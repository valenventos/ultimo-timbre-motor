# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T110 — cargo base por 60 meses alternados (US3 esc. 2, FR-019).

Un cargo ejercido 60 meses alternados pero nunca 36 consecutivos califica por
la vía alternada, y el motor lo explica. Es la vía que existe justamente para
las trayectorias discontinuas, que en la docencia son la norma y no la
excepción.

Un solo cargo en la historia: no hay jerarquía que comparar, así que este caso
corre sobre el catálogo real de `rules/v1/`.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.engine import cargo_base as cb
from ultimo_timbre.models.caso import MesCalendario
from ultimo_timbre.models.enums import CodigoAdvertencia, ViaCargoBase
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    """Cinco tramos de 12 meses, separados por huecos de 12.

    Racha máxima 12 meses; cardinalidad 60. Por los 36 consecutivos no
    calificaría nunca; por los 60 alternados, sí.
    """
    return calcular(
        caso(
            periodo("preceptor", desde="2010-01-01", hasta="2010-12-31"),
            periodo("preceptor", desde="2012-01-01", hasta="2012-12-31"),
            periodo("preceptor", desde="2014-01-01", hasta="2014-12-31"),
            periodo("preceptor", desde="2016-01-01", hasta="2016-12-31"),
            periodo("preceptor", desde="2018-01-01", hasta="2018-12-31"),
            nacimiento="1965-01-10",
            ceses=["2018-12-31"],
            fecha_de_calculo="2019-01-02",
        ),
        reglas=REGLAS,
    )


def test_el_cargo_califica(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "preceptor"


def test_califica_por_la_via_alternada(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.via is ViaCargoBase.ALTERNADOS_60


def test_son_60_meses_alternados(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert len(informe.cargo_base.meses_que_lo_sustentan) == 60


def test_nunca_alcanzo_36_consecutivos(informe: Informe) -> None:
    """Resguardo del escenario: si fueran corridos, el test no probaría nada."""
    meses = frozenset(
        MesCalendario(anio=int(m[:4]), mes=int(m[5:]))
        for m in informe.cargo_base.meses_que_lo_sustentan  # type: ignore[union-attr]
    )
    assert cb.racha_maxima(meses) == 12


def test_el_desglose_explica_la_via(informe: Informe) -> None:
    pasos = [p for p in informe.desglose if "alternados" in (p.salida or "")]
    assert pasos


def test_no_se_informa_el_promedio_de_36_meses(informe: Informe) -> None:
    """Hay cargo base: el tercer párrafo del art. 41 no entra en juego."""
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.FUERA_DE_ALCANCE_PROMEDIO_36 not in codigos
