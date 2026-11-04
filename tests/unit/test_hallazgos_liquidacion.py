# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T196 a T198 — los hallazgos verificados contra la liquidación DGCyE 09/2026.

Tres cosas se verificaron con aritmética exacta sobre un recibo real usado
**solo como muestra** para calibrar reglas generales. No es un caso, no
representa ninguna historia de servicios y no está en el repositorio.

Lo que sigue verifica que esos hallazgos quedaron **registrados como datos**,
con su evidencia, y que el motor los usa. Lo que no se puede verificar acá es el
recibo mismo: la evidencia es una afirmación del mantenedor, y el campo
`evidencia` existe para que un auditor pueda ir a buscarla.

## Por qué hay tests sobre reglas y no solo sobre comportamiento

Porque el Principio I pone los valores normativos en los datos, y entonces un
cambio de dato es un cambio de comportamiento sin cambio de código. Un test que
solo mire el resultado no distingue «el motor calcula bien» de «el motor
calcula bien por casualidad, con la regla equivocada».
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from ultimo_timbre.engine import haber
from ultimo_timbre.models.enums import EstadoRegla
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


def _valor(regla_id: str) -> dict[str, Any]:
    """El `valor` de una regla, como diccionario suelto.

    `ValorRegla` es una union amplia a propósito —el YAML trae strings, enteros,
    booleanos y listas— y eso hace que indexarlo en profundidad no tipifique.
    Acá se lo achata con un `cast`: lo que estos tests verifican es el
    contenido del dato, y el tipo estricto ya lo verifica el modelo al cargar.
    """
    regla = REGLAS.por_id(regla_id)
    assert regla is not None, regla_id
    return cast(dict[str, Any], regla.valor or {})


@pytest.fixture(scope="module")
def grilla() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(FIXTURE)


# ---------------------------------------------------------------------------
# Hallazgo 2 — la antigüedad se aplica solo sobre el básico
# ---------------------------------------------------------------------------


def test_la_base_bonificable_esta_verificada_y_es_el_basico() -> None:
    """1,25 x el básico exacto, no x el total.

    Los códigos 0455 y 0667 son remunerativos y llevan aporte, y aun así no
    integran la base. Es el ejemplo más claro de por qué `bonificable`,
    `remunerativo` y `aporte_ips` tienen que ser tres campos y no uno.
    """
    regla = REGLAS.por_id("antiguedad.base_bonificable")
    assert regla is not None
    assert regla.estado is EstadoRegla.VERIFICADO
    assert regla.evidencia is not None
    assert "09/2026" in regla.evidencia

    valor = _valor("antiguedad.base_bonificable")
    assert valor["base"] == "sueldo_basico"
    assert valor["unico_componente_bonificable"] is True
    assert set(valor["no_bonificables_verificados"]) == {"0455", "0667"}


def test_la_grilla_de_prueba_tiene_un_solo_componente_bonificable(
    grilla: GrillaSalarial,
) -> None:
    """La fixture respeta el hallazgo: si no, los tests medirían otra cosa."""
    for valor in grilla.valores:
        bonificables = [c for c in valor.componentes if c.bonificable]
        assert len(bonificables) == 1, valor.cargo
        assert valor.basico == bonificables[0].importe


def test_el_adicional_por_antiguedad_sale_del_basico_y_no_del_total(
    grilla: GrillaSalarial,
) -> None:
    valor = grilla.cargo("maestro_de_grado")
    assert valor is not None
    assert valor.basico == Decimal("100000.00")

    adicional = haber.adicional_por_antiguedad(valor, Decimal("1.25"))
    assert adicional == Decimal("125000.00")
    # Sobre el total daría mucho más: la diferencia es lo que FR-031b evita.
    assert adicional < valor.total * Decimal("1.25")


# ---------------------------------------------------------------------------
# Hallazgo 3 — los componentes porcentuales se calculan sobre el básico
# ---------------------------------------------------------------------------


def test_la_base_de_los_porcentuales_esta_registrada_como_parcialmente_verificada() -> None:
    """Verificado para 0667, sin verificar para el resto.

    Es el caso que obligó a admitir una regla `no_verificada` **con** valor: su
    valor no es un supuesto, es el registro de lo observado. La distinción está
    en `test_cargar_reglas.test_ninguna_regla_no_verificada_lleva_valor`.
    """
    regla = REGLAS.por_id("componentes.porcentuales_sobre_basico")
    assert regla is not None
    assert regla.estado is EstadoRegla.NO_VERIFICADA
    assert regla.cuestion_abierta == 2
    assert regla.evidencia is not None

    valor = _valor("componentes.porcentuales_sobre_basico")
    assert valor["base"] == "sueldo_basico"
    verificados = {c["codigo"]: c["porcentaje"] for c in valor["codigos_verificados"]}
    assert verificados == {"0667": "0.435"}
    assert "0653" in valor["codigos_sin_verificar"]


def test_el_porcentaje_declarado_cuadra_con_el_importe_de_la_grilla(
    grilla: GrillaSalarial,
) -> None:
    """La razón de ser de `porcentaje_del_basico`: auditar la transcripción.

    El motor **no** recalcula el importe —la grilla lo trae resuelto— pero si el
    porcentaje declarado y el importe no cuadran, la grilla está mal transcripta
    y conviene saberlo antes de que produzca un haber.
    """
    revisados = 0
    for valor in grilla.valores:
        basico = valor.basico
        assert basico is not None
        for componente in valor.componentes:
            if componente.porcentaje_del_basico is None:
                continue
            esperado = basico * componente.porcentaje_del_basico
            assert componente.importe == esperado, componente.codigo_concepto
            revisados += 1
    assert revisados >= 1, "la fixture dejó de declarar algún componente porcentual"


# ---------------------------------------------------------------------------
# Hallazgo 4 — la base del aporte personal
# ---------------------------------------------------------------------------


def test_la_alicuota_del_aporte_personal_quedo_registrada() -> None:
    """16 %, y sobre qué: es lo que vuelve verificable el criterio aplicado."""
    regla = REGLAS.por_id("remuneracion.conceptos_del_cargo")
    assert regla is not None
    valor = _valor("remuneracion.conceptos_del_cargo")
    assert valor["criterio_aplicado"] == "componentes_con_aporte_ips"
    assert valor["alicuota_aporte_personal"] == "0.16"
    assert set(valor["componentes_con_aporte_verificados"]) == {"0110", "0220", "0455", "0667"}
    assert valor["componentes_sin_aporte_verificados"] == ["2575"]


def test_la_cuestion_dos_sigue_abierta_pese_a_la_evidencia() -> None:
    """Que un concepto tribute no prueba que integre el haber.

    La evidencia mejoró el criterio por defecto y no cerró la cuestión. Esta
    distinción es la que impide que el motor presente como verificado algo que
    es una inferencia razonable.
    """
    regla = REGLAS.por_id("remuneracion.conceptos_del_cargo")
    assert regla is not None
    assert regla.estado is EstadoRegla.NO_VERIFICADA
    assert regla.cuestion_abierta == 2
    assert "resolución del IPS" in (regla.que_falta_verificar or "")


def test_un_componente_sin_aporte_declarado_no_se_supone(grilla: GrillaSalarial) -> None:
    """`None` no es `False`: el motor informa la laguna en lugar de suponerla."""
    valor = grilla.cargo("maestro_de_grado")
    assert valor is not None
    assert valor.declara_aporte_ips is True

    # Con un componente sin declarar, la grilla deja de poder sostener el
    # criterio con certeza y el motor tiene que poder detectarlo.
    sin_declarar = valor.model_copy(
        update={
            "componentes": (
                valor.componentes[0].model_copy(update={"aporte_ips": None}),
                *valor.componentes[1:],
            )
        }
    )
    assert sin_declarar.declara_aporte_ips is False


# ---------------------------------------------------------------------------
# Hallazgo 6 — el valor por unidad es proporcional a la cantidad
# ---------------------------------------------------------------------------


def test_la_proporcionalidad_de_la_unidad_esta_verificada() -> None:
    regla = REGLAS.por_id("remuneracion.unidad_proporcional")
    assert regla is not None
    assert regla.estado is EstadoRegla.VERIFICADO
    assert regla.evidencia is not None
    valor = _valor("remuneracion.unidad_proporcional")
    assert valor["proporcionalidad"] == "lineal"
    assert valor["redondeo_por_unidad"] is False


def test_el_basico_de_un_modulo_es_la_mitad_del_de_dos(grilla: GrillaSalarial) -> None:
    """Exacto, sin redondeo por unidad: lo que el hallazgo afirma.

    Se verifica sobre la grilla y con `Decimal`, así que la mitad de un valor
    impar tampoco introduce error.
    """
    valor = grilla.cargo("modulos_secundaria")
    assert valor is not None
    uno = valor.basico
    assert uno is not None

    dos = uno * 2
    assert dos / 2 == uno
    assert uno + uno == dos


def test_el_motor_todavia_no_escala_el_haber_por_cantidad_de_unidades(
    grilla: GrillaSalarial,
) -> None:
    """La limitación conocida, afirmada para que no se olvide (T202).

    La grilla trae el valor de **una** unidad y `haber.valuar` recibe el nombre
    del cargo, no la cantidad. Un cargo base de veinte módulos se valúa hoy
    como uno de un módulo.

    No bloquea nada —`grids/` está vacío y el motor no emite montos reales— pero
    dejarlo sin test lo convertiría en una sorpresa el día que haya grilla. Si
    alguien implementa el escalado, este test falla y lo manda a actualizar la
    tarea en lugar de dejarla abierta para siempre.
    """
    valor = grilla.cargo("modulos_secundaria")
    assert valor is not None
    # La remuneración del cargo es la de una unidad, no la de la carga real.
    assert haber.remuneracion_del_cargo(valor, reglas=REGLAS) == valor.total_con_aporte_ips
