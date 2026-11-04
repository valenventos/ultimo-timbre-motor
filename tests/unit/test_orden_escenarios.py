# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T161 — orden cronológico estable de los escenarios (FR-037).

Los escenarios se leen como una línea de tiempo: «si cesás acá cobrás esto, si
esperás hasta acá cobrás esto otro». Desordenados dejan de ser una comparación
y pasan a ser una lista.

Dos exigencias distintas:

* **cronológico**, para que la comparación se lea de izquierda a derecha;
* **estable**, para que el invariante I3 se sostenga: el orden en que el usuario
  escribió las fechas de cese no puede cambiar el informe, ni un byte.

Cuando una fecha provista coincide con una derivada no se duplica el escenario:
se queda con la etiqueta **más específica**. Saber que una fecha es la del
excedente de 3 años dice más que saber que el usuario la escribió.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.casos import caso, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import TipoEscenario
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.render.json_out import informe_a_json
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


def _caso(*ceses: str) -> Caso:
    return caso(
        periodo("maestro_de_grado", desde="2004-03-01", hasta=None),
        nacimiento="1980-03-15",
        ceses=list(ceses),
        fecha_de_calculo="2030-04-01",
    )


@pytest.fixture(scope="module")
def grilla() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(FIXTURE)


def _informe(grilla: GrillaSalarial, *ceses: str) -> Informe:
    return calcular(_caso(*ceses), reglas=REGLAS, grilla=grilla)


def test_los_escenarios_salen_en_orden_cronologico(grilla: GrillaSalarial) -> None:
    informe = _informe(grilla, "2032-06-30", "2030-03-31", "2031-12-31")
    fechas = [e.fecha_cese for e in informe.escenarios]
    assert fechas == sorted(fechas)


def test_el_orden_de_entrada_no_cambia_el_informe(grilla: GrillaSalarial) -> None:
    """Invariante I3: ni un byte de diferencia."""
    uno = informe_a_json(_informe(grilla, "2030-03-31", "2031-12-31", "2032-06-30"))
    otro = informe_a_json(_informe(grilla, "2032-06-30", "2030-03-31", "2031-12-31"))
    assert uno == otro


def test_las_derivadas_se_intercalan_entre_las_provistas(grilla: GrillaSalarial) -> None:
    """La habilitación es del 2030-03-15 y los excedentes de 2033 y 2035."""
    informe = _informe(grilla, "2031-12-31")
    fechas = [e.fecha_cese for e in informe.escenarios]
    assert fechas == [
        f("2030-03-15"),
        f("2031-12-31"),
        f("2033-03-15"),
        f("2035-03-15"),
    ]


def test_una_fecha_provista_que_coincide_con_una_derivada_no_se_duplica(
    grilla: GrillaSalarial,
) -> None:
    informe = _informe(grilla, "2033-03-15")
    fechas = [e.fecha_cese for e in informe.escenarios]
    assert len(fechas) == len(set(fechas))


def test_al_coincidir_gana_la_etiqueta_mas_especifica(grilla: GrillaSalarial) -> None:
    """«Excedente de 3 años» dice más que «la escribió el usuario»."""
    informe = _informe(grilla, "2033-03-15")
    coincidente = next(e for e in informe.escenarios if e.fecha_cese == f("2033-03-15"))
    assert coincidente.tipo is TipoEscenario.EXCEDENTE_3


def test_las_fechas_repetidas_por_el_usuario_no_duplican_escenarios(
    grilla: GrillaSalarial,
) -> None:
    """El modelo ya rechaza `fechas_cese` duplicadas; esto cuida el otro camino."""
    informe = _informe(grilla, "2031-12-31", "2032-06-30")
    fechas = [e.fecha_cese for e in informe.escenarios]
    assert len(fechas) == len(set(fechas))


def test_cada_tipo_derivado_aparece_una_sola_vez(grilla: GrillaSalarial) -> None:
    informe = _informe(grilla, "2031-12-31")
    for tipo in (
        TipoEscenario.HABILITACION,
        TipoEscenario.EXCEDENTE_3,
        TipoEscenario.EXCEDENTE_5,
    ):
        assert sum(1 for e in informe.escenarios if e.tipo is tipo) == 1
