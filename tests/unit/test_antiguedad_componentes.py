# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T143 — la antigüedad solo sobre los componentes bonificables (FR-031b).

`[Decreto 818/13, Anexo Único — VERIFICADO 2026-11-04]`

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


def test_la_remuneracion_suma_los_componentes_con_aporte_al_ips(
    grilla: GrillaSalarial,
) -> None:
    """Criterio aplicado de la Cuestión #2 desde el 2026-11-04.

    Los arts. 4 y 5 atan el sistema al aporte, y la liquidación DGCyE 09/2026
    muestra el aporte personal como el 16 % exacto de la suma de los conceptos
    que tributan. La maestra ficticia tiene tres con aporte —básico 100.000,
    suma fija 50.000 y bonificación no jerárquica 43.500— y uno sin aporte, la
    compensación no remunerativa de 9.000, que queda afuera.
    """
    valor = grilla.cargo("maestro_de_grado")
    assert valor is not None
    assert haber.remuneracion_del_cargo(valor, reglas=REGLAS) == Decimal("193500.00")
    # Y la base del aporte es la misma suma: es lo que hace el criterio
    # verificable contra un recibo, que la letra del art. 40 no es.
    assert valor.total_con_aporte_ips == Decimal("193500.00")


def test_un_componente_sin_aporte_no_integra_la_remuneracion(
    grilla: GrillaSalarial,
) -> None:
    """El bibliotecario ficticio tiene uno no remunerativo de 11.000 sin aporte.

    Bajo el criterio anterior —la letra del art. 40, todos los componentes—
    entraba y la remuneración era 216.000. Bajo el criterio aplicado queda
    afuera: 150.000 + 55.000.

    Es exactamente la diferencia que el FONID y la Conectividad producirían en
    un caso real, y por eso la lectura amplia se informa como alternativa al
    alza en lugar de descartarse.
    """
    valor = grilla.cargo("bibliotecario_ensenanza_superior")
    assert valor is not None
    assert haber.remuneracion_del_cargo(valor, reglas=REGLAS) == Decimal("205000.00")
    assert haber.base_bonificable(valor) == Decimal("150000.00")


def test_la_lectura_amplia_se_informa_y_da_mas(grilla: GrillaSalarial) -> None:
    """La alternativa al alza: también los no remunerativos sin aporte.

    216.000 contra los 205.000 aplicados. El sentido se invirtió respecto de la
    versión anterior de este test, y eso **es** el cambio de default: antes el
    motor aplicaba la lectura amplia y mostraba la restrictiva a la baja; ahora
    aplica la del aporte y muestra la amplia al alza.
    """
    valor = grilla.cargo("bibliotecario_ensenanza_superior")
    assert valor is not None
    alternativa = haber.remuneracion_alternativa(valor, reglas=REGLAS)
    assert alternativa is not None
    monto, regla = alternativa
    assert monto == Decimal("216000.00")
    assert monto > haber.remuneracion_del_cargo(valor, reglas=REGLAS)
    assert regla.id == "remuneracion.incluye_no_remunerativos_sin_aporte"
    assert (regla.valor or {})["sentido"] == "al_alza"


def test_un_componente_excluido_por_el_art_40_no_entra(grilla: GrillaSalarial) -> None:
    """El viático ficticio del preceptor: el artículo lo excluye expresamente."""
    valor = grilla.cargo("preceptor")
    assert valor is not None
    excluido = next(c for c in valor.componentes if c.excluido_art40)
    assert excluido.importe == Decimal("25000.00")
    # 90.000 + 40.000, sin los 25.000 del viático: el art. 40 lo excluye, y
    # además no tributa. Las dos razones apuntan al mismo lado, que es lo
    # esperable —el artículo excluye justamente conceptos no remunerativos—
    # pero el motor aplica la exclusión del artículo por separado, porque es de
    # la norma y no del criterio.
    assert excluido.aporte_ips is False
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


@pytest.mark.parametrize("anios", [0, 1, 10, 20, 24, 26, 40])
def test_la_antiguedad_ya_no_tiene_lectura_alternativa(anios: int) -> None:
    """La Ley 10.579 dejó de informarse al resolverse la Cuestión #1.

    La liquidación DGCyE 09/2026 muestra aplicado el 125 % del Decreto 818/13,
    así que ofrecer el 120 % de la ley como alternativa sembraría una duda que
    la evidencia despejó. La regla se conserva como referencia histórica —sirve
    para reproducir un cálculo anterior a julio de 2013— y el motor no la toma.
    """
    assert haber.antiguedad_alternativa(anios, reglas=REGLAS) is None


def test_la_escala_historica_sigue_cargada_y_marcada_como_no_vigente() -> None:
    """Se deja de informar, no se borra: borrarla perdería la trazabilidad."""
    regla = REGLAS.por_id("antiguedad.escala_ley_10579")
    assert regla is not None
    assert (regla.valor or {})["vigente"] is False
    assert (regla.valor or {})["tope"] == "1.20"


def test_el_tope_de_la_escala_aplicada_es_125() -> None:
    """Y se mantiene más allá del último tramo, el de 24 años."""
    assert haber.porcentaje_de_antiguedad(24, reglas=REGLAS) == Decimal("1.25")
    assert haber.porcentaje_de_antiguedad(26, reglas=REGLAS) == Decimal("1.25")
    assert haber.porcentaje_de_antiguedad(60, reglas=REGLAS) == Decimal("1.25")


def test_a_los_cero_anios_la_escala_del_decreto_arranca_en_13() -> None:
    assert haber.porcentaje_de_antiguedad(0, reglas=REGLAS) == Decimal("0.13")


def test_un_cargo_que_no_esta_en_la_grilla_no_se_valua(grilla: GrillaSalarial) -> None:
    assert grilla.cargo("inexistente") is None
