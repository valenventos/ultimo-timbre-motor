# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixtures compartidas por toda la suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CONTRACTS = RAIZ / "specs" / "001-motor-calculo-jubilacion" / "contracts"
SCHEMAS = RAIZ / "schemas"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _leer_json(ruta: Path) -> dict[str, Any]:
    with ruta.open(encoding="utf-8") as fh:
        datos: dict[str, Any] = json.load(fh)
    return datos


@pytest.fixture(scope="session")
def raiz() -> Path:
    return RAIZ


@pytest.fixture(scope="session")
def schema_caso() -> dict[str, Any]:
    return _leer_json(CONTRACTS / "caso.schema.json")


@pytest.fixture(scope="session")
def schema_informe() -> dict[str, Any]:
    return _leer_json(CONTRACTS / "informe.schema.json")


@pytest.fixture(scope="session")
def schema_regla() -> dict[str, Any]:
    ruta = SCHEMAS / "rule.schema.json"
    if not ruta.exists():
        pytest.fail(f"falta {ruta} (T025)")
    return _leer_json(ruta)


@pytest.fixture
def caso_minimo() -> dict[str, Any]:
    """El caso más chico que el contrato debe aceptar."""
    return {
        "schema_version": "1.0.0",
        "fecha_de_calculo": "2026-11-01",
        "fecha_nacimiento": "1975-04-10",
        "fechas_cese": ["2030-03-31"],
        "historia": {
            "periodos": [
                {
                    "cargo": "maestro_de_grado",
                    "establecimiento": {"tipo": "estatal_dgcye"},
                    "desde": "2000-03-01",
                    "hasta": "2026-02-28",
                    "caja_aportes": "ips",
                    "situacion_revista": "titular",
                }
            ]
        },
    }
