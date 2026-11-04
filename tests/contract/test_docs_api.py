# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T184 — los ejemplos de `docs/api.md` se ejecutan de verdad.

Un ejemplo de documentación que no corre es peor que no tener ejemplo: el
lector lo copia, no funciona, y pierde la confianza en todo lo demás que dice
la página. Acá los bloques ```python de `docs/api.md` se ejecutan en orden,
compartiendo un mismo espacio de nombres, tal como los leería alguien de
arriba hacia abajo.

Cada bloque afirma sobre su propio resultado con `assert`, así que no hace
falta comparar salidas impresas: si un ejemplo deja de ser verdad, el bloque
falla solo y el test nombra cuál.

Esto cubre además una garantía del contrato que ningún otro test mira desde el
borde público: que `from ultimo_timbre import ...` alcanza para hacer un
cálculo completo, sin importar nada de `engine` ni de `rules`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

DOC = Path("docs/api.md")

# ```python … ``` — solo los bloques de Python; las tablas y el prosa quedan
# afuera.
BLOQUE = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)


def _bloques() -> list[str]:
    assert DOC.exists(), f"{DOC} no existe"
    encontrados = BLOQUE.findall(DOC.read_text(encoding="utf-8"))
    assert encontrados, "docs/api.md no tiene ningún bloque de Python"
    return encontrados


BLOQUES = _bloques()


def test_hay_ejemplos_suficientes() -> None:
    """Un guardarraíl contra el caso en que la expresión regular deje de matchear.

    Sin esto, un cambio de formato en el documento vaciaría la lista y los
    tests pasarían sin ejecutar nada: el peor modo de falla posible para un
    test que existe para verificar que algo corre.
    """
    assert len(BLOQUES) >= 7


def test_los_ejemplos_corren_en_orden() -> None:
    """Se ejecutan compartiendo namespace, como los leería una persona."""
    espacio: dict[str, Any] = {"__name__": "docs_api"}
    for n, bloque in enumerate(BLOQUES, start=1):
        try:
            exec(compile(bloque, f"docs/api.md#bloque{n}", "exec"), espacio)
        except Exception as error:  # pragma: no cover - solo si el doc miente
            pytest.fail(f"el bloque {n} de docs/api.md falló: {error!r}\n\n{bloque}")


@pytest.mark.parametrize("prohibido", ["ultimo_timbre.engine", "ultimo_timbre.rules"])
def test_los_ejemplos_solo_usan_la_superficie_publica(prohibido: str) -> None:
    """FR-052: lo público alcanza para todo lo que la página muestra.

    Si un ejemplo necesitara `ultimo_timbre.engine`, eso significaría que la
    superficie pública está incompleta, y el documento lo estaría tapando.
    """
    for n, bloque in enumerate(BLOQUES, start=1):
        assert prohibido not in bloque, f"el bloque {n} importa {prohibido}"
