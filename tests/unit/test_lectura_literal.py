# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T119 — la lectura literal de los arts. 42 y 43 con impacto al alza (FR-027b).

El motor aplica la interpretación del IPS (excedente desde todas las
condiciones) y **advierte** que existe una lectura literal que mediría el
excedente solo por la edad respecto de la requerida por el inciso. Esa lectura
da un porcentaje mayor o igual, así que su sentido de impacto es `al_alza`.

Informarla es lo que permite que el profesional discuta el criterio con el
expediente en la mano en lugar de descubrirlo cuando el IPS resuelve.
"""

from __future__ import annotations

from decimal import Decimal

from tests.casos import f
from ultimo_timbre.engine import porcentaje
from ultimo_timbre.models.enums import SentidoImpacto
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def test_cuando_la_edad_adelanta_el_excedente_se_informa_la_alternativa() -> None:
    """Escenario 6: 75 % aplicado contra 80 % bajo la lectura literal."""
    alternativa = porcentaje.lectura_literal(
        inciso="b",
        habilitado_desde=f("2023-12-31"),
        cese=f("2023-12-31"),
        fecha_edad_requerida=f("2019-06-15"),
        aplicado=Decimal("0.75"),
        reglas=REGLAS,
    )
    assert alternativa is not None
    assert alternativa.porcentaje == Decimal("0.80")
    assert alternativa.sentido_impacto is SentidoImpacto.AL_ALZA


def test_la_alternativa_cita_los_arts_42_y_43() -> None:
    """Principio I: la lectura alternativa también tiene fuente."""
    alternativa = porcentaje.lectura_literal(
        inciso="b",
        habilitado_desde=f("2023-12-31"),
        cese=f("2023-12-31"),
        fecha_edad_requerida=f("2019-06-15"),
        aplicado=Decimal("0.75"),
        reglas=REGLAS,
    )
    assert alternativa is not None
    assert alternativa.norma.articulo == "42-43"


def test_si_las_dos_lecturas_coinciden_no_se_informa_nada() -> None:
    """No se advierte lo que no cambia: sería ruido (Principio VIII)."""
    assert (
        porcentaje.lectura_literal(
            inciso="b",
            habilitado_desde=f("2020-01-10"),
            cese=f("2020-01-10"),
            fecha_edad_requerida=f("2020-01-10"),
            aplicado=Decimal("0.75"),
            reglas=REGLAS,
        )
        is None
    )


def test_la_alternativa_nunca_baja_el_porcentaje() -> None:
    """Si la lectura literal diera menos, no es una alternativa al alza."""
    alternativa = porcentaje.lectura_literal(
        inciso="b",
        habilitado_desde=f("2015-01-10"),
        cese=f("2025-01-10"),
        fecha_edad_requerida=f("2024-01-10"),
        aplicado=Decimal("0.85"),
        reglas=REGLAS,
    )
    assert alternativa is None


def test_tambien_aplica_al_inciso_d_por_el_art_42() -> None:
    """El art. 42 rige los incs. c y d: base 70 %, excedentes 75 % y 80 %."""
    alternativa = porcentaje.lectura_literal(
        inciso="d",
        habilitado_desde=f("2024-12-31"),
        cese=f("2024-12-31"),
        fecha_edad_requerida=f("2021-01-10"),
        aplicado=Decimal("0.70"),
        reglas=REGLAS,
    )
    assert alternativa is not None
    assert alternativa.porcentaje == Decimal("0.75")
    assert alternativa.sentido_impacto is SentidoImpacto.AL_ALZA
