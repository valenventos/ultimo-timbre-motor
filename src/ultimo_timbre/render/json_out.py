# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serialización determinista del informe (T066, FR-048, SC-003).

Dos corridas del mismo caso tienen que producir el mismo JSON **byte a byte**:
sin eso, el `diff` entre dos informes es ruido y nadie puede auditar qué cambió
entre dos versiones de reglas.

Tres decisiones que lo garantizan:

* `sort_keys=True`, para que el orden de las claves no dependa del orden de
  declaración de los campos;
* `Decimal` se serializa como **string**, nunca como number: un number de JSON
  lo parsea cualquier consumidor como float binario y ahí se pierde la
  exactitud que el Principio II protege;
* el informe **no lleva marca de tiempo de la corrida**. Si la llevara, dos
  informes idénticos nunca serían iguales.
"""

from __future__ import annotations

import json
from typing import Any

from ultimo_timbre.models.informe import Informe

__all__ = ["informe_a_dict", "informe_a_json"]


def informe_a_dict(informe: Informe) -> dict[str, Any]:
    """El informe como estructura serializable.

    `mode="json"` convierte fechas a ISO, enums a su valor y `Decimal` a string.
    """
    datos: dict[str, Any] = informe.model_dump(mode="json")
    return datos


def informe_a_json(informe: Informe, *, indent: int | None = 2) -> str:
    """El informe como JSON determinista."""
    return json.dumps(
        informe_a_dict(informe),
        sort_keys=True,
        ensure_ascii=False,
        indent=indent,
        allow_nan=False,
    )
