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
from ultimo_timbre.models.enums import (
    CajaAportes,
    NaturalezaServicio,
    SituacionRevista,
    TipoEstablecimiento,
)

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


# ---------------------------------------------------------------------------
# Casos de referencia de la US2 (límites del motor)
# ---------------------------------------------------------------------------


def caso_otra_caja() -> Caso:
    """US2 esc. 2 — 20 años al IPS y 10 a ANSES `[DL 9650/80, arts. 66 y 67]`."""
    return caso(
        periodo(desde="2006-03-01", hasta="2026-02-28"),
        periodo(
            "maestro_de_grado",
            desde="1996-03-01",
            hasta="2006-02-28",
            caja_aportes=CajaAportes.ANSES,
        ),
        nacimiento="1970-05-10",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-03-01",
    )


def caso_privado() -> Caso:
    """US2 esc. 4 — un tramo en un establecimiento de gestión privada."""
    return caso(
        periodo(desde="2006-03-01", hasta="2026-02-28"),
        periodo(
            "maestro_de_grado",
            desde="1996-03-01",
            hasta="2006-02-28",
            establecimiento=PRIVADO,
        ),
        nacimiento="1970-05-10",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-03-01",
    )


def caso_simultaneidad() -> Caso:
    """US2 esc. 1 — dos cargos distintos superpuestos más de 3 años continuos."""
    return caso(
        periodo("maestro_de_grado", desde="1996-03-01", hasta="2026-02-28"),
        periodo("preceptor", desde="2010-03-01", hasta="2020-02-29"),
        nacimiento="1970-05-10",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-03-01",
    )


def caso_simultaneidad_breve() -> Caso:
    """Solapamiento real pero de menos de 3 años: no alcanza el art. 47."""
    return caso(
        periodo("maestro_de_grado", desde="1996-03-01", hasta="2026-02-28"),
        periodo("preceptor", desde="2010-03-01", hasta="2011-02-28"),
        nacimiento="1970-05-10",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-03-01",
    )


def caso_error_de_carga() -> Caso:
    """Mismo cargo y mismo establecimiento solapados: casi siempre carga duplicada."""
    return caso(
        periodo("maestro_de_grado", desde="1996-03-01", hasta="2026-02-28"),
        periodo("maestro_de_grado", desde="2010-03-01", hasta="2015-02-28"),
        nacimiento="1970-05-10",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-03-01",
    )


def caso_prorrateo_posible() -> Caso:
    """US2 esc. 5 — los docentes no alcanzan, pero hay no docentes al IPS.

    La naturaleza no docente entra por `naturaleza_override`: el catálogo
    versionado todavía no tiene ningún cargo no docente, porque ninguna norma
    citada en la spec lo documenta.
    """
    return caso(
        periodo(desde="2010-06-01", hasta="2026-05-31"),
        periodo(
            "maestro_de_grado",
            desde="1996-06-01",
            hasta="2010-05-31",
            naturaleza_override=NaturalezaServicio.NO_DOCENTE,
        ),
        nacimiento="1974-05-01",
        ceses=["2026-05-31"],
        fecha_de_calculo="2026-06-01",
    )
