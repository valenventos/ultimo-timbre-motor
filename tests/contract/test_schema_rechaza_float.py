# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T017 — el schema de reglas rechaza un porcentaje sin comillas (research R1).

Es el gate que hace fallar en CI, y no en producción, al YAML donde alguien
escribió `0.70` en lugar de `"0.70"`.
"""

from __future__ import annotations

from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def _regla(valor: Any) -> dict[str, Any]:
    return {
        "id": "haber.base",
        "norma": {"texto": "DL 9650/80, art. 41", "ley": "DL 9650/80", "articulo": "41"},
        "tipo": "letra_ley",
        "estado": "verificado",
        "verificada_en": "2026-10-30",
        "valor": valor,
    }


def test_el_schema_de_reglas_es_valido(schema_regla: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema_regla)


def test_acepta_el_porcentaje_como_string(schema_regla: dict[str, Any]) -> None:
    Draft202012Validator(schema_regla).validate(_regla({"porcentaje": "0.70"}))


def test_rechaza_el_porcentaje_como_number(schema_regla: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_regla).validate(_regla({"porcentaje": 0.70}))


def test_rechaza_el_importe_como_number(schema_regla: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_regla).validate(_regla({"importe": 123456.78}))


def test_acepta_enteros_para_edades_y_anios(schema_regla: dict[str, Any]) -> None:
    """Las edades y los años sí son enteros: no hay decimal que preservar."""
    Draft202012Validator(schema_regla).validate(_regla({"edad": 50, "anios_servicio": 25}))


def test_exige_impacto_cuando_la_regla_no_esta_verificada(schema_regla: dict[str, Any]) -> None:
    """FR-046b: sin el sentido del impacto no se puede cumplir FR-046b."""
    regla = {
        "id": "antiguedad.tope",
        "norma": {"texto": "Ley 10579, art. 33", "ley": "Ley 10579"},
        "tipo": "letra_ley",
        "estado": "no_verificada",
        "valor": None,
    }
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_regla).validate(regla)


def test_exige_verificada_en_cuando_la_regla_esta_verificada(
    schema_regla: dict[str, Any],
) -> None:
    regla = _regla({"porcentaje": "0.70"})
    del regla["verificada_en"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_regla).validate(regla)


def test_rechaza_un_tipo_de_fuente_desconocido(schema_regla: dict[str, Any]) -> None:
    """Principio I: letra de la ley e interpretación no se mezclan."""
    regla = _regla({"porcentaje": "0.70"})
    regla["tipo"] = "opinion"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_regla).validate(regla)
