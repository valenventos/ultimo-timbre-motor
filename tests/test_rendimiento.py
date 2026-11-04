# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T189 — SC-006: un caso grande produce su informe en menos de 5 segundos.

El criterio de éxito no es «rápido», es **usable en una consulta**: un abogado
con la docente sentada enfrente carga la historia y espera el informe. Cinco
segundos es el límite de lo que se tolera sin pensar que el programa se colgó.

El caso sintético es el grande de verdad: **30 años de historia** en 32
períodos, con cargos que cambian —para que el comparador de cargo base tenga
que decidir y no acepte el único candidato— y **5 fechas de cese**, que con las
derivadas de la US5 terminan siendo más escenarios todavía. Cada escenario se
valúa con la grilla ficticia, así que el camino medido incluye los montos.

**Qué se mide y qué no**: solo `calcular()`. La carga de reglas y de la grilla
queda afuera a propósito, porque es I/O que ocurre una vez por proceso y que la
CLI ya hizo antes de que el usuario empiece a esperar. Medirla adentro
convertiría este test en un test del disco de CI.

El umbral es deliberadamente generoso respecto del tiempo real observado. Un
test de rendimiento al borde del límite falla por el ruido de la máquina de CI
y termina marcado como inestable, que es la forma más común de perder un test
de rendimiento. Lo que este test detecta es una **regresión de orden de
magnitud** —un bucle cuadrático sobre los meses, una recarga de reglas por
escenario—, no una diferencia del 20 %.
"""

from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.models.normativa import ConjuntoDeReglas
from ultimo_timbre.rules import versiones

FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")

LIMITE_SEGUNDOS = 5.0

# Los cargos rotan para que el comparador de cargo base tenga trabajo: con un
# solo cargo elegiría sin comparar, y el camino caro quedaría sin medir.
ROTACION = (
    "maestro_de_grado",
    "maestro_de_grado",
    "maestro_de_grado",
    "preceptor",
    "vicedirector_primera",
)


def _caso_grande() -> Caso:
    """30 años de historia en 32 períodos y 5 fechas de cese.

    Un período por ciclo escolar, de marzo a febrero, más dos horas cátedra
    simultáneas en el medio para que la detección de simultaneidad y la unión
    de tramos (invariante I9) entren en el camino medido.
    """
    periodos = [
        periodo(
            ROTACION[n % len(ROTACION)],
            desde=f"{1996 + n}-03-01",
            hasta=f"{1997 + n}-02-28",
        )
        for n in range(30)
    ]
    periodos += [
        periodo("hora_catedra_secundaria", desde="2010-03-01", hasta="2012-02-28"),
        periodo("hora_catedra_secundaria", desde="2018-03-01", hasta="2020-02-28"),
    ]
    return caso(
        *periodos,
        nacimiento="1970-04-12",
        ceses=[
            "2026-02-28",
            "2027-02-28",
            "2028-02-29",
            "2029-02-28",
            "2030-02-28",
        ],
        fecha_de_calculo="2026-01-02",
    )


@pytest.fixture(scope="module")
def entradas() -> tuple[Caso, ConjuntoDeReglas, GrillaSalarial]:
    """Todo el I/O acá: lo que se mide después no toca el disco."""
    return (
        _caso_grande(),
        versiones.cargar_reglas("v1"),
        versiones.cargar_grilla_de_prueba(FIXTURE),
    )


def test_el_caso_sintetico_tiene_el_tamano_que_dice(
    entradas: tuple[Caso, ConjuntoDeReglas, GrillaSalarial],
) -> None:
    """Si el caso se encogiera, el test de tiempo pasaría por la razón equivocada."""
    caso_grande, _, _ = entradas
    assert len(caso_grande.historia.periodos) == 32
    assert len(caso_grande.fechas_cese) == 5

    abarca = caso_grande.fechas_cese[0] - caso_grande.historia.periodos[0].desde
    assert abarca >= dt.timedelta(days=365 * 29)


def test_el_informe_completo_sale_en_menos_de_cinco_segundos(
    entradas: tuple[Caso, ConjuntoDeReglas, GrillaSalarial],
) -> None:
    """SC-006. Se mide el reloj de pared, que es el que espera la persona."""
    caso_grande, reglas, grilla = entradas

    comenzado = time.perf_counter()
    informe = calcular(caso_grande, reglas=reglas, grilla=grilla)
    transcurrido = time.perf_counter() - comenzado

    # El informe tiene que ser el completo, no uno vacío que salga rápido.
    assert isinstance(informe, Informe)
    assert len(informe.escenarios) >= 5
    assert len(informe.desglose) > 0

    assert transcurrido < LIMITE_SEGUNDOS, (
        f"el informe tardó {transcurrido:.2f} s y el límite de SC-006 es {LIMITE_SEGUNDOS:.0f} s"
    )


def test_el_segundo_calculo_no_es_mas_lento_que_el_primero(
    entradas: tuple[Caso, ConjuntoDeReglas, GrillaSalarial],
) -> None:
    """Un cacheo que crece entre llamadas se vería acá antes que en producción.

    Los modelos son `frozen` y el motor no guarda estado, así que dos cálculos
    del mismo caso tienen que costar lo mismo. Si el segundo costara el doble,
    habría estado acumulándose en alguna parte —y con él, el riesgo de que un
    caso contamine al siguiente, que sería mucho peor que la lentitud.
    """
    caso_grande, reglas, grilla = entradas

    tiempos = []
    for _ in range(2):
        comenzado = time.perf_counter()
        calcular(caso_grande, reglas=reglas, grilla=grilla)
        tiempos.append(time.perf_counter() - comenzado)

    primero, segundo = tiempos
    # Umbral laxo: lo que se busca es un crecimiento de orden, no el ruido.
    assert segundo < primero * 3 + 0.5, f"primero {primero:.3f} s, segundo {segundo:.3f} s"
