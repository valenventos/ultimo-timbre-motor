# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verificación de infraestructura, no de dominio.

Confirma que el paquete quedó instalable e importable con el layout `src/`.
No prueba ninguna regla de cálculo: eso llega con las tareas de test de cada
historia, que se escriben antes de su implementación (Principio VI).
"""

import importlib

import pytest

SUBPAQUETES = ["models", "rules", "engine", "render", "cli"]


def test_el_paquete_se_importa() -> None:
    assert importlib.import_module("ultimo_timbre") is not None


@pytest.mark.parametrize("nombre", SUBPAQUETES)
def test_los_subpaquetes_se_importan(nombre: str) -> None:
    assert importlib.import_module(f"ultimo_timbre.{nombre}") is not None
