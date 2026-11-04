# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T174 — CLI y librería producen resultados idénticos (FR-051, Principio V).

La equivalencia es **estructural**, no una coincidencia que haya que mantener a
mano: la CLI es un cargador más un renderizador alrededor de la misma función
`calcular`. Este test es lo que impide que alguien «mejore» la CLI con un ajuste
que la librería no tenga —redondear para mostrar, completar un default, saltear
una advertencia— y que las dos vías empiecen a divergir sin que nadie lo note.

Un gremio que automatiza con la CLI y un estudio que integra la librería tienen
que poder discutir el mismo número.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import ultimo_timbre
from tests.cli.conftest import CASO_INC_B, CASO_OTRA_CAJA
from ultimo_timbre.cli.main import app
from ultimo_timbre.engine import calcular
from ultimo_timbre.entrada import cargar_caso
from ultimo_timbre.render.json_out import informe_a_dict
from ultimo_timbre.render.texto import informe_a_texto
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

CASOS = {"inc_b": CASO_INC_B, "otra_caja": CASO_OTRA_CAJA}


@pytest.fixture(params=sorted(CASOS))
def caso_en_disco(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    ruta = tmp_path / f"{request.param}.yaml"
    ruta.write_text(CASOS[request.param], encoding="utf-8")
    return ruta


def test_el_json_de_la_cli_es_el_de_la_libreria(caso_en_disco: Path) -> None:
    por_cli = CliRunner().invoke(app, ["calcular", str(caso_en_disco), "--formato", "json"])
    assert por_cli.exit_code in {0, 3}, por_cli.output

    por_libreria = informe_a_dict(calcular(cargar_caso(caso_en_disco), reglas=REGLAS))
    assert json.loads(por_cli.stdout) == por_libreria


def test_el_texto_de_la_cli_es_el_de_la_libreria(caso_en_disco: Path) -> None:
    por_cli = CliRunner().invoke(app, ["calcular", str(caso_en_disco)])
    assert por_cli.exit_code in {0, 3}, por_cli.output

    por_libreria = informe_a_texto(calcular(cargar_caso(caso_en_disco), reglas=REGLAS))
    assert por_cli.stdout.rstrip("\n") == por_libreria.rstrip("\n")


def test_cargar_caso_es_parte_de_la_api_publica() -> None:
    """El contrato de librería lo declara: un consumidor no debe reimplementarlo."""
    for nombre in ("cargar_caso", "cargar_caso_desde_texto", "informe_a_texto"):
        assert nombre in ultimo_timbre.__all__, nombre
        assert hasattr(ultimo_timbre, nombre), nombre


def test_la_libreria_no_necesita_la_cli() -> None:
    """FR-052: `calcular` no puede depender de la capa de línea de comandos.

    Se exceptúan `cli/` y `__main__.py`: el segundo **es** el punto de entrada
    del ejecutable —lo que hace que `python -m ultimo_timbre` funcione— así que
    importar la CLI es exactamente su razón de existir. Lo que el test cuida es
    que no lo haga ningún módulo de librería.
    """
    raiz = Path(__file__).resolve().parent.parent / "src" / "ultimo_timbre"
    for ruta in sorted(raiz.rglob("*.py")):
        if "cli" in ruta.parts or ruta.name == "__main__.py":
            continue
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        for nodo in ast.walk(arbol):
            modulo = (
                nodo.module
                if isinstance(nodo, ast.ImportFrom) and nodo.module
                else next((a.name for a in nodo.names), "")
                if isinstance(nodo, ast.Import)
                else ""
            )
            assert "ultimo_timbre.cli" not in modulo, f"{ruta.name} importa {modulo}"
