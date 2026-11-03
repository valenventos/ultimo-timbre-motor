# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reglas, normas y catálogo de cargos (T030).

Principio I: ninguna regla vive en el código. Estos modelos son la forma en que
el motor lee los YAML de `rules/`, y los validadores son los que impiden que
entre una regla sin fuente o una regla `NO_VERIFICADA` que no declare su
impacto — sin eso FR-046b sería incumplible.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ultimo_timbre.models.enums import (
    CondicionAlFrente,
    EstadoRegla,
    NaturalezaServicio,
    SentidoImpacto,
    TipoFuente,
)

__all__ = [
    "CatalogoDeCargos",
    "ConjuntoDeReglas",
    "EntradaCatalogo",
    "Norma",
    "Regla",
]

MODELO = ConfigDict(strict=True, frozen=True, extra="forbid")

# El valor de una regla: str para decimales, int para edades y años, y nunca
# float (research R1). `None` cuando la regla existe pero su valor no está
# verificado, que es preferible a un número plausible.
#
# `list[str]` para enumeraciones de conceptos —los que el art. 40 excluye— y
# `list[dict[str, str | int]]` para escalas por tramos, donde cada tramo lleva
# sus años como `int` y su porcentaje como `str`. `float` queda fuera de la
# unión a propósito: un decimal sin comillas en un YAML falla la validación en
# lugar de convertirse en binario en silencio.
TramoDeEscala = dict[str, str | int]
ValorRegla = dict[str, str | int | bool | list[str] | list[TramoDeEscala] | None] | None


class Norma(BaseModel):
    """La fuente de una regla. Sin esto, una regla es una opinión."""

    model_config = MODELO

    texto: str = Field(min_length=1)
    ley: str = Field(min_length=1)
    articulo: str | None = None
    inciso: str | None = None
    enlace: str | None = None

    def __str__(self) -> str:
        return self.texto


class Regla(BaseModel):
    """Una regla del régimen expresada como dato versionado (FR-006)."""

    model_config = MODELO

    id: str = Field(min_length=1)
    norma: Norma
    tipo: TipoFuente
    estado: EstadoRegla
    vigencia_desde: dt.date | None = None
    vigencia_hasta: dt.date | None = None
    verificada_en: dt.date | None = None
    impacto_si_no_verificada: SentidoImpacto | None = None
    que_falta_verificar: str | None = None
    magnitud_estimada: str | None = None
    """Cuánto puede mover el resultado, en los términos en que se discute.

    Es **dato**, no texto generado: el resguardo que el mantenedor pidió para
    las reglas sin verificar es que el informe diga la dirección **y** la
    magnitud del impacto, y una magnitud redactada por el motor no tendría de
    dónde salir. Queda en `null` cuando no se puede acotar.
    """
    cuestion_abierta: int | None = None
    valor_por_defecto_aplicado: bool = False
    """La regla no está verificada pero el motor **igual tuvo que elegir algo**.

    Distingue dos situaciones que no son lo mismo: una regla cuyo valor queda en
    `null` porque el motor puede negarse a calcular (un porcentaje, un tope), y
    una cuya ausencia no es una opción —no se puede *no* contar el tiempo—. En
    el segundo caso `valor` trae la convención aplicada, declarada provisional.
    """
    valor: ValorRegla = None

    @model_validator(mode="after")
    def _coherencia_del_estado(self) -> Self:
        if self.estado is EstadoRegla.VERIFICADO:
            if self.verificada_en is None:
                raise ValueError(
                    "una regla verificada debe declarar `verificada_en`: sin fecha de "
                    "verificación no se puede auditar cuándo se comprobó la fuente"
                )
            if self.impacto_si_no_verificada is not None:
                raise ValueError(
                    "`impacto_si_no_verificada` solo aplica a reglas con estado no_verificada"
                )
        else:
            if self.impacto_si_no_verificada is None:
                raise ValueError(
                    "una regla no_verificada debe declarar `impacto_si_no_verificada`: "
                    "sin el sentido del impacto el informe no puede cumplir FR-046b"
                )
            if not self.que_falta_verificar:
                raise ValueError(
                    "una regla no_verificada debe declarar `que_falta_verificar`: "
                    "decir «no verificada» sin decir qué falta no sirve a nadie"
                )
        return self

    @property
    def condiciona_resultado(self) -> bool:
        """Si interviene, el resultado no puede ser definitivo (FR-046)."""
        return self.estado is EstadoRegla.NO_VERIFICADA


class EntradaCatalogo(BaseModel):
    """Un cargo del escalafón con su condición y la norma que la sostiene."""

    model_config = MODELO

    cargo: str = Field(min_length=1)
    jerarquia: int | None = None
    """Orden abstracto del cargo. Mayor entero = mayor jerarquía, `None` = sin orden.

    Se conserva separado de `indice_escalafonario` porque responden preguntas
    distintas: este es un orden, aquel es el multiplicador del sueldo básico. El
    art. 41 habla de «mayor jerarquía» y la Res. IPS 995/2021 de «mejor
    remunerado»; mientras la Cuestión abierta #4 no se resuelva, el motor no
    puede dar por sentado que los dos coincidan.
    """
    indice_escalafonario: Decimal | None = None
    """Índice escalafonario del nomenclador. `None` = no verificado.

    Es el multiplicador del sueldo básico del cargo testigo: el básico de un
    cargo es el del Preceptor por este índice. Eso lo vuelve, a la vez, el
    criterio de «mejor remunerado» de la Res. IPS 995/2021 —a igual grilla, más
    índice es más remuneración— y el desempate verificable del art. 41.

    Viaja como `str` numérico en el YAML y llega como `Decimal` (research R1):
    los índices son decimales exactos (1,10 · 1,32 · 2,16) y un `float` binario
    los arruinaría antes de que el modelo los vea.

    Está en `None` para **todas** las entradas de la v1: el Anexo del art. 9º
    del Decreto 2397/2005, que aprueba el texto ordenado del nomenclador, no
    está publicado. El relevamiento de lo que sí se encontró y por qué no
    alcanza está en `docs/datos-pendientes/relevamiento-2026-11.md`.
    """
    indice_es_por_hora: bool = False
    """Si el índice se aplica por **hora cátedra** y no por cargo.

    Un índice por hora no es comparable con uno por cargo: 1,15 por hora de
    Enseñanza Media no es «menos jerarquía» que 1,70 de un Director. Sin esta
    marca, el comparador de `cargo_base` mezclaría dos magnitudes distintas y
    el resultado parecería válido.
    """
    regla_indice: str | None = None
    """Regla que condiciona el índice, cuando no está verificado."""
    al_frente_de_alumnos: bool | None = None
    naturaleza: NaturalezaServicio | None = None
    norma: Norma
    estado: EstadoRegla = EstadoRegla.VERIFICADO
    regla_id: str | None = None
    """Regla que **condiciona** esta entrada, incluso si el estado es verificado.

    Un cargo puede tener su condición verificada por la letra de la ley y aun así
    quedar condicionado por una regla sin verificar: director y vicedirector son
    `al_frente_de_alumnos: false` según el art. 24 inc. b, pero la extensión
    discutida de la Ley 13469 (Cuestión abierta #8) podría cambiarlo al alza.
    """
    condicion: CondicionAlFrente = CondicionAlFrente.DIRECTA
    regla_umbral: str | None = None
    """Regla de la que sale el umbral cuando `condicion` es por horas cátedra."""

    @model_validator(mode="after")
    def _coherencia(self) -> Self:
        if self.estado is EstadoRegla.NO_VERIFICADA and not self.regla_id:
            raise ValueError(
                "una entrada de catálogo no_verificada debe apuntar a la `regla_id` que la "
                "condiciona, para que el informe pueda explicar el impacto"
            )
        if self.indice_escalafonario is None and not self.regla_indice:
            raise ValueError(
                "una entrada sin `indice_escalafonario` debe apuntar a la `regla_indice` "
                "que lo discute, para que el informe pueda explicar por qué no puede "
                "comparar jerarquías"
            )
        if self.indice_escalafonario is not None and self.indice_escalafonario <= 0:
            raise ValueError("`indice_escalafonario` debe ser mayor que cero")
        if self.condicion is CondicionAlFrente.POR_HORAS_CATEDRA:
            if not self.regla_umbral:
                raise ValueError(
                    "una condición por horas cátedra debe declarar `regla_umbral`: el umbral "
                    "es un valor normativo y no puede quedar escrito en el código (Principio I)"
                )
            if self.al_frente_de_alumnos is not None:
                raise ValueError(
                    "una condición por horas cátedra no es booleana: "
                    "`al_frente_de_alumnos` debe quedar en null"
                )
        return self

    @property
    def condiciona_resultado(self) -> bool:
        """Una entrada verificada también condiciona si una regla la discute."""
        return self.estado is EstadoRegla.NO_VERIFICADA or self.regla_id is not None


class CatalogoDeCargos(BaseModel):
    """Fuente de verdad de «al frente de alumnos» y de la naturaleza (FR-002a)."""

    model_config = MODELO

    version: str = "v1"
    entradas: tuple[EntradaCatalogo, ...]

    def buscar(self, cargo: str) -> EntradaCatalogo | None:
        """`None` significa indeterminado, no «no está al frente de alumnos»."""
        for entrada in self.entradas:
            if entrada.cargo == cargo:
                return entrada
        return None


class ConjuntoDeReglas(BaseModel):
    """La colección versionada que el informe declara (FR-009)."""

    model_config = MODELO

    version: str = Field(min_length=1)
    reglas: tuple[Regla, ...]
    catalogo_cargos: CatalogoDeCargos

    def por_id(self, regla_id: str) -> Regla | None:
        for regla in self.reglas:
            if regla.id == regla_id:
                return regla
        return None

    @property
    def no_verificadas(self) -> tuple[Regla, ...]:
        return tuple(r for r in self.reglas if r.condiciona_resultado)
