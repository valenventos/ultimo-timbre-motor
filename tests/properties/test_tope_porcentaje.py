# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T108 — invariante I2: el porcentaje nunca supera el máximo del artículo (FR-028).

Es el invariante que impide que un excedente grande, una fecha rara o una
combinación que nadie previó produzcan un 90 %. El tope sale de las reglas, no
del código: el máximo del art. 43 es el mayor porcentaje cargado para el inc. b
y el del art. 41/42 el mayor cargado para los incs. c y d.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from ultimo_timbre.engine import porcentaje
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

TOPES = {
    "b": Decimal("0.85"),
    "c": Decimal("0.80"),
    "d": Decimal("0.80"),
}
BASES = {
    "b": Decimal("0.75"),
    "c": Decimal("0.70"),
    "d": Decimal("0.70"),
}

fechas = st.dates(min_value=dt.date(1960, 1, 1), max_value=dt.date(2100, 12, 31))


def test_los_topes_del_test_salen_de_las_reglas() -> None:
    """Resguardo: si una regla cambia un porcentaje, este test lo avisa."""
    assert porcentaje.tope("b", REGLAS) == TOPES["b"]
    assert porcentaje.tope("d", REGLAS) == TOPES["d"]
    assert porcentaje.base("b", REGLAS) == BASES["b"]
    assert porcentaje.base("d", REGLAS) == BASES["d"]


@settings(max_examples=250, deadline=None)
@given(inciso=st.sampled_from(["b", "c", "d"]), habilitado=fechas, cese=fechas)
def test_el_porcentaje_nunca_supera_el_tope(
    inciso: str, habilitado: dt.date, cese: dt.date
) -> None:
    valor = porcentaje.determinar(inciso, habilitado, cese, reglas=REGLAS)
    assert valor <= TOPES[inciso]


@settings(max_examples=250, deadline=None)
@given(inciso=st.sampled_from(["b", "c", "d"]), habilitado=fechas, cese=fechas)
def test_el_porcentaje_nunca_baja_de_la_base(
    inciso: str, habilitado: dt.date, cese: dt.date
) -> None:
    """El excedente solo puede sumar: nunca hay un haber por debajo de la base."""
    valor = porcentaje.determinar(inciso, habilitado, cese, reglas=REGLAS)
    assert valor >= BASES[inciso]


@settings(max_examples=200, deadline=None)
@given(inciso=st.sampled_from(["b", "c", "d"]), habilitado=fechas, cese=fechas)
def test_el_porcentaje_es_monotono_en_el_excedente(
    inciso: str, habilitado: dt.date, cese: dt.date
) -> None:
    """Postergar el cese nunca puede bajar el porcentaje."""
    mas_tarde = cese + dt.timedelta(days=400)
    assert porcentaje.determinar(inciso, habilitado, mas_tarde, reglas=REGLAS) >= (
        porcentaje.determinar(inciso, habilitado, cese, reglas=REGLAS)
    )


@settings(max_examples=100, deadline=None)
@given(inciso=st.sampled_from(["b", "c", "d"]), habilitado=fechas, cese=fechas)
def test_el_porcentaje_es_un_decimal_exacto(
    inciso: str, habilitado: dt.date, cese: dt.date
) -> None:
    """Principio II: ningún float binario se cuela por este camino."""
    valor = porcentaje.determinar(inciso, habilitado, cese, reglas=REGLAS)
    assert isinstance(valor, Decimal)
    assert valor == Decimal(str(valor))
