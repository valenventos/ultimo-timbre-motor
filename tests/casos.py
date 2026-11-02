# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Constructores de casos para la suite. No es un módulo de test."""

from __future__ import annotations

import datetime as dt
from typing import Any

from ultimo_timbre.models.caso import (
    Caso,
    Establecimiento,
    HistoriaDeServicios,
    PeriodoDeServicio,
)
from ultimo_timbre.models.enums import CajaAportes, SituacionRevista, TipoEstablecimiento

ESTATAL = Establecimiento(tipo=TipoEstablecimiento.ESTATAL_DGCYE)
PRIVADO = Establecimiento(tipo=TipoEstablecimiento.PRIVADO)

FECHA_DE_CALCULO = dt.date(2026, 11, 2)


def f(iso: str) -> dt.date:
    return dt.date.fromisoformat(iso)


def periodo(
    cargo: str = "maestro_de_grado",
    desde: str = "2000-03-01",
    hasta: str | None = "2026-02-28",
    **kw: Any,
) -> PeriodoDeServicio:
    base: dict[str, Any] = {
        "cargo": cargo,
        "establecimiento": ESTATAL,
        "desde": f(desde),
        "hasta": f(hasta) if hasta else None,
        "caja_aportes": CajaAportes.IPS,
        "situacion_revista": SituacionRevista.TITULAR,
    }
    base.update(kw)
    return PeriodoDeServicio(**base)


def caso(
    *periodos: PeriodoDeServicio,
    nacimiento: str,
    ceses: list[str],
    fecha_de_calculo: str | None = None,
) -> Caso:
    return Caso(
        fecha_de_calculo=f(fecha_de_calculo) if fecha_de_calculo else FECHA_DE_CALCULO,
        fecha_nacimiento=f(nacimiento),
        historia=HistoriaDeServicios(periodos=tuple(periodos)),
        fechas_cese=tuple(f(c) for c in ceses),
    )


# ---------------------------------------------------------------------------
# Casos de referencia de la US1 (escenarios de spec.md)
# ---------------------------------------------------------------------------


def caso_inc_b() -> Caso:
    """US1 esc. 1 — 26 años al frente de alumnos, 50 de edad al cese."""
    return caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )


def caso_no_cumple() -> Caso:
    """US1 esc. 2 — 24 años de servicio y 52 de edad: no alcanza ningún inciso."""
    return caso(
        periodo(desde="2002-06-01", hasta="2026-05-31"),
        nacimiento="1974-05-01",
        ceses=["2026-05-31"],
        fecha_de_calculo="2026-06-01",
    )


def caso_incisos_multiples() -> Caso:
    """US1 esc. 4 — cumple el inc. b y el inc. d en fechas distintas."""
    return caso(
        periodo(desde="1990-02-01", hasta="2025-12-31"),
        nacimiento="1970-01-10",
        ceses=["2025-12-31"],
        fecha_de_calculo="2026-01-02",
    )
