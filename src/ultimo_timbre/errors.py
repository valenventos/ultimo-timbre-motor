# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Excepciones del motor (T034).

Ninguna lleva valores de dominio en su mensaje: solo identificadores técnicos
anónimos como `periodo_idx`, `regla_id` o el nombre del campo (FR-054).
"""

from __future__ import annotations

__all__ = [
    "CasoInvalido",
    "FueraDeAlcance",
    "GrillaInvalida",
    "ReglasNoDisponibles",
    "UltimoTimbreError",
]


class UltimoTimbreError(Exception):
    """Raíz de todos los errores del motor."""


class CasoInvalido(UltimoTimbreError):
    """La entrada no valida: schema o coherencia temporal (FR-003, exit 2).

    Nombra el campo y el período afectado para que el mensaje sea accionable
    (FR-057), nunca el valor que el usuario cargó.
    """

    def __init__(
        self, mensaje: str, *, campo: str | None = None, periodo_idx: int | None = None
    ) -> None:
        self.campo = campo
        self.periodo_idx = periodo_idx
        ubicacion = ""
        if periodo_idx is not None:
            ubicacion += f" [periodo_idx={periodo_idx}]"
        if campo is not None:
            ubicacion += f" [campo={campo}]"
        super().__init__(mensaje + ubicacion)


class ReglasNoDisponibles(UltimoTimbreError):
    """La versión de reglas o de grilla pedida no existe (exit 2)."""


class GrillaInvalida(UltimoTimbreError):
    """La grilla no puede usarse: ficticia en `grids/`, o sin aprobador.

    Principio IX: ninguna grilla no aprobada puede valuar un informe, y una
    grilla de prueba no puede salir de `tests/fixtures/`.
    """


class FueraDeAlcance(UltimoTimbreError):
    """**Error de programación**, no un caso de usuario.

    Un caso fuera del alcance de la v1 NO lanza esta excepción: devuelve un
    informe con el análisis parcial sostenible y advertencias `bloquea_calculo`
    (FR-045a), y la CLI lo traduce a exit 3 (FR-045b).

    Que una ruta interna llegue a valuar un tramo ya marcado fuera de alcance
    es un bug del motor, y por eso termina en exit 4.
    """
