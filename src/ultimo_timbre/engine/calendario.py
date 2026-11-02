# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cómputo de tiempo de servicio (T058, research R2).

Tres reglas de este módulo, todas del Principio II:

* el cómputo va **sobre la unión** de los tramos, nunca sumando duraciones de
  períodos superpuestos (FR-004a, invariante I9);
* nada de «un mes = 30 días»: la duración se mide con aritmética de calendario
  y los meses se normalizan a años por definición (12 meses = 1 año), que no es
  una aproximación;
* **sin reloj**: toda fecha entra como argumento (FR-001a).

Los días residuales de cada tramo **no se arrastran** a meses: 20 días + 20 días
quedan en 40 días y no en «1 mes y 10 días». Es deliberado y conservador —nunca
declara cumplido un requisito que no lo está—, porque la regla de arrastre a
nivel de días depende de la Cuestión abierta #5.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Set
from typing import Self

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field

from ultimo_timbre.models.caso import (
    HistoriaDeServicios,
    MesCalendario,
    Tramo,
    unir_tramos,
)
from ultimo_timbre.models.enums import ConvencionConteo

__all__ = [
    "DIAS_POR_MES_ALTERNATIVA",
    "Duracion",
    "dias_cubiertos",
    "dias_de_servicio_faltantes",
    "fecha_al_alcanzar_servicio",
    "horas_catedra_simultaneas",
    "max_horas_catedra_simultaneas",
    "meses_cubiertos",
    "servicio_total",
    "tramos_unidos",
]

MESES_POR_ANIO = 12
DIAS_POR_MES_ALTERNATIVA = 30
"""Default de respaldo. El valor real sale de la regla `computo.convencion_de_conteo`."""


class Duracion(BaseModel):
    """Tiempo de servicio en años, meses y días de calendario."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    anios: int = Field(ge=0)
    meses: int = Field(ge=0, le=11)
    dias: int = Field(ge=0)

    @classmethod
    def cero(cls) -> Duracion:
        return cls(anios=0, meses=0, dias=0)

    @classmethod
    def de_tramos(
        cls,
        tramos: Iterable[Tramo],
        convencion: ConvencionConteo = ConvencionConteo.DIAS_REALES,
        *,
        dias_por_mes: int = DIAS_POR_MES_ALTERNATIVA,
    ) -> Duracion:
        """Suma la duración de tramos **ya unidos** (y por lo tanto disjuntos).

        `DIAS_REALES` (la aplicada por defecto) mide con la fecha final
        inclusiva y **no arrastra** los días residuales a meses: es la opción
        conservadora, porque nunca declara cumplido un requisito que no lo está.

        `MESES_30` mide con la fecha final exclusiva y arrastra los residuos a
        meses de `dias_por_mes` días. Las dos existen porque la convención que
        aplica el IPS no está verificada (Cuestión abierta #5): tener las dos
        es lo que permite medir si la elección está decidiendo el resultado.
        """
        anios = meses = dias = 0
        inclusiva = convencion is ConvencionConteo.DIAS_REALES
        for tramo in tramos:
            fin = tramo.hasta + dt.timedelta(days=1) if inclusiva else tramo.hasta
            delta = relativedelta(fin, tramo.desde)
            anios += delta.years
            meses += delta.months
            dias += delta.days
        if convencion is ConvencionConteo.MESES_30:
            meses += dias // dias_por_mes
            dias %= dias_por_mes
        anios += meses // MESES_POR_ANIO
        meses %= MESES_POR_ANIO
        return cls(anios=anios, meses=meses, dias=dias)

    @property
    def clave(self) -> tuple[int, int, int]:
        return (self.anios, self.meses, self.dias)

    def cumple_anios(self, requeridos: int) -> bool:
        """Si alcanza o supera un umbral expresado en años enteros."""
        return self.anios >= requeridos

    def __lt__(self, otra: Self) -> bool:
        return self.clave < otra.clave

    def __le__(self, otra: Self) -> bool:
        return self.clave <= otra.clave

    def __gt__(self, otra: Self) -> bool:
        return self.clave > otra.clave

    def __ge__(self, otra: Self) -> bool:
        return self.clave >= otra.clave

    def __str__(self) -> str:
        return f"{self.anios} años, {self.meses} meses, {self.dias} días"


def _tramos_crudos(
    historia: HistoriaDeServicios,
    hasta: dt.date,
    idx_incluidos: Set[int] | None,
) -> list[Tramo]:
    return [
        tramo
        for p in historia.periodos
        if (idx_incluidos is None or p.idx in idx_incluidos)
        and (tramo := p.tramo_a(hasta)) is not None
    ]


def tramos_unidos(
    historia: HistoriaDeServicios,
    hasta: dt.date,
    *,
    idx_incluidos: Set[int] | None = None,
) -> tuple[Tramo, ...]:
    """Los tramos cubiertos a una fecha de cese, con los solapamientos fusionados.

    `idx_incluidos` restringe el cómputo a ciertos períodos, que es lo que
    necesitan los años «al frente de alumnos»: un subconjunto de los de
    servicio.
    """
    return unir_tramos(_tramos_crudos(historia, hasta, idx_incluidos))


def meses_cubiertos(
    historia: HistoriaDeServicios,
    hasta: dt.date,
    *,
    idx_incluidos: Set[int] | None = None,
) -> frozenset[MesCalendario]:
    """El conjunto unión de meses calendario cubiertos."""
    return frozenset(
        m for t in tramos_unidos(historia, hasta, idx_incluidos=idx_incluidos) for m in t.meses()
    )


def dias_cubiertos(
    historia: HistoriaDeServicios,
    hasta: dt.date,
    *,
    idx_incluidos: Set[int] | None = None,
) -> int:
    return sum(t.dias for t in tramos_unidos(historia, hasta, idx_incluidos=idx_incluidos))


def servicio_total(
    historia: HistoriaDeServicios,
    hasta: dt.date,
    *,
    idx_incluidos: Set[int] | None = None,
    convencion: ConvencionConteo = ConvencionConteo.DIAS_REALES,
    dias_por_mes: int = DIAS_POR_MES_ALTERNATIVA,
) -> Duracion:
    """El tiempo de servicio computado a una fecha de cese."""
    return Duracion.de_tramos(
        tramos_unidos(historia, hasta, idx_incluidos=idx_incluidos),
        convencion,
        dias_por_mes=dias_por_mes,
    )


def fecha_al_alcanzar_servicio(
    historia: HistoriaDeServicios,
    anios: int,
    *,
    limite: dt.date,
    idx_incluidos: Set[int] | None = None,
    convencion: ConvencionConteo = ConvencionConteo.DIAS_REALES,
    dias_por_mes: int = DIAS_POR_MES_ALTERNATIVA,
) -> dt.date | None:
    """La primera fecha en que el servicio alcanza `anios`, o `None` si no llega.

    El servicio es monótono creciente en la fecha de corte, así que se resuelve
    por bisección. Sin reloj: `limite` entra como argumento.
    """

    def alcanzado(corte: dt.date) -> bool:
        return servicio_total(
            historia,
            corte,
            idx_incluidos=idx_incluidos,
            convencion=convencion,
            dias_por_mes=dias_por_mes,
        ).cumple_anios(anios)

    tramos = tramos_unidos(historia, limite, idx_incluidos=idx_incluidos)
    if not tramos or not alcanzado(limite):
        return None

    bajo, alto = tramos[0].desde, limite
    while bajo < alto:
        medio = bajo + (alto - bajo) // 2
        if alcanzado(medio):
            alto = medio
        else:
            bajo = medio + dt.timedelta(days=1)
    return bajo


def dias_de_servicio_faltantes(
    tramos: tuple[Tramo, ...],
    anios: int,
    *,
    desde: dt.date,
    convencion: ConvencionConteo = ConvencionConteo.DIAS_REALES,
    dias_por_mes: int = DIAS_POR_MES_ALTERNATIVA,
    horizonte_dias: int = 20_000,
) -> int | None:
    """Cuántos días de servicio continuo faltan para alcanzar `anios`.

    Sirve para medir **cuán cerca del umbral** está un requisito que todavía no
    se cumple, incluso con una historia cerrada: extiende hipotéticamente el
    último tramo y busca el cruce. No proyecta elegibilidad —eso necesita un
    período en curso real—, solo mide la distancia.

    Devuelve `None` si el umbral no se alcanza dentro del horizonte.
    """
    if not tramos:
        return None
    base = tramos[:-1]
    ultimo = tramos[-1]

    def alcanzado(dias_extra: int) -> bool:
        fin = max(ultimo.hasta, desde + dt.timedelta(days=dias_extra))
        extendido = (*base, Tramo(desde=ultimo.desde, hasta=fin))
        return Duracion.de_tramos(extendido, convencion, dias_por_mes=dias_por_mes).cumple_anios(
            anios
        )

    if not alcanzado(horizonte_dias):
        return None
    bajo, alto = 0, horizonte_dias
    while bajo < alto:
        medio = (bajo + alto) // 2
        if alcanzado(medio):
            alto = medio
        else:
            bajo = medio + 1
    return bajo


def horas_catedra_simultaneas(
    historia: HistoriaDeServicios,
    idx: int,
    fecha: dt.date,
) -> int:
    """Horas cátedra activas en una fecha, sumando los períodos que la cubren.

    El art. 24 inc. b habla de **reunir** veinte horas cátedra, y eso se reúne
    sumando cargos simultáneos: es una propiedad de la historia en un momento
    dado, no de un período suelto.
    """
    objetivo = next((p for p in historia.periodos if p.idx == idx), None)
    if objetivo is None:
        return 0
    total = 0
    for p in historia.periodos:
        fin = p.hasta or dt.date.max
        if p.desde <= fecha <= fin:
            total += p.horas_catedra or 0
    return total


def max_horas_catedra_simultaneas(
    historia: HistoriaDeServicios,
    idx: int,
    hasta: dt.date,
) -> int:
    """El máximo de horas simultáneas alcanzado mientras el período está activo.

    El máximo solo puede cambiar en los bordes de los períodos, así que se
    evalúa en ese conjunto finito de fechas en lugar de día por día: exacto y
    determinista.
    """
    objetivo = next((p for p in historia.periodos if p.idx == idx), None)
    if objetivo is None:
        return 0
    tramo = objetivo.tramo_a(hasta)
    if tramo is None:
        return 0

    candidatas = {tramo.desde, tramo.hasta}
    for p in historia.periodos:
        for borde in (p.desde, p.hasta):
            if borde is not None and tramo.desde <= borde <= tramo.hasta:
                candidatas.add(borde)
    return max(horas_catedra_simultaneas(historia, idx, f) for f in sorted(candidatas))
