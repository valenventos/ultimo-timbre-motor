# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T159 — un cese anterior a la habilitación (US5 esc. 3, FR-035).

Es la pregunta inversa de la US5: no «¿me conviene esperar?» sino «¿qué pasa si
me voy ahora?». La respuesta tiene que ser **no hay derecho, y falta esto**,
sin monto.

Emitir un monto ahí sería el peor error posible del motor: un número que parece
un haber para alguien que no tiene derecho a cobrarlo. Por eso el escenario sale
con `hay_derecho: false`, `haber: null` y el faltante de cada inciso.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.casos import caso, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import TipoEscenario
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Escenario, Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


def _caso() -> Caso:
    """Maestra en actividad que pregunta por 2028, y se habilita en 2030.

    A 2028 tiene 24 años al frente y 48 de edad: le falta un año de servicio y
    dos de edad. El escenario de habilitación se deriva igual, así que el
    informe trae las dos respuestas: la que preguntó y la que le conviene.
    """
    return caso(
        periodo("maestro_de_grado", desde="2004-03-01", hasta=None),
        nacimiento="1980-03-15",
        ceses=["2028-06-30"],
        fecha_de_calculo="2028-01-02",
    )


@pytest.fixture(scope="module")
def informe() -> Informe:
    grilla: GrillaSalarial = versiones.cargar_grilla_de_prueba(FIXTURE)
    return calcular(_caso(), reglas=REGLAS, grilla=grilla)


@pytest.fixture(scope="module")
def temprano(informe: Informe) -> Escenario:
    return next(e for e in informe.escenarios if e.fecha_cese == f("2028-06-30"))


def test_el_escenario_temprano_no_tiene_derecho(temprano: Escenario) -> None:
    assert temprano.hay_derecho is False


def test_no_se_emite_monto(temprano: Escenario) -> None:
    """Un número ahí parecería un haber que esa persona no puede cobrar."""
    assert temprano.haber is None


def test_tampoco_se_emite_porcentaje(temprano: Escenario) -> None:
    """Sin derecho no hay inciso aplicable, y sin inciso no hay porcentaje."""
    assert temprano.porcentaje is None
    assert temprano.inciso is None


def test_el_informe_dice_cuanto_falta(informe: Informe) -> None:
    """FR-035: la razón por la que no hay derecho, no solo que no lo hay."""
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.cumple is False
    assert inc_b.falta is not None
    assert inc_b.falta.anios_edad > 0 or inc_b.falta.anios_servicio > 0


def test_el_informe_estima_cuando_se_habilitaria(informe: Informe) -> None:
    """FR-016: con período en curso, la fecha se puede proyectar."""
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.estimado_para is not None
    assert inc_b.estimado_para > f("2028-06-30")


def test_el_escenario_de_habilitacion_se_deriva_igual(informe: Informe) -> None:
    """El informe trae las dos respuestas: la preguntada y la que conviene."""
    habilitacion = next(
        (e for e in informe.escenarios if e.tipo is TipoEscenario.HABILITACION), None
    )
    assert habilitacion is not None
    assert habilitacion.fecha_cese > f("2028-06-30")
    assert habilitacion.hay_derecho is True


def test_los_escenarios_van_en_orden_cronologico(informe: Informe) -> None:
    fechas = [e.fecha_cese for e in informe.escenarios]
    assert fechas == sorted(fechas)


def test_sin_derecho_a_ninguna_fecha_no_hay_escenarios_derivados() -> None:
    """Si el derecho nunca nace, no hay habilitación de la que derivar nada."""
    informe = calcular(
        caso(
            periodo("maestro_de_grado", desde="2020-03-01", hasta="2026-02-28"),
            nacimiento="1990-05-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=REGLAS,
    )
    assert informe.elegibilidad.inciso_mas_favorable is None
    assert len(informe.escenarios) == 1
    assert informe.escenarios[0].tipo is TipoEscenario.PROVISTA
    assert informe.escenarios[0].hay_derecho is False
    # Resguardo del acceso posicional: acá sí hay un solo escenario.
    assert len(informe.escenarios) == 1
