# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T172 — `--fecha-calculo` fija produce informes idénticos (FR-001a, FR-048).

Es lo que vuelve auditable un informe viejo: con la fecha de cálculo y las
versiones de reglas y grilla, dos corridas separadas en el tiempo tienen que dar
el mismo archivo **byte a byte**. Sin eso, el `diff` entre dos informes sería
ruido y nadie podría demostrar qué cambió entre dos versiones de reglas.

El informe no lleva marca de tiempo de la corrida justamente por esto: si la
llevara, dos informes idénticos nunca serían iguales.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ultimo_timbre.cli.main import app

FECHA = "2030-04-01"


def _correr(runner: CliRunner, caso: Path, *extra: str) -> str:
    r = runner.invoke(
        app,
        ["calcular", str(caso), "--formato", "json", "--fecha-calculo", FECHA, *extra],
    )
    assert r.exit_code == 0, r.output
    return r.stdout


def test_dos_corridas_dan_el_mismo_json_byte_a_byte(
    runner: CliRunner, caso_inc_b_yaml: Path
) -> None:
    assert _correr(runner, caso_inc_b_yaml) == _correr(runner, caso_inc_b_yaml)


def test_dos_corridas_dan_el_mismo_texto(runner: CliRunner, caso_inc_b_yaml: Path) -> None:
    def texto() -> str:
        r = runner.invoke(app, ["calcular", str(caso_inc_b_yaml), "--fecha-calculo", FECHA])
        assert r.exit_code == 0, r.output
        return r.stdout

    assert texto() == texto()


def test_el_informe_no_lleva_marca_de_tiempo_de_la_corrida(
    runner: CliRunner, caso_inc_b_yaml: Path
) -> None:
    """Si la llevara, dos informes idénticos nunca serían iguales."""
    salida = _correr(runner, caso_inc_b_yaml)
    assert "generado_en" not in salida
    assert "timestamp" not in salida


def test_la_fecha_de_calculo_queda_asentada_en_el_informe(
    runner: CliRunner, caso_inc_b_yaml: Path
) -> None:
    """Sin eso, el informe no sería reproducible: faltaría una entrada."""
    assert json.loads(_correr(runner, caso_inc_b_yaml))["fecha_de_calculo"] == FECHA


def test_la_version_de_reglas_queda_asentada(runner: CliRunner, caso_inc_b_yaml: Path) -> None:
    assert json.loads(_correr(runner, caso_inc_b_yaml))["version_reglas"] == "v1"


def test_cambiar_la_fecha_de_calculo_cambia_el_informe(
    runner: CliRunner, caso_inc_b_yaml: Path
) -> None:
    """Resguardo: si no cambiara, la fecha no estaría entrando al cálculo."""
    otra = runner.invoke(
        app,
        ["calcular", str(caso_inc_b_yaml), "--formato", "json", "--fecha-calculo", "2031-06-30"],
    )
    assert otra.exit_code == 0, otra.output
    assert otra.stdout != _correr(runner, caso_inc_b_yaml)
