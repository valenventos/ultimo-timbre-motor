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
    excluido_art40: bool = False
    """Si el art. 40 del DL 9650/80 lo excluye de la remuneración del cargo.

    El artículo excluye horas extras, asignaciones familiares, viáticos, gastos
    de residencia y becas. Lo declara la **grilla** y no el motor, porque es un
    dato del componente: qué código de concepto corresponde a cada uno de esos
    conceptos depende de la escala, no de una regla general que el motor pueda
    aplicar a ciegas.
    """
    remunerativo: bool
    aporte_ips: bool | None = None
    """Si sobre este componente se calcula el aporte personal al IPS.

    `None` = la grilla no lo declara, que **no** equivale a `False`: significa
    que no se sabe, y el motor lo informa en lugar de suponerlo.

    Es el atributo que define la remuneración del cargo desde que se verificó,
    en la liquidación DGCyE 09/2026, que el aporte personal (código 1060) es el
    16 % exacto de la suma de los componentes con aporte, y que la bonificación
    no remunerativa compensatoria queda afuera.

    No coincide necesariamente con `remunerativo`. Son dos preguntas distintas
    —si el concepto es remunerativo y si tributa al IPS— y la Cuestión abierta
    #2 es justamente cuál de las dos define el haber. Confundirlas sería
    decidir la cuestión por omisión.
    """
    porcentaje_del_basico: Decimal | None = None
    """Si el componente se liquida como porcentaje del básico, cuál.

    Metadato de procedencia, no de cálculo: la grilla trae el importe ya
    resuelto y el motor no lo recalcula. Sirve para auditar la grilla contra la
    escala publicada —0667 es el 43,50 % del básico— y para detectar una
    transcripción equivocada antes de que produzca un haber.

    Verificado solo para el código 0667. Que **todos** los componentes
    porcentuales se calculen sobre el básico es la regla
    `componentes.porcentuales_sobre_basico`, todavía sin verificar para los
    demás códigos.
    """
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

    @property
    def basico(self) -> Decimal | None:
        """El componente básico, que es la base de todo lo demás.

        Es el único bonificable (`antiguedad.base_bonificable`, verificado) y la
        base de los componentes porcentuales. `None` si la grilla no declara
        ninguno bonificable, caso en que el motor no puede auditar los
        porcentajes ni aplicar la antigüedad.
        """
        bonificables = [c for c in self.componentes if c.bonificable]
        if len(bonificables) != 1:
            return None
        return bonificables[0].importe

    @property
    def total_con_aporte_ips(self) -> Decimal:
        """La base del aporte personal al IPS (liquidación DGCyE 09/2026)."""
        return sum(
            (c.importe for c in self.componentes if c.aporte_ips),
            Decimal("0"),
        )

    @property
    def declara_aporte_ips(self) -> bool:
        """Si **todos** los componentes dicen si tributan al IPS.

        Alcanza con que uno no lo diga para que el criterio no se pueda aplicar
        con certeza: el motor suma lo que sabe y declara la laguna.
        """
        return all(c.aporte_ips is not None for c in self.componentes)


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
    acto_aprobatorio: Norma | None = None
    """El decreto o acta paritaria que aprueba la escala. `None` es válido.

    Una escala puede estar publicada oficialmente —la del Ministerio de
    Economía de la Provincia, por ejemplo— **sin que la publicación cite el
    acto que la aprobó**. Exigir el acto dejaría al motor sin poder valuar nada
    con la fuente oficial disponible; dar la grilla por firme sin él le daría al
    monto una certeza que no tiene.

    La salida es intermedia: se admite la grilla, y todo monto calculado con
    ella lleva el condicionante `grilla_sin_acto_aprobatorio`, con sentido
    indeterminado. El profesional ve el número y ve de qué carece.

    `norma` sigue siendo obligatoria y es la **fuente** de los valores; esto es
    el acto que les dio fuerza, que es otra cosa.
    """
    ficticia: bool = False
    """Solo las grillas de `tests/fixtures/`. El loader de `grids/` las rechaza."""

    @property
    def tiene_acto_aprobatorio(self) -> bool:
        return self.acto_aprobatorio is not None

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
