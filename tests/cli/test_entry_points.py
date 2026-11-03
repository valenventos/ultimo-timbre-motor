# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T182 — los puntos de entrada propagan el código de salida.

Se verifica por **subproceso** y no con `CliRunner` porque lo que está en
juego es justamente lo que `CliRunner` no puede ver: que invocar el paquete
desde la línea de comandos real termine con el código correcto.

El riesgo concreto que esto cubre: sin `__main__.py`, `python -m
ultimo_timbre.cli.main` importa el módulo, **no corre nada y termina con exit
0** —el código que significa «informe emitido»—. Un script que invocara el
motor así creería que todo salió bien sin haber calculado nada.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent.parent
EJEMPLOS = RAIZ / "examples"


def _correr(*argumentos: str) -> subprocess.CompletedProcess[str]:
    """Corre el motor como lo correría un script, y decodifica en UTF-8.

    `errors="replace"` cubre un solo caso: la **ayuda** de Typer, que se imprime
    antes de que corra cualquier comando —por `no_args_is_help`— y por lo tanto
    antes de que la CLI pueda forzar UTF-8 en la salida. Lleva caracteres de
    recuadro y en una consola cp1252 sale mal, lo cual es cosmético.

    El informe, que **sí** es un contrato de datos, no depende de esto: la CLI
    reconfigura la salida a UTF-8 antes de emitirlo, y el test de abajo verifica
    que el JSON se decodifica sin reemplazos.
    """
    return subprocess.run(
        [sys.executable, "-m", "ultimo_timbre", *argumentos],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=RAIZ,
        check=False,
        timeout=120,
    )


@pytest.mark.parametrize(
    ("ejemplo", "esperado"),
    [
        ("caso-inc-b.yaml", 0),
        ("caso-otra-caja.yaml", 3),
        ("caso-privado.yaml", 3),
    ],
)
def test_python_m_propaga_el_codigo_de_salida(ejemplo: str, esperado: int) -> None:
    r = _correr("calcular", str(EJEMPLOS / ejemplo), "--formato", "json")
    assert r.returncode == esperado, f"{ejemplo}: {r.returncode}\n{r.stderr}"


def test_python_m_emite_el_informe_en_stdout() -> None:
    r = _correr("calcular", str(EJEMPLOS / "caso-inc-b.yaml"), "--formato", "json")
    assert r.returncode == 0, r.stderr
    assert r.stdout.lstrip().startswith("{")


def test_el_informe_sale_en_utf8_aunque_la_consola_no_lo_sea() -> None:
    """El informe es un contrato de datos: los acentos tienen que sobrevivir.

    Se corre el caso con acentos y se verifica que no quedó ningún carácter de
    reemplazo, que es lo que aparecería si la salida fuera cp1252.
    """
    r = _correr("calcular", str(EJEMPLOS / "caso-inc-b.yaml"), "--formato", "texto")
    assert r.returncode == 0, r.stderr
    assert "�" not in r.stdout
    assert "JUBILACIÓN" in r.stdout
    assert "estimación orientativa" in r.stdout


def test_sin_argumentos_muestra_la_ayuda_y_no_sale_con_0() -> None:
    """Invocar el motor sin decirle qué hacer no es un éxito."""
    r = _correr()
    assert r.returncode != 0
    assert "calcular" in r.stdout + r.stderr
