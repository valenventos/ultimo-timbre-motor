# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T168 — exit 2 con mensaje accionable (US6 esc. 2, FR-003, FR-057).

FR-057 pide que el mensaje nombre **el campo y el período** y describa la
corrección posible. El Principio VIII lo completa: ningún error deja al usuario
sin una acción.

**Lo que el mensaje no lleva** es tan importante como lo que lleva: FR-054
prohíbe datos personales —nombre, CUIL, fecha de nacimiento, montos, cargos— en
reportes de error. Así que el mensaje identifica el período por su **índice
anónimo** y nombra el campo, nunca el cargo ni las fechas cargadas. El usuario
tiene su propio archivo delante; el índice le alcanza para encontrar la línea.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ultimo_timbre.cli.main import app

EXIT_ENTRADA_INVALIDA = 2


def test_una_entrada_invalida_devuelve_exit_2(runner: CliRunner, caso_invalido_yaml: Path) -> None:
    r = runner.invoke(app, ["calcular", str(caso_invalido_yaml)])
    assert r.exit_code == EXIT_ENTRADA_INVALIDA, r.output


def test_el_mensaje_nombra_el_periodo_afectado(runner: CliRunner, caso_invalido_yaml: Path) -> None:
    """El período 1, no «la historia»: el 0 es válido."""
    r = runner.invoke(app, ["calcular", str(caso_invalido_yaml)])
    assert "período 1" in r.output


def test_el_mensaje_nombra_el_campo(runner: CliRunner, caso_invalido_yaml: Path) -> None:
    r = runner.invoke(app, ["calcular", str(caso_invalido_yaml)])
    assert "hasta" in r.output


def test_el_mensaje_describe_la_correccion(runner: CliRunner, caso_invalido_yaml: Path) -> None:
    """Principio VIII: decir qué está mal sin decir qué hacer no sirve."""
    r = runner.invoke(app, ["calcular", str(caso_invalido_yaml)])
    assert "Corregí" in r.output or "corregí" in r.output


def test_el_mensaje_ubica_el_periodo_con_su_cargo_y_sus_fechas(
    runner: CliRunner, caso_invalido_yaml: Path
) -> None:
    """FR-057: la pantalla se enriquece con el dato de **ese** período.

    El objeto de excepción no lo lleva —eso es lo que podría terminar en un
    log—; lo agrega la CLI al imprimir. La distinción completa, con el lado del
    logging, está en `tests/cli/test_error_enriquecido.py`.
    """
    r = runner.invoke(app, ["calcular", str(caso_invalido_yaml)])
    assert "maestro_de_grado" in r.output
    assert "2014-12-31" in r.output


def test_el_mensaje_no_filtra_la_fecha_de_nacimiento(
    runner: CliRunner, caso_invalido_yaml: Path
) -> None:
    """El enriquecimiento se limita a cargo, 'desde' y 'hasta' del período."""
    r = runner.invoke(app, ["calcular", str(caso_invalido_yaml)])
    assert "1980-03-15" not in r.output


def test_un_archivo_que_no_existe_devuelve_exit_2(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["calcular", str(tmp_path / "no-existe.yaml")])
    assert r.exit_code == EXIT_ENTRADA_INVALIDA, r.output


def test_una_extension_no_soportada_devuelve_exit_2(runner: CliRunner, tmp_path: Path) -> None:
    ruta = tmp_path / "caso.txt"
    ruta.write_text("nada", encoding="utf-8")
    r = runner.invoke(app, ["calcular", str(ruta)])
    assert r.exit_code == EXIT_ENTRADA_INVALIDA, r.output
    assert ".yaml" in r.output or ".json" in r.output


def test_un_yaml_roto_devuelve_exit_2(runner: CliRunner, tmp_path: Path) -> None:
    ruta = tmp_path / "roto.yaml"
    ruta.write_text("historia: [[[", encoding="utf-8")
    r = runner.invoke(app, ["calcular", str(ruta)])
    assert r.exit_code == EXIT_ENTRADA_INVALIDA, r.output


def test_una_version_de_reglas_inexistente_devuelve_exit_2(
    runner: CliRunner, caso_inc_b_yaml: Path
) -> None:
    r = runner.invoke(app, ["calcular", str(caso_inc_b_yaml), "--reglas", "v999"])
    assert r.exit_code == EXIT_ENTRADA_INVALIDA, r.output


def test_el_comando_validar_tambien_devuelve_exit_2(
    runner: CliRunner, caso_invalido_yaml: Path
) -> None:
    r = runner.invoke(app, ["validar", str(caso_invalido_yaml)])
    assert r.exit_code == EXIT_ENTRADA_INVALIDA, r.output
    assert "período 1" in r.output


def test_un_campo_obligatorio_faltante_nombra_el_campo(runner: CliRunner, tmp_path: Path) -> None:
    ruta = tmp_path / "sin-nacimiento.yaml"
    ruta.write_text(
        'schema_version: "1.0.0"\n'
        "fecha_de_calculo: 2030-04-01\n"
        "fechas_cese:\n  - 2030-03-31\n"
        "historia:\n  periodos:\n"
        "    - cargo: maestro_de_grado\n"
        "      establecimiento:\n        tipo: estatal_dgcye\n"
        "      desde: 2004-03-01\n"
        "      caja_aportes: ips\n"
        "      situacion_revista: titular\n",
        encoding="utf-8",
    )
    r = runner.invoke(app, ["calcular", str(ruta)])
    assert r.exit_code == EXIT_ENTRADA_INVALIDA, r.output
    assert "fecha_nacimiento" in r.output


def test_el_codigo_1_no_se_usa(runner: CliRunner, caso_invalido_yaml: Path) -> None:
    """Queda reservado para los fallos no controlados de Python y Typer.

    Si un caso de usuario saliera con 1, un crash del intérprete sería
    indistinguible de una entrada inválida.
    """
    r = runner.invoke(app, ["calcular", str(caso_invalido_yaml)])
    assert r.exit_code != 1
