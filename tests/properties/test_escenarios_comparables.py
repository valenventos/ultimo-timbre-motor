# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T157 — los escenarios son comparables entre sí (FR-036a).

La comparación es el producto: «si cesás en 2033 cobrás tanto más que en 2030».
Esa frase solo es verdadera si los dos montos salen de la **misma grilla**. Si
uno se valuara con la grilla de 2030 y otro con la de 2033, la diferencia
mezclaría el aumento de porcentaje con el aumento salarial, y el profesional
compararía dos cosas distintas creyendo que compara una.

Por eso todos los escenarios se valúan con la última grilla aprobada y declaran
el mismo `a_valores_de`. La diferencia de monto entre escenarios queda explicada
**solo** por el porcentaje y por la antigüedad.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tests.casos import caso_escenarios, caso_inc_b
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")

CASOS = {"escenarios": caso_escenarios, "inc_b": caso_inc_b}


@pytest.fixture(params=sorted(CASOS))
def informe(request: pytest.FixtureRequest) -> Informe:
    grilla: GrillaSalarial = versiones.cargar_grilla_de_prueba(FIXTURE)
    caso: Caso = CASOS[request.param]()
    return calcular(caso, reglas=REGLAS, grilla=grilla)


def test_todos_los_montos_usan_la_misma_grilla(informe: Informe) -> None:
    versiones_usadas = {e.haber.grilla_version for e in informe.escenarios if e.haber}
    assert len(versiones_usadas) <= 1, versiones_usadas


def test_todos_los_montos_declaran_el_mismo_a_valores_de(informe: Informe) -> None:
    fechas = {e.haber.a_valores_de for e in informe.escenarios if e.haber}
    assert len(fechas) <= 1, fechas


def test_la_grilla_del_monto_es_la_que_declara_el_informe(informe: Informe) -> None:
    for escenario in informe.escenarios:
        if escenario.haber is not None:
            assert escenario.haber.grilla_version == informe.version_grilla


def test_la_diferencia_de_monto_se_explica_por_porcentaje_y_antiguedad(
    informe: Informe,
) -> None:
    """A igual porcentaje y antigüedad, el monto tiene que ser idéntico.

    Es la forma verificable de FR-036a: si dos escenarios coinciden en las dos
    variables que el motor dice que explican la diferencia, y aun así difieren,
    hay una tercera variable metida —típicamente la grilla—.
    """
    vistos: dict[tuple[Decimal | None, int | None], Decimal] = {}
    for escenario in informe.escenarios:
        if escenario.haber is None:
            continue
        clave = (escenario.porcentaje, escenario.antiguedad_anios)
        if clave in vistos:
            assert vistos[clave] == escenario.haber.valor, clave
        vistos[clave] = escenario.haber.valor


def test_a_mayor_porcentaje_mayor_monto(informe: Informe) -> None:
    """Con antigüedad igual, el orden de los montos sigue al de los porcentajes."""
    por_antiguedad: dict[int, list[tuple[Decimal, Decimal]]] = {}
    for e in informe.escenarios:
        if e.haber is None or e.porcentaje is None or e.antiguedad_anios is None:
            continue
        por_antiguedad.setdefault(e.antiguedad_anios, []).append((e.porcentaje, e.haber.valor))

    for pares in por_antiguedad.values():
        montos = [monto for _, monto in sorted(pares)]
        assert montos == sorted(montos)
