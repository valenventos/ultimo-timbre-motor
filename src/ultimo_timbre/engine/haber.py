# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Valuación del haber (T147 a T152, FR-030 a FR-034).

El único módulo que produce un número de plata, y por eso el que más cuidado
pide. Tres decisiones lo gobiernan:

**El valor del cargo no es un importe indiviso** (FR-031a). Es un conjunto de
componentes, cada uno con su código, si es *bonificable* —si la antigüedad se
aplica sobre él— y si es *remunerativo*. Un cargo modelado como un número
suelto haría imposible cumplir FR-031b, que es donde está el error caro: aplicar
la antigüedad sobre el total en lugar de sobre su parte bonificable infla el
haber sin que nada se vea raro.

**El redondeo ocurre una sola vez**, al final (FR-033). Redondear en cada
multiplicación acumula error y vuelve el resultado dependiente del orden de las
operaciones, que es justo lo que el invariante I3 prohíbe.

**Casi nada de esto está verificado.** Qué conceptos integran la remuneración
es la Cuestión abierta #2 y la política de redondeo la #6. Las dos condicionan
**todo** haber, así que ningún monto de la v1 sale definitivo. Lo que el motor
hace es elegir un criterio, declararlo como valor por defecto aplicado y decir
qué falta.

## La antigüedad, verificada

Era la Cuestión abierta #1 y se resolvió el 2026-11-04. Rige la escala del
`Decreto 818/13, Anexo Único`, con tope **125 %** en el tramo de 24 años, y se
aplica **solo sobre el sueldo básico**.

Los once tramos estaban transcriptos del Anexo Único desde el principio; lo que
faltaba era la certeza de que ninguna norma posterior los había modificado, y
eso ninguna relectura de la norma podía darla. La dio una liquidación DGCyE
09/2026, donde el código 0220 es exactamente 1,25 veces el código 0110. La
escala original de la Ley 10.579 (tope 120 %) quedó como referencia histórica y
ya no se informa como alternativa.

## La remuneración del cargo, hoy

El criterio aplicado son los **componentes con aporte al IPS**: los arts. 4 y 5
atan el sistema al aporte y la misma liquidación muestra el aporte personal como
el 16 % exacto de esa base, lo que vuelve el criterio verificable contra un
recibo. Sigue sin verificarse que la base del **haber** coincida con la del
aporte —eso lo tiene que decir una resolución del IPS— y la lectura amplia, que
incluye los no remunerativos sin aporte como el FONID, se informa al alza.
"""

from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from typing import TypeGuard

from ultimo_timbre.engine import advertencias as adv
from ultimo_timbre.engine import condicionantes as cond
from ultimo_timbre.engine.desglose import Trazador
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado
from ultimo_timbre.models.grilla import GrillaSalarial, ValorCargo
from ultimo_timbre.models.informe import Condicionante, Monto
from ultimo_timbre.models.normativa import ConjuntoDeReglas, Regla

__all__ = [
    "adicional_por_antiguedad",
    "base_bonificable",
    "porcentaje_de_antiguedad",
    "redondear",
    "remuneracion_del_cargo",
    "valuar",
]

REGLA_REMUNERACION = "remuneracion.conceptos_del_cargo"
REGLA_ANTIGUEDAD = "antiguedad.escala_y_tope"
REGLA_ANTIGUEDAD_ALTERNATIVA = "antiguedad.escala_ley_10579"
# Las lecturas alternativas de la remuneración, en el orden en que se informan.
# La amplia primero: desde que el criterio aplicado son los componentes con
# aporte, la restrictiva suele coincidir con él y no aporta nada.
REGLAS_REMUNERACION_ALTERNATIVAS = (
    "remuneracion.incluye_no_remunerativos_sin_aporte",
    "remuneracion.solo_remunerativos",
)
REGLA_REDONDEO = "redondeo.politica_ips"
REGLA_HABER = "haber.art41.base"

# Las políticas de redondeo que el motor sabe aplicar. La que usa el IPS es la
# Cuestión abierta #6; mientras no se verifique, la regla declara cuál se aplicó.
POLITICAS = {"ROUND_HALF_UP": ROUND_HALF_UP}
DECIMALES_POR_DEFECTO = 2


def _regla(reglas: ConjuntoDeReglas, regla_id: str) -> Regla:
    regla = reglas.por_id(regla_id)
    if regla is None:  # pragma: no cover - lo cubre el test de carga de reglas
        msg = f"falta la regla {regla_id} en el conjunto {reglas.version}"
        raise ValueError(msg)
    return regla


def base_bonificable(valor: ValorCargo) -> Decimal:
    """La parte del cargo sobre la que se aplica la antigüedad (FR-031b).

    Nunca el total: una suma fija no bonificable queda afuera por definición, y
    meterla en la base es el error que más infla un haber sin levantar sospecha.
    """
    return sum(
        (c.importe for c in valor.componentes if c.bonificable),
        start=Decimal(0),
    )


def _por_criterio(valor: ValorCargo, criterio: str) -> Decimal:
    """Suma los componentes que el criterio incluye.

    * `componentes_con_aporte_ips` es el criterio **aplicado**: los conceptos
      sobre los que se calcula el aporte personal al IPS. Se verificó en la
      liquidación DGCyE 09/2026 que el aporte es el 16 % exacto de esa base, y
      los arts. 4 y 5 atan el sistema al aporte. Un componente que no declara
      si tributa queda afuera y se informa: suponer que sí lo infla y suponer
      que no lo achica, y las dos cosas serían inventar.
    * `todos_los_componentes_del_cargo` es la lectura amplia de la letra del
      art. 40, que da **más**: incluye también los no remunerativos sin aporte.
      La exclusión del art. 40 la declara la grilla con `excluido_art40`.
    * `componentes_remunerativos` es la lectura restrictiva.

    En las tres, los componentes que el art. 40 excluye expresamente quedan
    afuera: la exclusión es de la norma y no del criterio.
    """
    if criterio == "componentes_con_aporte_ips":
        incluidos = (c for c in valor.componentes if c.aporte_ips and not c.excluido_art40)
    elif criterio == "todos_los_componentes_del_cargo":
        incluidos = (c for c in valor.componentes if not c.excluido_art40)
    elif criterio == "componentes_remunerativos":
        incluidos = (c for c in valor.componentes if c.remunerativo and not c.excluido_art40)
    else:  # pragma: no cover - los criterios cargados están arriba
        msg = f"criterio de remuneración no implementado: {criterio!r}"
        raise ValueError(msg)
    return sum((c.importe for c in incluidos), start=Decimal(0))


def remuneracion_del_cargo(valor: ValorCargo, *, reglas: ConjuntoDeReglas) -> Decimal:
    """La «remuneración asignada al cargo» del art. 40 (FR-031, Cuestión #2).

    El criterio aplicado sale de la regla y son los **componentes con aporte al
    IPS**: los arts. 4 y 5 atan el sistema al aporte, y la liquidación DGCyE
    09/2026 muestra el aporte personal como el 16 % exacto de esa base. Tiene
    la ventaja de ser verificable contra un recibo, que la letra del art. 40 no
    es.

    Qué conceptos integran el **haber** sigue sin verificarse (Cuestión abierta
    #2): que un concepto tribute no prueba que integre el haber, y eso lo tiene
    que decir una resolución del IPS. La lectura amplia —incluir también los no
    remunerativos sin aporte, como el FONID— se informa como alternativa al
    alza. Por eso el monto sale provisional igual.
    """
    regla = _regla(reglas, REGLA_REMUNERACION)
    criterio = str((regla.valor or {}).get("criterio_aplicado"))
    return _por_criterio(valor, criterio)


def remuneracion_alternativa(
    valor: ValorCargo, *, reglas: ConjuntoDeReglas
) -> tuple[Decimal, Regla] | None:
    """La remuneración bajo la primera lectura alternativa que difiera.

    Se prueban en orden: primero la amplia —que incluye los no remunerativos
    sin aporte y da más—, después la restrictiva. Devuelve `None` cuando
    ninguna cambia el número: informar una alternativa que no mueve nada sería
    ruido (Principio VIII).
    """
    aplicada = remuneracion_del_cargo(valor, reglas=reglas)
    for regla_id in REGLAS_REMUNERACION_ALTERNATIVAS:
        alternativa = reglas.por_id(regla_id)
        if not _rige(alternativa):
            continue
        criterio = str((alternativa.valor or {}).get("criterio_aplicado"))
        otra = _por_criterio(valor, criterio)
        if otra != aplicada:
            return otra, alternativa
    return None


def _escala(regla: Regla) -> tuple[tuple[int, Decimal], ...]:
    """Los tramos de una escala, ordenados de mayor a menor antigüedad.

    De mayor a menor para que la búsqueda tome el tramo más alto alcanzado y no
    el primero que se cumpla.
    """
    crudos = (regla.valor or {}).get("escala")
    if not isinstance(crudos, list):
        return ()
    tramos: list[tuple[int, Decimal]] = []
    for tramo in crudos:
        if not isinstance(tramo, dict):  # pragma: no cover - lo impide el schema
            continue
        anios, porcentaje = tramo.get("anios"), tramo.get("porcentaje")
        if isinstance(anios, int) and not isinstance(anios, bool) and porcentaje is not None:
            tramos.append((anios, Decimal(str(porcentaje))))
    return tuple(sorted(tramos, key=lambda t: t[0], reverse=True))


def _porcentaje_de(regla: Regla, anios: int) -> Decimal | None:
    """El tramo que corresponde a esa antigüedad, o `None` si no alcanza ninguno.

    Se aplica un tope solo si la regla lo declara. El Decreto 818/13 no declara
    ninguno: su último tramo es el de 24 años y más allá el porcentaje se
    mantiene, que es lo que sale naturalmente de tomar el tramo más alto
    alcanzado. La Ley 10.579 sí declara tope, y ahí sí acota.
    """
    for desde, porcentaje in _escala(regla):
        if anios >= desde:
            tope = (regla.valor or {}).get("tope")
            return min(porcentaje, Decimal(str(tope))) if tope is not None else porcentaje
    return None


def porcentaje_de_antiguedad(anios: int, *, reglas: ConjuntoDeReglas) -> Decimal | None:
    """El porcentaje de la escala de antigüedad aplicada (FR-032).

    La escala es la del **Decreto 818/13, Anexo Único**, transcripta tramo por
    tramo y **verificada** el 2026-11-04 contra una liquidación real: con 26
    años, el código 0220 es 1,25 veces el 0110. El tope es 125 % y coincide con
    el último tramo, el de 24 años, así que más allá de esa antigüedad el
    porcentaje se mantiene.

    Devuelve `None` solo si no hay escala cargada, que es distinto de cero:
    cero sería «la antigüedad no suma», `None` es «el motor no sabe cuánto».
    """
    return _porcentaje_de(_regla(reglas, REGLA_ANTIGUEDAD), anios)


def _rige(regla: Regla | None) -> TypeGuard[Regla]:
    """Si la regla existe y sigue vigente como lectura alternativa.

    Es un `TypeGuard` para que el estrechamiento llegue al llamador: después de
    `if not _rige(x): continue`, `x` es una `Regla` y no `Regla | None`. La
    alternativa era un `assert`, que bandit marca con razón —desaparece con
    `-O`— y que acá no verificaba nada que el tipo no pudiera expresar.

    Una regla con `valor.vigente: false` se conserva por trazabilidad y **no**
    se informa: la escala de la Ley 10.579 dejó de ser alternativa cuando la
    liquidación DGCyE 09/2026 mostró aplicado el 125 % del Decreto 818/13.
    Seguir informándola sembraría una duda que la evidencia ya despejó, y eso
    es ruido (Principio VIII).
    """
    if regla is None:
        return False
    return (regla.valor or {}).get("vigente") is not False


def antiguedad_alternativa(anios: int, *, reglas: ConjuntoDeReglas) -> tuple[Decimal, Regla] | None:
    """El porcentaje bajo una escala alternativa vigente, si difiere.

    Devuelve `None` cuando no hay alternativa vigente —hoy no la hay, desde que
    se verificó la escala del Decreto 818/13— o cuando las dos coinciden en ese
    tramo.
    """
    alternativa = reglas.por_id(REGLA_ANTIGUEDAD_ALTERNATIVA)
    if not _rige(alternativa):
        return None
    otro = _porcentaje_de(alternativa, anios)
    if otro is None or otro == porcentaje_de_antiguedad(anios, reglas=reglas):
        return None
    return otro, alternativa


def adicional_por_antiguedad(valor: ValorCargo, porcentaje: Decimal) -> Decimal:
    """El adicional, calculado **solo** sobre la base bonificable (FR-031b)."""
    return base_bonificable(valor) * porcentaje


def redondear(valor: Decimal, *, reglas: ConjuntoDeReglas) -> Decimal:
    """El único punto de redondeo del motor (FR-033, Principio II).

    La política sale de la regla, no del código: incluso el redondeo es dato.
    Hoy es `ROUND_HALF_UP` a dos decimales, declarado como valor por defecto
    aplicado porque la que usa el IPS es la Cuestión abierta #6.
    """
    regla = _regla(reglas, REGLA_REDONDEO)
    datos = regla.valor or {}
    nombre = datos.get("politica_aplicada")
    modo = POLITICAS.get(str(nombre), ROUND_HALF_UP)
    decimales = datos.get("decimales")
    if not isinstance(decimales, int) or isinstance(decimales, bool):
        decimales = DECIMALES_POR_DEFECTO
    return valor.quantize(Decimal(1).scaleb(-decimales), rounding=modo)


def _advertir_grilla_ausente(
    grilla: GrillaSalarial,
    cese: dt.date,
    *,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
) -> Condicionante | None:
    """FR-034: si la grilla no rige al cese, se dice con cuál se calculó.

    Pasa siempre que se evalúa un cese futuro, que es el caso normal: nadie
    consulta por un cese que ya ocurrió. Un haber a valores de años atrás
    presentado como definitivo es la clase de número convincente y equivocado
    que el Principio X existe para impedir.
    """
    if grilla.vigente_a(cese):
        return None

    traza.agregar_advertencia(
        adv.construir(
            CodigoAdvertencia.GRILLA_AUSENTE,
            f"no hay grilla vigente al {cese.isoformat()}: el monto se calculó con "
            f"la grilla «{grilla.version}», a valores del "
            f"{grilla.vigencia_desde.isoformat()}",
            reglas=reglas,
        )
    )
    return cond.de_situacion(
        CodigoAdvertencia.GRILLA_AUSENTE,
        f"qué grilla rige al {cese.isoformat()}: la vigente no está cargada y el "
        f"monto se valuó con «{grilla.version}», del "
        f"{grilla.vigencia_desde.isoformat()}",
    )


def _citar_alternativa(
    regla: Regla, monto_alternativo: Decimal, aplicado: Decimal, *, traza: Trazador
) -> None:
    """Deja en el desglose una lectura que el motor **no** aplica (Principio IV).

    Mismo criterio que con el incremento multiplicativo del art. 43: el
    profesional ve el número aplicado y ve el otro, en lugar de descubrirlo
    cuando el IPS resuelve.
    """
    sentido = (regla.valor or {}).get("sentido", "indeterminado")
    traza.paso_suelto(
        f"Lectura alternativa: {regla.norma.texto.split('(')[0].strip()}",
        regla_id=regla.id,
        norma=regla.norma,
        tipo_fuente=regla.tipo,
        entrada=f"aplicado: {aplicado}",
        salida=f"{monto_alternativo} bajo esta lectura (sentido {sentido}); no se aplica",
    )


def valuar(
    cargo: str,
    cese: dt.date,
    porcentaje: Decimal,
    *,
    antiguedad_anios: int,
    grilla: GrillaSalarial,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    condicionantes_previos: tuple[Condicionante, ...] = (),
) -> Monto | None:
    """El haber estimado del cargo base, o `None` si la grilla no lo tiene.

    `None` no es un error: significa que la grilla cargada no trae ese cargo, y
    el llamador lo informa. Inventar un valor sería peor.
    """
    valor = grilla.cargo(cargo)
    if valor is None:
        traza.agregar_advertencia(
            adv.construir(
                CodigoAdvertencia.GRILLA_AUSENTE,
                f"la grilla «{grilla.version}» no trae el cargo base: no se puede valuar el haber",
                reglas=reglas,
            )
        )
        return None

    remuneracion = remuneracion_del_cargo(valor, reglas=reglas)
    regla_remuneracion = _regla(reglas, REGLA_REMUNERACION)
    excluidos = [c.codigo_concepto for c in valor.componentes if c.excluido_art40]
    traza.paso(
        f"Remuneración asignada al cargo «{cargo}»",
        regla_remuneracion,
        entrada=f"grilla {grilla.version}, {len(valor.componentes)} componentes",
        salida=(
            f"{remuneracion} por la letra del art. 40: todos los componentes del "
            f"cargo" + (f", excepto {', '.join(excluidos)}" if excluidos else " (ninguno excluido)")
        ),
    )

    otra_remuneracion = remuneracion_alternativa(valor, reglas=reglas)
    if otra_remuneracion is not None:
        _citar_alternativa(otra_remuneracion[1], otra_remuneracion[0], remuneracion, traza=traza)

    pct_antiguedad = porcentaje_de_antiguedad(antiguedad_anios, reglas=reglas)
    adicional = (
        adicional_por_antiguedad(valor, pct_antiguedad)
        if pct_antiguedad is not None
        else Decimal(0)
    )
    regla_antiguedad = _regla(reglas, REGLA_ANTIGUEDAD)
    traza.paso(
        "Bonificación por antigüedad",
        regla_antiguedad,
        entrada=(
            f"{antiguedad_anios} años de antigüedad; base bonificable {base_bonificable(valor)}"
        ),
        salida=(
            f"{pct_antiguedad} sobre la base bonificable = {adicional}"
            if pct_antiguedad is not None
            else (
                "no se aplica: el conjunto de reglas no trae la escala de "
                "antigüedad. El haber queda por debajo del real"
            )
        ),
    )

    otra_antiguedad = antiguedad_alternativa(antiguedad_anios, reglas=reglas)
    if otra_antiguedad is not None and pct_antiguedad is not None:
        _citar_alternativa(
            otra_antiguedad[1],
            adicional_por_antiguedad(valor, otra_antiguedad[0]),
            adicional,
            traza=traza,
        )

    regla_haber = _regla(reglas, REGLA_HABER)
    bruto = (remuneracion + adicional) * porcentaje
    monto = redondear(bruto, reglas=reglas)
    traza.paso(
        "Haber estimado",
        regla_haber,
        entrada=f"({remuneracion} + {adicional}) por {porcentaje}",
        salida=f"{monto}",
    )

    condicionantes = list(condicionantes_previos)
    ausente = _advertir_grilla_ausente(grilla, cese, reglas=reglas, traza=traza)
    if ausente is not None:
        traza.agregar_condicionante(ausente)
        condicionantes.append(ausente)

    return Monto(
        valor=monto,
        # Ningún haber de la v1 es definitivo: las Cuestiones #1, #2 y #6
        # condicionan a todos, y el modelo exige que la marca viaje con el valor.
        estado=EstadoResultado.PROVISIONAL,
        condicionantes=tuple({c.referencia: c for c in condicionantes}.values()),
        grilla_version=grilla.version,
        a_valores_de=grilla.vigencia_desde,
    )
