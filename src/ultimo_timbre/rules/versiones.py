# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Carga de reglas y grillas versionadas (T036).

El motor **solo ve grillas que están en `grids/`**, y estar ahí significa haber
pasado por un PR aprobado (research R4). Lo que sí puede encontrar es la
ausencia de la grilla vigente, y eso dispara FR-034.

Además `grids/` rechaza toda grilla con `ficticia: true`: la grilla de prueba
vive en `tests/fixtures/` y un informe real valuado con importes inventados es
el peor resultado posible del motor (Principio IX).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from ultimo_timbre.errors import GrillaInvalida, ReglasNoDisponibles
from ultimo_timbre.models.enums import (
    CondicionAlFrente,
    EstadoRegla,
    NaturalezaServicio,
    SentidoImpacto,
    TipoFuente,
)
from ultimo_timbre.models.grilla import ComponenteSalarial, GrillaSalarial, ValorCargo
from ultimo_timbre.models.informe import Versiones
from ultimo_timbre.models.normativa import (
    CatalogoDeCargos,
    ConjuntoDeReglas,
    EntradaCatalogo,
    Norma,
    Regla,
)
from ultimo_timbre.rules.loader import a_decimal, cargar_yaml

__all__ = [
    "cargar_grilla",
    "cargar_grilla_de_prueba",
    "cargar_grilla_desde",
    "cargar_reglas",
    "grilla_vigente_a",
    "versiones_disponibles",
]

RAIZ = Path(__file__).resolve().parents[3]
DIR_REGLAS = RAIZ / "rules"
DIR_GRILLAS = RAIZ / "grids"


# --------------------------------------------------------------------------- #
# Reglas
# --------------------------------------------------------------------------- #
def _fecha(valor: Any) -> dt.date | None:
    if valor is None:
        return None
    if isinstance(valor, dt.date):
        return valor
    return dt.date.fromisoformat(str(valor))


def _norma(datos: dict[str, Any]) -> Norma:
    return Norma(
        texto=str(datos["texto"]),
        ley=str(datos["ley"]),
        articulo=datos.get("articulo"),
        inciso=datos.get("inciso"),
        enlace=datos.get("enlace"),
    )


def _regla(datos: dict[str, Any]) -> Regla:
    # strict=True no convierte str a enum: el loader lo hace explícito, para que
    # un valor desconocido falle acá y no silenciosamente más adelante.
    impacto = datos.get("impacto_si_no_verificada")
    return Regla(
        id=str(datos["id"]),
        norma=_norma(datos["norma"]),
        tipo=TipoFuente(datos["tipo"]),
        estado=EstadoRegla(datos["estado"]),
        vigencia_desde=_fecha(datos.get("vigencia_desde")),
        vigencia_hasta=_fecha(datos.get("vigencia_hasta")),
        verificada_en=_fecha(datos.get("verificada_en")),
        impacto_si_no_verificada=SentidoImpacto(impacto) if impacto else None,
        que_falta_verificar=datos.get("que_falta_verificar"),
        magnitud_estimada=datos.get("magnitud_estimada"),
        cuestion_abierta=datos.get("cuestion_abierta"),
        valor_por_defecto_aplicado=bool(datos.get("valor_por_defecto_aplicado", False)),
        valor=datos.get("valor"),
    )


def _entrada_catalogo(datos: dict[str, Any]) -> EntradaCatalogo:
    naturaleza = datos.get("naturaleza")
    indice = datos.get("indice_escalafonario")
    return EntradaCatalogo(
        cargo=str(datos["cargo"]),
        jerarquia=datos.get("jerarquia"),
        # str -> Decimal en el borde: un `float` binario arruinaría un índice
        # como 1,32 antes de que el modelo lo vea (research R1).
        indice_escalafonario=a_decimal(indice) if indice is not None else None,
        indice_es_por_hora=bool(datos.get("indice_es_por_hora", False)),
        regla_indice=datos.get("regla_indice"),
        al_frente_de_alumnos=datos.get("al_frente_de_alumnos"),
        naturaleza=NaturalezaServicio(naturaleza) if naturaleza else None,
        norma=_norma(datos["norma"]),
        estado=EstadoRegla(datos.get("estado", "verificado")),
        regla_id=datos.get("regla_id"),
        condicion=CondicionAlFrente(datos.get("condicion", "directa")),
        regla_umbral=datos.get("regla_umbral"),
    )


def versiones_de_reglas() -> tuple[str, ...]:
    if not DIR_REGLAS.exists():
        return ()
    return tuple(sorted(d.name for d in DIR_REGLAS.iterdir() if d.is_dir()))


def cargar_reglas(version: str | None = None) -> ConjuntoDeReglas:
    """Carga un conjunto de reglas versionado. Sin `version`, la última."""
    disponibles = versiones_de_reglas()
    if not disponibles:
        msg = f"no hay ninguna versión de reglas en {DIR_REGLAS}"
        raise ReglasNoDisponibles(msg)
    elegida = version or disponibles[-1]
    if elegida not in disponibles:
        msg = f"versión de reglas inexistente: {elegida}"
        raise ReglasNoDisponibles(msg)

    base = DIR_REGLAS / elegida
    reglas: list[Regla] = []
    entradas: list[EntradaCatalogo] = []

    for ruta in sorted(base.glob("*.yaml")):
        datos = cargar_yaml(ruta)
        for cruda in datos.get("reglas", ()):
            reglas.append(_regla(cruda))
        for cruda in datos.get("entradas", ()):
            entradas.append(_entrada_catalogo(cruda))

    return ConjuntoDeReglas(
        version=elegida,
        reglas=tuple(reglas),
        catalogo_cargos=CatalogoDeCargos(version=elegida, entradas=tuple(entradas)),
    )


# --------------------------------------------------------------------------- #
# Grillas
# --------------------------------------------------------------------------- #
def _grilla(datos: dict[str, Any], *, permitir_ficticia: bool, ruta: Path) -> GrillaSalarial:
    ficticia = bool(datos.get("ficticia", False))
    if ficticia and not permitir_ficticia:
        msg = (
            f"{ruta.name} declara `ficticia: true` y no puede usarse para valuar un informe. "
            "Una grilla de prueba vive en tests/fixtures/, nunca en grids/ (Principio IX)."
        )
        raise GrillaInvalida(msg)

    if not datos.get("aprobada_por"):
        msg = (
            f"{ruta.name} no declara `aprobada_por`: ninguna grilla sin aprobador puede "
            "valuar un informe (FR-010, Principio IX)."
        )
        raise GrillaInvalida(msg)

    valores: list[ValorCargo] = []
    for cargo, componentes in (datos.get("valores") or {}).items():
        valores.append(
            ValorCargo(
                cargo=str(cargo),
                componentes=tuple(
                    ComponenteSalarial(
                        codigo_concepto=str(c["codigo_concepto"]),
                        descripcion=str(c["descripcion"]),
                        importe=a_decimal(c["importe"]),
                        bonificable=bool(c["bonificable"]),
                        remunerativo=bool(c["remunerativo"]),
                        excluido_art40=bool(c.get("excluido_art40", False)),
                        regla_id=c.get("regla_id"),
                    )
                    for c in componentes
                ),
            )
        )

    vigencia_desde = _fecha(datos["vigencia_desde"])
    extraida_en = _fecha(datos["extraida_en"])
    aprobada_en = _fecha(datos["aprobada_en"])
    if vigencia_desde is None or extraida_en is None or aprobada_en is None:
        msg = f"{ruta.name} tiene fechas incompletas"
        raise GrillaInvalida(msg)

    return GrillaSalarial(
        version=str(datos["version"]),
        norma=_norma(datos["norma"]),
        vigencia_desde=vigencia_desde,
        vigencia_hasta=_fecha(datos.get("vigencia_hasta")),
        extraida_en=extraida_en,
        aprobada_por=str(datos["aprobada_por"]),
        aprobada_en=aprobada_en,
        # `None` cuando la publicación oficial no cita el acto que la aprueba.
        # No invalida la grilla: condiciona todo monto que salga de ella.
        acto_aprobatorio=(
            _norma(datos["acto_aprobatorio"]) if datos.get("acto_aprobatorio") else None
        ),
        valores=tuple(valores),
        enlace=datos.get("enlace"),
        ficticia=ficticia,
    )


def cargar_grilla_desde(ruta: Path) -> GrillaSalarial:
    """Carga una grilla destinada a valuar informes. Rechaza las ficticias."""
    try:
        return _grilla(cargar_yaml(ruta), permitir_ficticia=False, ruta=ruta)
    except KeyError as exc:
        msg = f"{ruta.name} le falta el campo {exc.args[0]!r}"
        raise GrillaInvalida(msg) from exc


def cargar_grilla_de_prueba(ruta: Path) -> GrillaSalarial:
    """Solo para la suite de tests: acepta `ficticia: true`."""
    return _grilla(cargar_yaml(ruta), permitir_ficticia=True, ruta=ruta)


def versiones_de_grillas() -> tuple[str, ...]:
    if not DIR_GRILLAS.exists():
        return ()
    return tuple(sorted(r.stem for r in DIR_GRILLAS.glob("*.yaml")))


def cargar_grilla(version: str | None = None) -> GrillaSalarial:
    disponibles = versiones_de_grillas()
    if not disponibles:
        msg = f"no hay ninguna grilla aprobada en {DIR_GRILLAS}"
        raise ReglasNoDisponibles(msg)
    elegida = version or disponibles[-1]
    ruta = DIR_GRILLAS / f"{elegida}.yaml"
    if not ruta.exists():
        msg = f"versión de grilla inexistente: {elegida}"
        raise ReglasNoDisponibles(msg)
    return cargar_grilla_desde(ruta)


def grilla_vigente_a(fecha: dt.date) -> GrillaSalarial | None:
    """La grilla aprobada vigente a una fecha, o `None`.

    Devolver `None` en lugar de lanzar es deliberado: el llamador decide, y
    `calcular` emite la advertencia `grilla_ausente` con el monto marcado
    provisional (FR-034) en lugar de quedarse sin informe.
    """
    for nombre in reversed(versiones_de_grillas()):
        grilla = cargar_grilla(nombre)
        if grilla.vigente_a(fecha):
            return grilla
    return None


def versiones_disponibles() -> Versiones:
    return Versiones(reglas=versiones_de_reglas(), grillas=versiones_de_grillas())
