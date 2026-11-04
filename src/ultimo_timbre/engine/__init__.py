# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El motor de cálculo (T070).

`calcular` **no hace I/O, no abre sockets y no consulta el reloj**: recibe el
caso y las reglas ya cargadas, y la fecha de cálculo viene dentro del caso
(FR-001a, FR-051). Eso es lo que hace que la equivalencia entre la CLI y la
librería sea estructural y no una coincidencia.

`grilla=None` es válido y es lo que necesita el MVP: produce un informe con
elegibilidad, cargo base y porcentaje, y sin montos.

## El orden de las fases, que no es arbitrario

1. **alcance**: qué períodos puede computar el motor (US2). Todo lo demás se
   mide sobre ese subconjunto.
2. **elegibilidad**: por qué inciso accede y desde cuándo (US1).
3. **cargo base**: sobre qué cargo se liquidaría (US3). Necesita el alcance.
4. **simultaneidad**: la clasificación del art. 47 necesita el cargo base, así
   que va después (FR-004, FR-043).
5. **escenarios**: el porcentaje de cada fecha de cese (US3). Necesita el
   inciso y la fecha de habilitación.
"""

from __future__ import annotations

import datetime as dt

from ultimo_timbre.engine import (
    advertencias,
    alcance,
    calendario,
    condicionantes,
    elegibilidad,
    haber,
)
from ultimo_timbre.engine import (
    cargo_base as cb,
)
from ultimo_timbre.engine import (
    escenarios as esc,
)
from ultimo_timbre.engine import (
    porcentaje as pct,
)
from ultimo_timbre.engine.desglose import Trazador
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import (
    CodigoAdvertencia,
    EstadoResultado,
    TipoEscenario,
)
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import (
    Advertencia,
    CargoBase,
    Condicionante,
    Elegibilidad,
    Escenario,
    Informe,
)
from ultimo_timbre.models.normativa import ConjuntoDeReglas

__all__ = [
    "advertencias",
    "alcance",
    "calcular",
    "calendario",
    "cb",
    "condicionantes",
    "elegibilidad",
    "esc",
    "haber",
    "pct",
]

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

    Sin grilla, el informe trae elegibilidad, cargo base, porcentaje, desglose,
    procedencias y advertencias, y ningún escenario lleva haber: el monto llega
    con la US4.
    """
    traza = Trazador()

    # La elegibilidad se evalúa a la primera fecha de cese; las demás se
    # comparan en los escenarios. Las fechas vienen ordenadas al normalizar.
    cese_principal = caso.fechas_cese[0]

    # 1. Los límites: qué puede computarse y qué no (US2, FR-044 a FR-045a).
    deteccion = alcance.detectar_alcance(caso, reglas=reglas, traza=traza)

    # 2. Elegibilidad (US1).
    resultado = elegibilidad.evaluar(
        caso,
        cese_principal,
        reglas=reglas,
        traza=traza,
        idx_en_alcance=deteccion.idx_en_alcance,
    )

    # FR-015a: el aviso del prorrateo solo tiene sentido si los docentes no
    # alcanzaron ningún inciso. Decirlo antes sería ruido; no decirlo, engañoso.
    if resultado.inciso_mas_favorable is None:
        alcance.advertir_prorrateo_posible(deteccion.idx_no_docentes, reglas, traza)

    # 3. Cargo base (US3). `None` es el caso del promedio de 36 meses (FR-020b).
    cargo = cb.determinar(
        caso,
        cese_principal,
        reglas=reglas,
        traza=traza,
        idx_en_alcance=deteccion.idx_en_alcance,
        # Con grilla el cargo base se elige por el mejor remunerado
        # (Res. IPS 995/2021); sin ella, por índice escalafonario o empate.
        grilla=grilla,
    )

    # 4. Simultaneidad, que recién ahora puede evaluar las dos condiciones del
    #    art. 47: duración **y** que alcance al cargo base (FR-004, FR-043).
    superposiciones = alcance.advertir_simultaneidad(
        caso,
        cese_principal,
        reglas=reglas,
        traza=traza,
        cargo_base=cargo.cargo if cargo is not None else None,
    )
    deteccion = deteccion.model_copy(update={"superposiciones": superposiciones})

    # En cuanto hay grilla el motor entra al camino del monto, y las tres
    # Cuestiones abiertas que condicionan cualquier haber intervienen.
    del_monto: tuple[Condicionante, ...] = ()
    if grilla is not None:
        del_monto = condicionantes.del_monto(reglas)
        for condicionante in del_monto:
            traza.agregar_condicionante(condicionante)

        # Una escala puede estar publicada oficialmente sin que la publicación
        # cite el acto que la aprobó. No invalida la grilla —dejaría al motor
        # sin poder valuar nada con la única fuente disponible— pero tampoco se
        # puede dar por firme: condiciona todo monto que salga de ella.
        if not grilla.tiene_acto_aprobatorio:
            traza.agregar_advertencia(
                advertencias.construir(
                    CodigoAdvertencia.GRILLA_SIN_ACTO_APROBATORIO,
                    f"la grilla «{grilla.version}» proviene de una publicación oficial "
                    "que no cita el decreto ni el acta paritaria que la aprueba: el "
                    "monto se calcula con ella y queda marcado",
                    reglas=reglas,
                )
            )
            sin_acto = condicionantes.de_situacion(CodigoAdvertencia.GRILLA_SIN_ACTO_APROBATORIO)
            traza.agregar_condicionante(sin_acto)
            del_monto = (*del_monto, sin_acto)

    bloqueantes = tuple(a for a in traza.advertencias if a.bloquea_calculo)

    # 5. Escenarios: las fechas provistas más las derivadas —habilitación y
    #    excedentes de 3 y 5 años—, deduplicadas y en orden cronológico (US5).
    a_evaluar = esc.derivar(caso, resultado, reglas=reglas)
    escenarios = tuple(
        _escenario(
            cese,
            tipo,
            resultado if cese == cese_principal else None,
            caso=caso,
            reglas=reglas,
            idx_en_alcance=deteccion.idx_en_alcance,
            bloqueantes=bloqueantes,
            traza=traza if cese == cese_principal else None,
            cargo_base=cargo,
            grilla=grilla,
            condicionantes_del_monto=del_monto,
        )
        for cese, tipo in a_evaluar
    )

    # 6. Los dos avisos que acotan un monto (FR-030a, FR-030c). Van después de
    #    los escenarios porque dependen de que alguno haya emitido haber.
    _avisar_sobre_los_montos(caso, escenarios, grilla=grilla, reglas=reglas, traza=traza)

    # El estado de la elegibilidad se cierra recién acá: las detecciones de
    # alcance, el cargo base y el aviso de prorrateo pueden haber agregado
    # condicionantes después de evaluarla.
    if traza.hay_condicionantes:
        resultado = resultado.model_copy(update={"estado": EstadoResultado.PROVISIONAL})

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
        cargo_base=cargo,
    )


def _avisar_sobre_los_montos(
    caso: Caso,
    escenarios: tuple[Escenario, ...],
    *,
    grilla: GrillaSalarial | None,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
) -> None:
    """Las dos aclaraciones sin las que un monto futuro engaña.

    Un escenario de 2035 valuado con la grilla de 2026 da un número correcto y
    profundamente engañoso si no se dice qué es:

    * **FR-030a**: el motor usa la última grilla aprobada y no proyecta
      aumentos salariales. El número está en pesos de esa grilla;
    * **FR-030c**: el haber es móvil y se actualiza por correlación con el cargo
      en actividad, y este motor no proyecta esa movilidad.

    Las dos citan el art. 50, que es la razón por la que son verdaderas a la
    vez. El aviso de movilidad va en **todo** informe con montos; el de valores
    solo si algún escenario cae después de la fecha de cálculo.
    """
    con_monto = [e for e in escenarios if e.haber is not None]
    if not con_monto or grilla is None:
        return

    traza.agregar_advertencia(
        advertencias.construir(
            CodigoAdvertencia.HABER_MOVIL_ART_50,
            "el haber es móvil: se actualiza por correlación con el cargo en "
            "actividad y este motor no proyecta esa movilidad",
            reglas=reglas,
        )
    )

    if any(e.fecha_cese > caso.fecha_de_calculo for e in con_monto):
        traza.agregar_advertencia(
            advertencias.construir(
                CodigoAdvertencia.MONTOS_A_VALORES_DE_HOY,
                f"hay escenarios posteriores a la fecha de cálculo: sus montos "
                f"están expresados a valores del {grilla.vigencia_desde.isoformat()}, "
                f"la vigencia de la grilla «{grilla.version}». El motor no proyecta "
                "aumentos salariales",
                reglas=reglas,
            )
        )


def _escenario(
    cese: dt.date,
    tipo: TipoEscenario,
    ya_evaluada: Elegibilidad | None,
    *,
    caso: Caso,
    reglas: ConjuntoDeReglas,
    idx_en_alcance: frozenset[int],
    bloqueantes: tuple[Advertencia, ...],
    traza: Trazador | None,
    cargo_base: CargoBase | None,
    grilla: GrillaSalarial | None,
    condicionantes_del_monto: tuple[Condicionante, ...],
) -> Escenario:
    """Un escenario: hay derecho o no, con qué inciso y con qué porcentaje.

    `tipo` lo decide `escenarios.derivar`: una fecha puede ser la que el
    usuario preguntó, la de habilitación del derecho o la de un excedente, y
    cuando coinciden gana la etiqueta más específica.

    `traza` es `None` para los ceses secundarios: sus pasos no van al desglose,
    que documenta el cese principal. Si fueran todos, el desglose dejaría de
    ser legible y repetiría la misma cadena por cada escenario.

    Las advertencias bloqueantes se adjuntan al escenario y no solo al informe,
    porque es ahí donde la CLI mira para derivar el exit 3 (FR-045b) y donde el
    validador del modelo impide que coexistan con un haber (invariante I7).
    """
    resultado = (
        ya_evaluada
        if ya_evaluada is not None
        else elegibilidad.evaluar(
            caso,
            cese,
            reglas=reglas,
            traza=Trazador(),
            idx_en_alcance=idx_en_alcance,
        )
    )
    inciso = resultado.inciso_mas_favorable
    hay_derecho = inciso is not None and resultado.minimo_22_anios.cumple

    if not hay_derecho or inciso is None:
        return Escenario(
            fecha_cese=cese,
            tipo=tipo,
            hay_derecho=False,
            advertencias=bloqueantes,
        )

    elegido = next(i for i in resultado.incisos if i.inciso == inciso)
    habilitado = elegido.habilitado_desde or cese

    # Cuestión abierta #9: el art. 43 rige el porcentaje del inc. b, pero no
    # está verificado que lo haga sobre un cargo base que no cuenta al frente
    # de alumnos. `None` es indeterminado y no activa la Cuestión.
    al_frente = cb.cuenta_al_frente(cargo_base.cargo, reglas) if cargo_base is not None else None

    valor = (
        pct.determinar_con_traza(
            inciso,
            habilitado,
            cese,
            reglas=reglas,
            traza=traza,
            cargo_base_al_frente=al_frente,
        )
        if traza is not None
        else pct.determinar(inciso, habilitado, cese, reglas=reglas, cargo_base_al_frente=al_frente)
    )
    alternativa = pct.lectura_literal(
        inciso=inciso,
        habilitado_desde=habilitado,
        cese=cese,
        fecha_edad_requerida=elegibilidad.fecha_edad_requerida(caso, inciso, reglas),
        aplicado=valor,
        reglas=reglas,
        cargo_base_al_frente=al_frente,
    )
    if alternativa is not None and traza is not None:
        traza.agregar_advertencia(
            advertencias.construir(
                CodigoAdvertencia.LECTURA_LITERAL_EXCEDENTE,
                f"bajo la lectura literal de los arts. 42 y 43 —que mide el excedente "
                f"solo por la edad respecto de la requerida por el inc. {inciso}— el "
                f"porcentaje sería {alternativa.porcentaje} en lugar de {valor}; el "
                "motor aplica el criterio de la Res. IPS 995/2021",
                reglas=reglas,
                sentido_impacto=alternativa.sentido_impacto,
            )
        )

    # El haber llega solo si hay grilla, cargo base y ninguna advertencia
    # bloqueante: el invariante I7 impide que un monto coexista con una.
    # FR-030b: la antigüedad es la que la persona **tendría a la fecha del
    # escenario**, no la de hoy. Se mide sobre los períodos computables, igual
    # que los años de servicio del art. 24.
    antiguedad = calendario.servicio_total(caso.historia, cese, idx_incluidos=idx_en_alcance).anios

    monto = None
    if grilla is not None and cargo_base is not None and not bloqueantes:
        # Los escenarios secundarios valúan contra un trazador descartable: el
        # monto se calcula igual, pero sus pasos no van al desglose, que
        # documenta el cese principal. Si fueran todos, el desglose repetiría la
        # misma cadena por cada escenario y dejaría de ser legible.
        #
        # Lo que **no** se pierde es la marca: los condicionantes del monto
        # viajan dentro del `Monto` (invariante I5), así que un escenario
        # secundario provisional se reconoce como tal aunque su paso no esté.
        monto = haber.valuar(
            cargo_base.cargo,
            cese,
            valor,
            antiguedad_anios=antiguedad,
            grilla=grilla,
            reglas=reglas,
            traza=traza if traza is not None else Trazador(),
            condicionantes_previos=condicionantes_del_monto,
        )

    return Escenario(
        fecha_cese=cese,
        tipo=tipo,
        hay_derecho=True,
        inciso=inciso,
        porcentaje=valor,
        antiguedad_anios=antiguedad,
        advertencias=bloqueantes,
        lectura_literal=alternativa,
        haber=monto,
    )


def estado_de(informe: Informe) -> EstadoResultado:
    """Atajo legible para los consumidores (FR-046c)."""
    return informe.estado_general
