# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Enumeraciones del dominio (T028).

Todos son `StrEnum`: el valor serializado es exactamente el que aparece en los
schemas de contrato y en los YAML normativos, así que no hay traducción entre
capas que pueda desincronizarse.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "CajaAportes",
    "ClaseCondicionante",
    "ClasificacionSuperposicion",
    "CodigoAdvertencia",
    "CondicionAlFrente",
    "EstadoRegla",
    "EstadoResultado",
    "Formato",
    "NaturalezaServicio",
    "OrigenDato",
    "SentidoImpacto",
    "SituacionRevista",
    "TipoEscenario",
    "TipoEstablecimiento",
    "TipoFuente",
    "TipoLicencia",
    "ViaCargoBase",
]


class SituacionRevista(StrEnum):
    """Si incide o no en la elección del cargo base es la Cuestión abierta #5."""

    TITULAR = "titular"
    PROVISIONAL = "provisional"
    SUPLENTE = "suplente"


class TipoLicencia(StrEnum):
    CON_GOCE = "con_goce"
    SIN_GOCE = "sin_goce"


class TipoEstablecimiento(StrEnum):
    ESTATAL_DGCYE = "estatal_dgcye"
    PRIVADO = "privado"
    OTRA_JURISDICCION = "otra_jurisdiccion"


class CajaAportes(StrEnum):
    """Se declara por período: depende de la relación de empleo, no del cargo."""

    IPS = "ips"
    ANSES = "anses"
    OTRA_CAJA = "otra_caja"


class NaturalezaServicio(StrEnum):
    DOCENTE = "docente"
    NO_DOCENTE = "no_docente"


class ClasificacionSuperposicion(StrEnum):
    """FR-004. Las tres categorías son excluyentes."""

    SIMULTANEIDAD_COMPUTABLE_ART47 = "simultaneidad_computable_art47"
    SIMULTANEIDAD_NO_COMPUTABLE = "simultaneidad_no_computable"
    POSIBLE_ERROR_CARGA = "posible_error_carga"


class CondicionAlFrente(StrEnum):
    """Cómo se resuelve la condición «al frente de alumnos» de un cargo.

    No todos los cargos la tienen como booleano. El art. 24 inc. b asimila a los
    profesores que reúnen **veinte horas cátedra**, y eso es un umbral sobre el
    total de horas simultáneas, no una propiedad del cargo tomado de a uno.
    """

    DIRECTA = "directa"
    POR_HORAS_CATEDRA = "por_horas_catedra"


class EstadoRegla(StrEnum):
    VERIFICADO = "verificado"
    NO_VERIFICADA = "no_verificada"


class EstadoResultado(StrEnum):
    DEFINITIVO = "definitivo"
    PROVISIONAL = "provisional"


class SentidoImpacto(StrEnum):
    AL_ALZA = "al_alza"
    A_LA_BAJA = "a_la_baja"
    INDETERMINADO = "indeterminado"


class ClaseCondicionante(StrEnum):
    """FR-046b: lo que impide que un monto sea definitivo es normativo o del caso."""

    REGLA_NO_VERIFICADA = "regla_no_verificada"
    SITUACION_DEL_CASO = "situacion_del_caso"


class TipoFuente(StrEnum):
    """Principio I: la letra de la ley no se mezcla con la interpretación."""

    LETRA_LEY = "letra_ley"
    INTERPRETACION = "interpretacion"


class OrigenDato(StrEnum):
    """FR-039: todo dato del informe declara de dónde salió."""

    DERIVADO = "derivado"
    MANUAL = "manual"


class ViaCargoBase(StrEnum):
    CONSECUTIVOS_36 = "36_consecutivos"
    ALTERNADOS_60 = "60_alternados"
    CARGO_INFERIOR = "cargo_inferior"


class TipoEscenario(StrEnum):
    PROVISTA = "provista"
    HABILITACION = "habilitacion"
    EXCEDENTE_3 = "excedente_3"
    EXCEDENTE_5 = "excedente_5"


class Formato(StrEnum):
    JSON = "json"
    TEXTO = "texto"
    YAML = "yaml"


class CodigoAdvertencia(StrEnum):
    """Identificadores anónimos: son lo único que puede cruzar a un log (FR-054)."""

    DATO_FALTANTE = "dato_faltante"
    SIMULTANEIDAD_COMPUTABLE_ART47 = "simultaneidad_computable_art47"
    SIMULTANEIDAD_NO_COMPUTABLE = "simultaneidad_no_computable"
    POSIBLE_ERROR_CARGA = "posible_error_carga"
    SERVICIOS_NO_DOCENTES_SIN_COMPUTAR = "servicios_no_docentes_sin_computar"
    PRORRATEO_PODRIA_COMPLETAR_REQUISITOS = "prorrateo_podria_completar_requisitos"
    FUERA_DE_ALCANCE_OTRA_CAJA = "fuera_de_alcance_otra_caja"
    FUERA_DE_ALCANCE_PRIVADO = "fuera_de_alcance_privado"
    FUERA_DE_ALCANCE_PROMEDIO_36 = "fuera_de_alcance_promedio_36"
    REGLA_NO_VERIFICADA = "regla_no_verificada"
    GRILLA_AUSENTE = "grilla_ausente"
    CARGO_FUERA_DE_CATALOGO = "cargo_fuera_de_catalogo"
    EMPATE_JERARQUIA = "empate_jerarquia"
    LECTURA_LITERAL_EXCEDENTE = "lectura_literal_excedente"
    MONTOS_A_VALORES_DE_HOY = "montos_a_valores_de_hoy"
    HABER_MOVIL_ART_50 = "haber_movil_art_50"
    SUPUESTO_CONTINUIDAD = "supuesto_continuidad"
    DATO_CORREGIDO_A_MANO = "dato_corregido_a_mano"
    PERIODO_RECORTADO_A_CESE = "periodo_recortado_a_cese"
