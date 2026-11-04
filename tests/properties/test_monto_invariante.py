# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T019 — invariante I5: `Monto.estado == provisional` ⟺ `condicionantes` no vacía.

FR-046a exige que la marca de provisional sea inseparable del monto. Acá se fija
la otra mitad: que la marca no pueda existir vacía de contenido. Un monto
provisional sin condicionantes sería una marca sin explicación.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    EstadoResultado,
    SentidoImpacto,
)
from ultimo_timbre.models.informe import Condicionante, Monto

condicionantes = st.builds(
    Condicionante,
    clase=st.sampled_from(list(ClaseCondicionante)),
    referencia=st.text(min_size=1, max_size=40).filter(lambda s: s.strip() != ""),
    sentido_impacto=st.sampled_from(list(SentidoImpacto)),
    que_falta_verificar=st.text(min_size=1, max_size=60).filter(lambda s: s.strip() != ""),
)

importes = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("99999999"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)


def _monto(estado: EstadoResultado, conds: list[Condicionante], valor: Decimal) -> Monto:
    return Monto(
        valor=valor,
        estado=estado,
        condicionantes=tuple(conds),
        grilla_version="2026-01",
        a_valores_de=dt.date(2026, 1, 1),
    )


@given(valor=importes, conds=st.lists(condicionantes, min_size=1, max_size=4))
def test_provisional_con_condicionantes_es_valido(
    valor: Decimal, conds: list[Condicionante]
) -> None:
    monto = _monto(EstadoResultado.PROVISIONAL, conds, valor)
    assert monto.estado is EstadoResultado.PROVISIONAL
    assert len(monto.condicionantes) >= 1


@given(valor=importes)
def test_provisional_sin_condicionantes_es_invalido(valor: Decimal) -> None:
    with pytest.raises(ValidationError):
        _monto(EstadoResultado.PROVISIONAL, [], valor)


@given(valor=importes)
def test_definitivo_sin_condicionantes_es_valido(valor: Decimal) -> None:
    monto = _monto(EstadoResultado.DEFINITIVO, [], valor)
    assert monto.estado is EstadoResultado.DEFINITIVO


@given(valor=importes, conds=st.lists(condicionantes, min_size=1, max_size=3))
def test_definitivo_con_condicionantes_es_invalido(
    valor: Decimal, conds: list[Condicionante]
) -> None:
    """Si algo lo condiciona, no es definitivo. La equivalencia va en los dos sentidos."""
    with pytest.raises(ValidationError):
        _monto(EstadoResultado.DEFINITIVO, conds, valor)


@given(valor=importes, conds=st.lists(condicionantes, max_size=3))
def test_el_estado_y_los_condicionantes_son_coherentes(
    valor: Decimal, conds: list[Condicionante]
) -> None:
    """La equivalencia I5, formulada directamente."""
    estado = EstadoResultado.PROVISIONAL if conds else EstadoResultado.DEFINITIVO
    monto = _monto(estado, conds, valor)
    assert (monto.estado is EstadoResultado.PROVISIONAL) == (len(monto.condicionantes) > 0)


def test_el_monto_no_acepta_float() -> None:
    """Principio II: ni por esta puerta entra un float."""
    with pytest.raises(ValidationError):
        Monto(
            valor=1234.56,  # type: ignore[arg-type]
            estado=EstadoResultado.DEFINITIVO,
            condicionantes=(),
            grilla_version="2026-01",
            a_valores_de=dt.date(2026, 1, 1),
        )


def test_el_monto_es_inmutable() -> None:
    monto = _monto(EstadoResultado.DEFINITIVO, [], Decimal("100.00"))
    with pytest.raises(ValidationError):
        monto.valor = Decimal("200.00")
