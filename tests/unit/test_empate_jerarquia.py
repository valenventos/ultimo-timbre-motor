# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T120 — empate de jerarquía: `empate_jerarquia` y cargo base provisional.

`[Res. IPS 14/10 — NO_VERIFICADA: criterio puntaje/índice vs remuneración,
Cuestión abierta #4]` (FR-022)

Este es el camino **normal** de la v1, no un caso borde: `rules/v1/cargos.yaml`
lleva `jerarquia: null` en todos los cargos porque ninguna norma citada
documenta un orden numérico que transcribir. Entonces, en cuanto dos cargos
distintos alcanzan los 36/60 meses, el motor no tiene con qué rankearlos.

Lo que hace es decirlo: advertencia `empate_jerarquia`, los candidatos
empatados expuestos, y el cargo base marcado provisional. Lo que **no** hace es
presentar su desempate técnico como si fuera el criterio del IPS.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
REGLA_JERARQUIA = "jerarquia.criterio_comparacion"


@pytest.fixture(scope="module")
def informe() -> Informe:
    """Maestra 15 años y preceptora 10: los dos cargos superan los 36 meses."""
    return calcular(
        caso(
            periodo("maestro_de_grado", desde="1996-01-01", hasta="2010-12-31"),
            periodo("preceptor", desde="2011-01-01", hasta="2020-12-31"),
            nacimiento="1968-01-10",
            ceses=["2020-12-31"],
            fecha_de_calculo="2021-01-01",
        ),
        reglas=REGLAS,
    )


def test_el_catalogo_real_no_tiene_jerarquia_que_comparar() -> None:
    """Resguardo del supuesto: si alguien carga jerarquía, este test lo avisa."""
    assert all(e.jerarquia is None for e in REGLAS.catalogo_cargos.entradas)


def test_se_advierte_el_empate(informe: Informe) -> None:
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.EMPATE_JERARQUIA in codigos


def test_el_empate_no_bloquea_el_calculo(informe: Informe) -> None:
    """El cargo base sigue siendo utilizable; lo que falta es el criterio."""
    adv = next(a for a in informe.advertencias if a.codigo is CodigoAdvertencia.EMPATE_JERARQUIA)
    assert adv.bloquea_calculo is False


def test_el_cargo_base_queda_provisional(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.estado is EstadoResultado.PROVISIONAL


def test_los_candidatos_empatados_quedan_expuestos(informe: Informe) -> None:
    """FR-021: con su razón, no solo el ganador."""
    assert informe.cargo_base is not None
    descartados = {d.cargo: d for d in informe.cargo_base.descartados}
    elegido = informe.cargo_base.cargo
    otro = "preceptor" if elegido == "maestro_de_grado" else "maestro_de_grado"
    assert otro in descartados
    assert "empate" in descartados[otro].razon.lower()


def test_el_condicionante_cita_la_cuestion_abierta_4(informe: Informe) -> None:
    cond = next(c for c in informe.condicionantes if c.referencia == REGLA_JERARQUIA)
    assert cond.norma is not None
    assert cond.que_falta_verificar


def test_el_estado_general_es_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_un_solo_cargo_no_empata_con_nadie() -> None:
    """Sin competencia no hace falta jerarquía: el resultado puede ser definitivo."""
    informe = calcular(
        caso(
            periodo("maestro_de_grado", desde="1996-01-01", hasta="2026-02-28"),
            nacimiento="1968-01-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=REGLAS,
    )
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.EMPATE_JERARQUIA not in codigos
    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "maestro_de_grado"
