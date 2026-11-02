# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Porcentaje aplicable de los arts. 41, 42 y 43 (T127 a T130).

Dos artículos, según por dónde se accede:

* los incs. **c** y **d** van por el **art. 41**: base 70 %, elevado al 75 % y
  al 80 % por excedente de 3 y 5 años (art. 42);
* el inc. **b** va por el **art. 43**: base 75 %, elevado al 80 % y al 85 %.

Ningún porcentaje ni plazo está escrito acá: todos salen de `rules/v1/haber.yaml`
(Principio I, FR-007). El tope del art. 43 es el mayor porcentaje cargado para
el inc. b, no un `0.85` literal en el código, así que el invariante I2 se
sostiene con lo que digan las reglas y no con lo que diga este archivo.

## Desde dónde se cuenta el excedente

Por defecto, desde la fecha en que se cumplen **todas** las condiciones del
inciso —edad **y** servicios—, no desde que se alcanza la edad requerida
`[Res. IPS 995/2021, Anexo, punto 2.1.a — Interpretación]` (FR-027a).

La diferencia es grande y es el caso del escenario 6: una docente que completa
sus 25 años a los 54 tiene cuatro años de edad por encima de los 50 que pide el
inc. b, pero excedente **cero**, porque recién ese día reúne todo. Existe una
lectura literal de los arts. 42 y 43 que mediría el excedente solo por la edad
y le daría 80 % en lugar de 75 %. El motor aplica la interpretación del IPS y
**informa** la otra con su impacto al alza (FR-027b): quien tiene que decidir
si la discute es el profesional, no el motor.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from ultimo_timbre.engine.desglose import Trazador
from ultimo_timbre.models.enums import CodigoAdvertencia, SentidoImpacto, TipoFuente
from ultimo_timbre.models.informe import LecturaAlternativa
from ultimo_timbre.models.normativa import ConjuntoDeReglas, Regla

__all__ = [
    "ART_41",
    "ART_43",
    "anios_de_excedente",
    "base",
    "determinar",
    "escalones",
    "fechas_de_excedente",
    "lectura_literal",
    "regimen",
    "tope",
]

# El **régimen de porcentaje**, que no siempre coincide con el inciso de
# acceso. Normalmente el inc. b va por el art. 43 y los incs. c y d por el
# art. 41 con los excedentes del art. 42; la Cuestión abierta #9 es el caso en
# que no (ver `regimen`).
ART_43 = "art43"
ART_41 = "art41"

REGLA_BASE: dict[str, str] = {
    ART_43: "haber.art43.base",
    ART_41: "haber.art41.base",
}
REGLAS_EXCEDENTE: dict[str, tuple[str, ...]] = {
    ART_43: ("haber.art43.excedente_3", "haber.art43.excedente_5"),
    ART_41: ("haber.art42.excedente_3", "haber.art42.excedente_5"),
}
REGLA_COMPUTO = "excedente.computo_desde"
REGLA_LITERAL = "excedente.lectura_literal"
REGLA_CUESTION_9 = "porcentaje.art43.cargo_base_no_al_frente"
# La lectura multiplicativa del art. 43, que no se aplica y se cita en el
# desglose cuando el excedente del art. 43 entra en juego (Principio I).
REGLAS_MULTIPLICATIVA: dict[int, str] = {
    3: "haber.art43.excedente_3.lectura_multiplicativa",
    5: "haber.art43.excedente_5.lectura_multiplicativa",
}


def _regla(reglas: ConjuntoDeReglas, regla_id: str) -> Regla:
    regla = reglas.por_id(regla_id)
    if regla is None:  # pragma: no cover - lo cubre el test de carga de reglas
        msg = f"falta la regla {regla_id} en el conjunto {reglas.version}"
        raise ValueError(msg)
    return regla


def _porcentaje(regla: Regla) -> Decimal:
    """El porcentaje de una regla, como `Decimal` exacto.

    Viaja como `str` en el YAML justamente para que no pase por `float`: un
    `number` se convierte a binario antes de que el modelo lo vea y ahí el
    error ya es invisible (research R1, Principio II).
    """
    valor = (regla.valor or {}).get("porcentaje")
    return Decimal(str(valor)) if valor is not None else Decimal(0)


def regimen(inciso: str, *, cargo_base_al_frente: bool | None = None) -> str:
    """Qué artículo rige el porcentaje, que no siempre es el del inciso de acceso.

    **Cuestión abierta #9**: si la docente cumple el inc. b por sus años al
    frente de alumnos pero su cargo base es un cargo que **no** cuenta al
    frente —un directivo—, no está verificado si corresponde el 75 % del
    art. 43 sobre ese cargo base o el 70 % del art. 41. El motor aplica el
    art. 41, que es el criterio más conservador: de los dos errores posibles,
    prometer un haber mayor que el que el IPS liquida es el que le cuesta plata
    al docente.

    `cargo_base_al_frente` es `None` cuando no se sabe —cargo fuera de
    catálogo, o condición por horas cátedra sin resolver—. En ese caso la
    Cuestión #9 no se activa: esos cargos ya arrastran su propio condicionante,
    y degradar además el porcentaje sería castigar dos veces la misma duda.
    """
    if inciso == "b" and cargo_base_al_frente is False:
        return ART_41
    return ART_43 if inciso == "b" else ART_41


def base(
    inciso: str, reglas: ConjuntoDeReglas, *, cargo_base_al_frente: bool | None = None
) -> Decimal:
    """El porcentaje de base del artículo que rige el porcentaje."""
    clave = regimen(inciso, cargo_base_al_frente=cargo_base_al_frente)
    return _porcentaje(_regla(reglas, REGLA_BASE[clave]))


def escalones(
    inciso: str, reglas: ConjuntoDeReglas, *, cargo_base_al_frente: bool | None = None
) -> tuple[tuple[int, Regla], ...]:
    """Los excedentes del régimen aplicable, de mayor a menor cantidad de años.

    De mayor a menor para que la búsqueda tome el escalón más alto alcanzado y
    no el primero que se cumpla.
    """
    clave = regimen(inciso, cargo_base_al_frente=cargo_base_al_frente)
    pares: list[tuple[int, Regla]] = []
    for regla_id in REGLAS_EXCEDENTE[clave]:
        regla = _regla(reglas, regla_id)
        anios = (regla.valor or {}).get("anios_excedente")
        if isinstance(anios, int) and not isinstance(anios, bool):
            pares.append((anios, regla))
    return tuple(sorted(pares, key=lambda par: par[0], reverse=True))


def tope(
    inciso: str, reglas: ConjuntoDeReglas, *, cargo_base_al_frente: bool | None = None
) -> Decimal:
    """El máximo legal del artículo aplicable (invariante I2, FR-028).

    Sale de las reglas: es el mayor porcentaje cargado para el régimen que rige
    el porcentaje, contando la base y todos sus excedentes. No hay ningún tope
    literal en el código.
    """
    al_frente = cargo_base_al_frente
    return max(
        [
            base(inciso, reglas, cargo_base_al_frente=al_frente),
            *[
                _porcentaje(regla)
                for _, regla in escalones(inciso, reglas, cargo_base_al_frente=al_frente)
            ],
        ]
    )


def anios_de_excedente(desde: dt.date, hasta: dt.date) -> int:
    """Años enteros cumplidos entre las dos fechas, nunca negativos.

    Cuenta aniversarios, no días divididos por 365: un excedente de 3 años se
    alcanza el día del tercer aniversario y no 364 días antes (Principio II).
    Si el cese es anterior a la habilitación no hay excedente: no se puede
    exceder un derecho que todavía no nació.
    """
    if hasta < desde:
        return 0
    anios: int = relativedelta(hasta, desde).years
    return max(0, anios)


def fechas_de_excedente(desde: dt.date, anios: Iterable[int]) -> dict[int, dt.date]:
    """La fecha exacta en que se alcanza cada excedente (FR-029).

    Tienen que ser utilizables como fecha de cese, así que son fechas de
    calendario reales: `relativedelta` resuelve el 29 de febrero sin inventar
    un 30 de febrero.
    """
    return {n: desde + relativedelta(years=n) for n in anios}


def determinar(
    inciso: str,
    habilitado_desde: dt.date,
    cese: dt.date,
    *,
    reglas: ConjuntoDeReglas,
    cargo_base_al_frente: bool | None = None,
) -> Decimal:
    """El porcentaje aplicable, acotado al máximo legal del artículo.

    El tope se aplica siempre, aunque los escalones cargados nunca lo superen:
    es el invariante I2 y tiene que sostenerse ante cualquier combinación de
    entradas, incluidas las que todavía no existen en las reglas (FR-028).

    `cargo_base_al_frente` activa la Cuestión abierta #9 cuando es `False`: ver
    `regimen`.
    """
    al_frente = cargo_base_al_frente
    excedente = anios_de_excedente(habilitado_desde, cese)
    aplicada, _ = _regla_aplicada(inciso, excedente, reglas=reglas, cargo_base_al_frente=al_frente)
    return min(_porcentaje(aplicada), tope(inciso, reglas, cargo_base_al_frente=al_frente))


def _regla_aplicada(
    inciso: str,
    excedente: int,
    *,
    reglas: ConjuntoDeReglas,
    cargo_base_al_frente: bool | None = None,
) -> tuple[Regla, int | None]:
    """La regla que fija el porcentaje y el escalón alcanzado, si hubo uno."""
    al_frente = cargo_base_al_frente
    for anios, regla in escalones(inciso, reglas, cargo_base_al_frente=al_frente):
        if excedente >= anios:
            return regla, anios
    clave = regimen(inciso, cargo_base_al_frente=al_frente)
    return _regla(reglas, REGLA_BASE[clave]), None


def lectura_literal(
    *,
    inciso: str,
    habilitado_desde: dt.date,
    cese: dt.date,
    fecha_edad_requerida: dt.date,
    aplicado: Decimal,
    reglas: ConjuntoDeReglas,
    cargo_base_al_frente: bool | None = None,
) -> LecturaAlternativa | None:
    """El porcentaje bajo la lectura literal de los arts. 42 y 43 (FR-027b).

    Esa lectura mide el excedente **solo por la edad** respecto de la requerida
    por el inciso, y por eso puede dar más que el criterio aplicado. Devuelve
    `None` cuando no da más: advertir una alternativa que no cambia nada sería
    ruido, y el Principio VIII pide lo contrario.

    `habilitado_desde` no entra en la cuenta —es justamente lo que esta lectura
    ignora— pero queda en la firma porque es lo que la hace legible frente al
    criterio aplicado.
    """
    del habilitado_desde
    al_frente = cargo_base_al_frente
    regla = _regla(reglas, REGLA_LITERAL)
    excedente = anios_de_excedente(fecha_edad_requerida, cese)
    aplicada, _ = _regla_aplicada(inciso, excedente, reglas=reglas, cargo_base_al_frente=al_frente)
    alternativo = min(_porcentaje(aplicada), tope(inciso, reglas, cargo_base_al_frente=al_frente))
    if alternativo <= aplicado:
        return None
    # El sentido sale de la regla, no del código: que esta lectura sea «al
    # alza» es un dato de `excedente.lectura_literal` (Principio I).
    sentido = (regla.valor or {}).get("sentido")
    return LecturaAlternativa(
        porcentaje=alternativo,
        sentido_impacto=(
            SentidoImpacto(sentido) if isinstance(sentido, str) else SentidoImpacto.AL_ALZA
        ),
        norma=regla.norma,
    )


def determinar_con_traza(
    inciso: str,
    habilitado_desde: dt.date,
    cese: dt.date,
    *,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
    cargo_base_al_frente: bool | None = None,
) -> Decimal:
    """`determinar`, dejando en el desglose de dónde salió cada paso (FR-038).

    Son tres cosas distintas y cada una lleva su norma: desde cuándo se cuenta
    el excedente (interpretación del IPS), cuál es la base del artículo, y qué
    escalón se alcanzó. Si la Cuestión abierta #9 interviene, también queda
    dicho por qué el art. 43 no se aplicó.
    """
    al_frente = cargo_base_al_frente
    excedente = anios_de_excedente(habilitado_desde, cese)
    computo = _regla(reglas, REGLA_COMPUTO)
    clave = regimen(inciso, cargo_base_al_frente=al_frente)

    traza.paso(
        "Cómputo del excedente de edad",
        computo,
        entrada=(f"habilitación {habilitado_desde.isoformat()}; cese {cese.isoformat()}"),
        salida=f"excedente de {excedente} años, contado desde todas las condiciones del inciso",
    )

    if inciso == "b" and clave == ART_41:
        _advertir_cuestion_9(reglas=reglas, traza=traza)

    regla_base = _regla(reglas, REGLA_BASE[clave])
    traza.paso(
        f"Porcentaje de base del inc. {inciso}",
        regla_base,
        entrada=f"inciso {inciso}",
        salida=f"{_porcentaje(regla_base)}",
    )

    aplicada, escalon = _regla_aplicada(
        inciso, excedente, reglas=reglas, cargo_base_al_frente=al_frente
    )
    valor = min(_porcentaje(aplicada), tope(inciso, reglas, cargo_base_al_frente=al_frente))

    if escalon is not None:
        traza.paso(
            f"Porcentaje aplicable con excedente de {escalon} años",
            aplicada,
            entrada=f"excedente de {excedente} años",
            salida=f"{valor}",
        )
        if clave == ART_43:
            _citar_lectura_multiplicativa(escalon, reglas=reglas, traza=traza)

    fechas = fechas_de_excedente(
        habilitado_desde,
        [n for n, _ in escalones(inciso, reglas, cargo_base_al_frente=al_frente)],
    )
    traza.paso(
        "Fechas en que se alcanza cada excedente",
        computo,
        entrada=f"habilitación {habilitado_desde.isoformat()}",
        salida="; ".join(f"{n} años: {f.isoformat()}" for n, f in sorted(fechas.items())),
    )
    return valor


def _advertir_cuestion_9(*, reglas: ConjuntoDeReglas, traza: Trazador) -> None:
    """Deja asentado que el art. 43 no se aplicó, y por qué (Cuestión abierta #9).

    Sin esto el informe diría «accede por el inc. b» y liquidaría el 70 % del
    art. 41 sin explicación, que es justo la clase de salto que el Principio IV
    existe para impedir. El condicionante hace el resto: marca el resultado
    provisional y declara la magnitud, 70 % contra 75 %.
    """
    regla = _regla(reglas, REGLA_CUESTION_9)
    base_43 = _porcentaje(_regla(reglas, REGLA_BASE[ART_43]))
    base_41 = _porcentaje(_regla(reglas, REGLA_BASE[ART_41]))

    traza.paso(
        "Porcentaje sobre un cargo base que no cuenta al frente de alumnos",
        regla,
        entrada="accede por el inc. b, pero el cargo base no cuenta al frente de alumnos",
        salida=(
            f"se aplica el {base_41} del art. 41 por ser el criterio más "
            f"conservador; no está verificado si corresponde el {base_43} del "
            "art. 43 sobre ese cargo base"
        ),
    )
    traza.condicionante_de_regla(regla)
    traza.advertencia(
        CodigoAdvertencia.REGLA_NO_VERIFICADA,
        f"cumple el art. 24 inc. b por sus años al frente de alumnos, pero el "
        f"cargo base no cuenta al frente: no está verificado si corresponde el "
        f"{base_43} del art. 43 sobre ese cargo base o el {base_41} del "
        f"art. 41. Se aplica el {base_41}, que es el criterio más conservador",
        norma=regla.norma,
        sentido_impacto=regla.impacto_si_no_verificada,
    )


def _citar_lectura_multiplicativa(
    escalon: int,
    *,
    reglas: ConjuntoDeReglas,
    traza: Trazador,
) -> None:
    """Deja en el desglose la lectura multiplicativa del art. 43 que no se aplica.

    El art. 43 dice que el porcentaje «se incrementará en un cinco por ciento».
    Leerlo como puntos (75 → 80) es una interpretación; la letra admite también
    el incremento multiplicativo (75 por 1,05 = 78,75), que daría menos. El
    criterio aplicado es el de puntos, porque es el único compatible con el
    techo de 85 % del Anexo de la Res. IPS 995/2021. La alternativa se cita
    para que la elección sea auditable y no tácita (Principio I y IV).

    Solo aplica al inc. b: el incremento del art. 43 es el que admite las dos
    lecturas. Los incs. c y d van por el art. 42, cuyos porcentajes están
    escritos como valores y no como incrementos.
    """
    regla_id = REGLAS_MULTIPLICATIVA.get(escalon)
    if regla_id is None:  # pragma: no cover - solo hay escalones de 3 y 5
        return
    alternativa = reglas.por_id(regla_id)
    if alternativa is None:  # pragma: no cover - lo cubre el test de carga de reglas
        return
    traza.paso_suelto(
        "Lectura multiplicativa del art. 43, no aplicada",
        regla_id=regla_id,
        norma=alternativa.norma,
        tipo_fuente=TipoFuente.LETRA_LEY,
        entrada=f"excedente de {escalon} años",
        salida=(
            f"{_porcentaje(alternativa)} bajo la lectura multiplicativa; "
            "se aplica la de puntos porcentuales"
        ),
    )
