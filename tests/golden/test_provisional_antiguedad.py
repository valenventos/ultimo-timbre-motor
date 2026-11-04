# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T096 — la escala de antigüedad ya **no** condiciona el haber (Cuestión #1).

Este módulo verificaba lo contrario. Nació para el escenario 3 de la US2 —«un
caso cuyo haber depende de la escala de bonificación por antigüedad sale
marcado no definitivo»— y afirmaba que la regla aparecía como condicionante.

El 2026-11-04 eso dejó de ser verdad, y el test se reescribió en lugar de
borrarse. La Cuestión abierta #1 se resolvió con la evidencia de una
liquidación DGCyE 09/2026: con 26 años de antigüedad, el código 0220 es
exactamente 1,25 veces el código 0110. Lo que faltaba no eran los valores de la
escala del Decreto 818/13 —estaban transcriptos del Anexo Único desde el
principio— sino la certeza de que ninguna norma posterior los había cambiado.
Un recibo con el tramo más alto aplicado es esa certeza.

## Por qué el test se conserva dado vuelta

Porque la afirmación sigue siendo valiosa, invertida: **el haber ya no se marca
provisional por la antigüedad**, y si alguien volviera a poner la escala en la
lista de reglas que condicionan todo monto, o le cambiara el estado a
`no_verificada` sin evidencia nueva, esto falla.

Y porque el escenario 3 de la US2 sigue existiendo: el haber **sí** sale
provisional, pero por las dos Cuestiones que quedan —qué conceptos integran la
remuneración (#2) y la política de redondeo (#6)—. El caso de prueba es el
mismo; lo que cambió es la razón, y que el informe diga la razón correcta es
precisamente el Principio IV.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.casos import caso_inc_b, escenario_de
from ultimo_timbre.engine import calcular
from ultimo_timbre.engine import condicionantes as cond
from ultimo_timbre.models.enums import EstadoRegla, EstadoResultado
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")
GRILLA_FICTICIA = "tests/fixtures/grilla-ficticia-test.yaml"
REGLA_ANTIGUEDAD = "antiguedad.escala_y_tope"
REGLA_LEY_10579 = "antiguedad.escala_ley_10579"


@pytest.fixture(scope="module")
def grilla() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(Path(GRILLA_FICTICIA))


@pytest.fixture(scope="module")
def informe(grilla: GrillaSalarial) -> Informe:
    return calcular(caso_inc_b(), reglas=REGLAS, grilla=grilla)


def test_la_grilla_usada_es_la_ficticia(grilla: GrillaSalarial) -> None:
    """Resguardo: ningún test de monto corre sobre importes que parezcan reales."""
    assert grilla.ficticia is True


def test_con_grilla_el_informe_declara_su_version(informe: Informe) -> None:
    assert informe.version_grilla == "ficticia-test"


# ---------------------------------------------------------------------------
# La Cuestión #1, resuelta
# ---------------------------------------------------------------------------


def test_la_escala_de_antiguedad_esta_verificada() -> None:
    regla = REGLAS.por_id(REGLA_ANTIGUEDAD)
    assert regla is not None
    assert regla.estado is EstadoRegla.VERIFICADO
    assert regla.cuestion_abierta is None
    assert regla.impacto_si_no_verificada is None


def test_la_escala_declara_contra_que_se_verifico() -> None:
    """Principio IV: una regla verificada dice **qué se miró**.

    La norma sola no alcanzaba y es justamente por eso que la cuestión estuvo
    abierta: el Anexo Único siempre dijo 125 %, y lo que no se podía saber
    desde la norma es si seguía rigiendo. Por eso la evidencia es un campo
    aparte de la norma, y no una nota en el texto de la norma.
    """
    regla = REGLAS.por_id(REGLA_ANTIGUEDAD)
    assert regla is not None
    assert regla.evidencia is not None
    assert "09/2026" in regla.evidencia
    assert "0220" in regla.evidencia
    assert "0110" in regla.evidencia


def test_la_escala_declara_su_tope() -> None:
    """125 %, el último tramo. Antes era el final de la tabla y ahora es tope."""
    regla = REGLAS.por_id(REGLA_ANTIGUEDAD)
    assert regla is not None
    assert (regla.valor or {})["tope"] == "1.25"


def test_la_escala_ya_no_condiciona_el_haber(informe: Informe) -> None:
    """El corazón de la inversión de este módulo."""
    refs = {c.referencia for c in informe.condicionantes}
    assert REGLA_ANTIGUEDAD not in refs


def test_la_escala_salio_de_la_lista_de_reglas_que_condicionan_todo_monto() -> None:
    """Y no quedó ahí descartándose en silencio por estar verificada.

    `de_regla` devuelve `None` para una regla verificada, así que dejarla en
    `REGLAS_DEL_MONTO` habría funcionado igual —y la lista habría dejado de
    decir la verdad sobre qué condiciona un haber.
    """
    assert REGLA_ANTIGUEDAD not in cond.REGLAS_DEL_MONTO


# ---------------------------------------------------------------------------
# La Ley 10.579 deja de ser lectura alternativa
# ---------------------------------------------------------------------------


def test_la_escala_de_la_ley_10579_queda_como_referencia_historica() -> None:
    """Se conserva, y no se informa.

    Borrarla perdería la trazabilidad de por qué la Cuestión #1 existió, y
    sirve para reproducir un cálculo anterior a julio de 2013. Pero informarla
    como alternativa sembraría una duda que el recibo ya despejó, y eso es
    ruido (Principio VIII).
    """
    regla = REGLAS.por_id(REGLA_LEY_10579)
    assert regla is not None
    valor = regla.valor or {}
    assert valor["vigente"] is False
    assert valor["se_informa_como"] == "referencia_historica"
    assert valor["reemplazada_por"] == REGLA_ANTIGUEDAD
    assert "alternativa_de" not in valor


def test_el_desglose_ya_no_cita_la_escala_de_la_ley_10579(informe: Informe) -> None:
    citadas = {p.regla_id for p in informe.desglose}
    assert REGLA_LEY_10579 not in citadas


# ---------------------------------------------------------------------------
# El escenario 3 de la US2 sigue en pie, con la razón correcta
# ---------------------------------------------------------------------------


def test_el_haber_sigue_siendo_provisional_por_las_cuestiones_que_quedan(
    informe: Informe,
) -> None:
    """#2 (qué integra la remuneración) y #6 (el redondeo)."""
    refs = {c.referencia for c in informe.condicionantes}
    assert "remuneracion.conceptos_del_cargo" in refs
    assert "redondeo.politica_ips" in refs


def test_el_informe_con_grilla_es_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_el_monto_arrastra_exactamente_las_dos_cuestiones_del_haber(
    informe: Informe,
) -> None:
    """Ni una más: si la antigüedad volviera a colarse, esto lo detecta."""
    haber = escenario_de(informe, "2030-03-31").haber
    assert haber is not None
    refs = {c.referencia for c in haber.condicionantes}
    assert "remuneracion.conceptos_del_cargo" in refs
    assert "redondeo.politica_ips" in refs
    assert REGLA_ANTIGUEDAD not in refs


def test_sin_grilla_las_reglas_del_monto_no_condicionan() -> None:
    """No se condiciona lo que no se calcula: la US1 no emite montos."""
    informe = calcular(caso_inc_b(), reglas=REGLAS)
    refs = {c.referencia for c in informe.condicionantes}
    assert "remuneracion.conceptos_del_cargo" not in refs
    assert informe.estado_general is EstadoResultado.DEFINITIVO
