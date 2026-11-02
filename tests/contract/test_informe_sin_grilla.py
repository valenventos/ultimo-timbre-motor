# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T054 — el informe de elegibilidad sin grilla valida contra su contrato.

La US1 entrega un informe sin montos. Que valide contra el mismo
`informe.schema.json` que usarán las historias siguientes es lo que hace que el
contrato sea estable y no una promesa.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from tests.casos import caso_inc_b, caso_incisos_multiples, caso_no_cumple
from ultimo_timbre.engine import calcular
from ultimo_timbre.render import json_out
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

CASOS = {
    "inc_b": caso_inc_b,
    "no_cumple": caso_no_cumple,
    "incisos_multiples": caso_incisos_multiples,
}


@pytest.fixture(params=sorted(CASOS))
def informe_json(request: pytest.FixtureRequest) -> dict[str, Any]:
    informe = calcular(CASOS[request.param](), reglas=REGLAS)
    datos: dict[str, Any] = json.loads(json_out.informe_a_json(informe))
    return datos


def test_el_informe_valida_contra_el_schema(
    schema_informe: dict[str, Any], informe_json: dict[str, Any]
) -> None:
    Draft202012Validator(schema_informe).validate(informe_json)


def test_el_informe_declara_los_campos_requeridos(
    schema_informe: dict[str, Any], informe_json: dict[str, Any]
) -> None:
    assert set(schema_informe["required"]) <= set(informe_json)


def test_sin_grilla_la_version_de_grilla_es_nula(informe_json: dict[str, Any]) -> None:
    assert informe_json["version_grilla"] is None


def test_sin_grilla_ningun_escenario_lleva_haber(informe_json: dict[str, Any]) -> None:
    assert all(e.get("haber") is None for e in informe_json["escenarios"])


def test_los_porcentajes_viajan_como_string(informe_json: dict[str, Any]) -> None:
    """Principio II: un number de JSON lo parsea cualquier consumidor como float."""
    for escenario in informe_json["escenarios"]:
        if escenario.get("porcentaje") is not None:
            assert isinstance(escenario["porcentaje"], str)
    for inciso in informe_json["elegibilidad"]["incisos"]:
        if inciso.get("falta"):
            for valor in inciso["falta"].values():
                assert isinstance(valor, str)


def test_el_estado_general_es_legible_por_maquina(informe_json: dict[str, Any]) -> None:
    """FR-046c, SC-012."""
    assert informe_json["estado_general"] in {"definitivo", "provisional"}


def test_cada_paso_del_desglose_declara_su_tipo_de_fuente(
    informe_json: dict[str, Any],
) -> None:
    """FR-040: la letra de la ley no se mezcla con la interpretación."""
    for paso in informe_json["desglose"]:
        assert paso["tipo_fuente"] in {"letra_ley", "interpretacion"}
        assert paso["norma"]["texto"]


def test_el_json_no_contiene_ningun_float(informe_json: dict[str, Any]) -> None:
    def recorrer(valor: object) -> None:
        if isinstance(valor, dict):
            for v in valor.values():
                recorrer(v)
        elif isinstance(valor, list):
            for v in valor:
                recorrer(v)
        else:
            assert not isinstance(valor, float), valor

    recorrer(informe_json)
