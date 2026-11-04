# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T156 — los escenarios derivados con su monto (US5 esc. 1, FR-036).

Es el valor diferencial del producto: responder «¿me conviene esperar?». El
motor deriva tres fechas además de las que el usuario provee —la habilitación
del derecho y los excedentes de 3 y 5 años— y valúa cada una.

Las fechas de excedente se cuentan desde que se cumplen **todas** las
condiciones del inciso `[Res. IPS 995/2021, Anexo, punto 2.1.a]`, no desde la
edad: es la misma interpretación que la US3 ya aplica, y acá es la que fija en
qué año cae cada escenario.

El caso: habilitación el 2030-03-15 con 75 %, excedente de 3 años el 2033-03-15
con 80 % y de 5 años el 2035-03-15 con 85 %.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tests.casos import caso, caso_escenarios, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import TipoEscenario
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Escenario, Informe
from ultimo_timbre.render.texto import informe_a_texto
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


@pytest.fixture(scope="module")
def informe() -> Informe:
    grilla: GrillaSalarial = versiones.cargar_grilla_de_prueba(FIXTURE)
    return calcular(caso_escenarios(), reglas=REGLAS, grilla=grilla)


def _por_tipo(informe: Informe, tipo: TipoEscenario) -> Escenario:
    return next(e for e in informe.escenarios if e.tipo is tipo)


# ---------------------------------------------------------------------------
# Las cuatro fechas: la provista y las tres derivadas
# ---------------------------------------------------------------------------


def test_se_emiten_los_tres_escenarios_derivados(informe: Informe) -> None:
    tipos = {e.tipo for e in informe.escenarios}
    assert TipoEscenario.HABILITACION in tipos
    assert TipoEscenario.EXCEDENTE_3 in tipos
    assert TipoEscenario.EXCEDENTE_5 in tipos


def test_la_fecha_provista_se_conserva(informe: Informe) -> None:
    """FR-035: el motor no reemplaza lo que el usuario preguntó."""
    assert f("2030-03-31") in {e.fecha_cese for e in informe.escenarios}


def test_la_habilitacion_es_la_ultima_condicion_en_cumplirse(informe: Informe) -> None:
    assert _por_tipo(informe, TipoEscenario.HABILITACION).fecha_cese == f("2030-03-15")


def test_los_excedentes_se_cuentan_desde_la_habilitacion(informe: Informe) -> None:
    """`Res. IPS 995/2021`, punto 2.1.a: no desde la edad requerida."""
    assert _por_tipo(informe, TipoEscenario.EXCEDENTE_3).fecha_cese == f("2033-03-15")
    assert _por_tipo(informe, TipoEscenario.EXCEDENTE_5).fecha_cese == f("2035-03-15")


# ---------------------------------------------------------------------------
# Los porcentajes del art. 43
# ---------------------------------------------------------------------------


def test_la_habilitacion_aplica_el_75_por_ciento(informe: Informe) -> None:
    """Excedente 0: recién ese día se cumplen todas las condiciones."""
    assert _por_tipo(informe, TipoEscenario.HABILITACION).porcentaje == Decimal("0.75")


def test_el_excedente_de_3_anios_aplica_el_80_por_ciento(informe: Informe) -> None:
    assert _por_tipo(informe, TipoEscenario.EXCEDENTE_3).porcentaje == Decimal("0.80")


def test_el_excedente_de_5_anios_aplica_el_85_por_ciento(informe: Informe) -> None:
    assert _por_tipo(informe, TipoEscenario.EXCEDENTE_5).porcentaje == Decimal("0.85")


def test_todos_acceden_por_el_inciso_b(informe: Informe) -> None:
    for escenario in informe.escenarios:
        assert escenario.hay_derecho is True
        assert escenario.inciso == "b"


# ---------------------------------------------------------------------------
# Los montos
# ---------------------------------------------------------------------------


def test_cada_escenario_trae_su_monto(informe: Informe) -> None:
    for escenario in informe.escenarios:
        assert escenario.haber is not None, escenario.tipo


def test_el_monto_crece_con_el_porcentaje(informe: Informe) -> None:
    """La diferencia entre escenarios es lo que el profesional compara."""
    habilitacion = _por_tipo(informe, TipoEscenario.HABILITACION).haber
    tres = _por_tipo(informe, TipoEscenario.EXCEDENTE_3).haber
    cinco = _por_tipo(informe, TipoEscenario.EXCEDENTE_5).haber
    assert habilitacion is not None
    assert tres is not None
    assert cinco is not None
    assert habilitacion.valor < tres.valor < cinco.valor


def test_los_montos_son_los_esperados(informe: Informe) -> None:
    """Grilla ficticia: remuneración 193.500 más 125.000 de antigüedad.

    La remuneración son los componentes con aporte al IPS (Cuestión #2,
    criterio aplicado): básico 100.000 + suma fija 50.000 + bonificación no
    jerárquica 43.500. La compensación de 9.000 no tributa y queda afuera.

    318.500 por cada porcentaje: 238875.0000, 254800.0000 y 270725.0000.
    """
    assert _por_tipo(informe, TipoEscenario.HABILITACION).haber is not None
    montos = {e.tipo: e.haber.valor for e in informe.escenarios if e.haber is not None}
    assert montos[TipoEscenario.HABILITACION] == Decimal("238875.0000")
    assert montos[TipoEscenario.EXCEDENTE_3] == Decimal("254800.0000")
    assert montos[TipoEscenario.EXCEDENTE_5] == Decimal("270725.0000")


def test_cada_monto_trae_su_marca_y_sus_condicionantes(informe: Informe) -> None:
    """FR-046a: la marca viaja con el valor en todos los escenarios, no en uno."""
    for escenario in informe.escenarios:
        assert escenario.haber is not None
        assert escenario.haber.condicionantes


# ---------------------------------------------------------------------------
# La aclaración en lenguaje claro (US5 esc. 5)
# ---------------------------------------------------------------------------


def test_el_texto_aclara_que_esperar_no_aumenta_la_antiguedad(informe: Informe) -> None:
    """Sin esta línea la comparación se lee al revés.

    Los años de antigüedad crecen entre escenarios —26, 29, 31— y el monto
    también. Es natural deducir que una cosa causa la otra, y es falso: la
    antigüedad ya está en el tramo máximo en todos los escenarios porque el
    art. 24 pide 25 años de servicio y la escala topa a los 24. Lo que aumenta
    es el porcentaje de los arts. 42 y 43.
    """
    texto = informe_a_texto(informe)
    assert (
        "Esperar no aumenta la bonificación por antigüedad (ya está en el máximo); "
        "lo que aumenta es el porcentaje del haber." in texto
    )


def test_la_aclaracion_aparece_una_sola_vez(informe: Informe) -> None:
    """Es una nota de la comparación, no de cada escenario."""
    texto = informe_a_texto(informe)
    assert texto.count("Esperar no aumenta la bonificación") == 1


def test_la_aclaracion_esta_en_la_seccion_de_escenarios(informe: Informe) -> None:
    """Donde se lee la comparación, no perdida entre las advertencias."""
    texto = informe_a_texto(informe)
    inicio = texto.index("Escenarios de cese")
    fin = texto.index("Desglose paso a paso")
    assert "Esperar no aumenta la bonificación" in texto[inicio:fin]


def test_sin_comparacion_no_hace_falta_la_aclaracion() -> None:
    """Con un solo escenario no hay nada que comparar, y la nota sería ruido."""
    informe = calcular(
        caso(
            periodo("maestro_de_grado", desde="2020-03-01", hasta="2026-02-28"),
            nacimiento="1990-05-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=REGLAS,
    )
    assert len(informe.escenarios) == 1
    assert "Esperar no aumenta la bonificación" not in informe_a_texto(informe)
