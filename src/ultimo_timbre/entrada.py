# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Carga del archivo de caso (T176, T179, FR-003, FR-057).

Este módulo es el **borde** del motor: lo único que convierte texto de un
archivo en un `Caso`. Está separado de `calcular` a propósito (research R7): un
consumidor que ya tiene los datos en memoria —la futura app web, que no puede
tocar disco por caso— usa solo `calcular`.

## Por qué hay conversión explícita y no coerción

Los modelos son `strict=True`, así que **no** aceptan un `str` donde esperan una
fecha o un enum, ni una `list` donde esperan una `tuple`. Eso no es un obstáculo
a sortear: es la misma decisión que con los decimales (research R1). Un YAML
entrega `date` para una fecha sin comillas pero `str` si está entrecomillada, y
un JSON siempre entrega `str` y listas. Si el modelo coercionara, todas esas
formas entrarían sin que nadie declarara qué pasó con ellas. Convertir acá,
campo por campo y en una tabla visible, hace que agregar un campo al caso
obligue a decidir cómo se lee.

## Mensajes de error

El **objeto** `CasoInvalido` lleva solo tres cosas: el índice anónimo del
período, el nombre del campo y qué hacer para corregirlo (FR-057, Principio
VIII). Ningún valor del caso entra ahí, porque una excepción es lo que termina
en un log, en una métrica o en un reporte de error, y FR-054 lo prohíbe.

Enriquecerlo para la pantalla es otra cosa y la hace la línea de comandos, que
vuelve a leer el documento con `leer_documento` y le agrega el cargo y las
fechas de ese período. Es el dato de quien corrió el comando, mostrado en su
propia terminal, y FR-057 pide que el mensaje sea accionable. La distinción está
documentada en `contracts/cli.md`.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ultimo_timbre.errors import CasoInvalido
from ultimo_timbre.models.caso import Caso, PeriodoDeServicio
from ultimo_timbre.models.enums import (
    CajaAportes,
    Formato,
    NaturalezaServicio,
    SituacionRevista,
    TipoEstablecimiento,
    TipoLicencia,
)
from ultimo_timbre.rules.loader import cargar_json_texto, cargar_yaml_texto

__all__ = ["cargar_caso", "cargar_caso_desde_texto", "leer_documento"]

EXTENSIONES: dict[str, Formato] = {
    ".yaml": Formato.YAML,
    ".yml": Formato.YAML,
    ".json": Formato.JSON,
}

# Qué campo se lee como qué. Declarado y no inferido: agregar un campo al caso
# obliga a decidir cómo entra, en lugar de dejarlo a merced de una coerción.
FECHAS_DEL_CASO = ("fecha_de_calculo", "fecha_nacimiento")
FECHAS_DEL_PERIODO = ("desde", "hasta")
FECHAS_DE_LA_LICENCIA = ("desde", "hasta")

ENUMS_DEL_PERIODO: dict[str, type[CajaAportes | SituacionRevista | NaturalezaServicio]] = {
    "caja_aportes": CajaAportes,
    "situacion_revista": SituacionRevista,
    "naturaleza_override": NaturalezaServicio,
}

# Qué hacer ante cada error, en castellano y accionable. La clave es el campo;
# el texto nunca menciona el valor cargado (FR-054).
CORRECCIONES: dict[str, str] = {
    "hasta": "Corregí 'hasta' para que sea posterior o igual a 'desde'.",
    "desde": "Revisá 'desde': tiene que ser una fecha válida y anterior a 'hasta'.",
    "fecha_nacimiento": (
        "Agregá 'fecha_nacimiento' con formato YYYY-MM-DD, anterior a la fecha de cálculo."
    ),
    "fecha_de_calculo": (
        "Agregá 'fecha_de_calculo' con formato YYYY-MM-DD, o pasá --fecha-calculo "
        "para que la línea de comandos la complete."
    ),
    "fechas_cese": "Declará al menos una fecha de cese, sin repetir ninguna.",
    "cargo": "Declará 'cargo' con el nombre del cargo tal como lo nombra el catálogo.",
    # Los campos de enumeración no llevan la lista de valores acá: `_enum` ya
    # la arma **desde el enum**. Transcribirla a mano fue cómo se colaron un
    # «otra_provincial» que no existe y un «otra_jurisdiccion» mal atribuido.
    "establecimiento": "Declará 'establecimiento' con su 'tipo'.",
    "tipo": "Revisá el 'tipo' del establecimiento.",
    "caja_aportes": "Revisá 'caja_aportes'.",
    "situacion_revista": "Revisá 'situacion_revista'.",
    "naturaleza_override": "Revisá 'naturaleza_override'.",
    "historia": "Declará 'historia' con al menos un período en 'periodos'.",
    "periodos": "Declará al menos un período en 'historia.periodos'.",
    "licencias": "Revisá las licencias: cada una necesita 'tipo', 'desde' y 'hasta'.",
}
CORRECCION_GENERICA = "Revisá ese campo contra el esquema del caso (contracts/caso.schema.json)."


def _fecha(valor: Any, *, campo: str, periodo_idx: int | None) -> Any:
    """Una fecha ISO como `date`. Deja pasar lo que ya lo es y lo ausente."""
    if valor is None or isinstance(valor, dt.date):
        return valor
    if isinstance(valor, str):
        try:
            return dt.date.fromisoformat(valor)
        except ValueError as exc:
            msg = (
                f"'{campo}' no es una fecha válida: se espera el formato YYYY-MM-DD. "
                + CORRECCIONES.get(campo, CORRECCION_GENERICA)
            )
            raise CasoInvalido(msg, campo=campo, periodo_idx=periodo_idx) from exc
    return valor


def _enum(valor: Any, tipo: Any, *, campo: str, periodo_idx: int | None) -> Any:
    """Un valor de enumeración por su nombre. Deja pasar lo que ya lo es."""
    if valor is None or isinstance(valor, tipo):
        return valor
    if isinstance(valor, str):
        try:
            return tipo(valor)
        except ValueError as exc:
            opciones = ", ".join(m.value for m in tipo)
            msg = (
                f"'{campo}' no reconoce ese valor. Las opciones son: {opciones}. "
                + CORRECCIONES.get(campo, CORRECCION_GENERICA)
            )
            raise CasoInvalido(msg, campo=campo, periodo_idx=periodo_idx) from exc
    return valor


def _normalizar_licencia(datos: Any, *, periodo_idx: int) -> Any:
    if not isinstance(datos, dict):
        return datos
    salida = dict(datos)
    for campo in FECHAS_DE_LA_LICENCIA:
        if campo in salida:
            salida[campo] = _fecha(salida[campo], campo=campo, periodo_idx=periodo_idx)
    if "tipo" in salida:
        salida["tipo"] = _enum(salida["tipo"], TipoLicencia, campo="tipo", periodo_idx=periodo_idx)
    return salida


def _validar_periodo(datos: Any, *, periodo_idx: int) -> None:
    """Valida un período **solo** para poder atribuirle el error (FR-057).

    `HistoriaDeServicios` construye sus períodos en un validador `mode="before"`
    —ahí asigna el `idx`—, así que un error de un período sale reportado a la
    altura de `historia` y pierde cuál era. Validarlo por separado antes de
    armar el caso es lo que permite decir «período 1» en lugar de «la historia»,
    que es la diferencia entre un mensaje accionable y uno que no lo es.
    """
    try:
        PeriodoDeServicio.model_validate(datos)
    except ValidationError as exc:
        raise _traducir(exc, periodo_idx=periodo_idx) from exc


def _normalizar_periodo(datos: Any, *, periodo_idx: int) -> Any:
    if not isinstance(datos, dict):
        return datos
    salida = dict(datos)

    for campo in FECHAS_DEL_PERIODO:
        if campo in salida:
            salida[campo] = _fecha(salida[campo], campo=campo, periodo_idx=periodo_idx)

    for campo, tipo in ENUMS_DEL_PERIODO.items():
        if campo in salida:
            salida[campo] = _enum(salida[campo], tipo, campo=campo, periodo_idx=periodo_idx)

    establecimiento = salida.get("establecimiento")
    if isinstance(establecimiento, dict) and "tipo" in establecimiento:
        salida["establecimiento"] = {
            **establecimiento,
            "tipo": _enum(
                establecimiento["tipo"],
                TipoEstablecimiento,
                campo="tipo",
                periodo_idx=periodo_idx,
            ),
        }

    licencias = salida.get("licencias")
    if isinstance(licencias, list):
        # `tuple` y no `list`: en modo estricto los dos no son intercambiables,
        # y el modelo declara `tuple[Licencia, ...]` porque el caso es inmutable.
        salida["licencias"] = tuple(
            _normalizar_licencia(lic, periodo_idx=periodo_idx) for lic in licencias
        )

    _validar_periodo(salida, periodo_idx=periodo_idx)
    return salida


def _normalizar(
    datos: dict[str, Any],
    *,
    fecha_de_calculo: dt.date | None,
    fecha_de_calculo_si_falta: dt.date | None,
) -> dict[str, Any]:
    """Lleva el documento crudo a los tipos que los modelos estrictos esperan.

    Resuelve también la precedencia de la fecha de cálculo, que es
    **explícita > la del archivo > la de respaldo** (FR-001a). Las dos fechas
    llegan desde afuera porque este módulo no consulta el reloj: el único lugar
    del paquete que puede hacerlo es la línea de comandos.
    """
    salida: dict[str, Any] = dict(datos)

    if fecha_de_calculo is not None:
        salida["fecha_de_calculo"] = fecha_de_calculo
    elif salida.get("fecha_de_calculo") is None and fecha_de_calculo_si_falta is not None:
        salida["fecha_de_calculo"] = fecha_de_calculo_si_falta

    for campo in FECHAS_DEL_CASO:
        if campo in salida:
            salida[campo] = _fecha(salida[campo], campo=campo, periodo_idx=None)

    ceses = salida.get("fechas_cese")
    if isinstance(ceses, list):
        salida["fechas_cese"] = [_fecha(c, campo="fechas_cese", periodo_idx=None) for c in ceses]

    historia = salida.get("historia")
    if isinstance(historia, dict) and isinstance(historia.get("periodos"), list):
        salida["historia"] = {
            **historia,
            "periodos": [
                _normalizar_periodo(p, periodo_idx=i) for i, p in enumerate(historia["periodos"])
            ],
        }

    return salida


def _ubicacion(loc: tuple[Any, ...]) -> tuple[str | None, int | None]:
    """El campo y el índice del período de un error de Pydantic.

    `loc` viene como `('historia', 'periodos', 1, 'hasta')`. Lo que interesa es
    el último nombre —el campo— y el último entero —el período—.
    """
    campo = next((p for p in reversed(loc) if isinstance(p, str)), None)
    idx = next((p for p in reversed(loc) if isinstance(p, int)), None)
    return campo, idx


def _traducir(error: ValidationError, *, periodo_idx: int | None = None) -> CasoInvalido:
    """Un `ValidationError` de Pydantic como mensaje accionable (FR-057).

    Se toma el primer error y no todos: un mensaje con una acción clara es más
    útil que una lista de siete, y el resto aparece al corregir el primero.
    """
    primero = error.errors()[0]
    campo, idx = _ubicacion(tuple(primero.get("loc", ())))
    if periodo_idx is not None:
        idx = periodo_idx
    tipo = str(primero.get("type", ""))

    detalle_crudo = str(primero.get("msg", ""))
    if campo in {None, "historia", "periodos"}:
        nombrado = next((c for c in CORRECCIONES if f"`{c}`" in detalle_crudo), None)
        if nombrado is not None:
            campo = nombrado

    if tipo == "missing":
        descripcion = f"falta el campo obligatorio '{campo}'"
    elif campo is not None:
        descripcion = f"el campo '{campo}' no es válido"
    else:
        descripcion = "el caso no es válido"

    # El mensaje del validador del modelo sí es seguro: está escrito para no
    # llevar valores de dominio (ver `errors.py`).
    detalle = str(primero.get("msg", "")).removeprefix("Value error, ").strip()
    if detalle and campo is None:
        descripcion = f"{descripcion}: {detalle}"

    correccion = CORRECCIONES.get(campo or "", CORRECCION_GENERICA)
    return CasoInvalido(f"{descripcion}. {correccion}", campo=campo, periodo_idx=idx)


def cargar_caso_desde_texto(
    texto: str,
    formato: Formato,
    *,
    fecha_de_calculo: dt.date | None = None,
    fecha_de_calculo_si_falta: dt.date | None = None,
) -> Caso:
    """Un `Caso` a partir del contenido de un archivo.

    `formato` dice cómo parsear: `Formato.YAML` o `Formato.JSON`. `Formato.TEXTO`
    no es un formato de entrada y se rechaza.

    `fecha_de_calculo` **reemplaza** la del archivo —es lo que permite reproducir
    un informe viejo tal como se emitió— y `fecha_de_calculo_si_falta` solo se
    usa cuando el archivo no la declara. Ninguna de las dos se deriva acá: las
    provee el llamador, porque el motor no consulta el reloj (FR-001a).
    """
    if formato is Formato.YAML:
        parsear = cargar_yaml_texto
    elif formato is Formato.JSON:
        parsear = cargar_json_texto
    else:
        msg = (
            f"'{formato.value}' no es un formato de entrada. "
            "Un caso se carga desde .yaml, .yml o .json."
        )
        raise CasoInvalido(msg, campo="formato")

    try:
        datos = parsear(texto)
    except CasoInvalido:
        raise
    except Exception as exc:
        msg = (
            f"el archivo no se puede interpretar como {formato.value}. "
            "Revisá la sintaxis: la indentación y los dos puntos en YAML, "
            "las comas y las llaves en JSON."
        )
        raise CasoInvalido(msg, campo="archivo") from exc

    if not datos:
        msg = "el archivo está vacío. " + CORRECCIONES["historia"]
        raise CasoInvalido(msg, campo="archivo")

    normalizado = _normalizar(
        datos,
        fecha_de_calculo=fecha_de_calculo,
        fecha_de_calculo_si_falta=fecha_de_calculo_si_falta,
    )
    try:
        return Caso.model_validate(normalizado)
    except ValidationError as exc:
        raise _traducir(exc) from exc


def leer_documento(ruta: Path) -> dict[str, Any]:
    """El documento **crudo**, parseado y sin validar ni convertir.

    Existe para que la línea de comandos pueda enriquecer un mensaje de error
    con el cargo y las fechas del período afectado sin que esos valores pasen
    nunca por el objeto de excepción, que es lo que podría terminar en un log
    (FR-054). Devuelve `{}` si el archivo no se puede leer o parsear: quien la
    llama ya está en un camino de error y no tiene que manejar otro.
    """
    formato = EXTENSIONES.get(ruta.suffix.lower())
    if formato is None:
        return {}
    try:
        texto = ruta.read_text(encoding="utf-8")
        parsear = cargar_yaml_texto if formato is Formato.YAML else cargar_json_texto
        return parsear(texto)
    except (OSError, UnicodeDecodeError, ValueError):
        return {}


def cargar_caso(
    ruta: Path,
    *,
    fecha_de_calculo: dt.date | None = None,
    fecha_de_calculo_si_falta: dt.date | None = None,
) -> Caso:
    """Un `Caso` desde un archivo `.yaml`, `.yml` o `.json`.

    Es la única función del paquete que lee un caso del disco. `calcular` no
    toca archivos (FR-051), y por eso la equivalencia entre la línea de comandos
    y la librería es estructural: las dos pasan por acá y por `calcular`.

    Las dos fechas opcionales funcionan como en `cargar_caso_desde_texto`.
    """
    formato = EXTENSIONES.get(ruta.suffix.lower())
    if formato is None:
        soportadas = ", ".join(sorted(EXTENSIONES))
        msg = (
            f"la extensión '{ruta.suffix}' no está soportada. "
            f"Guardá el caso con una de estas extensiones: {soportadas}."
        )
        raise CasoInvalido(msg, campo="archivo")

    try:
        texto = ruta.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        msg = "el archivo de caso no existe. Revisá la ruta."
        raise CasoInvalido(msg, campo="archivo") from exc
    except OSError as exc:
        msg = "el archivo de caso no se puede leer. Revisá los permisos."
        raise CasoInvalido(msg, campo="archivo") from exc
    except UnicodeDecodeError as exc:
        msg = "el archivo de caso no está en UTF-8. Guardalo con esa codificación."
        raise CasoInvalido(msg, campo="archivo") from exc

    return cargar_caso_desde_texto(
        texto,
        formato,
        fecha_de_calculo=fecha_de_calculo,
        fecha_de_calculo_si_falta=fecha_de_calculo_si_falta,
    )
