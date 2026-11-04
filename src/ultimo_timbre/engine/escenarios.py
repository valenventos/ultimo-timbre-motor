# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Derivación de los escenarios de cese (T162 a T166, FR-035 a FR-037).

Responde «¿me conviene esperar?», que es el valor diferencial del motor. A las
fechas que el usuario provee se agregan tres derivadas:

* la **habilitación** del derecho;
* el **excedente de 3 años** y el de **5**, contados desde que se cumplen todas
  las condiciones del inciso `[Res. IPS 995/2021, Anexo, punto 2.1.a]`.

## Comparabilidad

Los escenarios se emiten **en orden cronológico** y se valúan todos con la
**misma grilla** (FR-036a). Eso último no es un detalle: si uno se valuara con
la grilla de 2030 y otro con la de 2033, la diferencia mezclaría el aumento del
porcentaje con el aumento salarial, y el profesional compararía dos cosas
distintas creyendo que compara una. Con una sola grilla, la diferencia queda
explicada solo por el porcentaje y por la antigüedad.

## Cuando la fecha ya pasó, o todavía no llegó

Si el derecho no está habilitado a la fecha que el usuario pregunta, el
escenario sale sin monto y con el faltante (FR-035), y la habilitación se
deriva igual desde la **fecha estimada** (FR-016). Así el informe trae las dos
respuestas: la que preguntó y la que le conviene.

Si el derecho no nace nunca —historia cerrada que no alcanza ningún inciso— no
hay habilitación de la que derivar nada y queda solo lo provisto.
"""

from __future__ import annotations

import datetime as dt

from ultimo_timbre.engine import porcentaje as pct
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import TipoEscenario
from ultimo_timbre.models.informe import Elegibilidad
from ultimo_timbre.models.normativa import ConjuntoDeReglas

__all__ = ["derivar", "fecha_de_habilitacion"]

# Qué etiqueta gana cuando dos fechas coinciden. La más específica: saber que
# una fecha es la del excedente de 3 años dice más que saber que el usuario la
# escribió. Menor número, mayor prioridad.
PRIORIDAD: dict[TipoEscenario, int] = {
    TipoEscenario.HABILITACION: 0,
    TipoEscenario.EXCEDENTE_3: 1,
    TipoEscenario.EXCEDENTE_5: 2,
    TipoEscenario.PROVISTA: 3,
}

# Los excedentes que el modelo sabe nombrar. Un escalón de otra cantidad de
# años quedaría sin `TipoEscenario`, así que no se deriva: antes que emitirlo
# con una etiqueta que miente, no se emite.
TIPO_POR_EXCEDENTE: dict[int, TipoEscenario] = {
    3: TipoEscenario.EXCEDENTE_3,
    5: TipoEscenario.EXCEDENTE_5,
}


def fecha_de_habilitacion(resultado: Elegibilidad) -> tuple[dt.date, str] | None:
    """La fecha en que nace el derecho y por qué inciso, o `None`.

    Dos caminos, y el segundo es el que vuelve útil el caso del cese temprano:

    1. si **ya** hay derecho, la fecha del inciso más favorable;
    2. si todavía no, la **estimación** más temprana entre los incisos (FR-016).
       El informe puede así comparar «me voy ahora» contra «espero a tener
       derecho», que es exactamente la pregunta de la US5.

    `None` cuando el derecho no nace nunca: una historia cerrada que no alcanza
    ningún inciso no tiene habilitación de la que derivar excedentes.
    """
    favorable = resultado.inciso_mas_favorable
    if favorable is not None:
        elegido = next(i for i in resultado.incisos if i.inciso == favorable)
        if elegido.habilitado_desde is not None:
            return elegido.habilitado_desde, elegido.inciso

    estimadas = [
        (i.estimado_para, i.inciso) for i in resultado.incisos if i.estimado_para is not None
    ]
    return min(estimadas) if estimadas else None


def _agregar(candidatos: dict[dt.date, TipoEscenario], fecha: dt.date, tipo: TipoEscenario) -> None:
    """Registra una fecha, conservando la etiqueta más específica si ya estaba."""
    previo = candidatos.get(fecha)
    if previo is None or PRIORIDAD[tipo] < PRIORIDAD[previo]:
        candidatos[fecha] = tipo


def derivar(
    caso: Caso,
    resultado: Elegibilidad,
    *,
    reglas: ConjuntoDeReglas,
) -> tuple[tuple[dt.date, TipoEscenario], ...]:
    """Las fechas a evaluar, deduplicadas y en orden cronológico (FR-036, FR-037).

    El orden es estable y no depende de cómo el usuario escribió las fechas de
    cese: es el invariante I3 aplicado a la comparación.
    """
    candidatos: dict[dt.date, TipoEscenario] = {}
    for cese in caso.fechas_cese:
        _agregar(candidatos, cese, TipoEscenario.PROVISTA)

    habilitacion = fecha_de_habilitacion(resultado)
    if habilitacion is not None:
        fecha, inciso = habilitacion
        _agregar(candidatos, fecha, TipoEscenario.HABILITACION)

        # Los años de excedente salen de las reglas del inciso, no del código.
        anios = [n for n, _ in pct.escalones(inciso, reglas)]
        for n, cuando in pct.fechas_de_excedente(fecha, anios).items():
            tipo = TIPO_POR_EXCEDENTE.get(n)
            if tipo is not None:
                _agregar(candidatos, cuando, tipo)

    return tuple(sorted(candidatos.items()))
