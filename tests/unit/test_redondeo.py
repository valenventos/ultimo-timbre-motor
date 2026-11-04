# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T144 — el redondeo en un único punto y declarado (FR-033, Cuestión #6).

El Principio II pide aritmética decimal exacta. «Exacta» no significa infinitos
decimales: significa que el redondeo ocurre **una sola vez**, al final, con una
política explícita, y no disperso por cada multiplicación. Redondear en cada
paso acumula error y vuelve el resultado dependiente del orden de las
operaciones, que es justo lo que el invariante I3 prohíbe.

La política que aplica el IPS no está verificada (Cuestión abierta #6), así que
el motor usa `ROUND_HALF_UP` a dos decimales **declarado como valor por
defecto** y marca el monto provisional. El último decimal no está garantizado.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from ultimo_timbre.engine import haber
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("100.004", "100.00"),
        ("100.005", "100.01"),
        ("100.014", "100.01"),
        ("100.015", "100.02"),
        ("0.005", "0.01"),
        ("100", "100.00"),
    ],
)
def test_redondea_half_up_a_dos_decimales(valor: str, esperado: str) -> None:
    assert haber.redondear(Decimal(valor), reglas=REGLAS) == Decimal(esperado)


def test_la_politica_sale_de_la_regla_y_no_del_codigo() -> None:
    """Principio I: incluso el redondeo es dato."""
    regla = REGLAS.por_id("redondeo.politica_ips")
    assert regla is not None
    assert regla.valor is not None
    assert regla.valor["politica_aplicada"] == "ROUND_HALF_UP"
    assert regla.valor["decimales"] == 2


def test_la_regla_declara_que_aplico_un_valor_por_defecto() -> None:
    """Distingue «sin verificar y sin valor» de «hubo que elegir algo»."""
    regla = REGLAS.por_id("redondeo.politica_ips")
    assert regla is not None
    assert regla.valor_por_defecto_aplicado is True


def test_el_resultado_es_exacto_y_no_un_float() -> None:
    resultado = haber.redondear(Decimal("1") / Decimal("3"), reglas=REGLAS)
    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("0.33")


def test_redondear_dos_veces_no_cambia_el_resultado() -> None:
    """Idempotencia: si no lo fuera, el punto único no serviría de nada."""
    una = haber.redondear(Decimal("100.005"), reglas=REGLAS)
    assert haber.redondear(una, reglas=REGLAS) == una
