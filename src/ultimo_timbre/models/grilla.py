# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Grilla salarial y sus componentes (T031, FR-031a).

El valor de un cargo **no es un importe único**: es un conjunto de componentes.
La antigüedad se aplica solo sobre los bonificables (FR-031b), y con un importe
indiviso no habría forma de hacerlo bien ni —sobre todo— de mostrar en el
desglose sobre qué base se calculó, que es el producto (Principio IV).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ultimo_timbre.models.normativa import Norma

__all__ = ["ComponenteSalarial", "GrillaSalarial", "ValorCargo"]

MODELO = ConfigDict(strict=True, frozen=True, extra="forbid")


class ComponenteSalarial(BaseModel):
    """Una línea del valor de un cargo."""

    model_config = MODELO

    codigo_concepto: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    importe: Decimal
    bonificable: bool
    remunerativo: bool
    regla_id: str | None = None


class ValorCargo(BaseModel):
    model_config = MODELO

    cargo: str = Field(min_length=1)
    componentes: tuple[ComponenteSalarial, ...] = Field(min_length=1)

    @property
    def total(self) -> Decimal:
        return sum((c.importe for c in self.componentes), Decimal("0"))

    @property
    def base_bonificable(self) -> Decimal:
        """La base sobre la que se aplica la antigüedad (FR-031b)."""
        return sum((c.importe for c in self.componentes if c.bonificable), Decimal("0"))

    @property
    def total_remunerativo(self) -> Decimal:
        return sum((c.importe for c in self.componentes if c.remunerativo), Decimal("0"))


class GrillaSalarial(BaseModel):
    """Una versión de grilla con su procedencia y su aprobador (FR-008, Principio IX)."""

    model_config = MODELO

    version: str = Field(min_length=1)
    norma: Norma
    vigencia_desde: dt.date
    extraida_en: dt.date
    aprobada_por: str = Field(min_length=1)
    aprobada_en: dt.date
    valores: tuple[ValorCargo, ...] = Field(min_length=1)
    enlace: str | None = None
    vigencia_hasta: dt.date | None = None
    ficticia: bool = False
    """Solo las grillas de `tests/fixtures/`. El loader de `grids/` las rechaza."""

    @model_validator(mode="after")
    def _vigencia_coherente(self) -> Self:
        if self.vigencia_hasta is not None and self.vigencia_hasta < self.vigencia_desde:
            raise ValueError("`vigencia_hasta` no puede ser anterior a `vigencia_desde`")
        return self

    def cargo(self, nombre: str) -> ValorCargo | None:
        for valor in self.valores:
            if valor.cargo == nombre:
                return valor
        return None

    def vigente_a(self, fecha: dt.date) -> bool:
        if fecha < self.vigencia_desde:
            return False
        return self.vigencia_hasta is None or fecha <= self.vigencia_hasta
