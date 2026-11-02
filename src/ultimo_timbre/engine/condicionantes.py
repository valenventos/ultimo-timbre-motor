# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Construcción de condicionantes (T101, FR-046a, FR-046b).

Un condicionante es lo que impide que un resultado sea definitivo, y son **dos
clases**:

* una **regla `NO_VERIFICADA`**, que trae su norma y su sentido de impacto;
* una **situación del caso** —grilla ausente, cargo fuera de catálogo,
  corrección manual, supuesto de continuidad—, que no tiene norma porque la
  incertidumbre no es normativa sino del caso.

Si solo se modelaran las reglas, esas cuatro situaciones tendrían que marcar un
resultado como provisional **sin poder explicar por qué**, que es exactamente
lo que FR-046b prohíbe.
"""

from __future__ import annotations

from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    CodigoAdvertencia,
    EstadoRegla,
    SentidoImpacto,
)
from ultimo_timbre.models.informe import Condicionante, Monto
from ultimo_timbre.models.normativa import ConjuntoDeReglas, Regla

__all__ = ["de_regla", "de_situacion", "del_monto", "propagar_a_monto"]

# --------------------------------------------------------------------------
# Condicionantes informativos
# --------------------------------------------------------------------------
# No toda duda condiciona el resultado. Un condicionante —de sensibilidad de la
# convención de conteo o de cualquier otro origen— que recae sobre un inciso
# que **no** es el más favorable es **informativo**: se informa en ese inciso,
# con su margen, y **no** vuelve provisional ni `Elegibilidad.estado` ni
# `estado_general`.
#
# La excepción, que sí condiciona, es que la duda pudiera cambiar:
#
# 1. **si hay derecho** —el inciso dudoso es el único que se cumple—, o
# 2. **cuál es el inciso más favorable** —y con él el artículo aplicable, el
#    porcentaje y el haber—.
#
# Por qué la regla existe: el art. 24 ofrece tres vías alternativas y el motor
# informa las tres. Si la duda sobre una vía que nadie va a usar marcara todo
# el informe como provisional, el caso holgado por el inc. b saldría igual de
# dudoso que el caso que está a tres días del umbral. La marca de provisional
# solo informa mientras distinga; aplicada a todo, no distingue nada y el
# profesional deja de mirarla —y entonces el resguardo de FR-046a, que la hace
# inseparable del monto, se vuelve ruido—.
#
# Esto **no** debilita el invariante I5 (`provisional` ⟺ `condicionantes` no
# vacío): el condicionante informativo no se registra, así que no hay marca sin
# explicación ni explicación sin marca. Lo que queda asentado es el `estado`
# del inciso y su `margen_dias`, que es dónde corresponde que esté.
#
# La implementa `engine.elegibilidad._sensibilidades_que_importan`, que mide la
# relevancia dando vuelta un inciso a la vez y volviendo a rankear.

# Las Cuestiones abiertas que condicionan **cualquier** haber, sin importar el
# caso: la escala de antigüedad (#1), qué conceptos integran la remuneración del
# cargo (#2) y la política de redondeo (#6).
REGLAS_DEL_MONTO = (
    "antiguedad.escala_y_tope",
    "remuneracion.conceptos_del_cargo",
    "redondeo.politica_ips",
)

# Qué falta verificar en cada situación del caso. Vive acá y no repartido por el
# motor para que el texto que lee el profesional sea uno solo.
QUE_FALTA: dict[CodigoAdvertencia, str] = {
    CodigoAdvertencia.GRILLA_AUSENTE: (
        "qué grilla salarial rige a la fecha de cese: la vigente no está cargada "
        "y el monto se valuó con otra"
    ),
    CodigoAdvertencia.CARGO_FUERA_DE_CATALOGO: (
        "la condición y la naturaleza del cargo: no figura en el catálogo "
        "versionado y el motor no las asume"
    ),
    CodigoAdvertencia.DATO_CORREGIDO_A_MANO: (
        "la corrección manual de un dato derivado del catálogo no está "
        "respaldada por el catálogo versionado"
    ),
    CodigoAdvertencia.SUPUESTO_CONTINUIDAD: (
        "que el desempeño continúe en el mismo cargo hasta la fecha de cese es "
        "un supuesto del motor, no un dato de la historia"
    ),
    CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47: (
        "el incremento por cargos simultáneos del art. 47 y la Res. IPS "
        "995/2021, que está fuera del Alcance de la v1 y no se calcula"
    ),
    CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS: (
        "si el prorrateo del art. 27 completaría los requisitos con los "
        "servicios no docentes, que está fuera del Alcance de la v1"
    ),
    CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA: (
        "cuál es la caja otorgante: por el art. 67 lo es la de mayor tiempo con "
        "aportes, de modo que computar los servicios de la otra caja podría "
        "desplazar el otorgamiento a esa caja, con otro régimen, otros "
        "requisitos y otro haber. La reciprocidad está fuera del Alcance de la v1"
    ),
    CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO: (
        "los servicios en establecimientos de gestión privada no se computan: "
        "están fuera del Alcance de la v1"
    ),
    CodigoAdvertencia.FUERA_DE_ALCANCE_PROMEDIO_36: (
        "el promedio de 36 meses del tercer párrafo del art. 41, que está fuera "
        "del Alcance de la v1"
    ),
}

SENTIDO: dict[CodigoAdvertencia, SentidoImpacto] = {
    # Si el prorrateo o la extensión alcanzaran, el resultado solo puede mejorar.
    CodigoAdvertencia.PRORRATEO_PODRIA_COMPLETAR_REQUISITOS: SentidoImpacto.AL_ALZA,
    # El incremento del art. 47 suma sobre el haber.
    CodigoAdvertencia.SIMULTANEIDAD_COMPUTABLE_ART47: SentidoImpacto.AL_ALZA,
    # Los servicios en gestión privada, de computarse, sumarían antigüedad
    # dentro de este mismo régimen.
    CodigoAdvertencia.FUERA_DE_ALCANCE_PRIVADO: SentidoImpacto.AL_ALZA,
    # Los aportes a otra caja son el caso que **no** es «al alza», y la
    # diferencia no es menor: computarlos no es sumar antigüedad a este cálculo.
    # Por el art. 67 la caja otorgante es la de mayor tiempo con aportes, de
    # modo que esos servicios podrían desplazar el otorgamiento a la otra caja,
    # con otro régimen, otros requisitos y otro haber —que bien puede ser menor
    # que el de este régimen—. Va explícito y no librado al valor por defecto
    # porque `None` acá significa «no mueve el resultado», que es otra cosa.
    CodigoAdvertencia.FUERA_DE_ALCANCE_OTRA_CAJA: SentidoImpacto.INDETERMINADO,
}


def de_regla(regla: Regla) -> Condicionante | None:
    """El condicionante de una regla `NO_VERIFICADA`, o `None` si está verificada."""
    if regla.estado is not EstadoRegla.NO_VERIFICADA:
        return None
    if regla.impacto_si_no_verificada is None:  # pragma: no cover - lo impide el modelo
        return None
    return Condicionante(
        clase=ClaseCondicionante.REGLA_NO_VERIFICADA,
        referencia=regla.id,
        norma=regla.norma,
        sentido_impacto=regla.impacto_si_no_verificada,
        que_falta_verificar=regla.que_falta_verificar or "sin especificar",
    )


def de_situacion(
    codigo: CodigoAdvertencia,
    que_falta_verificar: str | None = None,
    *,
    sentido_impacto: SentidoImpacto | None = None,
    magnitud_estimada: str | None = None,
) -> Condicionante:
    """El condicionante de una situación del caso. Nunca lleva norma."""
    return Condicionante(
        clase=ClaseCondicionante.SITUACION_DEL_CASO,
        referencia=codigo.value,
        norma=None,
        sentido_impacto=(
            sentido_impacto
            if sentido_impacto is not None
            else SENTIDO.get(codigo, SentidoImpacto.INDETERMINADO)
        ),
        magnitud_estimada=magnitud_estimada,
        que_falta_verificar=(
            que_falta_verificar
            if que_falta_verificar is not None
            else QUE_FALTA.get(codigo, "sin especificar")
        ),
    )


def del_monto(reglas: ConjuntoDeReglas) -> tuple[Condicionante, ...]:
    """Las reglas que condicionan **cualquier** haber (Cuestiones #1, #2 y #6).

    En cuanto el motor entra al camino del monto —es decir, en cuanto recibe una
    grilla— estas tres intervienen, con independencia del caso.
    """
    salida = []
    for regla_id in REGLAS_DEL_MONTO:
        regla = reglas.por_id(regla_id)
        if regla is None:  # pragma: no cover - lo cubre el test de carga de reglas
            continue
        cond = de_regla(regla)
        if cond is not None:
            salida.append(cond)
    return tuple(salida)


def propagar_a_monto(monto: Monto, condicionantes: tuple[Condicionante, ...]) -> Monto:
    """Devuelve el monto con sus condicionantes incorporados (FR-046a).

    Preparado para la US4: la marca de provisional es inseparable del monto, así
    que la propagación pasa por un único lugar en lugar de repetirse en cada
    camino que construya un `Monto`.
    """
    if not condicionantes:
        return monto
    return monto.model_copy(
        update={
            "condicionantes": tuple(
                {c.referencia: c for c in (*monto.condicionantes, *condicionantes)}.values()
            ),
        }
    )
