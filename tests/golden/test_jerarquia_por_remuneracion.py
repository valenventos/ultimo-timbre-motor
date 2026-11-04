# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T154 — el cargo base por «mejor remunerado» (Cuestión abierta #4).

`[Res. IPS 995/2021, Anexo, definición de CARGO BASE]`

La Cuestión #4 es el límite que hoy deja **todo** cargo base provisional en
cuanto hay dos cargos distintos: `rules/v1/cargos.yaml` lleva
`indice_escalafonario: null` porque el Anexo del art. 9º del Decreto 2397/2005
no está publicado.

El criterio de la Res. IPS 995/2021 abre una salida que no depende de ese
anexo: **con grilla disponible, el cargo mejor remunerado es el cargo base**. Es
verificable contra la grilla y no exige conocer el escalafón.

Orden de preferencia, de más verificable a menos:

1. **remuneración** de la grilla, cuando hay grilla;
2. **índice escalafonario** del nomenclador, como desempate verificable;
3. sin ninguno de los dos, empate declarado y cargo base provisional.

Todo corre con el **catálogo y la grilla ficticios**: la mecánica se verifica
sin cargar un solo valor real.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado, TipoFuente
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.models.normativa import ConjuntoDeReglas
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")
REGLA = "jerarquia.criterio_comparacion"


@pytest.fixture(scope="module")
def grilla() -> GrillaSalarial:
    return versiones.cargar_grilla_de_prueba(FIXTURE)


def _caso_dos_cargos() -> Caso:
    """Maestra 20 años y vicedirectora 6: los dos alcanzan los plazos del art. 41.

    En la grilla ficticia el maestro remunera 150.000 y la vicedirectora
    260.000, así que por remuneración gana la vicedirección. Por cantidad de
    meses ganaría la maestra, que es el desempate de determinismo: el test
    distingue los dos criterios en lugar de confundirlos.
    """
    return caso(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2020-02-29"),
        periodo("vicedirector_primera", desde="2020-03-01", hasta="2026-02-28"),
        nacimiento="1970-01-10",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-03-01",
    )


def _con_indices(**indices: str) -> ConjuntoDeReglas:
    """El catálogo real con algunos índices cargados, para probar el desempate."""
    entradas = tuple(
        e.model_copy(update={"indice_escalafonario": Decimal(indices[e.cargo])})
        if e.cargo in indices
        else e
        for e in REGLAS.catalogo_cargos.entradas
    )
    catalogo = REGLAS.catalogo_cargos.model_copy(update={"entradas": entradas})
    return REGLAS.model_copy(update={"catalogo_cargos": catalogo})


# ---------------------------------------------------------------------------
# (a) Con grilla: gana el mejor remunerado
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def con_grilla(grilla: GrillaSalarial) -> Informe:
    return calcular(_caso_dos_cargos(), reglas=REGLAS, grilla=grilla)


def test_con_grilla_el_cargo_base_es_el_mejor_remunerado(con_grilla: Informe) -> None:
    assert con_grilla.cargo_base is not None
    assert con_grilla.cargo_base.cargo == "vicedirector_primera"


def test_el_descarte_explica_que_fue_por_remuneracion(con_grilla: Informe) -> None:
    assert con_grilla.cargo_base is not None
    descartado = next(d for d in con_grilla.cargo_base.descartados if d.cargo == "maestro_de_grado")
    assert "remunera" in descartado.razon.lower()


def test_con_grilla_no_se_declara_empate(con_grilla: Informe) -> None:
    """La remuneración desempata: no hace falta el índice."""
    assert CodigoAdvertencia.EMPATE_JERARQUIA not in {a.codigo for a in con_grilla.advertencias}


def test_el_criterio_queda_en_el_desglose_como_interpretacion(con_grilla: Informe) -> None:
    """FR-040: no es la letra del art. 41, es la lectura de la Res. IPS 995/2021."""
    pasos = [p for p in con_grilla.desglose if p.regla_id == REGLA]
    assert pasos
    assert pasos[0].tipo_fuente is TipoFuente.INTERPRETACION
    assert "995/2021" in pasos[0].norma.texto


def test_el_cargo_base_sigue_provisional(con_grilla: Informe) -> None:
    """El criterio es una interpretación sin verificar, no la letra de la ley."""
    assert con_grilla.cargo_base is not None
    assert con_grilla.cargo_base.estado is EstadoResultado.PROVISIONAL


# ---------------------------------------------------------------------------
# (b) Sin grilla: se conserva el empate y la marca
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sin_grilla() -> Informe:
    return calcular(_caso_dos_cargos(), reglas=REGLAS)


def test_sin_grilla_se_declara_el_empate(sin_grilla: Informe) -> None:
    """Sin remuneración y sin índice no hay con qué comparar."""
    assert CodigoAdvertencia.EMPATE_JERARQUIA in {a.codigo for a in sin_grilla.advertencias}


def test_sin_grilla_el_cargo_base_queda_provisional(sin_grilla: Informe) -> None:
    assert sin_grilla.cargo_base is not None
    assert sin_grilla.cargo_base.estado is EstadoResultado.PROVISIONAL


def test_sin_grilla_gana_el_desempate_de_determinismo(sin_grilla: Informe) -> None:
    """Más meses, y declarado como empate: el resultado es reproducible (I3)."""
    assert sin_grilla.cargo_base is not None
    assert sin_grilla.cargo_base.cargo == "maestro_de_grado"


def test_los_dos_informes_eligen_distinto(con_grilla: Informe, sin_grilla: Informe) -> None:
    """Resguardo: si eligieran lo mismo, el test (a) no probaría nada."""
    assert con_grilla.cargo_base is not None
    assert sin_grilla.cargo_base is not None
    assert con_grilla.cargo_base.cargo != sin_grilla.cargo_base.cargo


# ---------------------------------------------------------------------------
# (c) El índice como desempate verificable
# ---------------------------------------------------------------------------


def test_el_indice_desempata_cuando_no_hay_grilla() -> None:
    """Con índices cargados, el orden sale del nomenclador y no de los meses."""
    reglas = _con_indices(vicedirector_primera="1.86", maestro_de_grado="1.10")
    informe = calcular(_caso_dos_cargos(), reglas=reglas)

    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "vicedirector_primera"
    assert CodigoAdvertencia.EMPATE_JERARQUIA not in {a.codigo for a in informe.advertencias}


def test_un_indice_por_hora_no_compite_con_uno_por_cargo() -> None:
    """Comparar 1,15 por hora contra 1,86 por cargo mezcla dos magnitudes.

    Se le carga a la hora cátedra un índice absurdamente alto: si el comparador
    los mezclara, ganaría. No gana, porque su `unidad_de_carga` es
    `hora_catedra` y no `cargo`.
    """
    reglas = _con_indices(hora_catedra_secundaria="9.99", maestro_de_grado="1.10")
    informe = calcular(
        caso(
            periodo("maestro_de_grado", desde="2000-03-01", hasta="2020-02-29"),
            periodo(
                "hora_catedra_secundaria",
                desde="2020-03-01",
                hasta="2026-02-28",
                horas_catedra=20,
            ),
            nacimiento="1970-01-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=reglas,
    )
    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "maestro_de_grado"
