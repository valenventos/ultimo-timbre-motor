# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T169 — exit 3 **con** informe parcial (FR-045a, FR-045b).

El código 3 no significa «no hay informe». Significa «no confíes en el monto».
El caso igual produce todo lo que el motor pudo sostener: la elegibilidad de los
tramos computables, las detecciones con su norma y el desglose de lo calculado.

Negar el informe entero le quitaría al profesional el análisis que el motor ya
tenía hecho —qué dicen los 20 años que sí son del IPS— y el Principio IV
prefiere un resultado parcial explicado a ninguno.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ultimo_timbre.cli.main import app

EXIT_FUERA_DE_ALCANCE = 3


def test_un_caso_con_advertencia_bloqueante_devuelve_exit_3(
    runner: CliRunner, caso_otra_caja_yaml: Path
) -> None:
    r = runner.invoke(app, ["calcular", str(caso_otra_caja_yaml)])
    assert r.exit_code == EXIT_FUERA_DE_ALCANCE, r.output


def test_el_informe_se_emite_igual_en_json(runner: CliRunner, caso_otra_caja_yaml: Path) -> None:
    """FR-045a: el exit 3 no suprime la salida."""
    r = runner.invoke(app, ["calcular", str(caso_otra_caja_yaml), "--formato", "json"])
    assert r.exit_code == EXIT_FUERA_DE_ALCANCE
    informe = json.loads(r.stdout)
    assert len(informe["elegibilidad"]["incisos"]) == 3
    assert informe["desglose"]


def test_el_informe_se_emite_igual_en_texto(runner: CliRunner, caso_otra_caja_yaml: Path) -> None:
    r = runner.invoke(app, ["calcular", str(caso_otra_caja_yaml)])
    assert r.exit_code == EXIT_FUERA_DE_ALCANCE
    assert "Elegibilidad" in r.output


def test_el_informe_declara_la_advertencia_bloqueante(
    runner: CliRunner, caso_otra_caja_yaml: Path
) -> None:
    r = runner.invoke(app, ["calcular", str(caso_otra_caja_yaml), "--formato", "json"])
    bloqueantes = [a for a in json.loads(r.stdout)["advertencias"] if a["bloquea_calculo"]]
    assert bloqueantes
    assert all(a["norma"] is not None for a in bloqueantes)


def test_no_se_emite_haber(runner: CliRunner, caso_otra_caja_yaml: Path) -> None:
    """Invariante I7: con advertencia bloqueante no hay monto."""
    r = runner.invoke(app, ["calcular", str(caso_otra_caja_yaml), "--formato", "json"])
    assert all(e["haber"] is None for e in json.loads(r.stdout)["escenarios"])


def test_el_exit_3_se_distingue_del_exit_2(
    runner: CliRunner, caso_otra_caja_yaml: Path, caso_invalido_yaml: Path
) -> None:
    """Un caso fuera de alcance no es una entrada inválida: el archivo está bien."""
    fuera = runner.invoke(app, ["calcular", str(caso_otra_caja_yaml)])
    invalido = runner.invoke(app, ["calcular", str(caso_invalido_yaml)])
    assert fuera.exit_code != invalido.exit_code


def test_el_caso_fuera_de_alcance_no_lanza_excepcion(
    runner: CliRunner, caso_otra_caja_yaml: Path
) -> None:
    """`FueraDeAlcance` quedó para errores de programación, que son exit 4."""
    r = runner.invoke(app, ["calcular", str(caso_otra_caja_yaml)])
    assert r.exception is None or isinstance(r.exception, SystemExit)
