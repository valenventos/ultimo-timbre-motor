# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T112 — el promedio de 36 meses del art. 41, fuera de alcance (US3 esc. 4, FR-020b).

`[DL 9650/80, art. 41, tercer párrafo — fuera de alcance v1]`

Ningún cargo alcanza los 36 consecutivos ni los 60 alternados. El tercer
párrafo del art. 41 prevé en ese caso un promedio de 36 meses, que la v1 **no
calcula**: lo detecta y lo informa (Principio X). Calcularlo a medias sería
peor que no calcularlo, porque el número saldría igual de convincente.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado
from ultimo_timbre.models.informe import Advertencia, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    """24 meses de maestra y 18 de preceptora: ni 36 corridos ni 60 alternados."""
    return calcular(
        caso(
            periodo("maestro_de_grado", desde="2020-01-01", hasta="2021-12-31"),
            periodo("preceptor", desde="2022-01-01", hasta="2023-06-30"),
            nacimiento="1968-01-10",
            ceses=["2023-06-30"],
            fecha_de_calculo="2023-07-01",
        ),
        reglas=REGLAS,
    )


def _adv(informe: Informe) -> Advertencia:
    return next(
        a
        for a in informe.advertencias
        if a.codigo is CodigoAdvertencia.FUERA_DE_ALCANCE_PROMEDIO_36
    )


def test_se_detecta_el_caso_del_tercer_parrafo(informe: Informe) -> None:
    assert _adv(informe) is not None


def test_la_advertencia_cita_el_tercer_parrafo(informe: Informe) -> None:
    adv = _adv(informe)
    assert adv.norma is not None
    assert adv.norma.articulo == "41"
    assert "tercer párrafo" in adv.norma.texto


def test_la_advertencia_bloquea_el_calculo(informe: Informe) -> None:
    """Sin cargo base no hay haber que estimar (invariante I7)."""
    assert _adv(informe).bloquea_calculo is True
    assert informe.tiene_bloqueos is True


def test_no_se_determina_cargo_base(informe: Informe) -> None:
    assert informe.cargo_base is None


def test_no_se_calcula_haber(informe: Informe) -> None:
    assert all(e.haber is None for e in informe.escenarios)


def test_el_informe_igual_se_emite_con_su_analisis_parcial(informe: Informe) -> None:
    """FR-045a: lo que sí se sabe se entrega."""
    assert len(informe.elegibilidad.incisos) == 3
    assert informe.desglose


def test_el_desglose_explica_por_que_se_descarto_cada_cargo(informe: Informe) -> None:
    """FR-021 sigue valiendo aunque no haya cargo base elegido."""
    salidas = " ".join(p.salida or "" for p in informe.desglose)
    assert "maestro_de_grado" in salidas
    assert "preceptor" in salidas


def test_el_estado_general_es_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL
