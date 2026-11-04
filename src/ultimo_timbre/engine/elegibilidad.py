# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Elegibilidad por el art. 24 (T062, T063, T064).

Ningún umbral está escrito acá: las edades, los años de servicio y las horas
cátedra salen de `rules/v1/requisitos.yaml` (Principio I, FR-007). Si la regla
cambia, cambia el resultado sin tocar este archivo.

La fecha de habilitación es la de la **última** condición en cumplirse, que es
el criterio del IPS (`Res. IPS 995/2021, Anexo, punto 2.1.a`) y el que la US3
usará para contar el excedente.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

from ultimo_timbre.engine import calendario
from ultimo_timbre.engine.desglose import Trazador
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import (
    CodigoAdvertencia,
    ConvencionConteo,
    EstadoResultado,
    OrigenDato,
    SituacionRevista,
    TipoFuente,
)
from ultimo_timbre.models.informe import (
    Elegibilidad,
    Faltante,
    ResultadoInciso,
    ResultadoRequisito,
)
from ultimo_timbre.models.normativa import ConjuntoDeReglas, Norma, Regla, ValorRegla
from ultimo_timbre.rules import catalogo as cat

__all__ = ["Umbrales", "evaluar", "fecha_edad_requerida"]

REGLA_MINIMO = "requisitos.art24.minimo_con_aportes"
REGLA_REVISTA = "computo.licencias_suplencias_y_revista"
REGLA_CARGO_SIN_NORMA = "al_frente.cargo_sin_norma_expresa"

# La equivalencia módulo ↔ hora cátedra y su lectura conservadora (Cuestión #3).
REGLA_MODULOS = "modulos.equivalencia_horas_catedra"
REGLA_MODULOS_ALTERNATIVA = "modulos.equivalencia_uno_a_uno"
REGLA_CONVENCION = "computo.convencion_de_conteo"
HORIZONTE_ANIOS = 50
"""Tope de la proyección al estimar una habilitación futura (FR-016)."""
INCISOS = ("b", "c", "d")


def _regla(reglas: ConjuntoDeReglas, regla_id: str) -> Regla:
    regla = reglas.por_id(regla_id)
    if regla is None:  # pragma: no cover - lo cubre el test de carga de reglas
        msg = f"falta la regla {regla_id} en el conjunto {reglas.version}"
        raise ValueError(msg)
    return regla


def _entero(regla: Regla, clave: str) -> int | None:
    if not regla.valor:
        return None
    valor: object = regla.valor.get(clave)
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def _horas_por_modulo(regla: Regla | None) -> Decimal:
    """Cuántas horas cátedra equivale un módulo, según esa regla.

    Si la regla no declara el factor, se usa 1: es la lectura que **menos**
    horas atribuye, y por lo tanto la que menos riesgo tiene de afirmar que
    alguien alcanza un umbral que no alcanza.
    """
    crudo = (regla.valor or {}).get("horas_catedra_por_modulo") if regla else None
    return Decimal(str(crudo)) if crudo is not None else Decimal(1)


def _hay_modulos(caso: Caso, en_alcance: set[int]) -> bool:
    """Si algún período en alcance declara carga en módulos.

    Sin módulos las dos equivalencias dan lo mismo por construcción, y la
    Cuestión #3 no tiene nada que decir sobre el caso.
    """
    return any(
        p.modulos is not None and p.modulos > 0
        for p in caso.historia.periodos
        if p.idx in en_alcance
    )


class AlFrente(NamedTuple):
    """Los períodos al frente de alumnos bajo las dos equivalencias de módulo.

    `alternativo` es igual a `aplicado` cuando no hay módulos en juego, que es
    la mayoría de los casos: ahí la Cuestión #3 no tiene nada que decir.
    """

    aplicado: set[int]
    alternativo: set[int]
    hay_modulos: bool


def _al_frente(
    caso: Caso,
    cese: dt.date,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    en_alcance: set[int],
) -> AlFrente:
    """Los `idx` de los períodos que cuentan como al frente de alumnos.

    La condición se deriva del cargo, nunca se carga (FR-002a). Para los cargos
    cuya condición es un umbral de horas cátedra, el umbral sale de la regla del
    art. 24 inc. b.

    ## Los módulos y la doble lectura (Cuestión abierta #3)

    Cuando algún período declara carga en **módulos**, el umbral se evalúa dos
    veces: con la equivalencia aplicada —1 módulo = 1,5 horas cátedra— y con la
    conservadora de 1 a 1. Las dos salen de acá; quién decide si la diferencia
    condiciona el resultado es el requisito de años al frente, porque es ahí
    donde la diferencia puede cambiar algo.

    La segunda lectura se calcula con un `Trazador` descartable: lo que
    interesa es el conjunto, no duplicar cada paso del desglose con una lectura
    que el motor no aplicó.
    """
    umbral = _entero(_regla(reglas, "requisitos.art24.inc_b"), "horas_catedra")
    regla = reglas.por_id(REGLA_MODULOS)
    factor = _horas_por_modulo(regla)

    aplicado = _al_frente_con_factor(
        caso, cese, reglas, traza, en_alcance, umbral=umbral, factor=factor
    )

    hay_modulos = _hay_modulos(caso, en_alcance)
    otro_factor = _horas_por_modulo(reglas.por_id(REGLA_MODULOS_ALTERNATIVA))
    if not hay_modulos or otro_factor == factor:
        return AlFrente(aplicado, aplicado, hay_modulos=False)

    alternativo = _al_frente_con_factor(
        caso, cese, reglas, Trazador(), en_alcance, umbral=umbral, factor=otro_factor
    )
    return AlFrente(aplicado, alternativo, hay_modulos=True)


def _decide_el_frente(
    letra: str,
    reglas: ConjuntoDeReglas,
    frente: calendario.Duracion,
    alternativo: calendario.Duracion,
) -> bool:
    """Si las dos lecturas de módulo resuelven distinto el requisito del inciso.

    Mide el **resultado**, no el conjunto de períodos: con 30 años al frente,
    mover un período corto entre lecturas cambia el conjunto y no cambia si se
    cumplen los 25 años. Solo lo segundo justifica marcar provisional.
    """
    requerido = _entero(_regla(reglas, f"requisitos.art24.inc_{letra}"), "anios_al_frente")
    if requerido is None:
        return False
    return frente.cumple_anios(requerido) != alternativo.cumple_anios(requerido)


def _informar_equivalencia_de_modulos(
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    *,
    decide: bool,
) -> None:
    """Deja asentada la equivalencia, y la condiciona solo si decide algo.

    `decide` es verdadero cuando el requisito de años al frente de algún inciso
    se cumple bajo una lectura y no bajo la otra. Solo entonces la Cuestión #3
    pasa de información a condicionante (FR-046b).

    Condicionar todo caso con módulos haría que el motor dijera «no sé» donde
    sabe —treinta módulos pasan el umbral con cualquier equivalencia— y eso
    entrena al lector a ignorar la marca de provisional, que es peor que no
    tenerla.
    """
    regla = reglas.por_id(REGLA_MODULOS)
    if regla is None:  # pragma: no cover - lo cubre el test de carga de reglas
        return
    alternativa = reglas.por_id(REGLA_MODULOS_ALTERNATIVA)
    factor = _horas_por_modulo(regla)
    otro = _horas_por_modulo(alternativa)

    if not decide:
        traza.paso_suelto(
            "Equivalencia módulo ↔ hora cátedra: no altera el resultado",
            regla_id=regla.id,
            norma=regla.norma,
            tipo_fuente=regla.tipo,
            entrada=f"1 módulo = {factor} h contra 1 módulo = {otro} h",
            salida="el requisito de años al frente da lo mismo con las dos lecturas",
        )
        return

    traza.condicionante_de_regla(regla)
    traza.advertencia(
        CodigoAdvertencia.REGLA_NO_VERIFICADA,
        "la equivalencia entre módulos y horas cátedra decide si se alcanzan los "
        "años al frente de alumnos que exige el art. 24: con la lectura aplicada "
        f"({factor} horas cátedra por módulo) el requisito se resuelve distinto "
        f"que con la lectura conservadora ({otro} por módulo)",
        norma=regla.norma,
        sentido_impacto=regla.impacto_si_no_verificada,
    )
    if alternativa is not None:
        traza.paso_suelto(
            "Equivalencia módulo ↔ hora cátedra: lectura alternativa",
            regla_id=alternativa.id,
            norma=alternativa.norma,
            tipo_fuente=alternativa.tipo,
            entrada=f"1 módulo = {otro} hora cátedra",
            salida="cambia si se alcanza el umbral de veinte horas del art. 24 inc. b",
        )


def _al_frente_con_factor(
    caso: Caso,
    cese: dt.date,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    en_alcance: set[int],
    *,
    umbral: int | None,
    factor: Decimal,
) -> set[int]:
    """El conjunto al frente para una equivalencia de módulo dada."""
    al_frente: set[int] = set()

    for periodo in caso.historia.periodos:
        if periodo.idx not in en_alcance:
            continue
        derivada = cat.derivar(
            reglas.catalogo_cargos,
            periodo,
            horas_catedra_simultaneas=calendario.max_horas_catedra_simultaneas(
                caso.historia, periodo.idx, cese, horas_por_modulo=factor
            ),
            umbral_horas_catedra=umbral,
        )
        if derivada.al_frente_de_alumnos:
            al_frente.add(periodo.idx)

        traza.procedencia(
            f"al_frente[{periodo.idx}]",
            derivada.origen,
            derivado_de=(f"catálogo de cargos {reglas.catalogo_cargos.version}: {periodo.cargo}"),
            difiere_del_catalogo=derivada.difiere_del_catalogo,
        )
        if derivada.norma is not None:
            traza.paso_suelto(
                f"Condición de al frente de alumnos del cargo «{periodo.cargo}»",
                regla_id=derivada.regla_id or f"catalogo.{periodo.cargo}",
                norma=derivada.norma,
                tipo_fuente=TipoFuente.LETRA_LEY,
                entrada=f"periodo_idx={periodo.idx}",
                salida=str(derivada.al_frente_de_alumnos),
            )

        # --- lo que vuelve provisional el resultado -----------------------
        if not derivada.en_catalogo:
            traza.advertencia(
                CodigoAdvertencia.CARGO_FUERA_DE_CATALOGO,
                f"el cargo del período {periodo.idx} no figura en el catálogo: su "
                "condición queda indeterminada y no se asume",
                periodo_idx=periodo.idx,
            )
            traza.condicionante_de_regla(_regla(reglas, REGLA_CARGO_SIN_NORMA))
        # La equivalencia de módulos queda afuera del camino genérico: su
        # condicionante lo decide `_comparar_equivalencias` según si las dos
        # lecturas cambian el resultado, no el solo hecho de estar sin
        # verificar. Entrar acá la volvería bloqueante siempre.
        if derivada.regla_id is not None and derivada.regla_id != REGLA_MODULOS:
            condicionante = reglas.por_id(derivada.regla_id)
            if condicionante is not None and condicionante.condiciona_resultado:
                traza.condicionante_de_regla(condicionante)
                traza.advertencia(
                    CodigoAdvertencia.REGLA_NO_VERIFICADA,
                    f"la condición del cargo «{periodo.cargo}» depende de una regla sin verificar",
                    norma=condicionante.norma,
                    sentido_impacto=condicionante.impacto_si_no_verificada,
                    periodo_idx=periodo.idx,
                )

    return al_frente


def _condicionantes_de_la_historia(
    caso: Caso,
    cese: dt.date,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
) -> None:
    """Licencias, situación de revista, períodos en curso y recortes."""
    regla_revista = _regla(reglas, REGLA_REVISTA)

    if any(p.licencias for p in caso.historia.periodos if not p.fuera_de_alcance):
        traza.advertencia(
            CodigoAdvertencia.REGLA_NO_VERIFICADA,
            "hay licencias en la historia y su cómputo no está verificado",
            norma=regla_revista.norma,
            sentido_impacto=regla_revista.impacto_si_no_verificada,
        )
        traza.condicionante_de_regla(regla_revista)

    if any(
        p.situacion_revista is not SituacionRevista.TITULAR
        for p in caso.historia.periodos
        if not p.fuera_de_alcance
    ):
        traza.advertencia(
            CodigoAdvertencia.REGLA_NO_VERIFICADA,
            "hay períodos con situación de revista distinta de titular y su "
            "incidencia no está verificada",
            norma=regla_revista.norma,
            sentido_impacto=regla_revista.impacto_si_no_verificada,
        )
        traza.condicionante_de_regla(regla_revista)

    for idx in caso.historia.periodos_en_curso():
        traza.advertencia(
            CodigoAdvertencia.SUPUESTO_CONTINUIDAD,
            f"el período {idx} está en curso: se proyectó hasta la fecha de cese "
            "bajo supuesto de continuidad en el mismo cargo",
            periodo_idx=idx,
        )
        traza.procedencia(
            f"supuesto_continuidad[{idx}]",
            OrigenDato.DERIVADO,
            derivado_de="período sin fecha de fin proyectado hasta la fecha de cese",
        )
    if caso.historia.periodos_en_curso():
        traza.condicionante_de_situacion(
            CodigoAdvertencia.SUPUESTO_CONTINUIDAD,
            "que el desempeño continúe en el mismo cargo hasta la fecha de cese "
            "es un supuesto del motor, no un dato de la historia",
        )

    for idx in caso.historia.periodos_recortados_a(cese):
        traza.advertencia(
            CodigoAdvertencia.PERIODO_RECORTADO_A_CESE,
            f"el período {idx} se extiende más allá del cese y se recortó a esa fecha",
            periodo_idx=idx,
        )


def _convencion_alternativa(reglas: ConjuntoDeReglas) -> tuple[ConvencionConteo, int]:
    """La convención alternativa y su umbral de arrastre, tomados de la regla.

    El «30» de los meses de 30 días es un valor normativo: sale de la regla,
    no del código (Principio I, FR-007).
    """
    regla = _regla(reglas, REGLA_CONVENCION)
    dias = _entero(regla, "dias_por_mes_alternativa")
    return ConvencionConteo.MESES_30, dias or calendario.DIAS_POR_MES_ALTERNATIVA


def _sensibilidad(
    caso: Caso,
    cese: dt.date,
    requeridos: int,
    idx: set[int],
    reglas: ConjuntoDeReglas,
) -> tuple[bool, int | None]:
    """Si la convención de conteo decide este requisito, y el margen en días.

    Devuelve `(es_sensible, margen_dias)`.

    La idea: se calcula la fecha en que el umbral se cruza bajo cada convención.
    El **margen** es la distancia entre el cese y ese cruce; el **desplazamiento**
    es cuánto mueve el cruce el cambio de convención. Si el margen no supera al
    desplazamiento, la convención está decidiendo el resultado y eso no se puede
    presentar como definitivo (Cuestión abierta #5, FR-046b).
    """
    alternativa, dias_por_mes = _convencion_alternativa(reglas)
    cumple_a = calendario.servicio_total(caso.historia, cese, idx_incluidos=idx).cumple_anios(
        requeridos
    )
    cumple_b = calendario.servicio_total(
        caso.historia,
        cese,
        idx_incluidos=idx,
        convencion=alternativa,
        dias_por_mes=dias_por_mes,
    ).cumple_anios(requeridos)

    if cumple_a != cumple_b:
        # la convención decide directamente: no hay margen que medir
        return True, 0

    # horizonte amplio para poder medir el cruce incluso si todavía no ocurrió
    horizonte = cese + relativedelta(years=HORIZONTE_ANIOS)
    cruce_a = calendario.fecha_al_alcanzar_servicio(
        caso.historia, requeridos, limite=horizonte, idx_incluidos=idx
    )
    cruce_b = calendario.fecha_al_alcanzar_servicio(
        caso.historia,
        requeridos,
        limite=horizonte,
        idx_incluidos=idx,
        convencion=alternativa,
        dias_por_mes=dias_por_mes,
    )
    tramos = calendario.tramos_unidos(caso.historia, cese, idx_incluidos=idx)

    if cruce_a is not None and cruce_b is not None:
        # el umbral ya se cruzó (o se cruza proyectando): el margen es la
        # distancia del cese al cruce
        margen = abs((cese - cruce_a).days)
        medido = abs((cruce_a - cruce_b).days)
    else:
        # historia cerrada que no alcanza el umbral: se mide cuántos días de
        # servicio continuo faltarían. No es una proyección de elegibilidad,
        # es la distancia al umbral.
        falta_a = calendario.dias_de_servicio_faltantes(tramos, requeridos, desde=cese)
        falta_b = calendario.dias_de_servicio_faltantes(
            tramos,
            requeridos,
            desde=cese,
            convencion=alternativa,
            dias_por_mes=dias_por_mes,
        )
        if falta_a is None:
            return False, None
        margen = falta_a
        medido = abs(falta_a - falta_b) if falta_b is not None else 0

    # El desplazamiento medido entre las dos convenciones implementadas
    # **subestima** el rango: son dos puntos de una familia más amplia. La cota
    # del rango es, por cada tramo unido, el día de la fecha inclusiva más el
    # residuo de arrastre: hasta un mes alternativo completo.
    cota = len(tramos) * dias_por_mes
    return margen <= max(medido, cota), margen


class Umbrales(NamedTuple):
    """Los umbrales de un inciso y los períodos sobre los que se miden."""

    edad: int
    servicio: int
    al_frente: int | None
    idx_en_alcance: set[int]
    idx_al_frente: set[int]


def _estimar(
    caso: Caso,
    cese: dt.date,
    umbrales: Umbrales,
) -> tuple[dt.date | None, str | None]:
    """La fecha en que se cumpliría el inciso, proyectando lo que esté en curso.

    Los períodos en curso se proyectan hasta el horizonte bajo supuesto de
    continuidad (FR-002e); los cerrados no crecen. Si lo que falta es servicio
    y no hay ningún período en curso, la fecha no existe: sin servicios futuros
    el requisito no avanza. Si lo único que falta es edad, sí se estima, porque
    la edad avanza sola.
    """
    horizonte = cese + relativedelta(years=HORIZONTE_ANIOS)
    fechas: list[dt.date] = [_fecha_edad(caso, umbrales.edad)]
    hay_en_curso = bool(caso.historia.periodos_en_curso())

    for requeridos, idx in (
        (umbrales.servicio, umbrales.idx_en_alcance),
        (umbrales.al_frente, umbrales.idx_al_frente),
    ):
        if requeridos is None:
            continue
        ya = calendario.servicio_total(caso.historia, cese, idx_incluidos=idx).cumple_anios(
            requeridos
        )
        if ya:
            continue
        if not hay_en_curso:
            return None, (
                "no puede estimarse sin servicios futuros: el requisito de "
                "servicio no se alcanzó y la historia no tiene ningún período "
                "en curso que proyectar"
            )
        cruce = calendario.fecha_al_alcanzar_servicio(
            caso.historia, requeridos, limite=horizonte, idx_incluidos=idx
        )
        if cruce is None:
            return None, (
                f"no puede estimarse: el requisito no se alcanza ni proyectando "
                f"{HORIZONTE_ANIOS} años de continuidad"
            )
        fechas.append(cruce)

    return max(fechas), None


def _requisito(
    nombre: str,
    alcanzado: object,
    requerido: object,
    cumple: bool,
    norma: Norma,
    *,
    sensible: bool = False,
    margen_dias: int | None = None,
) -> ResultadoRequisito:
    return ResultadoRequisito(
        nombre=nombre,
        cumple=cumple,
        norma=norma,
        valor_alcanzado=str(alcanzado),
        valor_requerido=str(requerido),
        estado=(EstadoResultado.PROVISIONAL if sensible else EstadoResultado.DEFINITIVO),
        margen_dias=margen_dias,
    )


def _fecha_edad(caso: Caso, anios: int) -> dt.date:
    """La fecha del cumpleaños número `anios`. Sin reloj."""
    # `dateutil` no trae stubs: la suma devuelve Any y hay que acotarla.
    fecha: dt.date = caso.fecha_nacimiento + relativedelta(years=anios)
    return fecha


def fecha_edad_requerida(caso: Caso, inciso: str, reglas: ConjuntoDeReglas) -> dt.date:
    """La fecha en que se cumple la edad que pide el inciso.

    La necesita la lectura literal de los arts. 42 y 43, que mide el excedente
    contra esa edad y no contra la habilitación (FR-027b). La edad sale de la
    regla del inciso, no del código.
    """
    regla = _regla(reglas, f"requisitos.art24.inc_{inciso}")
    return _fecha_edad(caso, _entero(regla, "edad") or 0)


def _evaluar_inciso(
    letra: str,
    *,
    caso: Caso,
    cese: dt.date,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    edad: int,
    servicio: calendario.Duracion,
    frente: calendario.Duracion,
    en_alcance: set[int],
    al_frente: set[int],
    frente_alternativo: calendario.Duracion | None = None,
) -> ResultadoInciso:
    """Evalúa un inciso del art. 24.

    El inc. b mide los años **al frente de alumnos**; el c pide 25 de servicio
    con 10 al frente; el d solo años de servicio. Los tres umbrales salen de la
    regla, no del código (Principio I, FR-007).
    """
    regla = _regla(reglas, f"requisitos.art24.inc_{letra}")
    edad_req = _entero(regla, "edad") or 0
    serv_req = _entero(regla, "anios_servicio") or 0
    frente_req = _entero(regla, "anios_al_frente")

    umbrales = Umbrales(
        edad=edad_req,
        servicio=serv_req,
        al_frente=frente_req,
        idx_en_alcance=en_alcance,
        idx_al_frente=al_frente,
    )

    requisitos = [_requisito("edad", edad, edad_req, edad >= edad_req, regla.norma)]
    """La edad no depende de la convención de conteo: no hay tramos que sumar."""

    sensible_serv, margen_serv = _sensibilidad(caso, cese, serv_req, en_alcance, reglas)
    requisitos.append(
        _requisito(
            "años de servicio",
            servicio.anios,
            serv_req,
            servicio.cumple_anios(serv_req),
            regla.norma,
            sensible=sensible_serv,
            margen_dias=margen_serv,
        )
    )
    if frente_req is not None:
        sensible_frente, margen_frente = _sensibilidad(caso, cese, frente_req, al_frente, reglas)
        # La equivalencia de módulos (Cuestión #3) solo vuelve sensible este
        # requisito si **cambia si se cumple**. Que cambie el conjunto de
        # períodos al frente no alcanza: con 30 años al frente, mover un
        # período corto no mueve el requisito de 25.
        cumple_frente = frente.cumple_anios(frente_req)
        if frente_alternativo is not None:
            sensible_frente = sensible_frente or (
                frente_alternativo.cumple_anios(frente_req) != cumple_frente
            )
        requisitos.append(
            _requisito(
                "años al frente de alumnos (o 20 horas cátedra)",
                frente.anios,
                frente_req,
                cumple_frente,
                regla.norma,
                sensible=sensible_frente,
                margen_dias=margen_frente,
            )
        )

    cumple = all(r.cumple for r in requisitos)
    sensible = any(r.estado is EstadoResultado.PROVISIONAL for r in requisitos)
    # La sensibilidad se deja asentada en el inciso, pero **no** se registra acá
    # como condicionante: eso se decide después de saber cuál es el inciso más
    # favorable (ver `_sensibilidades_que_importan`).

    habilitado_desde: dt.date | None = None
    falta: Faltante | None = None
    estimado_para: dt.date | None = None
    motivo: str | None = None

    if cumple:
        habilitado_desde = _habilitado_desde(caso, cese, umbrales)
    else:
        alcanzado = frente.anios if frente_req is not None else servicio.anios
        pedido = frente_req if frente_req is not None else serv_req
        falta = Faltante(
            anios_edad=Decimal(max(0, edad_req - edad)),
            anios_servicio=Decimal(max(0, pedido - alcanzado)),
        )
        estimado_para, motivo = _estimar(caso, cese, umbrales)

    traza.paso(
        f"Requisitos del art. 24 inc. {letra}",
        regla,
        entrada=f"edad={edad}; servicio={servicio.anios}; al frente={frente.anios}",
        salida=(
            f"cumple desde {habilitado_desde.isoformat()}"
            if habilitado_desde
            else (
                f"no cumple; estimado para {estimado_para.isoformat()}"
                if estimado_para
                else "no cumple"
            )
        ),
    )

    return ResultadoInciso(
        inciso=letra,
        cumple=cumple,
        norma=regla.norma,
        requisitos=tuple(requisitos),
        habilitado_desde=habilitado_desde,
        falta=falta,
        estado=EstadoResultado.PROVISIONAL if sensible else EstadoResultado.DEFINITIVO,
        estimado_para=estimado_para,
        motivo_sin_estimacion=motivo,
    )


def _advertir_convencion(letra: str, reglas: ConjuntoDeReglas, traza: Trazador) -> None:
    """La convención de conteo está decidiendo este inciso (Cuestión abierta #5)."""
    regla = _regla(reglas, REGLA_CONVENCION)
    traza.condicionante_de_regla(regla)
    traza.advertencia(
        CodigoAdvertencia.REGLA_NO_VERIFICADA,
        f"en el inc. {letra} la convención de conteo de tiempo decide el "
        "resultado: el margen al umbral no supera el desplazamiento que "
        "produce cambiarla",
        norma=regla.norma,
        sentido_impacto=regla.impacto_si_no_verificada,
    )


def _habilitado_desde(caso: Caso, cese: dt.date, umbrales: Umbrales) -> dt.date:
    """La fecha de la **última** condición en cumplirse.

    Es el criterio del IPS (`Res. IPS 995/2021, Anexo, punto 2.1.a`) y el que la
    US3 usará para contar el excedente de los arts. 42 y 43.
    """
    fechas = [_fecha_edad(caso, umbrales.edad)]
    for requeridos, idx in (
        (umbrales.servicio, umbrales.idx_en_alcance),
        (umbrales.al_frente, umbrales.idx_al_frente),
    ):
        if requeridos is None:
            continue
        cruce = calendario.fecha_al_alcanzar_servicio(
            caso.historia, requeridos, limite=cese, idx_incluidos=idx
        )
        if cruce is not None:
            fechas.append(cruce)
    return max(fechas)


def evaluar(
    caso: Caso,
    cese: dt.date,
    *,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    idx_en_alcance: frozenset[int] | None = None,
) -> Elegibilidad:
    """Evalúa los tres incisos y el mínimo general a una fecha de cese.

    `idx_en_alcance` viene de `engine.alcance.detectar`: son los períodos que el
    motor puede computar. Sin él se calcula de forma directa, que es lo que
    necesitan los escenarios secundarios.
    """
    en_alcance = (
        set(idx_en_alcance)
        if idx_en_alcance is not None
        else {p.idx for p in caso.historia.periodos if not p.fuera_de_alcance}
    )
    frentes = _al_frente(caso, cese, reglas, traza, en_alcance)
    al_frente = frentes.aplicado
    _condicionantes_de_la_historia(caso, cese, reglas, traza)

    servicio = calendario.servicio_total(caso.historia, cese, idx_incluidos=en_alcance)
    frente = calendario.servicio_total(caso.historia, cese, idx_incluidos=al_frente)
    # La duración al frente bajo la equivalencia conservadora de módulos, solo
    # si hay módulos en juego y las dos lecturas difieren (Cuestión #3).
    frente_alternativo = (
        calendario.servicio_total(caso.historia, cese, idx_incluidos=frentes.alternativo)
        if frentes.hay_modulos and frentes.alternativo != al_frente
        else None
    )
    edad = caso.edad_a(cese)

    # Si la equivalencia decide algún requisito de años al frente. Se calcula de
    # las dos duraciones y no del estado del requisito, porque ese estado puede
    # venir de la convención de conteo y atribuirlo a la #3 sería mentir sobre
    # la causa.
    equivalencia_decide = frente_alternativo is not None and any(
        _decide_el_frente(letra, reglas, frente, frente_alternativo) for letra in INCISOS
    )

    regla_cierre = _regla(reglas, "requisitos.arts71_72.cierre_de_computos")
    traza.paso(
        "Cierre de cómputos a la fecha de cese",
        regla_cierre,
        entrada=f"cese={cese.isoformat()}",
        salida=f"servicio={servicio}; al frente={frente}; edad={edad}",
    )

    # ------------------------------------------------- mínimo general
    regla_minimo = _regla(reglas, REGLA_MINIMO)
    anios_minimo = _entero(regla_minimo, "anios_con_aportes") or 0
    minimo = _requisito(
        "años con aportes",
        servicio.anios,
        anios_minimo,
        servicio.cumple_anios(anios_minimo),
        regla_minimo.norma,
    )
    traza.paso(
        "Mínimo general de años con aportes",
        regla_minimo,
        entrada=str(servicio),
        salida="cumple" if minimo.cumple else "no cumple",
    )

    # ------------------------------------------------- los tres incisos
    resultados: tuple[ResultadoInciso, ...] = tuple(
        _evaluar_inciso(
            letra,
            caso=caso,
            cese=cese,
            reglas=reglas,
            traza=traza,
            edad=edad,
            servicio=servicio,
            frente=frente,
            en_alcance=en_alcance,
            al_frente=al_frente,
            frente_alternativo=frente_alternativo,
        )
        for letra in INCISOS
    )

    if frentes.hay_modulos:
        _informar_equivalencia_de_modulos(reglas, traza, decide=equivalencia_decide)

    # ------------------------------------------------- inciso más favorable
    mas_favorable = _elegir_mas_favorable(resultados, reglas, traza)

    # Recién ahora se sabe qué sensibilidades pueden mover el resultado. Las
    # que no pueden quedan informadas en su inciso y no condicionan el informe.
    for letra in _sensibilidades_que_importan(
        resultados,
        reglas,
        por_la_convencion=_sensibles_a_la_convencion(caso, cese, reglas, en_alcance, al_frente),
    ):
        _advertir_convencion(letra, reglas, traza)

    return Elegibilidad(
        incisos=resultados,
        minimo_22_anios=minimo,
        inciso_mas_favorable=mas_favorable,
        estado=(
            EstadoResultado.PROVISIONAL if traza.hay_condicionantes else EstadoResultado.DEFINITIVO
        ),
    )


class _Candidato(NamedTuple):
    """Lo mínimo que el ranking necesita de un inciso.

    Se rankea sobre esto y no sobre `ResultadoInciso` para poder evaluar
    hipótesis —«¿y si este inciso no se cumpliera?»— sin construir modelos
    inválidos.
    """

    inciso: str
    cumple: bool
    desde: dt.date


_Base = tuple[Regla, ValorRegla]


def _bases(reglas: ConjuntoDeReglas) -> dict[str, _Base]:
    """El artículo y la base porcentual de cada inciso, leídos de las reglas."""
    art41 = _regla(reglas, "haber.art41.base")
    art43 = _regla(reglas, "haber.art43.base")
    return {
        "b": (art43, art43.valor or {}),
        "c": (art41, art41.valor or {}),
        "d": (art41, art41.valor or {}),
    }


def _ranking(candidatos: tuple[_Candidato, ...], reglas: ConjuntoDeReglas) -> str | None:
    """El inciso más favorable entre los que se cumplen, sin tocar la traza.

    El inc. b accede por el art. 43, cuya base es 75 %; los incisos c y d van
    por el art. 41, con 70 %. A igual porcentaje gana el que se habilita antes.
    """
    cumplidos = [c for c in candidatos if c.cumple]
    if not cumplidos:
        return None
    bases = _bases(reglas)

    def clave(c: _Candidato) -> tuple[Decimal, dt.date]:
        _, valor = bases[c.inciso]
        porcentaje = Decimal(str((valor or {}).get("porcentaje", "0")))
        # más porcentaje primero; a igualdad, habilitación más temprana
        return (-porcentaje, c.desde)

    return min(cumplidos, key=clave).inciso


def _candidatos(resultados: tuple[ResultadoInciso, ...]) -> tuple[_Candidato, ...]:
    return tuple(
        _Candidato(r.inciso, r.cumple, r.habilitado_desde or dt.date.max) for r in resultados
    )


def _sensibles_a_la_convencion(
    caso: Caso,
    cese: dt.date,
    reglas: ConjuntoDeReglas,
    en_alcance: set[int],
    al_frente: set[int],
) -> set[str]:
    """Los incisos cuyo resultado puede moverlo la convención de conteo.

    Se mide aparte del estado del inciso a propósito. Un inciso puede estar
    provisional por otra causa —la equivalencia de módulos, por ejemplo— y
    entonces filtrar por «inciso provisional» le atribuiría a la convención un
    condicionante que no es suyo. Una razón equivocada en el informe manda al
    profesional a verificar la norma que no era.
    """
    sensibles: set[str] = set()
    for letra in INCISOS:
        regla = _regla(reglas, f"requisitos.art24.inc_{letra}")
        requerido_serv = _entero(regla, "anios_servicio") or 0
        if _sensibilidad(caso, cese, requerido_serv, en_alcance, reglas)[0]:
            sensibles.add(letra)
            continue
        requerido_frente = _entero(regla, "anios_al_frente")
        if (
            requerido_frente is not None
            and _sensibilidad(caso, cese, requerido_frente, al_frente, reglas)[0]
        ):
            sensibles.add(letra)
    return sensibles


def _sensibilidades_que_importan(
    resultados: tuple[ResultadoInciso, ...],
    reglas: ConjuntoDeReglas,
    *,
    por_la_convencion: set[str],
) -> tuple[str, ...]:
    """Qué incisos sensibles pueden mover el resultado (FR-046b).

    Implementa la regla documentada en `engine.condicionantes`, sección
    «Condicionantes informativos»: la sensibilidad de un inciso condiciona el
    informe solo si, de darse vuelta, cambiaría **si hay derecho** o **cuál es
    el inciso más favorable** —y con él el artículo, el porcentaje y el haber—.

    Se mide dando vuelta un inciso a la vez y volviendo a rankear. Al inciso
    que se voltea *hacia* «cumple» se le da la fecha de habilitación más
    temprana posible, para que gane el desempate si pudiera ganarlo: el
    criterio se equivoca hacia marcar provisional, nunca hacia ocultar la duda.
    """
    base = _candidatos(resultados)
    actual = _ranking(base, reglas)
    importan: list[str] = []

    for r in resultados:
        if r.estado is not EstadoResultado.PROVISIONAL:
            continue
        if r.inciso not in por_la_convencion:
            # Provisional por otra causa: no es la convención la que lo mueve.
            continue
        hipotetica = r.habilitado_desde or r.estimado_para or dt.date.min
        volteados = tuple(
            _Candidato(c.inciso, not c.cumple, hipotetica) if c.inciso == r.inciso else c
            for c in base
        )
        if _ranking(volteados, reglas) != actual:
            importan.append(r.inciso)

    return tuple(importan)


def _elegir_mas_favorable(
    resultados: tuple[ResultadoInciso, ...],
    reglas: ConjuntoDeReglas,
    traza: Trazador,
) -> str | None:
    """El inciso que da el mejor haber (FR-017), dejando el paso en la traza."""
    elegido = _ranking(_candidatos(resultados), reglas)
    if elegido is None:
        return None

    regla_elegida, valor = _bases(reglas)[elegido]
    valor = valor or {}
    traza.paso(
        f"Inciso más favorable: {elegido}",
        regla_elegida,
        entrada="incisos cumplidos: " + ", ".join(r.inciso for r in resultados if r.cumple),
        salida=(f"inc. {elegido} por {regla_elegida.norma.texto} (base {valor.get('porcentaje')})"),
    )
    return elegido
