# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Los YAML normativos **reales** validan contra sus schemas (T025-T027, T039-T042).

Lo que este módulo cubre, y que faltaba: `test_schema_rechaza_float.py` valida
reglas sintéticas contra `rule.schema.json`, así que el schema podía describir
una forma distinta de la que tienen los archivos de `rules/` sin que nada lo
notara. El paso de CI que debía atrapar eso aplicaba el schema de **una regla**
a documentos que son `{reglas: [...]}`, de modo que fallaba por la razón
equivocada en lugar de validar nada.

Acá se valida el documento completo, con el schema del documento, sobre los
archivos que el motor efectivamente carga.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

RAIZ = Path(__file__).resolve().parent.parent.parent
SCHEMAS = RAIZ / "schemas"
REGLAS_DIR = RAIZ / "rules"

DOCUMENTOS_DE_REGLAS = ("requisitos.yaml", "haber.yaml", "no_verificadas.yaml")


def _leer_schema(nombre: str) -> dict[str, Any]:
    with (SCHEMAS / nombre).open(encoding="utf-8") as fh:
        datos: dict[str, Any] = json.load(fh)
    return datos


def _validador(nombre: str) -> Draft202012Validator:
    """Un validador que resuelve los `$ref` relativos a archivos de `schemas/`.

    `ruleset.schema.json` y `cargo.schema.json` referencian a
    `rule.schema.json` por ruta relativa, igual que lo hace `check-jsonschema`
    en CI: el registro replica esa resolución sin salir a la red.
    """
    registro = Registry().with_resources(
        [
            (ruta.name, Resource.from_contents(_leer_schema(ruta.name)))
            for ruta in sorted(SCHEMAS.glob("*.schema.json"))
        ]
    )
    return Draft202012Validator(_leer_schema(nombre), registry=registro)


def _versiones() -> list[Path]:
    return sorted(d for d in REGLAS_DIR.iterdir() if d.is_dir())


def _cargar(ruta: Path) -> Any:
    with ruta.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_hay_al_menos_una_version_de_reglas() -> None:
    """Resguardo: sin esto los tests parametrizados pasarían vacíos."""
    assert _versiones()


@pytest.mark.parametrize("nombre", ["rule.schema.json", "ruleset.schema.json", "cargo.schema.json"])
def test_los_schemas_son_draft_2020_12_validos(nombre: str) -> None:
    Draft202012Validator.check_schema(_leer_schema(nombre))


@pytest.mark.parametrize("version", _versiones(), ids=lambda d: d.name)
@pytest.mark.parametrize("documento", DOCUMENTOS_DE_REGLAS)
def test_los_documentos_de_reglas_validan(version: Path, documento: str) -> None:
    ruta = version / documento
    assert ruta.exists(), f"falta {ruta}"
    _validador("ruleset.schema.json").validate(_cargar(ruta))


@pytest.mark.parametrize("version", _versiones(), ids=lambda d: d.name)
def test_el_catalogo_de_cargos_valida(version: Path) -> None:
    ruta = version / "cargos.yaml"
    assert ruta.exists(), f"falta {ruta}"
    _validador("cargo.schema.json").validate(_cargar(ruta))


@pytest.mark.parametrize("version", _versiones(), ids=lambda d: d.name)
def test_no_queda_ningun_yaml_de_reglas_sin_validar(version: Path) -> None:
    """Un archivo nuevo en `rules/` no puede quedar fuera de los schemas."""
    presentes = {p.name for p in version.glob("*.yaml")}
    cubiertos = {*DOCUMENTOS_DE_REGLAS, "cargos.yaml"}
    assert presentes <= cubiertos, (
        f"estos archivos de {version.name} no los valida ningún schema: "
        f"{sorted(presentes - cubiertos)}"
    )


# ---------------------------------------------------------------------------
# Que el `$ref` al schema de la regla se aplique de verdad
# ---------------------------------------------------------------------------
#
# Sin esto los tests de arriba podrían pasar en vacío: si el `$ref` no
# resolviera, `{reglas: [...]}` validaría con cualquier contenido adentro.


def test_el_documento_rechaza_un_porcentaje_sin_comillas() -> None:
    """research R1: el float binario tiene que morir en el schema, no en el motor."""
    doc = {
        "reglas": [
            {
                "id": "haber.art41.base",
                "norma": {"texto": "DL 9650/80, art. 41", "ley": "DL 9650/80"},
                "tipo": "letra_ley",
                "estado": "verificado",
                "verificada_en": "2026-10-30",
                "valor": {"porcentaje": 0.70},
            }
        ]
    }
    with pytest.raises(ValidationError):
        _validador("ruleset.schema.json").validate(doc)


def test_el_documento_rechaza_una_regla_sin_norma() -> None:
    """Principio I: una regla sin fuente no entra ni al repositorio."""
    doc = {"reglas": [{"id": "x", "tipo": "letra_ley", "estado": "verificado", "valor": None}]}
    with pytest.raises(ValidationError):
        _validador("ruleset.schema.json").validate(doc)


def test_el_catalogo_rechaza_una_entrada_fuera_de_forma() -> None:
    doc = {
        "reglas": [
            {
                "id": "al_frente.ley_13469.extension",
                "norma": {"texto": "Ley 13469", "ley": "Ley 13469"},
                "tipo": "letra_ley",
                "estado": "verificado",
                "verificada_en": "2026-10-30",
                "valor": None,
            }
        ],
        "entradas": [{"cargo": "maestro_de_grado"}],
    }
    with pytest.raises(ValidationError):
        _validador("cargo.schema.json").validate(doc)
