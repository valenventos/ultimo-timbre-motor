# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T020 — el motor no consulta el reloj (FR-001a, research R13).

Sin esto el determinismo del Principio II valdría solo dentro de la misma
jornada: un `date.today()` escondido en una validación rompe la reproducibilidad
de un modo difícil de detectar, porque los tests pasan todos los días menos uno.

La verificación es estática, por AST, para que no dependa de que una ruta se
ejecute en la corrida.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PAQUETES_PUROS = ["src/ultimo_timbre/engine", "src/ultimo_timbre/rules"]

# Nombres de atributo que, llamados sobre date, datetime o time, devuelven
# el instante actual.
ATRIBUTOS_PROHIBIDOS = {
    "today",
    "now",
    "utcnow",
    "fromtimestamp",
    "utcfromtimestamp",
    "time",
    "time_ns",
    "monotonic",
    "perf_counter",
}
MODULOS_PROHIBIDOS = {"time"}


def _archivos_py(subdir: str) -> list[Path]:
    base = RAIZ / subdir
    if not base.exists():
        pytest.fail(f"falta {subdir}: la Fase 2 debe crearlo")
    return sorted(base.rglob("*.py"))


def _accesos_al_reloj(ruta: Path) -> list[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    hallazgos: list[str] = []
    for nodo in ast.walk(arbol):
        # llamadas del estilo date.today / datetime.now / time.time
        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr in ATRIBUTOS_PROHIBIDOS
        ):
            hallazgos.append(f"{ruta.name}:{nodo.lineno} llamada a .{nodo.func.attr}()")
        # from time import time  /  import time
        if isinstance(nodo, ast.ImportFrom) and nodo.module in MODULOS_PROHIBIDOS:
            hallazgos.append(f"{ruta.name}:{nodo.lineno} importa de {nodo.module}")
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name in MODULOS_PROHIBIDOS:
                    hallazgos.append(f"{ruta.name}:{nodo.lineno} importa {alias.name}")
    return hallazgos


@pytest.mark.parametrize("subdir", PAQUETES_PUROS)
def test_sin_accesos_al_reloj(subdir: str) -> None:
    hallazgos = [h for f in _archivos_py(subdir) for h in _accesos_al_reloj(f)]
    assert not hallazgos, (
        f"{subdir} consulta el reloj del sistema: "
        + "; ".join(hallazgos)
        + ". La fecha de cálculo entra por `Caso.fecha_de_calculo` (FR-001a)."
    )


@pytest.mark.parametrize("subdir", PAQUETES_PUROS)
def test_los_paquetes_puros_existen_y_tienen_modulos(subdir: str) -> None:
    assert _archivos_py(subdir), f"{subdir} no tiene ningún módulo"


def test_el_detector_encuentra_un_acceso_plantado(tmp_path: Path) -> None:
    """Un test de verificación que no puede fallar no verifica nada."""
    trampa = tmp_path / "trampa.py"
    trampa.write_text(
        "import datetime\n\ndef f():\n    return datetime.date.today()\n", encoding="utf-8"
    )
    assert _accesos_al_reloj(trampa), "el detector no vio un date.today() evidente"


def test_el_detector_no_marca_codigo_limpio(tmp_path: Path) -> None:
    limpio = tmp_path / "limpio.py"
    limpio.write_text(
        "import datetime\n\ndef f(hoy: datetime.date) -> int:\n    return hoy.year\n",
        encoding="utf-8",
    )
    assert not _accesos_al_reloj(limpio)
