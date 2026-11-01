# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Entrada del motor: el caso y su historia de servicios (T029 y T033).

Dos decisiones estructurales viven acá:

* **La fecha de cálculo es un campo del caso**, no el reloj del sistema
  (FR-001a). Sin eso el determinismo valdría solo dentro de la misma jornada.
* **`HistoriaDeServicios` normaliza al construirse**, así que el resto del motor
  no puede observar el orden de carga (FR-049/SC-010), y computa siempre sobre
  la **unión** de tramos, nunca sumando duraciones (FR-004a, invariante I9).
"""

from __future__ import annotations

import datetime as dt
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ultimo_timbre.models.enums import (
    CajaAportes,
    ClasificacionSuperposicion,
    NaturalezaServicio,
    SituacionRevista,
    TipoEstablecimiento,
    TipoLicencia,
)

__all__ = [
    "CargoRef",
    "Caso",
    "Establecimiento",
    "HistoriaDeServicios",
    "Licencia",
    "MesCalendario",
    "PeriodoDeServicio",
    "Superposicion",
    "Tramo",
]

MODELO = ConfigDict(strict=True, frozen=True, extra="forbid")

CargoRef = str
"""Nombre del cargo tal como lo nombra el catálogo versionado.

Es un `str`, no un objeto. Se valida contra el catálogo, pero **un cargo ausente
no invalida el caso**: se advierte `cargo_fuera_de_catalogo`, su condición queda
indeterminada y el resultado sale provisional. Rechazar el caso obligaría al
profesional a esperar una actualización del catálogo para obtener cualquier
análisis, cuando el resto de la historia sí es computable (Principio IV).
"""

MESES_POR_ANIO = 12


class MesCalendario(BaseModel):
    """Un mes calendario. La unidad del conteo de los 36/60 meses (research R2)."""

    model_config = MODELO

    anio: int = Field(ge=1900, le=2200)
    mes: int = Field(ge=1, le=12)

    @classmethod
    def de_fecha(cls, fecha: dt.date) -> MesCalendario:
        return cls(anio=fecha.year, mes=fecha.month)

    @property
    def ordinal(self) -> int:
        """Índice absoluto, para comparar y detectar rachas consecutivas."""
        return self.anio * MESES_POR_ANIO + (self.mes - 1)

    def siguiente(self) -> MesCalendario:
        return (
            MesCalendario(anio=self.anio + 1, mes=1)
            if self.mes == MESES_POR_ANIO
            else MesCalendario(anio=self.anio, mes=self.mes + 1)
        )

    def __lt__(self, otro: MesCalendario) -> bool:
        return self.ordinal < otro.ordinal

    def __str__(self) -> str:
        return f"{self.anio:04d}-{self.mes:02d}"


class Tramo(BaseModel):
    """Un intervalo cerrado de fechas, ya unido con los que se solapaban."""

    model_config = MODELO

    desde: dt.date
    hasta: dt.date

    @model_validator(mode="after")
    def _orden(self) -> Self:
        if self.hasta < self.desde:
            raise ValueError("`hasta` no puede ser anterior a `desde`")
        return self

    @property
    def dias(self) -> int:
        return (self.hasta - self.desde).days + 1

    def meses(self) -> tuple[MesCalendario, ...]:
        """Los meses calendario que el tramo toca, sin repetir."""
        actual = MesCalendario.de_fecha(self.desde)
        fin = MesCalendario.de_fecha(self.hasta)
        salida: list[MesCalendario] = []
        while actual.ordinal <= fin.ordinal:
            salida.append(actual)
            actual = actual.siguiente()
        return tuple(salida)


class Licencia(BaseModel):
    """Su efecto sobre el cómputo es la Cuestión abierta #5."""

    model_config = MODELO

    tipo: TipoLicencia
    desde: dt.date
    hasta: dt.date

    @model_validator(mode="after")
    def _orden(self) -> Self:
        if self.hasta < self.desde:
            raise ValueError("`hasta` no puede ser anterior a `desde`")
        return self


class Establecimiento(BaseModel):
    """Dónde se prestó el servicio.

    La caja de aportes NO vive acá: se declara por período, porque depende de la
    relación de empleo y no del lugar (FR-002d).
    """

    model_config = MODELO

    tipo: TipoEstablecimiento
    nombre: str | None = None

    @property
    def fuera_de_alcance(self) -> bool:
        """FR-045: solo los estatales de la DGCyE están en alcance de la v1."""
        return self.tipo is not TipoEstablecimiento.ESTATAL_DGCYE


class PeriodoDeServicio(BaseModel):
    """Un tramo de desempeño.

    Ni `al_frente_de_alumnos` ni `naturaleza` son campos de entrada: se derivan
    del cargo vía el catálogo (FR-002a, FR-002d). Los dos `*_override` existen
    solo para la corrección manual, y su uso deja rastro en la procedencia.
    """

    model_config = MODELO

    cargo: CargoRef = Field(min_length=1)
    establecimiento: Establecimiento
    desde: dt.date
    caja_aportes: CajaAportes
    situacion_revista: SituacionRevista
    hasta: dt.date | None = None
    """`None` = período en curso: se proyecta hasta cada fecha de cese (FR-002e)."""
    horas_catedra: int | None = Field(default=None, ge=0)
    licencias: tuple[Licencia, ...] = ()
    al_frente_override: bool | None = None
    naturaleza_override: NaturalezaServicio | None = None
    idx: int = Field(default=-1, ge=-1)
    """Identificador anónimo asignado al normalizar. Es lo único que va a un log."""

    @model_validator(mode="after")
    def _coherencia_temporal(self) -> Self:
        if self.hasta is not None and self.hasta < self.desde:
            raise ValueError("`hasta` no puede ser anterior a `desde`")
        for lic in self.licencias:
            if lic.desde < self.desde:
                raise ValueError("una licencia no puede empezar antes que el período")
            if self.hasta is not None and lic.hasta > self.hasta:
                raise ValueError("una licencia no puede terminar después que el período")
        return self

    @property
    def en_curso(self) -> bool:
        return self.hasta is None

    @property
    def fuera_de_alcance(self) -> bool:
        """FR-044, FR-045: otra caja o establecimiento no estatal de la DGCyE."""
        return self.caja_aportes is not CajaAportes.IPS or self.establecimiento.fuera_de_alcance

    def tramo_a(self, cese: dt.date) -> Tramo | None:
        """El tramo efectivo a una fecha de cese.

        Un período en curso se **proyecta** hasta el cese bajo supuesto de
        continuidad (FR-002e); uno que lo excede se **recorta**, no se rechaza
        (FR-018a). Devuelve `None` si el período empieza después del cese.
        """
        if self.desde > cese:
            return None
        fin = cese if self.hasta is None else min(self.hasta, cese)
        return Tramo(desde=self.desde, hasta=fin)

    def recortado_a(self, cese: dt.date) -> bool:
        return self.hasta is not None and self.hasta > cese


class Superposicion(BaseModel):
    """Un solapamiento detectado entre dos períodos (FR-004).

    La clasificación definitiva la fija la US2 (T073): decidir si una
    simultaneidad es computable por el art. 47 exige saber si alcanza al cargo
    base, y eso no se conoce todavía acá. Lo que el modelo sí decide es lo
    estructural —mismo cargo y mismo establecimiento es carga duplicada— y deja
    `anios_continuos` calculado para que el motor resuelva el resto.
    """

    model_config = MODELO

    periodos: tuple[int, int]
    desde: dt.date
    hasta: dt.date
    clasificacion: ClasificacionSuperposicion
    anios_continuos: int
    """Años continuos del solapamiento.

    Es **dato**, no veredicto: el umbral del art. 47 vive en la regla
    `simultaneidad.art47.minimo_continuo` y la comparación la hace el motor
    (US2, FR-004). Tener el `3` acá sería un valor normativo escrito en el
    código, que es exactamente lo que prohíbe el Principio I.
    """


def _clave_orden(p: PeriodoDeServicio) -> tuple[dt.date, bool, dt.date, str]:
    """Orden total y estable. Un período en curso va después del cerrado que empieza igual."""
    return (p.desde, p.hasta is None, p.hasta or dt.date.max, p.cargo)


def _detectar_superposiciones(
    periodos: tuple[PeriodoDeServicio, ...],
) -> tuple[Superposicion, ...]:
    halladas: list[Superposicion] = []
    for i, a in enumerate(periodos):
        for b in periodos[i + 1 :]:
            fin_a = a.hasta or dt.date.max
            fin_b = b.hasta or dt.date.max
            desde = max(a.desde, b.desde)
            hasta = min(fin_a, fin_b)
            if desde > hasta:
                continue
            anios = (hasta - desde).days // 365
            mismo_puesto = a.cargo == b.cargo and a.establecimiento == b.establecimiento
            clasificacion = (
                ClasificacionSuperposicion.POSIBLE_ERROR_CARGA
                if mismo_puesto
                else ClasificacionSuperposicion.SIMULTANEIDAD_NO_COMPUTABLE
            )
            halladas.append(
                Superposicion(
                    periodos=(a.idx, b.idx),
                    desde=desde,
                    hasta=hasta,
                    clasificacion=clasificacion,
                    anios_continuos=anios,
                )
            )
    return tuple(halladas)


class HistoriaDeServicios(BaseModel):
    """El conjunto de períodos, normalizado al construirse.

    La normalización es lo que hace cumplir FR-049/SC-010 **por construcción**:
    dos historias con los mismos períodos en distinto orden producen el mismo
    objeto, así que el resto del motor ni siquiera puede observar el orden.
    """

    model_config = MODELO

    periodos: tuple[PeriodoDeServicio, ...] = Field(min_length=1)
    superposiciones: tuple[Superposicion, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _normalizar(cls, datos: object) -> object:
        if not isinstance(datos, dict):
            return datos
        crudos = datos.get("periodos")
        if not crudos:
            return datos
        objetos = [
            p if isinstance(p, PeriodoDeServicio) else PeriodoDeServicio.model_validate(p)
            for p in crudos
        ]
        objetos.sort(key=_clave_orden)
        objetos = [p.model_copy(update={"idx": i}) for i, p in enumerate(objetos)]
        ordenados = tuple(objetos)
        return {
            **datos,
            "periodos": ordenados,
            "superposiciones": _detectar_superposiciones(ordenados),
        }

    # -- cómputo sobre la UNIÓN, nunca sobre la suma (FR-004a, invariante I9) --

    def tramos_unidos(self, hasta: dt.date) -> tuple[Tramo, ...]:
        """Los tramos cubiertos a una fecha de cese, con los solapamientos fusionados.

        Dos cargos simultáneos durante 2015 aportan el año 2015 **una vez**.
        Sumar duraciones es el error clásico de este dominio: produce historias
        de 40 años de servicio sobre una carrera de 25.
        """
        tramos = sorted(
            (t for p in self.periodos if (t := p.tramo_a(hasta)) is not None),
            key=lambda t: (t.desde, t.hasta),
        )
        if not tramos:
            return ()
        unidos: list[Tramo] = [tramos[0]]
        for tramo in tramos[1:]:
            ultimo = unidos[-1]
            # contiguo o solapado: un día de diferencia no abre un hueco real
            if tramo.desde <= ultimo.hasta + dt.timedelta(days=1):
                if tramo.hasta > ultimo.hasta:
                    unidos[-1] = Tramo(desde=ultimo.desde, hasta=tramo.hasta)
            else:
                unidos.append(tramo)
        return tuple(unidos)

    def meses_cubiertos(self, hasta: dt.date) -> frozenset[MesCalendario]:
        """El conjunto unión de meses calendario cubiertos."""
        return frozenset(m for t in self.tramos_unidos(hasta) for m in t.meses())

    def dias_cubiertos(self, hasta: dt.date) -> int:
        return sum(t.dias for t in self.tramos_unidos(hasta))

    def periodos_recortados_a(self, cese: dt.date) -> tuple[int, ...]:
        """Los `idx` de los períodos que el cese recorta (FR-018a)."""
        return tuple(p.idx for p in self.periodos if p.recortado_a(cese))

    def periodos_en_curso(self) -> tuple[int, ...]:
        """Los `idx` de los períodos proyectados por supuesto de continuidad (FR-002e)."""
        return tuple(p.idx for p in self.periodos if p.en_curso)


class Caso(BaseModel):
    """La única entrada del motor."""

    model_config = MODELO

    fecha_de_calculo: dt.date
    """FR-001a: el motor nunca llama al reloj. Toda comparación con «hoy» usa esto."""
    fecha_nacimiento: dt.date
    historia: HistoriaDeServicios
    fechas_cese: tuple[dt.date, ...] = Field(min_length=1)
    schema_version: str = "1.0.0"

    @model_validator(mode="after")
    def _coherencia(self) -> Self:
        if self.fecha_nacimiento >= self.fecha_de_calculo:
            raise ValueError("`fecha_nacimiento` debe ser anterior a `fecha_de_calculo`")
        if len(set(self.fechas_cese)) != len(self.fechas_cese):
            raise ValueError("`fechas_cese` no admite duplicados")
        return self

    @model_validator(mode="before")
    @classmethod
    def _ordenar_ceses(cls, datos: object) -> object:
        if isinstance(datos, dict) and datos.get("fechas_cese"):
            datos = {**datos, "fechas_cese": tuple(sorted(datos["fechas_cese"]))}
        return datos

    def edad_a(self, fecha: dt.date) -> int:
        """Edad cumplida a una fecha. Sin reloj: la fecha entra como argumento."""
        n = self.fecha_nacimiento
        return fecha.year - n.year - ((fecha.month, fecha.day) < (n.month, n.day))
