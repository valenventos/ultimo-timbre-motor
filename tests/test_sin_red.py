# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T170 — el mismo informe con los sockets bloqueados (US6 esc. 3, SC-007).

`tests/test_aislamiento.py` ya verifica que `calcular` **no abre** sockets. Lo
que se agrega acá es distinto y es lo que pide SC-007: que el informe sea
**idéntico** con la red cortada, por las dos vías —librería y CLI—.

La diferencia importa. Un motor podría no abrir sockets en el camino feliz y
aun así degradar silenciosamente si algo de la cadena intentara resolver un DNS
o buscar una actualización: el informe saldría distinto sin que nadie lo note.
Comparar las dos salidas byte a byte lo convierte en verificable.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any, NoReturn

import pytest
from typer.testing import CliRunner

from tests.casos import caso_inc_b
from tests.cli.conftest import CASO_INC_B
from ultimo_timbre.cli.main import app
from ultimo_timbre.engine import calcular
from ultimo_timbre.render.json_out import informe_a_json
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture
def sin_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """Corta todo acceso a red, incluido el DNS."""

    def prohibido(*_a: Any, **_k: Any) -> NoReturn:
        msg = "el motor no puede tocar la red (SC-007, Principio V)"
        raise AssertionError(msg)

    monkeypatch.setattr(socket, "socket", prohibido)
    monkeypatch.setattr(socket, "create_connection", prohibido)
    monkeypatch.setattr(socket, "getaddrinfo", prohibido)
    monkeypatch.setattr(socket, "gethostbyname", prohibido)


@pytest.mark.usefixtures("sin_red")
def test_la_libreria_produce_el_mismo_informe_sin_red() -> None:
    con_red = informe_a_json(calcular(caso_inc_b(), reglas=versiones.cargar_reglas("v1")))
    assert con_red == informe_a_json(calcular(caso_inc_b(), reglas=REGLAS))


def test_la_cli_produce_el_mismo_informe_sin_red(tmp_path: Path) -> None:
    """Se corre dos veces la CLI: una normal y otra con los sockets cortados."""
    ruta = tmp_path / "caso.yaml"
    ruta.write_text(CASO_INC_B, encoding="utf-8")
    runner = CliRunner()
    argumentos = ["calcular", str(ruta), "--formato", "json"]

    normal = runner.invoke(app, argumentos)
    assert normal.exit_code == 0, normal.output

    with pytest.MonkeyPatch.context() as mp:

        def prohibido(*_a: Any, **_k: Any) -> NoReturn:
            msg = "la CLI no puede tocar la red (SC-007)"
            raise AssertionError(msg)

        mp.setattr(socket, "socket", prohibido)
        mp.setattr(socket, "create_connection", prohibido)
        mp.setattr(socket, "getaddrinfo", prohibido)
        cortado = runner.invoke(app, argumentos)

    assert cortado.exit_code == 0, cortado.output
    assert cortado.stdout == normal.stdout


@pytest.mark.usefixtures("sin_red")
def test_cargar_las_reglas_tampoco_necesita_red() -> None:
    """Los datos normativos son archivos del repo, no un servicio."""
    reglas = versiones.cargar_reglas("v1")
    assert reglas.version == "v1"
    assert reglas.reglas


@pytest.mark.usefixtures("sin_red")
def test_el_bloqueo_de_sockets_funciona() -> None:
    """Resguardo: sin esto, los tests de arriba podrían pasar en vacío."""
    with pytest.raises(AssertionError):
        socket.socket()
