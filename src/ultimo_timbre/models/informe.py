# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Salida del motor (T032).

La decisión central está en `Monto`: el estado y los condicionantes son **parte
del tipo**, no metadatos al costado. Así FR-046a («la marca es inseparable del
monto en toda vía de salida») se cumple por construcción y no por disciplina de
cada serializador: no existe una representación del monto sin su marca.

`Informe.estado_general` se **deriva** de sus componentes en lugar de aceptarse
como entrada, para que no puedan quedar inconsistentes (FR-046c).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    CodigoAdvertencia,
    EstadoResultado,
    OrigenDato,
    SentidoImpacto,
    TipoEscenario,
    TipoFuente,
    ViaCargoBase,
)
from ultimo_timbre.models.normativa import Norma

__all__ = [
    "Advertencia",
    "CandidatoDescartado",
    "CargoBase",
    "Condicionante",
    "Elegibilidad",
    "Escenario",
    "Faltante",
    "Informe",
    "LecturaAlternativa",
    "Monto",
    "PasoDelDesglose",
    "Procedencia",
    "ResultadoInciso",
    "ResultadoRequisito",
    "Versiones",
]

MODELO = ConfigDict(strict=True, frozen=True, extra="forbid")


class Condicionante(BaseModel):
    """Lo que impide que un monto sea definitivo (FR-046b).

    Son dos clases: una regla `NO_VERIFICADA` o una **situación del caso**
    (grilla ausente, cargo fuera de catálogo, override manual, supuesto de
    continuidad). Si solo se modelaran las reglas, esas situaciones tendrían que
    marcar el monto como provisional sin poder explicar por qué.
    """

    model_config = MODELO

    clase: ClaseCondicionante
    referencia: str = Field(min_length=1)
    sentido_impacto: SentidoImpacto
    que_falta_verificar: str = Field(min_length=1)
    norma: Norma | None = None
    magnitud_estimada: str | None = None

    @model_validator(mode="after")
    def _la_regla_declara_su_norma(self) -> Self:
        if self.clase is ClaseCondicionante.SITUACION_DEL_CASO and self.norma is not None:
            raise ValueError("una situación del caso no tiene norma asociada")
        return self


class Monto(BaseModel):
    """Un importe con su estado y sus condicionantes incorporados (FR-046a, I5)."""

    model_config = MODELO

    valor: Decimal
    estado: EstadoResultado
    condicionantes: tuple[Condicionante, ...]
    grilla_version: str = Field(min_length=1)
    a_valores_de: dt.date
    """Fecha de la grilla usada. En escenarios futuros es la última aprobada (FR-030a)."""
    moneda: str = "ARS"

    @model_validator(mode="after")
    def _invariante_i5(self) -> Self:
        """`estado == provisional` ⟺ `condicionantes` no vacía."""
        tiene = len(self.condicionantes) > 0
        if self.estado is EstadoResultado.PROVISIONAL and not tiene:
            raise ValueError(
                "un monto provisional debe declarar al menos un condicionante: "
                "una marca sin explicación no sirve a quien lee el informe (FR-046a)"
            )
        if self.estado is EstadoResultado.DEFINITIVO and tiene:
            raise ValueError(
                "un monto con condicionantes no puede ser definitivo: la equivalencia "
                "del invariante I5 vale en los dos sentidos"
            )
        return self


class Faltante(BaseModel):
    """Cuánto falta para habilitar un inciso (FR-016)."""

    model_config = MODELO

    anios_edad: Decimal = Decimal("0")
    anios_servicio: Decimal = Decimal("0")


class ResultadoRequisito(BaseModel):
    model_config = MODELO

    nombre: str = Field(min_length=1)
    cumple: bool
    norma: Norma
    valor_alcanzado: str | None = None
    valor_requerido: str | None = None


class ResultadoInciso(BaseModel):
    """El resultado de un inciso del art. 24 (FR-011 a FR-013)."""

    model_config = MODELO

    inciso: str = Field(pattern="^[bcd]$")
    cumple: bool
    norma: Norma
    requisitos: tuple[ResultadoRequisito, ...] = ()
    habilitado_desde: dt.date | None = None
    falta: Faltante | None = None


class Elegibilidad(BaseModel):
    model_config = MODELO

    incisos: tuple[ResultadoInciso, ...]
    minimo_22_anios: ResultadoRequisito
    estado: EstadoResultado
    inciso_mas_favorable: str | None = None


class CandidatoDescartado(BaseModel):
    """Por qué un cargo no quedó como cargo base (FR-021)."""

    model_config = MODELO

    cargo: str = Field(min_length=1)
    razon: str = Field(min_length=1)
    meses_alcanzados: int | None = None


class CargoBase(BaseModel):
    model_config = MODELO

    cargo: str = Field(min_length=1)
    via: ViaCargoBase
    meses_que_lo_sustentan: tuple[str, ...]
    """Serializados `YYYY-MM`, para que el desglose muestre meses concretos (FR-020)."""
    descartados: tuple[CandidatoDescartado, ...]
    estado: EstadoResultado
    norma: Norma
    descenso_desde: str | None = None
    """Cargo superior que no alcanzó los 36/60 meses (FR-020a)."""


class LecturaAlternativa(BaseModel):
    """La lectura literal de los arts. 42 y 43 (FR-027b).

    El criterio aplicado por defecto es el del IPS —el excedente se cuenta desde
    que se cumplen todas las condiciones—, pero existe la lectura que lo mide
    solo por edad, y esa tendría impacto al alza. El informe la expone.
    """

    model_config = MODELO

    porcentaje: Decimal
    sentido_impacto: SentidoImpacto
    norma: Norma


class Advertencia(BaseModel):
    model_config = MODELO

    codigo: CodigoAdvertencia
    mensaje: str = Field(min_length=1)
    bloquea_calculo: bool = False
    """FR-045a: impide emitir haber, pero NO aborta el informe."""
    norma: Norma | None = None
    sentido_impacto: SentidoImpacto | None = None
    periodo_idx: int | None = None


class Escenario(BaseModel):
    model_config = MODELO

    fecha_cese: dt.date
    tipo: TipoEscenario
    hay_derecho: bool
    advertencias: tuple[Advertencia, ...] = ()
    inciso: str | None = None
    porcentaje: Decimal | None = None
    antiguedad_anios: int | None = None
    haber: Monto | None = None
    lectura_literal: LecturaAlternativa | None = None

    @model_validator(mode="after")
    def _sin_haber_si_hay_bloqueo(self) -> Self:
        """Invariante I7: una advertencia bloqueante impide el haber."""
        if self.haber is not None and any(a.bloquea_calculo for a in self.advertencias):
            raise ValueError(
                "un escenario con advertencia bloqueante no puede llevar haber (FR-044, FR-045)"
            )
        return self


class PasoDelDesglose(BaseModel):
    """Una operación del cálculo con su regla y su norma (FR-038, FR-040)."""

    model_config = MODELO

    orden: int = Field(ge=1)
    descripcion: str = Field(min_length=1)
    regla_id: str = Field(min_length=1)
    norma: Norma
    tipo_fuente: TipoFuente
    entrada: str | None = None
    salida: str | None = None


class Procedencia(BaseModel):
    """De dónde salió cada dato del informe (FR-039)."""

    model_config = MODELO

    dato: str = Field(min_length=1)
    origen: OrigenDato
    derivado_de: str | None = None
    difiere_del_catalogo: bool = False


class Versiones(BaseModel):
    """Lo que `versiones_disponibles()` devuelve a la CLI."""

    model_config = MODELO

    reglas: tuple[str, ...] = ()
    grillas: tuple[str, ...] = ()


class Informe(BaseModel):
    """El resultado completo."""

    model_config = MODELO

    fecha_de_calculo: dt.date
    elegibilidad: Elegibilidad
    escenarios: tuple[Escenario, ...]
    desglose: tuple[PasoDelDesglose, ...]
    procedencias: tuple[Procedencia, ...]
    advertencias: tuple[Advertencia, ...]
    version_reglas: str = Field(min_length=1)
    aviso_estimacion: str = Field(min_length=1)
    aviso_movilidad: str = Field(min_length=1)
    cargo_base: CargoBase | None = None
    version_grilla: str | None = None
    estado_general: EstadoResultado = EstadoResultado.DEFINITIVO
    schema_version: str = "1.0.0"

    @model_validator(mode="after")
    def _derivar_estado_general(self) -> Self:
        """FR-046c, invariante I6: se deriva, no se acepta como entrada."""
        provisional = (
            self.elegibilidad.estado is EstadoResultado.PROVISIONAL
            or (
                self.cargo_base is not None
                and self.cargo_base.estado is EstadoResultado.PROVISIONAL
            )
            or any(
                e.haber is not None and e.haber.estado is EstadoResultado.PROVISIONAL
                for e in self.escenarios
            )
        )
        esperado = EstadoResultado.PROVISIONAL if provisional else EstadoResultado.DEFINITIVO
        if self.estado_general is not esperado:
            object.__setattr__(self, "estado_general", esperado)
        return self

    @property
    def tiene_bloqueos(self) -> bool:
        """La CLI deriva el exit 3 de esto (FR-045b)."""
        return any(a.bloquea_calculo for a in self.advertencias) or any(
            a.bloquea_calculo for e in self.escenarios for a in e.advertencias
        )
