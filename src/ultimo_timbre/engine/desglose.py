# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Trazado del cálculo: desglose, procedencias y condicionantes (T062, T063).

El desglose **es** el producto (Principio IV): un abogado tiene que poder
rastrear cada número hasta su norma. Este módulo es el único lugar donde se
acumulan los pasos, para que ninguna rama del motor pueda calcular algo sin
dejar rastro.

`Trazador` es mutable a propósito —es un acumulador, no un dato del dominio—,
pero lo que entrega son tuplas inmutables.
"""

from __future__ import annotations

from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    CodigoAdvertencia,
    OrigenDato,
    SentidoImpacto,
    TipoFuente,
)
from ultimo_timbre.models.informe import (
    Advertencia,
    Condicionante,
    PasoDelDesglose,
    Procedencia,
)
from ultimo_timbre.models.normativa import Norma, Regla

__all__ = ["Trazador"]


class Trazador:
    """Acumula el rastro del cálculo."""

    def __init__(self) -> None:
        self._pasos: list[PasoDelDesglose] = []
        self._procedencias: list[Procedencia] = []
        self._advertencias: list[Advertencia] = []
        self._condicionantes: dict[str, Condicionante] = {}

    # ------------------------------------------------------------------ pasos
    def paso(
        self,
        descripcion: str,
        regla: Regla,
        *,
        entrada: str | None = None,
        salida: str | None = None,
    ) -> None:
        """Registra un paso con la regla que lo sostiene (FR-038, FR-040)."""
        self._pasos.append(
            PasoDelDesglose(
                orden=len(self._pasos) + 1,
                descripcion=descripcion,
                regla_id=regla.id,
                norma=regla.norma,
                tipo_fuente=regla.tipo,
                entrada=entrada,
                salida=salida,
            )
        )

    def paso_suelto(
        self,
        descripcion: str,
        *,
        regla_id: str,
        norma: Norma,
        tipo_fuente: TipoFuente = TipoFuente.LETRA_LEY,
        entrada: str | None = None,
        salida: str | None = None,
    ) -> None:
        """Paso cuya fuente no está en el conjunto de reglas (p. ej. el catálogo)."""
        self._pasos.append(
            PasoDelDesglose(
                orden=len(self._pasos) + 1,
                descripcion=descripcion,
                regla_id=regla_id,
                norma=norma,
                tipo_fuente=tipo_fuente,
                entrada=entrada,
                salida=salida,
            )
        )

    # ----------------------------------------------------------- procedencias
    def procedencia(
        self,
        dato: str,
        origen: OrigenDato,
        *,
        derivado_de: str | None = None,
        difiere_del_catalogo: bool = False,
    ) -> None:
        """De dónde salió un dato del informe (FR-039)."""
        self._procedencias.append(
            Procedencia(
                dato=dato,
                origen=origen,
                derivado_de=derivado_de,
                difiere_del_catalogo=difiere_del_catalogo,
            )
        )

    # ----------------------------------------------------------- advertencias
    def advertencia(
        self,
        codigo: CodigoAdvertencia,
        mensaje: str,
        *,
        norma: Norma | None = None,
        sentido_impacto: SentidoImpacto | None = None,
        bloquea_calculo: bool = False,
        periodo_idx: int | None = None,
    ) -> None:
        self._advertencias.append(
            Advertencia(
                codigo=codigo,
                mensaje=mensaje,
                norma=norma,
                sentido_impacto=sentido_impacto,
                bloquea_calculo=bloquea_calculo,
                periodo_idx=periodo_idx,
            )
        )

    # ---------------------------------------------------------- condicionantes
    def condicionante_de_regla(self, regla: Regla) -> None:
        """Una regla `NO_VERIFICADA` que intervino (FR-046b).

        Se indexa por `regla_id` para no repetir la misma regla aunque
        intervenga en varios pasos.
        """
        if regla.impacto_si_no_verificada is None:
            return
        self._condicionantes[regla.id] = Condicionante(
            clase=ClaseCondicionante.REGLA_NO_VERIFICADA,
            referencia=regla.id,
            norma=regla.norma,
            sentido_impacto=regla.impacto_si_no_verificada,
            que_falta_verificar=regla.que_falta_verificar or "sin especificar",
        )

    def condicionante_de_situacion(
        self,
        codigo: CodigoAdvertencia,
        que_falta_verificar: str,
        *,
        sentido_impacto: SentidoImpacto = SentidoImpacto.INDETERMINADO,
        magnitud_estimada: str | None = None,
    ) -> None:
        """Una situación del caso que introduce incertidumbre (FR-046b)."""
        self._condicionantes[codigo.value] = Condicionante(
            clase=ClaseCondicionante.SITUACION_DEL_CASO,
            referencia=codigo.value,
            norma=None,
            sentido_impacto=sentido_impacto,
            magnitud_estimada=magnitud_estimada,
            que_falta_verificar=que_falta_verificar,
        )

    # ------------------------------------------------------------------ salida
    @property
    def pasos(self) -> tuple[PasoDelDesglose, ...]:
        return tuple(self._pasos)

    @property
    def procedencias(self) -> tuple[Procedencia, ...]:
        return tuple(self._procedencias)

    @property
    def advertencias(self) -> tuple[Advertencia, ...]:
        """Ordenadas por código, para que el informe sea determinista (SC-003)."""
        return tuple(sorted(self._advertencias, key=lambda a: (a.codigo.value, a.mensaje)))

    @property
    def condicionantes(self) -> tuple[Condicionante, ...]:
        return tuple(self._condicionantes[k] for k in sorted(self._condicionantes))

    @property
    def hay_condicionantes(self) -> bool:
        return bool(self._condicionantes)
