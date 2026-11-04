# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T092 — un caso fuera de alcance igual devuelve un informe (FR-045a, FR-047).

La decisión de diseño que esto verifica: abortar con excepción le quitaría al
profesional el análisis parcial que el motor ya tenía calculado —qué dicen los
20 años que sí son del IPS—, y el Principio IV prefiere un resultado parcial
explicado a ninguno.

`FueraDeAlcance` quedó reservada para errores de programación.
"""

from __future__ import annotations

import pytest

from tests.casos import PRIVADO, caso, caso_otra_caja, caso_privado, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.errors import FueraDeAlcance
from ultimo_timbre.models.enums import EstadoResultado
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

CASOS = {"otra_caja": caso_otra_caja, "privado": caso_privado}


@pytest.fixture(params=sorted(CASOS))
def informe(request: pytest.FixtureRequest) -> Informe:
    return calcular(CASOS[request.param](), reglas=REGLAS)


def test_no_se_lanza_fuera_de_alcance(informe: Informe) -> None:
    assert informe is not None


def test_fuera_de_alcance_sigue_siendo_un_error_de_programacion() -> None:
    """No se usa para casos de usuario: si aparece, es un bug del motor."""
    assert issubclass(FueraDeAlcance, Exception)
    with pytest.raises(FueraDeAlcance):
        raise FueraDeAlcance("ruta interna que valuó un tramo fuera de alcance")


def test_el_informe_trae_la_elegibilidad_de_los_tramos_computables(
    informe: Informe,
) -> None:
    assert len(informe.elegibilidad.incisos) == 3
    for inciso in informe.elegibilidad.incisos:
        assert inciso.requisitos


def test_el_informe_trae_el_desglose(informe: Informe) -> None:
    assert informe.desglose
    for paso in informe.desglose:
        assert paso.norma.texto


def test_el_informe_trae_las_procedencias(informe: Informe) -> None:
    assert informe.procedencias


def test_el_informe_no_trae_haber(informe: Informe) -> None:
    assert all(e.haber is None for e in informe.escenarios)


def test_el_informe_declara_sus_bloqueos(informe: Informe) -> None:
    assert informe.tiene_bloqueos is True


def test_el_informe_es_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL
    assert informe.condicionantes


def test_el_informe_conserva_los_avisos(informe: Informe) -> None:
    assert informe.aviso_estimacion
    assert informe.aviso_movilidad


def test_el_informe_declara_la_version_de_reglas(informe: Informe) -> None:
    assert informe.version_reglas == "v1"


def test_un_caso_enteramente_fuera_de_alcance_tambien_devuelve_informe() -> None:
    """Sin ningún período computable, la elegibilidad es «no cumple», no un error."""
    c = caso(
        periodo(desde="2000-03-01", hasta="2026-02-28", establecimiento=PRIVADO),
        nacimiento="1970-05-10",
        ceses=["2026-02-28"],
    )
    informe = calcular(c, reglas=REGLAS)
    assert all(not i.cumple for i in informe.elegibilidad.incisos)
    assert informe.tiene_bloqueos is True
