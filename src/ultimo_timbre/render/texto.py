# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Salida legible en terminal (T175, research R5, FR-038 a FR-042).

Renderiza el **mismo** `Informe` que produce el JSON y **no recalcula nada**.
Eso no es una convención: este módulo no importa `engine` ni `rules`, así que no
tiene con qué recalcular, y un test lo verifica por AST
(`tests/unit/test_render_equivalente.py`).

Por qué importa tanto: una salida de texto que recalculara el porcentaje «para
mostrarlo lindo» podría mostrar 75 % mientras el JSON dice 70 %, y el
profesional no tendría forma de saber cuál de los dos leyó el IPS.

El orden de las secciones sigue el del informe y es el que un expediente
necesita leer: qué se concluyó, sobre qué base, con qué porcentaje, y después
todo lo que lo condiciona.
"""

from __future__ import annotations

from decimal import Decimal

from ultimo_timbre.models.enums import EstadoResultado, SentidoImpacto
from ultimo_timbre.models.informe import (
    Advertencia,
    CargoBase,
    Condicionante,
    Elegibilidad,
    Escenario,
    Informe,
    Monto,
)

__all__ = ["informe_a_texto"]

ANCHO = 78
_CIEN = Decimal(100)

SENTIDOS = {
    SentidoImpacto.AL_ALZA: "podría ser mayor",
    SentidoImpacto.A_LA_BAJA: "podría ser menor",
    SentidoImpacto.INDETERMINADO: "podría variar en cualquier sentido",
}


def _titulo(texto: str) -> list[str]:
    return ["", texto, "=" * min(len(texto), ANCHO)]


def _subtitulo(texto: str) -> list[str]:
    return ["", texto, "-" * min(len(texto), ANCHO)]


def _porcentaje(valor: Decimal) -> str:
    """Un porcentaje como lo lee una persona, sin tocar la exactitud.

    El `Decimal` del informe se multiplica por cien y se muestra sin ceros de
    relleno: `75 %` y no `75.00 %`, `78.75 %` y no `78.7500 %`. La aritmética
    sigue siendo exacta; esto es presentación, no cálculo.

    **No se normaliza antes de comparar con el entero**: `normalize()` convierte
    `80.00` en `8E+1`, y de ahí salía un «Porcentaje: 8E+1 %» en el informe. El
    orden de las dos operaciones importa.
    """
    escalado = valor * _CIEN
    entero = escalado.to_integral_value()
    return f"{entero if escalado == entero else escalado.normalize()} %"


def _estado(estado: EstadoResultado) -> str:
    return estado.value


def _monto(monto: Monto) -> str:
    """El valor **nunca** sin su estado (FR-046a, invariante I5)."""
    return f"{monto.moneda} {monto.valor} ({_estado(monto.estado)}, grilla {monto.grilla_version})"


def _elegibilidad(elegibilidad: Elegibilidad) -> list[str]:
    lineas = _titulo("Elegibilidad")
    favorable = elegibilidad.inciso_mas_favorable

    if favorable is None:
        lineas.append("No se cumple ningún inciso del art. 24 a la fecha evaluada.")
    else:
        lineas.append(f"Accede por el inc. {favorable} del art. 24 del DL 9650/80.")
    lineas.append(f"Estado de la elegibilidad: {_estado(elegibilidad.estado)}.")

    minimo = elegibilidad.minimo_22_anios
    lineas.append(
        f"Mínimo general de años con aportes: {minimo.valor_alcanzado} de "
        f"{minimo.valor_requerido} ({'cumple' if minimo.cumple else 'no cumple'})."
    )

    for inciso in elegibilidad.incisos:
        marca = "cumple" if inciso.cumple else "no cumple"
        encabezado = f"  inc. {inciso.inciso}: {marca}"
        if inciso.cumple and inciso.habilitado_desde is not None:
            encabezado += f", habilitado desde {inciso.habilitado_desde.isoformat()}"
        if inciso.estado is EstadoResultado.PROVISIONAL:
            encabezado += "  [provisional]"
        lineas.append(encabezado)

        for requisito in inciso.requisitos:
            detalle = (
                f"      {requisito.nombre}: {requisito.valor_alcanzado} "
                f"de {requisito.valor_requerido}"
            )
            if requisito.margen_dias is not None:
                detalle += f" (margen {requisito.margen_dias} días)"
            lineas.append(detalle)

        if not inciso.cumple:
            if inciso.estimado_para is not None:
                lineas.append(f"      se estima para {inciso.estimado_para.isoformat()}")
            elif inciso.motivo_sin_estimacion:
                lineas.append(f"      {inciso.motivo_sin_estimacion}")

    return lineas


def _cargo_base(cargo: CargoBase | None) -> list[str]:
    lineas = _titulo("Cargo base (art. 41)")
    if cargo is None:
        lineas.append(
            "No se pudo determinar un cargo base: ningún cargo alcanza los plazos "
            "del art. 41. Ver las advertencias."
        )
        return lineas

    lineas.append(f"Cargo: {cargo.cargo}")
    lineas.append(f"Vía: {cargo.via.value} ({len(cargo.meses_que_lo_sustentan)} meses)")
    if cargo.meses_que_lo_sustentan:
        primero = cargo.meses_que_lo_sustentan[0]
        ultimo = cargo.meses_que_lo_sustentan[-1]
        lineas.append(f"Meses que lo sustentan: {primero} a {ultimo}")
    if cargo.descenso_desde is not None:
        lineas.append(
            f"Descenso al cargo inferior: «{cargo.descenso_desde}» no alcanza los plazos."
        )
    lineas.append(f"Estado: {_estado(cargo.estado)}")
    lineas.append(f"Norma: {cargo.norma.texto}")

    if cargo.descartados:
        lineas.append("Candidatos descartados:")
        for descartado in cargo.descartados:
            meses = (
                f" ({descartado.meses_alcanzados} meses)"
                if descartado.meses_alcanzados is not None
                else ""
            )
            lineas.append(f"  {descartado.cargo}{meses}: {descartado.razon}")
    return lineas


def _escenarios(escenarios: tuple[Escenario, ...]) -> list[str]:
    lineas = _titulo("Escenarios de cese")
    for escenario in escenarios:
        titulo = f"Cese {escenario.fecha_cese.isoformat()} ({escenario.tipo.value})"
        lineas.extend(_subtitulo(titulo))
        if not escenario.hay_derecho:
            lineas.append("No hay derecho a la fecha evaluada.")
            continue

        lineas.append(f"Inciso aplicable: inc. {escenario.inciso}")
        if escenario.porcentaje is not None:
            lineas.append(f"Porcentaje: {_porcentaje(escenario.porcentaje)}")
        if escenario.antiguedad_anios is not None:
            lineas.append(f"Antigüedad: {escenario.antiguedad_anios} años")

        if escenario.haber is not None:
            lineas.append(f"Haber estimado: {_monto(escenario.haber)}")
        else:
            lineas.append("Haber estimado: no se calcula (ver advertencias).")

        if escenario.lectura_literal is not None:
            alternativa = escenario.lectura_literal
            lineas.append(
                f"Lectura alternativa: {_porcentaje(alternativa.porcentaje)} "
                f"({SENTIDOS[alternativa.sentido_impacto]}) — {alternativa.norma.texto}"
            )
    return lineas


def _advertencias(advertencias: tuple[Advertencia, ...]) -> list[str]:
    if not advertencias:
        return []
    lineas = _titulo("Advertencias")
    for aviso in advertencias:
        prefijo = "[BLOQUEA] " if aviso.bloquea_calculo else ""
        ubicacion = f" (período {aviso.periodo_idx})" if aviso.periodo_idx is not None else ""
        lineas.append(f"{prefijo}{aviso.codigo.value}{ubicacion}:")
        lineas.append(f"  {aviso.mensaje}")
        if aviso.norma is not None:
            lineas.append(f"  Norma: {aviso.norma.texto}")
    return lineas


def _condicionantes(condicionantes: tuple[Condicionante, ...]) -> list[str]:
    if not condicionantes:
        return []
    lineas = _titulo("Qué falta verificar")
    lineas.append(
        "Cada punto de esta lista es una razón por la que el resultado no es "
        "definitivo, con el sentido en que podría cambiar."
    )
    for cond in condicionantes:
        lineas.append(f"  {cond.referencia} — el resultado {SENTIDOS[cond.sentido_impacto]}")
        lineas.append(f"    {cond.que_falta_verificar}")
        if cond.magnitud_estimada is not None:
            lineas.append(f"    Magnitud: {cond.magnitud_estimada}")
        if cond.norma is not None:
            lineas.append(f"    Norma: {cond.norma.texto}")
    return lineas


def _desglose(informe: Informe) -> list[str]:
    lineas = _titulo("Desglose paso a paso")
    for paso in informe.desglose:
        lineas.append(f"{paso.orden:>3}. {paso.descripcion}")
        if paso.entrada:
            lineas.append(f"      entrada: {paso.entrada}")
        if paso.salida:
            lineas.append(f"      salida:  {paso.salida}")
        lineas.append(f"      norma:   {paso.norma.texto} [{paso.tipo_fuente.value}]")
    return lineas


def _procedencias(informe: Informe) -> list[str]:
    if not informe.procedencias:
        return []
    lineas = _titulo("Procedencia de los datos")
    for procedencia in informe.procedencias:
        marca = " [corregido a mano]" if procedencia.difiere_del_catalogo else ""
        origen = procedencia.origen.value
        detalle = f" ← {procedencia.derivado_de}" if procedencia.derivado_de else ""
        lineas.append(f"  {procedencia.dato}: {origen}{detalle}{marca}")
    return lineas


def _encabezado(informe: Informe) -> list[str]:
    lineas = [
        "INFORME DE JUBILACIÓN ORDINARIA DOCENTE — IPS Provincia de Buenos Aires",
        "=" * ANCHO,
        f"Fecha de cálculo: {informe.fecha_de_calculo.isoformat()}",
        f"Versión de reglas: {informe.version_reglas}",
    ]
    lineas.append(
        f"Versión de grilla: {informe.version_grilla}"
        if informe.version_grilla is not None
        else "Versión de grilla: ninguna (informe sin montos)"
    )
    lineas.append(f"Estado general: {_estado(informe.estado_general).upper()}")
    if informe.tiene_bloqueos:
        lineas.append(
            "ATENCIÓN: el caso contiene situaciones fuera del Alcance de la v1. "
            "El análisis es parcial y no se emite haber."
        )
    return lineas


def _cierre(informe: Informe) -> list[str]:
    return [
        *_titulo("Avisos"),
        informe.aviso_estimacion,
        informe.aviso_movilidad,
        "",
    ]


def informe_a_texto(informe: Informe) -> str:
    """El informe como texto legible en terminal.

    Función pura del `Informe`: dos llamadas con el mismo informe devuelven el
    mismo string, y no muta nada.
    """
    lineas: list[str] = [
        *_encabezado(informe),
        *_elegibilidad(informe.elegibilidad),
        *_cargo_base(informe.cargo_base),
        *_escenarios(informe.escenarios),
        *_advertencias(informe.advertencias),
        *_condicionantes(informe.condicionantes),
        *_desglose(informe),
        *_procedencias(informe),
        *_cierre(informe),
    ]
    return "\n".join(lineas)
