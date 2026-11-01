# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T014 — contrato del archivo de caso.

Verifica que `contracts/caso.schema.json` es un schema Draft 2020-12 válido y
que acepta o rechaza lo que la especificación dice que debe aceptar o rechazar.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def test_el_schema_es_draft_2020_12_valido(schema_caso: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema_caso)


def test_acepta_el_caso_minimo(schema_caso: dict[str, Any], caso_minimo: dict[str, Any]) -> None:
    Draft202012Validator(schema_caso).validate(caso_minimo)


@pytest.mark.parametrize(
    "campo",
    ["schema_version", "fecha_de_calculo", "fecha_nacimiento", "fechas_cese", "historia"],
)
def test_rechaza_el_caso_sin_un_campo_requerido(
    schema_caso: dict[str, Any], caso_minimo: dict[str, Any], campo: str
) -> None:
    caso = copy.deepcopy(caso_minimo)
    del caso[campo]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_caso).validate(caso)


def test_rechaza_campos_no_declarados(
    schema_caso: dict[str, Any], caso_minimo: dict[str, Any]
) -> None:
    caso = copy.deepcopy(caso_minimo)
    caso["ruta_pdf"] = "recibo.pdf"  # FR-005: no hay carga de PDF
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_caso).validate(caso)


def test_el_periodo_sin_hasta_es_valido(
    schema_caso: dict[str, Any], caso_minimo: dict[str, Any]
) -> None:
    """FR-002e: `hasta` ausente significa período en curso."""
    caso = copy.deepcopy(caso_minimo)
    del caso["historia"]["periodos"][0]["hasta"]
    Draft202012Validator(schema_caso).validate(caso)


@pytest.mark.parametrize(
    "campo", ["cargo", "establecimiento", "desde", "caja_aportes", "situacion_revista"]
)
def test_rechaza_el_periodo_sin_un_campo_requerido(
    schema_caso: dict[str, Any], caso_minimo: dict[str, Any], campo: str
) -> None:
    caso = copy.deepcopy(caso_minimo)
    del caso["historia"]["periodos"][0][campo]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_caso).validate(caso)


def test_rechaza_fechas_de_cese_duplicadas(
    schema_caso: dict[str, Any], caso_minimo: dict[str, Any]
) -> None:
    caso = copy.deepcopy(caso_minimo)
    caso["fechas_cese"] = ["2030-03-31", "2030-03-31"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_caso).validate(caso)


def test_rechaza_historia_vacia(schema_caso: dict[str, Any], caso_minimo: dict[str, Any]) -> None:
    caso = copy.deepcopy(caso_minimo)
    caso["historia"]["periodos"] = []
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_caso).validate(caso)


def test_la_condicion_al_frente_no_es_un_campo_de_entrada(schema_caso: dict[str, Any]) -> None:
    """FR-002a: se deriva del catálogo; solo existe el override."""
    props = schema_caso["$defs"]["periodo"]["properties"]
    assert "al_frente_de_alumnos" not in props
    assert "naturaleza" not in props
    assert "al_frente_override" in props
    assert "naturaleza_override" in props


def test_la_caja_de_aportes_vive_en_el_periodo_no_en_el_establecimiento(
    schema_caso: dict[str, Any],
) -> None:
    """FR-002d: depende de la relación de empleo, no del cargo."""
    assert "caja_aportes" in schema_caso["$defs"]["periodo"]["properties"]
    assert "caja_aportes" not in schema_caso["$defs"]["establecimiento"]["properties"]
