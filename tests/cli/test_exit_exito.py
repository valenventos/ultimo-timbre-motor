# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T167 — exit 0 con informe completo (US6 esc. 1, FR-055, FR-056).

El punto que este test fija: **un resultado provisional sale con exit 0**. Es un
resultado válido del motor (decisión Q3), y lo que lo distingue es
`estado_general` en el informe, no el código de salida. Un script que quiera
rechazar resultados provisionales lee ese campo; si el provisional saliera con
código de error, no habría forma de distinguir «el motor no pudo» de «el motor
pudo, con reservas».
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from ultimo_timbre.cli.main import app


def test_un_caso_valido_termina_con_exit_0(runner: CliRunner, caso_inc_b_yaml: Path) -> None:
    r = runner.invoke(app, ["calcular", str(caso_inc_b_yaml)])
    assert r.exit_code == 0, r.output


def test_la_salida_por_defecto_es_texto_legible(runner: CliRunner, caso_inc_b_yaml: Path) -> None:
    r = runner.invoke(app, ["calcular", str(caso_inc_b_yaml)])
    assert "inc. b" in r.output
    assert "{" not in r.output.splitlines()[0]


def test_el_formato_json_emite_el_informe_completo(
    runner: CliRunner, caso_inc_b_yaml: Path
) -> None:
    """FR-055: el informe estructurado completo, no un resumen."""
    r = runner.invoke(app, ["calcular", str(caso_inc_b_yaml), "--formato", "json"])
    assert r.exit_code == 0, r.output
    informe = json.loads(r.stdout)
    for clave in (
        "elegibilidad",
        "escenarios",
        "desglose",
        "procedencias",
        "advertencias",
        "condicionantes",
        "cargo_base",
        "estado_general",
        "version_reglas",
        "aviso_estimacion",
        "aviso_movilidad",
        "schema_version",
    ):
        assert clave in informe, clave


def test_un_resultado_provisional_tambien_sale_con_exit_0(
    runner: CliRunner, caso_inc_b_yaml: Path
) -> None:
    """Decisión Q3: lo provisional es un resultado, no un fallo."""
    r = runner.invoke(app, ["calcular", str(caso_inc_b_yaml), "--formato", "json"])
    assert r.exit_code == 0
    assert json.loads(r.stdout)["estado_general"] in {"definitivo", "provisional"}


def test_acepta_json_como_entrada(runner: CliRunner, caso_inc_b_json: Path) -> None:
    """Las fechas llegan como string y el cargador las convierte en el borde."""
    r = runner.invoke(app, ["calcular", str(caso_inc_b_json), "--formato", "json"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.stdout)["fecha_de_calculo"] == "2030-04-01"


def test_el_yaml_y_el_json_producen_el_mismo_informe(
    runner: CliRunner, caso_inc_b_yaml: Path, caso_inc_b_json: Path
) -> None:
    """El formato de entrada no puede cambiar el resultado (FR-048)."""
    a = runner.invoke(app, ["calcular", str(caso_inc_b_yaml), "--formato", "json"])
    b = runner.invoke(app, ["calcular", str(caso_inc_b_json), "--formato", "json"])
    assert a.stdout == b.stdout


def test_la_opcion_salida_escribe_el_informe_a_un_archivo(
    runner: CliRunner, caso_inc_b_yaml: Path, tmp_path: Path
) -> None:
    """FR-053: lo único que el motor escribe a disco es el informe que se pide."""
    destino = tmp_path / "informe.json"
    r = runner.invoke(
        app,
        ["calcular", str(caso_inc_b_yaml), "--formato", "json", "--salida", str(destino)],
    )
    assert r.exit_code == 0, r.output
    assert destino.exists()
    assert json.loads(destino.read_text(encoding="utf-8"))["estado_general"]


def test_la_cli_completa_la_fecha_de_calculo_cuando_falta(
    runner: CliRunner, caso_sin_fecha_yaml: Path
) -> None:
    """FR-001a: el motor no mira el reloj; la CLI sí, y lo deja asentado."""
    r = runner.invoke(
        app,
        [
            "calcular",
            str(caso_sin_fecha_yaml),
            "--formato",
            "json",
            "--fecha-calculo",
            "2030-04-01",
        ],
    )
    assert r.exit_code == 0, r.output
    assert json.loads(r.stdout)["fecha_de_calculo"] == "2030-04-01"


def test_la_fecha_calculo_explicita_tiene_prioridad_sobre_la_del_archivo(
    runner: CliRunner, caso_inc_b_yaml: Path
) -> None:
    """Es lo que permite reproducir un informe viejo tal como se emitió."""
    r = runner.invoke(
        app,
        ["calcular", str(caso_inc_b_yaml), "--formato", "json", "--fecha-calculo", "2031-01-15"],
    )
    assert r.exit_code == 0, r.output
    assert json.loads(r.stdout)["fecha_de_calculo"] == "2031-01-15"


def test_el_comando_versiones_lista_las_reglas_disponibles(runner: CliRunner) -> None:
    r = runner.invoke(app, ["versiones"])
    assert r.exit_code == 0, r.output
    assert "v1" in r.output


def test_el_comando_validar_acepta_un_caso_valido(runner: CliRunner, caso_inc_b_yaml: Path) -> None:
    r = runner.invoke(app, ["validar", str(caso_inc_b_yaml)])
    assert r.exit_code == 0, r.output


# ---------------------------------------------------------------------------
# Los ejemplos del quickstart tienen que existir y correr
# ---------------------------------------------------------------------------


def test_los_ejemplos_del_quickstart_existen_y_corren(runner: CliRunner) -> None:
    """`quickstart.md` los invoca por nombre: si faltan, la guía está rota.

    Los códigos esperados son 0 o 3: varios ejemplos son casos fuera del
    Alcance de la v1 a propósito, y ese es el punto de tenerlos.
    """
    raiz = Path(__file__).resolve().parent.parent.parent
    quickstart = (raiz / "specs" / "001-motor-calculo-jubilacion" / "quickstart.md").read_text(
        encoding="utf-8"
    )
    citados = sorted(set(re.findall(r"examples/([\w.-]+\.yaml)", quickstart)))
    assert citados, "el quickstart dejó de citar ejemplos: revisá este test"

    for nombre in citados:
        ruta = raiz / "examples" / nombre
        assert ruta.exists(), f"el quickstart cita examples/{nombre} y no existe"
        r = runner.invoke(app, ["calcular", str(ruta), "--formato", "json"])
        assert r.exit_code in {0, 3}, f"{nombre}: exit {r.exit_code}\n{r.output}"


def test_los_ejemplos_declaran_que_son_inventados() -> None:
    """Ningún ejemplo puede parecer el caso de una persona real."""
    raiz = Path(__file__).resolve().parent.parent.parent
    ejemplos = sorted((raiz / "examples").glob("*.yaml"))
    assert ejemplos
    for ruta in ejemplos:
        assert "datos inventados" in ruta.read_text(encoding="utf-8"), ruta.name
