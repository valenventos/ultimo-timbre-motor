# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T015 — contrato del informe (FR-046a, invariante I5).

Lo central: el schema debe **rechazar** un monto marcado provisional que no
declare qué lo condiciona. Un número provisional sin explicación es el defecto
que FR-046a existe para impedir.
"""

from __future__ import annotations

from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def _condicionante() -> dict[str, Any]:
    return {
        "clase": "regla_no_verificada",
        "referencia": "antiguedad.tope",
        "norma": {"texto": "Ley 10579, art. 33", "ley": "Ley 10579"},
        "sentido_impacto": "indeterminado",
        "que_falta_verificar": "si el tope vigente es 120 % o 125 %",
    }


def _monto(estado: str, condicionantes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "valor": "1234567.89",
        "moneda": "ARS",
        "estado": estado,
        "condicionantes": condicionantes,
        "grilla_version": "2026-01",
        "a_valores_de": "2026-01-01",
    }


def test_el_schema_es_draft_2020_12_valido(schema_informe: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema_informe)


def _validar_monto(schema_informe: dict[str, Any], monto: dict[str, Any]) -> None:
    sub = {
        "$schema": schema_informe["$schema"],
        "$ref": "#/$defs/monto",
        "$defs": schema_informe["$defs"],
    }
    Draft202012Validator(sub).validate(monto)


def test_rechaza_monto_provisional_sin_condicionantes(schema_informe: dict[str, Any]) -> None:
    """FR-046a, I5: provisional obliga a declarar al menos un condicionante."""
    with pytest.raises(ValidationError):
        _validar_monto(schema_informe, _monto("provisional", []))


def test_acepta_monto_provisional_con_condicionante(schema_informe: dict[str, Any]) -> None:
    _validar_monto(schema_informe, _monto("provisional", [_condicionante()]))


def test_acepta_monto_definitivo_sin_condicionantes(schema_informe: dict[str, Any]) -> None:
    _validar_monto(schema_informe, _monto("definitivo", []))


def test_el_importe_viaja_como_string_no_como_number(schema_informe: dict[str, Any]) -> None:
    """Principio II: un number de JSON lo parsea cualquier consumidor como float."""
    monto = _monto("definitivo", [])
    monto["valor"] = 1234567.89
    with pytest.raises(ValidationError):
        _validar_monto(schema_informe, monto)


def test_el_monto_no_puede_omitir_su_estado_ni_sus_condicionantes(
    schema_informe: dict[str, Any],
) -> None:
    requeridos = set(schema_informe["$defs"]["monto"]["required"])
    assert {"estado", "condicionantes", "valor", "grilla_version", "a_valores_de"} <= requeridos


def test_el_informe_expone_estado_general_legible_por_maquina(
    schema_informe: dict[str, Any],
) -> None:
    """FR-046c, SC-012."""
    assert "estado_general" in schema_informe["required"]
    assert set(schema_informe["properties"]["estado_general"]["enum"]) == {
        "definitivo",
        "provisional",
    }


def test_el_informe_declara_la_fecha_de_calculo(schema_informe: dict[str, Any]) -> None:
    """FR-001a: permite reproducir el informe más adelante."""
    assert "fecha_de_calculo" in schema_informe["required"]


def test_la_advertencia_declara_si_bloquea_el_calculo(schema_informe: dict[str, Any]) -> None:
    """FR-045a, invariante I7."""
    adv = schema_informe["$defs"]["advertencia"]
    assert "bloquea_calculo" in adv["required"]
