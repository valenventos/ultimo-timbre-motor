# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Derivación de la condición del cargo (T037, FR-002a, FR-002b, FR-002d).

Ni «al frente de alumnos» ni la naturaleza del servicio son datos de entrada:
son propiedades del **cargo**, y se derivan del catálogo versionado.

Tres reglas que el motor no rompe:

* un cargo **ausente** del catálogo no se asume: queda indeterminado, se
  advierte `cargo_fuera_de_catalogo` y el resultado sale provisional — pero el
  caso **no** se invalida, porque el resto de la historia sí es computable
  (Principio IV);
* un **override** del usuario se respeta y deja rastro de dato manual, que
  además condiciona el monto (FR-002b);
* la condición **no siempre es booleana**. El art. 24 inc. b asimila a los
  profesores que reúnen veinte horas cátedra, y eso es un umbral sobre el total
  de horas **simultáneas**, no una propiedad del cargo tomado de a uno. El
  umbral sale de la regla, nunca del código (Principio I).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from ultimo_timbre.models.caso import PeriodoDeServicio
from ultimo_timbre.models.enums import (
    CodigoAdvertencia,
    CondicionAlFrente,
    NaturalezaServicio,
    OrigenDato,
)
from ultimo_timbre.models.normativa import CatalogoDeCargos, Norma

__all__ = ["CondicionDerivada", "derivar"]


class CondicionDerivada(BaseModel):
    """El resultado de resolver un período contra el catálogo."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    al_frente_de_alumnos: bool | None
    """`None` = indeterminado. No equivale a `False`."""
    naturaleza: NaturalezaServicio | None
    origen: OrigenDato
    en_catalogo: bool
    difiere_del_catalogo: bool = False
    condiciona_resultado: bool = False
    norma: Norma | None = None
    regla_id: str | None = None
    condicion: CondicionAlFrente = CondicionAlFrente.DIRECTA
    requiere_umbral_horas_catedra: bool = False
    """El motor debe resolverlo con el total de horas simultáneas y el umbral."""
    umbral_horas_catedra: int | None = None
    horas_catedra_evaluadas: Decimal | None = None
    """La carga del período en horas cátedra, con los módulos ya convertidos.

    `Decimal` y no `int`: trece módulos son 19,5 horas cátedra, y redondear
    acá decidiría el umbral en lugar de evaluarlo.
    """
    advertencias: tuple[CodigoAdvertencia, ...] = ()


def _carga_declarada(periodo: PeriodoDeServicio) -> Decimal | None:
    """La carga del propio período, sin convertir módulos.

    Es el camino de repliegue para cuando el llamador no calculó las horas
    simultáneas. Si el período declara **módulos**, devuelve `None`: convertir
    acá exigiría un factor que solo está en la regla, y suponer uno sería poner
    un valor normativo en el código (Principio I).
    """
    if periodo.modulos is not None:
        return None
    return Decimal(periodo.horas_catedra) if periodo.horas_catedra is not None else None


def derivar(
    catalogo: CatalogoDeCargos,
    periodo: PeriodoDeServicio,
    *,
    horas_catedra_simultaneas: Decimal | None = None,
    umbral_horas_catedra: int | None = None,
) -> CondicionDerivada:
    """Resuelve la condición y la naturaleza de un período.

    `horas_catedra_simultaneas` es el total de horas del período **más** las de
    los períodos que se le superponen; lo calcula el motor, porque es una
    propiedad de la historia y no de un período suelto. `umbral_horas_catedra`
    sale de la regla que el catálogo indica en `regla_umbral`.

    Si la entrada necesita el umbral y el llamador no lo provee, la condición
    queda indeterminada y el resultado condicionado: el motor nunca completa un
    umbral normativo por su cuenta.
    """
    entrada = catalogo.buscar(periodo.cargo)
    advertencias: list[CodigoAdvertencia] = []

    hay_override = periodo.al_frente_override is not None or periodo.naturaleza_override is not None

    if entrada is None:
        # No se adivina: indeterminado y se advierte. El caso sigue siendo válido.
        advertencias.append(CodigoAdvertencia.CARGO_FUERA_DE_CATALOGO)
        if hay_override:
            advertencias.append(CodigoAdvertencia.DATO_CORREGIDO_A_MANO)
        return CondicionDerivada(
            al_frente_de_alumnos=periodo.al_frente_override,
            naturaleza=periodo.naturaleza_override,
            origen=OrigenDato.MANUAL if hay_override else OrigenDato.DERIVADO,
            en_catalogo=False,
            condiciona_resultado=True,
            advertencias=tuple(advertencias),
        )

    # --- condición del catálogo, antes de aplicar el override ---
    requiere_umbral = False
    horas_evaluadas: Decimal | None = None
    if entrada.condicion is CondicionAlFrente.POR_HORAS_CATEDRA:
        horas_evaluadas = (
            horas_catedra_simultaneas
            if horas_catedra_simultaneas is not None
            else _carga_declarada(periodo)
        )
        if umbral_horas_catedra is None or horas_evaluadas is None:
            del_catalogo: bool | None = None
            requiere_umbral = True
        else:
            del_catalogo = horas_evaluadas >= umbral_horas_catedra
    else:
        del_catalogo = entrada.al_frente_de_alumnos

    al_frente = (
        periodo.al_frente_override if periodo.al_frente_override is not None else del_catalogo
    )
    naturaleza = (
        periodo.naturaleza_override
        if periodo.naturaleza_override is not None
        else entrada.naturaleza
    )

    difiere = (
        periodo.al_frente_override is not None and periodo.al_frente_override != del_catalogo
    ) or (
        periodo.naturaleza_override is not None
        and periodo.naturaleza_override is not entrada.naturaleza
    )

    if hay_override:
        advertencias.append(CodigoAdvertencia.DATO_CORREGIDO_A_MANO)
    if entrada.condiciona_resultado:
        advertencias.append(CodigoAdvertencia.REGLA_NO_VERIFICADA)

    return CondicionDerivada(
        al_frente_de_alumnos=al_frente,
        naturaleza=naturaleza,
        origen=OrigenDato.MANUAL if hay_override else OrigenDato.DERIVADO,
        en_catalogo=True,
        difiere_del_catalogo=difiere,
        condiciona_resultado=entrada.condiciona_resultado or hay_override or requiere_umbral,
        norma=entrada.norma,
        regla_id=entrada.regla_id,
        condicion=entrada.condicion,
        requiere_umbral_horas_catedra=requiere_umbral,
        umbral_horas_catedra=umbral_horas_catedra,
        horas_catedra_evaluadas=horas_evaluadas,
        advertencias=tuple(advertencias),
    )
