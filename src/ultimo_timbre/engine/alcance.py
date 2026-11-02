# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Detección de los límites del motor (T097, T098, T099).

El Principio X pide que lo fuera de alcance se **detecte y se informe**, nunca
se aproxime. Y el Principio IV pide que, aun así, el informe entregue el
análisis parcial que sí se sostiene: negar el informe entero le quita al
profesional información que el motor ya tenía.

Este módulo resuelve las tres detecciones de la US2:

* **superposiciones** en tres categorías excluyentes (FR-004);
* **servicios fuera de alcance**: otra caja (FR-044), gestión privada (FR-045) y
  el promedio de 36 meses del art. 41 (FR-020b);
* **servicios no docentes** y la advertencia condicional de prorrateo cuando los
  docentes no alcanzan ningún inciso (FR-015, FR-015a).
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from ultimo_timbre.engine import advertencias as adv
from ultimo_timbre.engine import condicionantes as cond
from ultimo_timbre.engine.desglose import Trazador
from ultimo_timbre.models.caso import Caso, HistoriaDeServicios, Superposicion
from ultimo_timbre.models.enums import (
    CajaAportes,
    CodigoAdvertencia,
    NaturalezaServicio,
)
from ultimo_timbre.models.enums import (
    ClasificacionSuperposicion as Clase,
)
from ultimo_timbre.models.normativa import ConjuntoDeReglas
from ultimo_timbre.rules import catalogo as cat

__all__ = ["Deteccion", "clasificar_superposiciones", "detectar"]

REGLA_ART47 = "simultaneidad.art47.minimo_continuo"


class Deteccion(BaseModel):
    """Lo que el análisis de alcance encontró."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    idx_en_alcance: frozenset[int]
    idx_fuera_de_alcance: frozenset[int]
    idx_no_docentes: frozenset[int]
    superposiciones: tuple[Superposicion, ...]
    hay_bloqueo: bool


def _minimo_art47(reglas: ConjuntoDeReglas) -> int:
    """Los 3 años continuos del art. 47, tomados de la regla (Principio I)."""
    regla = reglas.por_id(REGLA_ART47)
    if regla is None or not regla.valor:  # pragma: no cover - lo cubre el test de reglas
        return 0
    valor = regla.valor.get("anios_continuos")
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else 0


def clasificar_superposiciones(
    historia: HistoriaDeServicios,
    cese: dt.date,
    *,
    reglas: ConjuntoDeReglas,
    cargo_base: str | None = None,
) -> tuple[Superposicion, ...]:
    """Reclasifica las superposiciones detectadas por el modelo (FR-004).

    El modelo decide lo estructural —mismo cargo y mismo establecimiento es
    carga duplicada— porque no necesita nada más. Acá se resuelve la parte que
    sí necesita las reglas: si el solapamiento alcanza el mínimo de 3 años
    continuos del art. 47.

    `cargo_base` es el segundo requisito de FR-004. Mientras no exista —hasta la
    US3— la clasificación se apoya solo en la duración, que es la mitad
    decidible: promover de más haría que el informe advierta un impacto que
    después no se confirma, y eso entrena al profesional a ignorar la
    advertencia.
    """
    minimo = _minimo_art47(reglas)
    salida: list[Superposicion] = []

    for cruda in historia.superposiciones:
        # Un solapamiento posterior al cese no existe para este cálculo, y uno
        # que lo cruza se recorta: el cómputo cierra en el cese (FR-018).
        if cruda.desde > cese:
            continue
        sup = cruda
        if cruda.hasta > cese:
            sup = cruda.model_copy(
                update={
                    "hasta": cese,
                    "anios_continuos": (cese - cruda.desde).days // 365,
                }
            )

        if sup.clasificacion is Clase.POSIBLE_ERROR_CARGA:
            # el mismo puesto duplicado no es simultaneidad, sea cual sea su duración
            salida.append(sup)
            continue

        alcanza_duracion = sup.anios_continuos >= minimo
        alcanza_cargo_base = cargo_base is None or any(
            p.cargo == cargo_base for p in historia.periodos if p.idx in sup.periodos
        )
        computable = alcanza_duracion and alcanza_cargo_base
        salida.append(
            sup.model_copy(
                update={
                    "clasificacion": (
                        Clase.SIMULTANEIDAD_COMPUTABLE_ART47
                        if computable
                        else Clase.SIMULTANEIDAD_NO_COMPUTABLE
                    )
                }
            )
        )
    return tuple(salida)


def _detectar_fuera_de_alcance(
    caso: Caso, reglas: ConjuntoDeReglas, traza: Trazador
) -> tuple[frozenset[int], frozenset[int], bool]:
    """Períodos que el motor no puede computar (FR-044, FR-045)."""
    en_alcance: set[int] = set()
    fuera: set[int] = set()
    hay_bloqueo = False

    for p in caso.historia.periodos:
        if p.caja_aportes is not CajaAportes.IPS:
            fuera.add(p.idx)
            hay_bloqueo = True
            traza.agregar_advertencia(
                adv.construir(
                    CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA,
                    f"el período {p.idx} tiene aportes a otra caja y no se computa. "
                    "Por el art. 67 la caja otorgante es la de mayor tiempo con "
                    "aportes: computar esos servicios podría convertir a la otra "
                    "caja en otorgante, con otro régimen, otros requisitos y otro "
                    "haber. La reciprocidad está fuera del Alcance de la v1",
                    reglas=reglas,
                    periodo_idx=p.idx,
                )
            )
            traza.agregar_condicionante(
                cond.de_situacion(CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA)
            )
        elif p.establecimiento.fuera_de_alcance:
            fuera.add(p.idx)
            hay_bloqueo = True
            traza.agregar_advertencia(
                adv.construir(
                    CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO,
                    f"el período {p.idx} corresponde a un establecimiento que no es "
                    "estatal de la DGCyE y no se computa",
                    reglas=reglas,
                    periodo_idx=p.idx,
                )
            )
            traza.agregar_condicionante(
                cond.de_situacion(CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO)
            )
        else:
            en_alcance.add(p.idx)

    return frozenset(en_alcance), frozenset(fuera), hay_bloqueo


def _detectar_no_docentes(
    caso: Caso,
    en_alcance: frozenset[int],
    reglas: ConjuntoDeReglas,
    traza: Trazador,
) -> frozenset[int]:
    """Servicios no docentes aportados al IPS (FR-015).

    Se detectan y se advierten; el prorrateo del art. 27 no se computa. La
    advertencia de que **podría** completar los requisitos se emite después, una
    vez que se sabe si los docentes alcanzaron algún inciso (FR-015a).
    """
    no_docentes: set[int] = set()
    for p in caso.historia.periodos:
        if p.idx not in en_alcance:
            continue
        derivada = cat.derivar(reglas.catalogo_cargos, p)
        if derivada.naturaleza is NaturalezaServicio.NO_DOCENTE:
            no_docentes.add(p.idx)

    if no_docentes:
        traza.agregar_advertencia(
            adv.construir(
                CodigoAdvertencia.SERVICIOS_NO_DOCENTES_SIN_COMPUTAR,
                "hay servicios no docentes aportados al IPS que no se computan: "
                f"períodos {sorted(no_docentes)}",
                reglas=reglas,
            )
        )
    return frozenset(no_docentes)


def advertir_prorrateo_posible(
    no_docentes: frozenset[int],
    reglas: ConjuntoDeReglas,
    traza: Trazador,
) -> None:
    """FR-015a: el aviso que vuelve honesto un «no cumple».

    Decir que no alcanza, teniendo servicios no docentes a la vista y sabiendo
    que el prorrateo del art. 27 existe, sería una negativa engañosa: el
    profesional tomaría una decisión de cese irreversible sobre un resultado que
    podría revertirse por una vía que el motor conoce y no aplicó.
    """
    if not no_docentes:
        return
    traza.agregar_advertencia(
        adv.construir(
            CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS,
            "los servicios no docentes podrían completar los requisitos mediante "
            "el prorrateo del art. 27, que está fuera del Alcance de la v1: el "
            "resultado de elegibilidad no es definitivo",
            reglas=reglas,
        )
    )
    traza.agregar_condicionante(
        cond.de_situacion(CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS)
    )


def _detectar_overrides(caso: Caso, reglas: ConjuntoDeReglas, traza: Trazador) -> None:
    """Correcciones manuales de datos derivados del catálogo (FR-002b, FR-002d).

    Se registra **todo** override, con independencia de si el período entra al
    cómputo docente y de si difiere del catálogo: un cargo que no está en el
    catálogo no tiene con qué diferir, y aun así el dato lo puso el usuario y no
    el catálogo versionado. Que la corrección quede sin rastro sería justamente
    lo que FR-002b existe para impedir.
    """
    corregidos = [
        p.idx
        for p in caso.historia.periodos
        if p.al_frente_override is not None or p.naturaleza_override is not None
    ]
    if not corregidos:
        return
    for idx in corregidos:
        traza.agregar_advertencia(
            adv.construir(
                CodigoAdvertencia.DATO_CORREGIDO_A_MANO,
                f"la condición del período {idx} fue corregida a mano y no sale "
                "del catálogo versionado",
                reglas=reglas,
                periodo_idx=idx,
            )
        )
    traza.agregar_condicionante(cond.de_situacion(CodigoAdvertencia.DATO_CORREGIDO_A_MANO))


def detectar(
    caso: Caso,
    cese: dt.date,
    *,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    cargo_base: str | None = None,
) -> Deteccion:
    """Corre las tres detecciones y deja su rastro en la traza."""
    _detectar_overrides(caso, reglas, traza)
    en_alcance, fuera, hay_bloqueo = _detectar_fuera_de_alcance(caso, reglas, traza)
    no_docentes = _detectar_no_docentes(caso, en_alcance, reglas, traza)
    superposiciones = clasificar_superposiciones(
        caso.historia, cese, reglas=reglas, cargo_base=cargo_base
    )

    for sup in superposiciones:
        codigo = CodigoAdvertencia(sup.clasificacion.value)
        traza.agregar_advertencia(
            adv.construir(
                codigo,
                _mensaje_superposicion(sup),
                reglas=reglas,
                periodo_idx=sup.periodos[0],
            )
        )
        if sup.clasificacion is Clase.SIMULTANEIDAD_COMPUTABLE_ART47:
            traza.agregar_condicionante(
                cond.de_situacion(CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47)
            )

    # Los servicios no docentes se computan **fuera** del cómputo docente.
    return Deteccion(
        idx_en_alcance=frozenset(en_alcance - no_docentes),
        idx_fuera_de_alcance=fuera,
        idx_no_docentes=no_docentes,
        superposiciones=superposiciones,
        hay_bloqueo=hay_bloqueo,
    )


def _mensaje_superposicion(sup: Superposicion) -> str:
    uno, otro = sup.periodos
    tramo = f"{sup.desde.isoformat()} a {sup.hasta.isoformat()}"
    if sup.clasificacion is Clase.POSIBLE_ERROR_CARGA:
        return (
            f"los períodos {uno} y {otro} son el mismo cargo en el mismo "
            f"establecimiento y se superponen ({tramo}): confirmá si no es una "
            "carga duplicada"
        )
    if sup.clasificacion is Clase.SIMULTANEIDAD_COMPUTABLE_ART47:
        return (
            f"los períodos {uno} y {otro} se superponen {sup.anios_continuos} años "
            f"continuos ({tramo}): podría corresponder el incremento por cargos "
            "simultáneos, que no se calcula"
        )
    return (
        f"los períodos {uno} y {otro} se superponen ({tramo}) pero no reúnen las "
        "condiciones del art. 47: no hay impacto en el haber"
    )
