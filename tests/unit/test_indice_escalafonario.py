# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El índice escalafonario del catálogo (Cuestión abierta #4).

El índice es el multiplicador del sueldo básico del cargo testigo: el básico de
un cargo es el del Preceptor por su índice. Eso lo vuelve, a la vez, el criterio
de «mejor remunerado» de la `Res. IPS 995/2021` —a igual grilla, más índice es
más remuneración— y el desempate verificable del art. 41.

Está en `null` en **todas** las entradas de la v1, y eso no es un pendiente que
se olvidó: el Anexo del art. 9º del Decreto 2397/2005, que aprueba el texto
ordenado del nomenclador, no está publicado. Lo relevado y por qué no alcanza
está en `docs/datos-pendientes/relevamiento-2026-11.md`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from ultimo_timbre.models.enums import EstadoRegla, NaturalezaServicio
from ultimo_timbre.models.normativa import EntradaCatalogo, Norma
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
REGLA_INDICES = "jerarquia.indices_escalafonarios"

NORMA = Norma(texto="Ley 13469", ley="Ley 13469")


def _entrada(**kw: object) -> EntradaCatalogo:
    base: dict[str, object] = {
        "cargo": "x",
        "naturaleza": NaturalezaServicio.DOCENTE,
        "al_frente_de_alumnos": True,
        "norma": NORMA,
        "estado": EstadoRegla.VERIFICADO,
        "regla_indice": REGLA_INDICES,
    }
    base.update(kw)
    return EntradaCatalogo(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# El campo y sus invariantes
# ---------------------------------------------------------------------------


def test_el_indice_llega_como_decimal_exacto() -> None:
    """research R1: viaja como str y nunca pasa por float."""
    entrada = _entrada(indice_escalafonario=Decimal("1.32"))
    assert entrada.indice_escalafonario == Decimal("1.32")
    assert str(entrada.indice_escalafonario) == "1.32"


def test_un_indice_nulo_exige_declarar_la_regla_que_lo_discute() -> None:
    """Si no, el informe no podría explicar por qué no compara jerarquías."""
    with pytest.raises(ValidationError, match="regla_indice"):
        _entrada(indice_escalafonario=None, regla_indice=None)


def test_un_indice_no_positivo_se_rechaza() -> None:
    with pytest.raises(ValidationError, match="mayor que cero"):
        _entrada(indice_escalafonario=Decimal("0"))


def test_el_indice_por_hora_se_marca_aparte() -> None:
    """Un índice por hora no es comparable con uno por cargo."""
    por_hora = _entrada(indice_es_por_hora=True)
    assert por_hora.indice_es_por_hora is True
    assert _entrada().indice_es_por_hora is False


def test_la_jerarquia_y_el_indice_son_campos_distintos() -> None:
    """Una es un orden abstracto; el otro multiplica el básico.

    Que coincidan es parte de lo que la Cuestión abierta #4 todavía no fijó, así
    que el modelo no los colapsa en uno.
    """
    entrada = _entrada(jerarquia=40, indice_escalafonario=Decimal("1.10"))
    assert entrada.jerarquia == 40
    assert entrada.indice_escalafonario == Decimal("1.10")


# ---------------------------------------------------------------------------
# El catálogo real
# ---------------------------------------------------------------------------


def test_ninguna_entrada_del_catalogo_declara_indice() -> None:
    """Resguardo de la regla de datos: ningún índice se infirió.

    Si alguien carga uno, este test lo obliga a revisar que venga del
    nomenclador y no del instructivo ni de una cuenta.
    """
    con_indice = [e.cargo for e in REGLAS.catalogo_cargos.entradas if e.indice_escalafonario]
    assert con_indice == [], f"estas entradas declaran índice sin fuente: {con_indice}"


def test_todas_apuntan_a_la_regla_de_los_indices() -> None:
    for entrada in REGLAS.catalogo_cargos.entradas:
        assert entrada.regla_indice == REGLA_INDICES, entrada.cargo


def test_la_regla_de_los_indices_esta_cargada_y_sin_verificar() -> None:
    regla = REGLAS.por_id(REGLA_INDICES)
    assert regla is not None
    assert regla.estado is EstadoRegla.NO_VERIFICADA
    assert regla.cuestion_abierta == 4
    assert regla.valor is None
    assert "Anexo" in (regla.que_falta_verificar or "")


def test_las_horas_catedra_llevan_indice_por_hora() -> None:
    """Y son tres, una por nivel: el nomenclador les da índices distintos."""
    por_hora = [e.cargo for e in REGLAS.catalogo_cargos.entradas if e.indice_es_por_hora]
    assert sorted(por_hora) == [
        "hora_catedra_adultos",
        "hora_catedra_secundaria",
        "hora_catedra_superior",
    ]


def test_los_cargos_van_por_categoria_y_no_por_nombre_generico() -> None:
    """El nomenclador distingue categorías con índices distintos.

    Un cargo «director» genérico obligaría a elegir una de las tres categorías
    y el informe no podría decir cuál eligió.
    """
    cargos = {e.cargo for e in REGLAS.catalogo_cargos.entradas}
    for generico in ("director", "vicedirector", "bibliotecario"):
        assert generico not in cargos, f"«{generico}» es un nombre genérico sin categoría"
    assert {"director_primera", "director_segunda", "director_tercera"} <= cargos
    assert {"vicedirector_primera", "vicedirector_segunda"} <= cargos
    assert {"bibliotecario_instituto_menores", "bibliotecario_ensenanza_superior"} <= cargos


def test_todas_las_categorias_de_un_cargo_comparten_su_condicion() -> None:
    """La categoría cambia el índice, no si está al frente de alumnos."""
    directivos = [
        e
        for e in REGLAS.catalogo_cargos.entradas
        if e.cargo.startswith(("director_", "vicedirector_"))
    ]
    assert len(directivos) == 5
    for entrada in directivos:
        assert entrada.al_frente_de_alumnos is False
        assert entrada.regla_id == "al_frente.ley_13469.extension"
