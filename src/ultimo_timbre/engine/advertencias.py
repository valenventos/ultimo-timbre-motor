# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Emisión de advertencias (T100, FR-041).

Un solo lugar decide **qué código bloquea el cálculo** y con qué norma se
informa cada situación. Repartir esos dos datos por el motor es cómo se llega a
que una advertencia bloqueante quede sin bloquear, que es justo lo que el
invariante I7 existe para impedir.

Los mensajes nombran el período por su `idx` anónimo y nunca un dato del caso
(FR-054).
"""

from __future__ import annotations

from ultimo_timbre.engine import condicionantes as cond
from ultimo_timbre.models.enums import CodigoAdvertencia, SentidoImpacto
from ultimo_timbre.models.informe import Advertencia
from ultimo_timbre.models.normativa import ConjuntoDeReglas, Norma

__all__ = ["BLOQUEAN", "POR_PERIODO", "construir", "norma_de"]

# Qué situaciones impiden emitir un haber. Son las que dejan el cómputo
# incompleto de un modo que ningún monto puede salvar: tramos que el motor no
# puede computar (FR-044, FR-045) y el promedio del art. 41 (FR-020b).
#
# La simultaneidad **no** está acá a propósito: los servicios sí se computan
# sobre la unión; lo que queda sin calcular es el incremento (FR-043).
BLOQUEAN: frozenset[CodigoAdvertencia] = frozenset(
    {
        CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA,
        CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO,
        CodigoAdvertencia.FUERA_DE_ALCANCE_PROMEDIO_36,
    }
)

# Qué advertencias hablan de **un** período, y por lo tanto tienen que nombrarlo
# con su `periodo_idx` anónimo (FR-054).
#
# El resto habla de la historia entera —que ningún cargo alcance los plazos del
# art. 41, que el criterio de jerarquía esté sin verificar, que la lectura del
# excedente sea discutible— y no tiene un período al que apuntar. Exigirles uno
# obligaría a elegir uno arbitrario, que es peor que no poner ninguno: el
# profesional lo leería como que el problema está en ese período.
#
# `REGLA_NO_VERIFICADA` no está en ninguna de las dos listas a propósito: se
# emite con período cuando la regla condiciona un cargo concreto y sin período
# cuando condiciona el cómputo entero.
POR_PERIODO: frozenset[CodigoAdvertencia] = frozenset(
    {
        CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA,
        CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO,
        CodigoAdvertencia.CARGO_FUERA_DE_CATALOGO,
        CodigoAdvertencia.DATO_CORREGIDO_A_MANO,
        CodigoAdvertencia.PERIODO_RECORTADO_A_CESE,
        CodigoAdvertencia.SUPUESTO_CONTINUIDAD,
        CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47,
        CodigoAdvertencia.SIMULTANEIDAD_NO_COMPUTABLE,
        CodigoAdvertencia.POSIBLE_ERROR_CARGA,
    }
)

# La regla cuya norma respalda cada advertencia. Principio I: una advertencia
# sin fuente es una opinión del motor.
REGLA_DE: dict[CodigoAdvertencia, str] = {
    CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA: "alcance.arts66_67.otras_cajas",
    CodigoAdvertencia.FUERA_DE_ALCANCE_PROMEDIO_36: "haber.art41.promedio_36",
    CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47: "simultaneidad.art47.minimo_continuo",
    CodigoAdvertencia.SIMULTANEIDAD_NO_COMPUTABLE: "simultaneidad.art47.minimo_continuo",
    CodigoAdvertencia.EMPATE_JERARQUIA: "jerarquia.criterio_comparacion",
    CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS: "requisitos.art27.prorrateo",
    CodigoAdvertencia.SERVICIOS_NO_DOCENTES_SIN_COMPUTAR: "requisitos.art27.prorrateo",
    CodigoAdvertencia.HABER_MOVIL_ART_50: "movilidad.art50",
    CodigoAdvertencia.LECTURA_LITERAL_EXCEDENTE: "excedente.lectura_literal",
}

# El establecimiento privado queda fuera por el Alcance de la v1, no por un
# artículo que lo excluya: la norma que se cita es la del inciso que enumera a
# quiénes alcanza el régimen docente.
NORMA_PRIVADO = Norma(
    texto="DL 9650/80, art. 24 inc. b (régimen docente de establecimientos "
    "estatales de la DGCyE) — fuera del Alcance de la v1",
    ley="DL 9650/80",
    articulo="24",
    inciso="b",
)


def norma_de(codigo: CodigoAdvertencia, reglas: ConjuntoDeReglas) -> Norma | None:
    """La norma que respalda una advertencia, tomada de la regla."""
    if codigo is CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO:
        return NORMA_PRIVADO
    regla_id = REGLA_DE.get(codigo)
    if regla_id is None:
        return None
    regla = reglas.por_id(regla_id)
    return regla.norma if regla is not None else None


def construir(
    codigo: CodigoAdvertencia,
    mensaje: str,
    *,
    reglas: ConjuntoDeReglas,
    periodo_idx: int | None = None,
    sentido_impacto: SentidoImpacto | None = None,
) -> Advertencia:
    """Arma una advertencia con su norma y su carácter bloqueante.

    `bloquea_calculo` no se pasa como argumento a propósito: lo decide la tabla
    `BLOQUEAN`, para que no haya dos respuestas posibles a la misma pregunta.
    """
    return Advertencia(
        codigo=codigo,
        mensaje=mensaje,
        norma=norma_de(codigo, reglas),
        sentido_impacto=(
            sentido_impacto if sentido_impacto is not None else cond.SENTIDO.get(codigo)
        ),
        bloquea_calculo=codigo in BLOQUEAN,
        periodo_idx=periodo_idx,
    )
