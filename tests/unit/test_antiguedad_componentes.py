# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T143 — la antigüedad solo sobre los componentes bonificables (FR-031b).

`[Ley 10579, art. 33 — NO_VERIFICADA: tope, Cuestión abierta #1]`

El error que esto impide es caro y silencioso: aplicar la antigüedad sobre el
total del cargo en lugar de sobre su parte bonificable infla el haber sin que
nada se vea raro. Con la grilla ficticia, un maestro tiene $100.000 bonificables
y $50.000 que no lo son; la diferencia entre las dos cuentas es del orden del
50 % del adicional.

**Estado en la v1**: la escala de antigüedad está `NO_VERIFICADA` con `valor:
null` —no hay porcentajes que transcribir sin fuente— así que el motor aplica
**cero** y lo declara. Lo que estos tests fijan es la *base* sobre la que se
aplicará en cuanto la escala se cargue, y que mientras tanto la omisión sea
explícita y no silenciosa.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ultimo_timbre.engine import haber
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


@pytest.fixture(scope="module")
def grilla() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(FIXTURE)


def test_la_base_bonificable_excluye_las_sumas_no_bonificables(
    grilla: GrillaSalarial,
) -> None:
    valor = grilla.cargo("maestro_de_grado")
    assert valor is not None
    assert haber.base_bonificable(valor) == Decimal("100000.00")


def test_la_remuneracion_suma_los_componentes_remunerativos(
    grilla: GrillaSalarial,
) -> None:
    """Criterio por defecto de la Cuestión #2: remunerativos sí, el resto no."""
    valor = grilla.cargo("maestro_de_grado")
    assert valor is not None
    assert haber.remuneracion_del_cargo(valor, reglas=REGLAS) == Decimal("150000.00")


def test_los_componentes_no_remunerativos_tambien_entran(grilla: GrillaSalarial) -> None:
    """Letra del art. 40: todos los componentes del cargo, no solo los remunerativos.

    El bibliotecario ficticio tiene uno no remunerativo de 11.000 que el art. 40
    no excluye, así que integra la remuneración: 150.000 + 55.000 + 11.000.
    """
    valor = grilla.cargo("bibliotecario_ensenanza_superior")
    assert valor is not None
    assert haber.remuneracion_del_cargo(valor, reglas=REGLAS) == Decimal("216000.00")
    assert haber.base_bonificable(valor) == Decimal("150000.00")


def test_la_lectura_restrictiva_se_informa_y_da_menos(grilla: GrillaSalarial) -> None:
    """La alternativa a la baja: solo los remunerativos, 205.000."""
    valor = grilla.cargo("bibliotecario_ensenanza_superior")
    assert valor is not None
    alternativa = haber.remuneracion_alternativa(valor, reglas=REGLAS)
    assert alternativa is not None
    monto, regla = alternativa
    assert monto == Decimal("205000.00")
    assert regla.id == "remuneracion.solo_remunerativos"
    assert (regla.valor or {})["sentido"] == "a_la_baja"


def test_un_componente_excluido_por_el_art_40_no_entra(grilla: GrillaSalarial) -> None:
    """El viático ficticio del preceptor: el artículo lo excluye expresamente."""
    valor = grilla.cargo("preceptor")
    assert valor is not None
    excluido = next(c for c in valor.componentes if c.excluido_art40)
    assert excluido.importe == Decimal("25000.00")
    # 90.000 + 40.000, sin los 25.000 del viático.
    assert haber.remuneracion_del_cargo(valor, reglas=REGLAS) == Decimal("130000.00")


def test_cuando_las_dos_lecturas_coinciden_no_se_informa_alternativa(
    grilla: GrillaSalarial,
) -> None:
    """Principio VIII: advertir algo que no cambia nada es ruido.

    En el preceptor, su único componente no remunerativo es justamente el que el
    art. 40 excluye, así que las dos lecturas dan lo mismo.
    """
    valor = grilla.cargo("preceptor")
    assert valor is not None
    assert haber.remuneracion_alternativa(valor, reglas=REGLAS) is None


def test_la_antiguedad_se_calcula_sobre_la_base_y_no_sobre_el_total(
    grilla: GrillaSalarial,
) -> None:
    """La diferencia entre las dos cuentas, con un porcentaje cualquiera."""
    valor = grilla.cargo("maestro_de_grado")
    assert valor is not None
    sobre_base = haber.adicional_por_antiguedad(valor, Decimal("0.50"))
    assert sobre_base == Decimal("50000.00")
    # Sobre el total daría 75000: el error que FR-031b existe para impedir.
    assert sobre_base != haber.remuneracion_del_cargo(valor, reglas=REGLAS) * Decimal("0.50")


@pytest.mark.parametrize(
    ("anios", "esperado"),
    [
        (0, "0.13"),
        (1, "0.13"),
        (2, "0.23"),
        (3, "0.23"),
        (4, "0.33"),
        (7, "0.43"),
        (10, "0.54"),
        (12, "0.64"),
        (15, "0.74"),
        (17, "0.84"),
        (20, "1.05"),
        (22, "1.15"),
        (24, "1.25"),
        (40, "1.25"),
    ],
)
def test_la_escala_del_decreto_818_13_por_tramos(anios: int, esperado: str) -> None:
    """Los once tramos del Anexo Único, transcriptos y verificados.

    Entre tramos rige el anterior: a los 3 años sigue el 23 % de los 2. Más allá
    de los 24 el porcentaje se mantiene, porque el decreto no declara tope y su
    último tramo es ese.
    """
    assert haber.porcentaje_de_antiguedad(anios, reglas=REGLAS) == Decimal(esperado)


def test_el_salto_irregular_de_los_20_anios_es_de_la_fuente() -> None:
    """De 84 % a 105 %, no a 94 %: está así en el Anexo Único.

    Se deja explícito porque parece un error de transcripción y no lo es.
    """
    assert haber.porcentaje_de_antiguedad(17, reglas=REGLAS) == Decimal("0.84")
    assert haber.porcentaje_de_antiguedad(20, reglas=REGLAS) == Decimal("1.05")


@pytest.mark.parametrize(
    ("anios", "esperado"),
    [(1, "0.10"), (10, "0.50"), (20, "1.00"), (24, "1.20"), (40, "1.20")],
)
def test_la_escala_alternativa_de_la_ley_10579(anios: int, esperado: str) -> None:
    """La original del Estatuto, con tope 120 %, que se informa y no se aplica."""
    alternativa = haber.antiguedad_alternativa(anios, reglas=REGLAS)
    assert alternativa is not None
    assert alternativa[0] == Decimal(esperado)
    assert alternativa[1].id == "antiguedad.escala_ley_10579"


def test_la_escala_alternativa_siempre_da_menos_o_igual() -> None:
    """Es lo que justifica su `sentido: a_la_baja`."""
    for anios in range(0, 45):
        aplicada = haber.porcentaje_de_antiguedad(anios, reglas=REGLAS)
        alternativa = haber.antiguedad_alternativa(anios, reglas=REGLAS)
        assert aplicada is not None
        if alternativa is not None:
            assert alternativa[0] < aplicada, anios


def test_a_los_cero_anios_la_ley_10579_no_tiene_tramo() -> None:
    """Su escala arranca al año; la del decreto arranca en cero con 13 %."""
    assert haber.porcentaje_de_antiguedad(0, reglas=REGLAS) == Decimal("0.13")
    assert haber.antiguedad_alternativa(0, reglas=REGLAS) is None


def test_un_cargo_que_no_esta_en_la_grilla_no_se_valua(grilla: GrillaSalarial) -> None:
    assert grilla.cargo("inexistente") is None
