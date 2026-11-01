# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T023 — aislamiento del motor (FR-050, FR-052, FR-053, Principio V).

Dos mitades:

* **estática** (corre desde la Fase 2): ningún módulo del paquete importa la
  aplicación web, una base de datos, red ni nada probabilístico, y `engine/` no
  toca el sistema de archivos;
* **dinámica** (queda pendiente hasta la Fase 3): que `calcular()` no escriba a
  disco ni abra sockets no se puede verificar antes de que `calcular()` exista
  (T061, US1). Esa parte se saltea con motivo explícito en lugar de dar un
  verde falso.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PAQUETE = RAIZ / "src" / "ultimo_timbre"
ENGINE = PAQUETE / "engine"

# Nada de esto puede entrar al motor (Principios II, III y V).
IMPORTS_PROHIBIDOS = {
    # red
    "socket",
    "http",
    "httpx",
    "requests",
    "urllib",
    "urllib3",
    "aiohttp",
    "ftplib",
    "smtplib",
    # base de datos
    "sqlite3",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "pymongo",
    "redis",
    "asyncpg",
    # web
    "fastapi",
    "flask",
    "django",
    "starlette",
    "uvicorn",
    # probabilístico / LLM (Principio II)
    "random",
    "secrets",
    "numpy",
    "torch",
    "tensorflow",
    "sklearn",
    "openai",
    "anthropic",
    "transformers",
    "langchain",
}
# En `engine/` tampoco entra el sistema de archivos: `calcular` no hace I/O.
IMPORTS_PROHIBIDOS_EN_ENGINE = IMPORTS_PROHIBIDOS | {"pathlib", "shutil", "tempfile", "os", "io"}


def _modulos(base: Path) -> list[Path]:
    if not base.exists():
        pytest.fail(f"falta {base.relative_to(RAIZ)}: la Fase 2 debe crearlo")
    return sorted(base.rglob("*.py"))


def _imports(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module.split(".")[0])
    return nombres


def test_el_paquete_no_importa_red_base_de_datos_web_ni_nada_probabilistico() -> None:
    hallazgos = [
        f"{f.relative_to(PAQUETE)} importa {sorted(_imports(f) & IMPORTS_PROHIBIDOS)}"
        for f in _modulos(PAQUETE)
        if _imports(f) & IMPORTS_PROHIBIDOS
    ]
    assert not hallazgos, "; ".join(hallazgos)


def test_el_engine_no_toca_el_sistema_de_archivos() -> None:
    """FR-053: `calcular` recibe datos ya cargados; los loaders viven en `rules/`."""
    hallazgos = [
        f"{f.relative_to(PAQUETE)} importa {sorted(_imports(f) & IMPORTS_PROHIBIDOS_EN_ENGINE)}"
        for f in _modulos(ENGINE)
        if _imports(f) & IMPORTS_PROHIBIDOS_EN_ENGINE
    ]
    assert not hallazgos, "; ".join(hallazgos)


def test_el_engine_no_llama_a_open() -> None:
    hallazgos: list[str] = []
    for f in _modulos(ENGINE):
        arbol = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Name)
                and nodo.func.id == "open"
            ):
                hallazgos.append(f"{f.name}:{nodo.lineno}")
    assert not hallazgos, f"engine/ llama a open() en {hallazgos}"


def test_la_libreria_no_configura_logging() -> None:
    """Principio III, research R12: la librería solo usa NullHandler."""
    hallazgos: list[str] = []
    for f in _modulos(PAQUETE):
        if f.parts[-2] == "cli":  # la CLI sí configura el logging
            continue
        texto = f.read_text(encoding="utf-8")
        for prohibido in ("basicConfig", "StreamHandler", "FileHandler"):
            if prohibido in texto:
                hallazgos.append(f"{f.relative_to(PAQUETE)} usa {prohibido}")
    assert not hallazgos, "; ".join(hallazgos)


def test_el_detector_de_imports_encuentra_uno_plantado(tmp_path: Path) -> None:
    trampa = tmp_path / "trampa.py"
    trampa.write_text("import socket\n", encoding="utf-8")
    assert _imports(trampa) & IMPORTS_PROHIBIDOS


# ---------------------------------------------------------------------------
# Mitad dinámica — requiere `calcular()`, que llega con la US1 (T061)
# ---------------------------------------------------------------------------
_HAY_CALCULAR = importlib.util.find_spec("ultimo_timbre.engine") is not None and hasattr(
    importlib.import_module("ultimo_timbre.engine"), "calcular"
)

pendiente_us1 = pytest.mark.skipif(
    not _HAY_CALCULAR,
    reason="`calcular()` se implementa en la US1 (T061); el aislamiento en ejecución "
    "se verifica recién entonces",
)


@pendiente_us1
def test_calcular_no_escribe_a_disco() -> None:  # pragma: no cover - llega con la US1
    raise AssertionError("pendiente de implementar junto con calcular() en la US1")


@pendiente_us1
def test_calcular_no_abre_sockets() -> None:  # pragma: no cover - llega con la US1
    raise AssertionError("pendiente de implementar junto con calcular() en la US1")
