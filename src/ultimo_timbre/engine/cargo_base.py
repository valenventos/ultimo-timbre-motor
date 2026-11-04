# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Determinación del cargo base del art. 41 (T121 a T126).

`[DL 9650/80, art. 41 (texto Ley 13968); Res. IPS 14/10]`

El conteo se resuelve sobre un **conjunto de meses calendario**, no sobre
deltas de días (research R2): «60 alternados» es la cardinalidad del conjunto y
«36 consecutivos» la racha máxima en la secuencia ordenada. Eso lo hace exacto
—sin «un mes = 30 días», que el Principio II prohíbe— y permite exponer qué
meses concretos sustentan el cargo, que es lo que exige FR-020.

Los meses se cuentan sobre la **unión** de los tramos (FR-004a, invariante I9):
dos períodos simultáneos del mismo cargo aportan cada mes una vez.

## El límite real de la v1: la jerarquía

El art. 41 habla del cargo «de mayor jerarquía», y el criterio para comparar
jerarquías es la **Cuestión abierta #4**: ninguna norma citada documenta un
orden numérico, así que `rules/v1/cargos.yaml` lleva `jerarquia: null` en todos
los cargos y este módulo **no puede rankear** con los datos de la v1.

Lo que hace entonces no es inventar un orden, sino decir que no lo tiene:
advierte `empate_jerarquia`, expone los candidatos empatados con su razón y
marca el cargo base provisional. El desempate que igual necesita para devolver
un cargo —más meses, después alfabético— es un criterio de **determinismo**
(invariante I3), no normativo, y está declarado como tal en `_elegir`.

El algoritmo de ranking está implementado y probado de todos modos, porque
entra en servicio el día que el criterio se verifique. La suite lo ejercita con
jerarquía ficticia (`tests/catalogos.py`), igual que ejercita los montos con la
grilla ficticia.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Set
from decimal import Decimal
from itertools import pairwise
from typing import NamedTuple

from ultimo_timbre.engine import advertencias as adv
from ultimo_timbre.engine import calendario, haber
from ultimo_timbre.engine import condicionantes as cond
from ultimo_timbre.engine.desglose import Trazador
from ultimo_timbre.errors import FueraDeAlcance
from ultimo_timbre.models.caso import Caso, HistoriaDeServicios, MesCalendario
from ultimo_timbre.models.enums import (
    CodigoAdvertencia,
    CondicionAlFrente,
    EstadoResultado,
    SituacionRevista,
    ViaCargoBase,
)
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import CandidatoDescartado, CargoBase
from ultimo_timbre.models.normativa import ConjuntoDeReglas, Regla

__all__ = ["cuenta_al_frente", "determinar", "meses_del_cargo", "racha_maxima"]

REGLA_PLAZOS = "haber.art41.cargo_base"
REGLA_INFERIOR = "haber.art41.cargo_inferior"
REGLA_PROMEDIO = "haber.art41.promedio_36"
REGLA_JERARQUIA = "jerarquia.criterio_comparacion"
REGLA_HORAS_CATEDRA = "horas_catedra.como_carrera"
REGLA_REVISTA = "computo.licencias_suplencias_y_revista"


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


def cuenta_al_frente(cargo: str, reglas: ConjuntoDeReglas) -> bool | None:
    """Si el cargo cuenta al frente de alumnos según el catálogo.

    `None` es **indeterminado**, y no equivale a `False`: el cargo no está en
    el catálogo, o su condición depende de un umbral de horas cátedra que acá
    no se resuelve. Lo necesita la Cuestión abierta #9 para decidir si el
    art. 43 se aplica sobre el cargo base (ver `engine.porcentaje.regimen`).
    """
    entrada = reglas.catalogo_cargos.buscar(cargo)
    if entrada is None or entrada.condicion is not CondicionAlFrente.DIRECTA:
        return None
    return entrada.al_frente_de_alumnos


def racha_maxima(meses: Set[MesCalendario]) -> int:
    """La cantidad de meses consecutivos más larga del conjunto.

    Opera sobre el `ordinal` absoluto de cada mes, así que diciembre y enero
    son consecutivos sin ningún caso especial por el corte de año.
    """
    if not meses:
        return 0
    ordinales = sorted(m.ordinal for m in meses)
    mejor = actual = 1
    for previo, siguiente in pairwise(ordinales):
        actual = actual + 1 if siguiente == previo + 1 else 1
        mejor = max(mejor, actual)
    return mejor


def meses_del_cargo(
    historia: HistoriaDeServicios,
    cese: dt.date,
    cargo: str,
    *,
    idx_incluidos: Set[int] | None = None,
) -> frozenset[MesCalendario]:
    """Los meses calendario cubiertos por un cargo, sobre la unión de tramos.

    `idx_incluidos` restringe a los períodos que el motor puede computar: un
    tramo fuera de alcance no sustenta un cargo base (FR-044, FR-045).
    """
    idx = {
        p.idx
        for p in historia.periodos
        if p.cargo == cargo and (idx_incluidos is None or p.idx in idx_incluidos)
    }
    if not idx:
        return frozenset()
    return calendario.meses_cubiertos(historia, cese, idx_incluidos=idx)


class _Candidato(NamedTuple):
    """Un cargo de la historia medido contra los plazos del art. 41."""

    cargo: str
    meses: frozenset[MesCalendario]
    racha: int
    jerarquia: int | None
    via: ViaCargoBase | None
    """`None` significa que no alcanza ni los 36 consecutivos ni los 60 alternados."""
    remuneracion: Decimal | None = None
    """Lo que el cargo remunera según la grilla, o `None` si no hay grilla."""
    indice: Decimal | None = None
    """Índice escalafonario, o `None` si no está verificado o es por hora."""


def _candidatos(
    caso: Caso,
    cese: dt.date,
    *,
    reglas: ConjuntoDeReglas,
    idx_en_alcance: Set[int],
    consecutivos: int,
    alternados: int,
    grilla: GrillaSalarial | None,
) -> tuple[_Candidato, ...]:
    cargos = sorted({p.cargo for p in caso.historia.periodos if p.idx in idx_en_alcance})
    salida: list[_Candidato] = []
    for cargo in cargos:
        meses = meses_del_cargo(caso.historia, cese, cargo, idx_incluidos=idx_en_alcance)
        racha = racha_maxima(meses)
        entrada = reglas.catalogo_cargos.buscar(cargo)
        via = (
            ViaCargoBase.CONSECUTIVOS_36
            if racha >= consecutivos
            else ViaCargoBase.ALTERNADOS_60
            if len(meses) >= alternados
            else None
        )
        # Un índice por hora no se compara con uno por cargo: mezclar las dos
        # magnitudes da un resultado que parece válido y no lo es.
        indice = (
            entrada.indice_escalafonario
            if entrada is not None and not entrada.indice_es_por_hora
            else None
        )
        salida.append(
            _Candidato(
                cargo=cargo,
                meses=meses,
                racha=racha,
                jerarquia=entrada.jerarquia if entrada is not None else None,
                via=via,
                remuneracion=_remuneracion(cargo, grilla, reglas),
                indice=indice,
            )
        )
    return tuple(salida)


def _remuneracion(
    cargo: str, grilla: GrillaSalarial | None, reglas: ConjuntoDeReglas
) -> Decimal | None:
    """Lo que el cargo remunera según la grilla, o `None` si no se puede saber.

    `None` cuando no hay grilla o cuando la grilla no trae ese cargo. En los dos
    casos el criterio de «mejor remunerado» no se puede aplicar y el motor cae
    al siguiente, en lugar de inventar un cero que lo dejaría último.
    """
    if grilla is None:
        return None
    valor = grilla.cargo(cargo)
    if valor is None:
        return None
    return haber.remuneracion_del_cargo(valor, reglas=reglas)


CRITERIOS = {
    "remuneracion": "remuneración (Res. IPS 995/2021)",
    "indice": "índice escalafonario del nomenclador",
}


def _detalle_del_criterio(elegido: _Candidato, criterio: str) -> str:
    if criterio == "remuneracion":
        return f"remunera {elegido.remuneracion} según la grilla"
    return f"índice escalafonario {elegido.indice}"


def _mejor_por(califican: tuple[_Candidato, ...], atributo: str) -> tuple[_Candidato, ...] | None:
    """Los candidatos con el valor más alto de un atributo, o `None` si falta.

    Devuelve `None` en cuanto **alguno** no lo tiene: comparar un número contra
    un `None` sería inventar un orden. Que falte en uno basta para que el
    criterio entero no se pueda aplicar.
    """
    valores = [getattr(c, atributo) for c in califican]
    if any(v is None for v in valores):
        return None
    tope = max(v for v in valores if v is not None)
    return tuple(c for c in califican if getattr(c, atributo) == tope)


def _elegir(califican: tuple[_Candidato, ...]) -> tuple[_Candidato, tuple[_Candidato, ...], str]:
    """El cargo elegido, los que empataron con él y con qué criterio se eligió.

    Tres criterios, en orden de **verificabilidad**:

    1. **remuneración** (`Res. IPS 995/2021`, Anexo, definición de CARGO BASE):
       el cargo mejor remunerado. Es el mejor de los tres porque se verifica
       contra la grilla sin necesitar el escalafón, que es justamente lo que no
       está publicado;
    2. **índice escalafonario** del nomenclador, cuando no hay grilla. Es
       verificable contra la norma, pero hoy ninguna entrada lo declara;
    3. **nada**: se declara el empate y el cargo base sale provisional.

    El desempate final —más meses, después alfabético— no es ninguno de los
    tres: existe solo para que el resultado sea reproducible (invariante I3), y
    por eso cuando decide, el informe sale con `empate_jerarquia`.
    """
    for criterio, atributo in (("remuneracion", "remuneracion"), ("indice", "indice")):
        mejores = _mejor_por(califican, atributo)
        if mejores is not None and len(mejores) == 1:
            return mejores[0], mejores, criterio

    elegido = min(califican, key=lambda c: (-len(c.meses), c.cargo))
    return elegido, califican, "empate"


# Qué atributo mira cada criterio. Vive acá y no repartido para que elegir el
# cargo base y detectar el descenso usen, por construcción, la misma vara.
ATRIBUTO_DEL_CRITERIO = {"remuneracion": "remuneracion", "indice": "indice"}


def _descenso_desde(
    candidatos: tuple[_Candidato, ...], elegido: _Candidato, criterio: str
) -> str | None:
    """El cargo superior que no alcanzó los plazos, si lo hay (FR-020a).

    Se compara con **el mismo criterio** que eligió el cargo base: si el motor
    eligió por remuneración, «superior» significa mejor remunerado; si eligió
    por índice, mayor índice. Usar dos varas distintas para elegir y para
    descender podría producir un informe que afirme un descenso desde un cargo
    que, por el criterio aplicado, no era superior.

    Devuelve `None` cuando el criterio fue el empate: sin vara no existe
    «superior» ni «inferior», solo candidatos.
    """
    atributo = ATRIBUTO_DEL_CRITERIO.get(criterio)
    if atributo is None:
        return None
    referencia = getattr(elegido, atributo)
    if referencia is None:  # pragma: no cover - el criterio lo garantiza
        return None

    superiores = [
        c
        for c in candidatos
        if c.via is None and getattr(c, atributo) is not None and getattr(c, atributo) > referencia
    ]
    if not superiores:
        return None
    return max(superiores, key=lambda c: (getattr(c, atributo), c.cargo)).cargo


def _razon_del_descarte(
    candidato: _Candidato,
    elegido: _Candidato,
    empatados: tuple[_Candidato, ...],
    criterio: str,
    *,
    consecutivos: int,
    alternados: int,
) -> str:
    if candidato.via is None:
        return (
            f"no alcanza los {consecutivos} meses consecutivos ni los "
            f"{alternados} alternados: llegó a {len(candidato.meses)} meses "
            f"con una racha máxima de {candidato.racha}"
        )
    if criterio == "remuneracion":
        return (
            f"remunera {candidato.remuneracion} contra {elegido.remuneracion} de «{elegido.cargo}»"
        )
    if criterio == "indice":
        return (
            f"índice escalafonario {candidato.indice} contra {elegido.indice} de «{elegido.cargo}»"
        )
    if candidato in empatados:
        return (
            f"empate de jerarquía con «{elegido.cargo}»: el criterio de "
            "comparación entre cargos no está verificado"
        )
    return f"menor jerarquía que «{elegido.cargo}»"


def _condicionantes_del_cargo_base(
    caso: Caso,
    *,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    idx_en_alcance: Set[int],
    elegido: _Candidato,
    hay_comparacion: bool,
) -> bool:
    """Registra lo que impide que el cargo base sea definitivo (T126).

    Devuelve si quedó condicionado. Son tres Cuestiones abiertas distintas:

    * **#4** (FR-022): el criterio de jerarquía. Condiciona en cuanto hubo que
      comparar dos cargos, con jerarquía conocida o no: el criterio está sin
      verificar en los dos casos.
    * **#3** (FR-023): horas cátedra y módulos como carrera.
    * **#5** (FR-024, FR-024a): licencias, suplencias y situación de revista
      dentro de los 36/60 meses. El art. 41 habla del cargo «de que era
      titular», así que un cargo sustentado por meses de suplencia es
      exactamente lo que la Cuestión #5 discute.
    """
    condicionado = False

    if hay_comparacion:
        traza.condicionante_de_regla(_regla(reglas, REGLA_JERARQUIA))
        condicionado = True

    por_horas = any(
        (entrada := reglas.catalogo_cargos.buscar(p.cargo)) is not None
        and entrada.condicion is CondicionAlFrente.POR_HORAS_CATEDRA
        for p in caso.historia.periodos
        if p.idx in idx_en_alcance
    )
    if por_horas:
        traza.condicionante_de_regla(_regla(reglas, REGLA_HORAS_CATEDRA))
        condicionado = True

    sustentan = [
        p for p in caso.historia.periodos if p.idx in idx_en_alcance and p.cargo == elegido.cargo
    ]
    if any(p.licencias or p.situacion_revista is not SituacionRevista.TITULAR for p in sustentan):
        traza.condicionante_de_regla(_regla(reglas, REGLA_REVISTA))
        condicionado = True

    return condicionado


def determinar(
    caso: Caso,
    cese: dt.date,
    *,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    idx_en_alcance: Set[int],
    grilla: GrillaSalarial | None = None,
) -> CargoBase | None:
    """El cargo base del art. 41, o `None` si corresponde el promedio de 36 meses.

    `None` no es un error: es el caso del tercer párrafo del art. 41, que la v1
    detecta e informa sin calcular (FR-020b, Principio X).
    """
    plazos = _regla(reglas, REGLA_PLAZOS)
    consecutivos = _entero(plazos, "meses_consecutivos") or 0
    alternados = _entero(plazos, "meses_alternados") or 0

    candidatos = _candidatos(
        caso,
        cese,
        reglas=reglas,
        idx_en_alcance=idx_en_alcance,
        consecutivos=consecutivos,
        alternados=alternados,
        grilla=grilla,
    )

    # FR-021: cada candidato con sus meses queda en el desglose, incluso si al
    # final ninguno califica. Es la cuenta que un expediente necesita revisar.
    for c in candidatos:
        traza.paso(
            f"Cargo candidato «{c.cargo}» para el cargo base",
            plazos,
            entrada=f"{len(c.meses)} meses cubiertos; racha máxima {c.racha}",
            salida=(
                f"{c.cargo}: califica por {c.via.value}"
                if c.via is not None
                else (
                    f"{c.cargo}: descartado, no alcanza {consecutivos} meses "
                    f"consecutivos ni {alternados} alternados"
                )
            ),
        )

    califican = tuple(c for c in candidatos if c.via is not None)
    if not califican:
        _advertir_promedio_36(candidatos, reglas=reglas, traza=traza)
        return None

    elegido, empatados, criterio = _elegir(califican)
    hay_empate = criterio == "empate" and len(califican) > 1

    if criterio != "empate":
        traza.paso(
            f"Cargo base elegido por {CRITERIOS[criterio]}",
            _regla(reglas, REGLA_JERARQUIA),
            entrada="candidatos: " + ", ".join(c.cargo for c in califican),
            salida=f"«{elegido.cargo}» {_detalle_del_criterio(elegido, criterio)}",
        )
    descenso = _descenso_desde(candidatos, elegido, criterio)

    # `elegido` sale de `califican`, donde todos tienen vía: si llegara sin
    # ella, el motor eligió un cargo que no califica y eso es un error de
    # programación, no un caso de usuario (para eso existe `FueraDeAlcance`).
    if elegido.via is None:  # pragma: no cover - lo garantiza `califican`
        msg = f"el cargo base «{elegido.cargo}» no califica por ninguna vía del art. 41"
        raise FueraDeAlcance(msg)
    via = ViaCargoBase.CARGO_INFERIOR if descenso is not None else elegido.via

    if hay_empate:
        traza.agregar_advertencia(
            adv.construir(
                CodigoAdvertencia.EMPATE_JERARQUIA,
                "los cargos "
                + ", ".join(f"«{c.cargo}»" for c in empatados)
                + " alcanzan los plazos del art. 41 y el criterio para comparar "
                "su jerarquía no está verificado: la elección no es definitiva",
                reglas=reglas,
            )
        )

    if descenso is not None:
        traza.paso(
            f"Descenso al cargo inferior: de «{descenso}» a «{elegido.cargo}»",
            _regla(reglas, REGLA_INFERIOR),
            entrada=f"«{descenso}» no alcanza los plazos del art. 41",
            salida=(
                f"se considera comprendida en «{elegido.cargo}», que sí los "
                f"alcanza con {len(elegido.meses)} meses"
            ),
        )

    condicionado = _condicionantes_del_cargo_base(
        caso,
        reglas=reglas,
        traza=traza,
        idx_en_alcance=idx_en_alcance,
        elegido=elegido,
        hay_comparacion=len(candidatos) > 1,
    )

    traza.paso(
        f"Cargo base: «{elegido.cargo}»",
        plazos,
        entrada="candidatos: " + ", ".join(c.cargo for c in candidatos),
        salida=f"«{elegido.cargo}» por {via.value}, con {len(elegido.meses)} meses",
    )

    return CargoBase(
        cargo=elegido.cargo,
        via=via,
        meses_que_lo_sustentan=tuple(str(m) for m in sorted(elegido.meses)),
        descartados=tuple(
            CandidatoDescartado(
                cargo=c.cargo,
                razon=_razon_del_descarte(
                    c,
                    elegido,
                    empatados,
                    criterio,
                    consecutivos=consecutivos,
                    alternados=alternados,
                ),
                meses_alcanzados=len(c.meses),
            )
            for c in candidatos
            if c.cargo != elegido.cargo
        ),
        estado=(
            EstadoResultado.PROVISIONAL
            if (hay_empate or condicionado)
            else EstadoResultado.DEFINITIVO
        ),
        norma=plazos.norma,
        descenso_desde=descenso,
    )


def _advertir_promedio_36(
    candidatos: tuple[_Candidato, ...],
    *,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
) -> None:
    """El tercer párrafo del art. 41: se detecta y se informa, no se calcula.

    Calcularlo a medias sería peor que no calcularlo: el número saldría igual
    de convincente que uno correcto (Principio X).
    """
    detalle = (
        ", ".join(f"«{c.cargo}» {len(c.meses)} meses" for c in candidatos)
        if candidatos
        else "sin cargos computables"
    )
    traza.agregar_advertencia(
        adv.construir(
            CodigoAdvertencia.FUERA_DE_ALCANCE_PROMEDIO_36,
            "ningún cargo alcanza los plazos del art. 41 "
            f"({detalle}): correspondería el promedio de 36 meses del tercer "
            "párrafo, que está fuera del Alcance de la v1 y no se calcula",
            reglas=reglas,
        )
    )
    traza.agregar_condicionante(cond.de_situacion(CodigoAdvertencia.FUERA_DE_ALCANCE_PROMEDIO_36))
    traza.paso(
        "Promedio de 36 meses del art. 41, tercer párrafo",
        _regla(reglas, REGLA_PROMEDIO),
        entrada=detalle,
        salida="fuera del Alcance de la v1: se informa y no se calcula",
    )
