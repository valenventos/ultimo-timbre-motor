# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T118 — el excedente se cuenta desde **todas** las condiciones (FR-027a).

`[Res. IPS 995/2021, Anexo, punto 2.1.a — Interpretación]`

La diferencia que esto fija: una docente que cumplió 50 años mucho antes de
completar los 25 de servicio **no** tiene excedente el día que se habilita. El
excedente se mide desde la última condición en cumplirse, no desde la edad.

Leerlo al revés —solo por la edad— es la lectura literal de los arts. 42 y 43,
que el motor informa como alternativa al alza y no aplica (FR-027b, T119).
"""

from __future__ import annotations

import pytest

from tests.casos import f
from ultimo_timbre.engine import porcentaje


@pytest.mark.parametrize(
    ("desde", "hasta", "esperado"),
    [
        ("2020-01-10", "2020-01-10", 0),
        ("2020-01-10", "2022-01-09", 1),
        ("2020-01-10", "2023-01-09", 2),
        ("2020-01-10", "2023-01-10", 3),
        ("2020-01-10", "2025-01-10", 5),
        ("2020-01-10", "2030-01-10", 10),
    ],
)
def test_anios_de_excedente_cuenta_aniversarios_cumplidos(
    desde: str, hasta: str, esperado: int
) -> None:
    """Un excedente de 3 años se cumple en el aniversario, no 364 días antes."""
    assert porcentaje.anios_de_excedente(f(desde), f(hasta)) == esperado


def test_un_cese_anterior_a_la_habilitacion_no_tiene_excedente() -> None:
    """No hay excedente negativo: sin derecho todavía, no hay nada que exceder."""
    assert porcentaje.anios_de_excedente(f("2025-01-10"), f("2020-01-10")) == 0


def test_el_dia_de_la_habilitacion_el_excedente_es_cero() -> None:
    """El caso del escenario 6: completa el servicio a los 54 y arranca en cero."""
    assert porcentaje.anios_de_excedente(f("2023-12-31"), f("2023-12-31")) == 0


def test_el_excedente_no_se_mide_por_la_edad_sino_por_la_habilitacion() -> None:
    """FR-027a contra la lectura literal, con números del escenario 6.

    Nacida 1969-06-15, completa 25 años de servicio el 2023-12-31 con 54 años
    de edad. Por la edad le sobrarían 4 años sobre los 50 del inc. b; por la
    interpretación del IPS el excedente es 0, porque recién ese día se cumplen
    **todas** las condiciones.
    """
    habilitacion = f("2023-12-31")
    cumple_50 = f("2019-06-15")
    assert porcentaje.anios_de_excedente(habilitacion, habilitacion) == 0
    assert porcentaje.anios_de_excedente(cumple_50, habilitacion) == 4


def test_la_fecha_de_cada_excedente_es_el_aniversario_de_la_habilitacion() -> None:
    """FR-029: tiene que ser utilizable como fecha de cese."""
    fechas = porcentaje.fechas_de_excedente(f("2023-12-31"), (3, 5))
    assert fechas == {3: f("2026-12-31"), 5: f("2028-12-31")}


def test_el_29_de_febrero_no_rompe_el_aniversario() -> None:
    """Principio II: sin «un mes = 30 días» ni sorpresas de calendario."""
    fechas = porcentaje.fechas_de_excedente(f("2024-02-29"), (3,))
    assert fechas[3] == f("2027-02-28")
