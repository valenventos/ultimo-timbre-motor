# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El motor de cálculo (T064).

`calcular` **no hace I/O, no abre sockets y no consulta el reloj**: recibe el
caso y las reglas ya cargadas, y la fecha de cálculo viene dentro del caso
(FR-001a, FR-051). Eso es lo que hace que la equivalencia entre la CLI y la
librería sea estructural y no una coincidencia.

`grilla=None` es válido y es lo que necesita la US1: produce un informe con
elegibilidad y sin montos.
"""

from __future__ import annotations

import datetime as dt

from ultimo_timbre.engine import calendario, elegibilidad
from ultimo_timbre.engine.desglose import Trazador
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import EstadoResultado, TipoEscenario
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Elegibilidad, Escenario, Informe
from ultimo_timbre.models.normativa import ConjuntoDeReglas

__all__ = ["calcular", "calendario", "elegibilidad"]

AVISO_ESTIMACION = (
    "Este informe es una estimación orientativa. No reemplaza el cálculo oficial "
    "del IPS ni el asesoramiento profesional."
)
AVISO_MOVILIDAD = (
    "El haber es móvil: se actualiza por correlación con el cargo en actividad "
    "(DL 9650/80, art. 50). Este motor no proyecta esa movilidad."
)


def calcular(
    caso: Caso,
    *,
    reglas: ConjuntoDeReglas,
    grilla: GrillaSalarial | None = None,
) -> Informe:
    """Produce el informe de un caso.

    Sin grilla, el informe trae elegibilidad, desglose, procedencias y
    advertencias, y ningún escenario lleva haber: el monto llega con la US4.
    """
    traza = Trazador()

    # La elegibilidad se evalúa a la primera fecha de cese; las demás se
    # comparan en los escenarios. Las fechas vienen ordenadas al normalizar.
    cese_principal = caso.fechas_cese[0]
    resultado = elegibilidad.evaluar(caso, cese_principal, reglas=reglas, traza=traza)

    escenarios = tuple(
        _escenario(cese, resultado if cese == cese_principal else None, caso, reglas)
        for cese in caso.fechas_cese
    )

    return Informe(
        fecha_de_calculo=caso.fecha_de_calculo,
        elegibilidad=resultado,
        escenarios=escenarios,
        desglose=traza.pasos,
        procedencias=traza.procedencias,
        advertencias=traza.advertencias,
        condicionantes=traza.condicionantes,
        version_reglas=reglas.version,
        version_grilla=grilla.version if grilla is not None else None,
        aviso_estimacion=AVISO_ESTIMACION,
        aviso_movilidad=AVISO_MOVILIDAD,
        cargo_base=None,
    )


def _escenario(
    cese: dt.date,
    ya_evaluada: Elegibilidad | None,
    caso: Caso,
    reglas: ConjuntoDeReglas,
) -> Escenario:
    """Un escenario de la US1: hay derecho o no, sin monto.

    El porcentaje y el haber llegan con la US3 y la US4; los escenarios
    derivados —habilitación y excedentes de 3 y 5 años— con la US5.

    Para las fechas de cese distintas de la principal se reevalúa con un
    trazador descartable: el desglose del informe corresponde a la fecha
    principal, y duplicar sus pasos por cada cese lo volvería ilegible.
    """
    resultado = (
        ya_evaluada
        if ya_evaluada is not None
        else elegibilidad.evaluar(caso, cese, reglas=reglas, traza=Trazador())
    )
    inciso = resultado.inciso_mas_favorable
    hay_derecho = inciso is not None and resultado.minimo_22_anios.cumple

    return Escenario(
        fecha_cese=cese,
        tipo=TipoEscenario.PROVISTA,
        hay_derecho=hay_derecho,
        inciso=inciso if hay_derecho else None,
    )


def estado_de(informe: Informe) -> EstadoResultado:
    """Atajo legible para los consumidores (FR-046c)."""
    return informe.estado_general
