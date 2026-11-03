# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Interfaz de línea de comandos (T176 a T181, contrato `cli.md`).

La CLI es **un cargador más un renderizador** alrededor de `calcular`. No tiene
lógica de cálculo propia, y por eso la equivalencia con la vía de librería
(FR-051) es estructural y no una coincidencia que haya que mantener a mano.

Lo único que hace y la librería no:

* **lee el archivo** de caso (`entrada.cargar_caso`);
* **completa `fecha_de_calculo`** con la fecha del sistema cuando el caso no la
  declara, y la deja asentada en el informe. El motor nunca llama al reloj
  (FR-001a); este es el único lugar del paquete que puede;
* **configura el logging**. La librería solo instala `NullHandler` (research
  R12), así que un consumidor que la importe no recibe logs que no pidió;
* **traduce el resultado a un código de salida** (FR-056).

## Códigos de salida

| 0 | informe emitido, **incluso si es provisional** (decisión Q3) |
| 2 | entrada inválida (FR-003, FR-057) |
| 3 | el informe tiene al menos una advertencia bloqueante (FR-045b) |
| 4 | error interno |

El `1` queda sin asignar a propósito: Python y Typer lo usan para fallos no
controlados, y reservarlo evita que un crash se confunda con un caso fuera de
alcance.

**El 3 no significa «no hay informe»**: el informe se emite igual, con el
análisis parcial que sí se sostiene (FR-045a). El 3 le dice a un script que no
confíe en el monto, no que el análisis no exista.
"""

from __future__ import annotations

import datetime as dt
import logging
import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from ultimo_timbre import __version__
from ultimo_timbre.engine import calcular as calcular_informe
from ultimo_timbre.entrada import cargar_caso, leer_documento
from ultimo_timbre.errors import (
    CasoInvalido,
    GrillaInvalida,
    ReglasNoDisponibles,
    UltimoTimbreError,
)
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import Formato
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.models.normativa import ConjuntoDeReglas
from ultimo_timbre.render.json_out import informe_a_json
from ultimo_timbre.render.texto import informe_a_texto
from ultimo_timbre.rules import versiones

__all__ = ["app"]

EXIT_OK = 0
EXIT_ENTRADA_INVALIDA = 2
EXIT_FUERA_DE_ALCANCE = 3
EXIT_ERROR_INTERNO = 4

_log = logging.getLogger("ultimo_timbre.cli")

app = typer.Typer(
    name="ultimo-timbre",
    help=(
        "Motor de cálculo de la jubilación ordinaria docente del IPS de la "
        "Provincia de Buenos Aires. Sin red y sin persistencia del caso."
    ),
    no_args_is_help=True,
    add_completion=False,
)


def _forzar_utf8() -> None:
    """Fuerza UTF-8 en la salida, sin depender de la consola del sistema.

    El informe es un **contrato de datos**, y `informe_a_json` lo serializa con
    `ensure_ascii=False`: los acentos viajan como caracteres, no escapados. En
    Windows la consola usa cp1252 por defecto, así que sin esto
    `ultimo-timbre calcular caso.yaml --formato json > informe.json` escribiría
    bytes cp1252 que cualquier consumidor leería mal —y un carácter no
    representable directamente rompería la corrida—.

    No alcanza con que `--salida` escriba en UTF-8 explícitamente: la salida por
    defecto es stdout, que es como se usa en una tubería.
    """
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is not None:
            reconfigurar(encoding="utf-8")


def _configurar_logging(verboso: bool) -> None:
    """El logging se configura **solo acá** (research R12, FR-054).

    Va a stderr y no a stdout: el informe tiene que poder redirigirse a un
    archivo sin que un mensaje de diagnóstico se mezcle con el JSON.

    No se corta la propagación a propósito. Sería lo habitual en una CLI, pero
    dejaría el test de canarios (T171) sin poder observar lo que el motor emite,
    y un resguardo de privacidad que no se puede auditar no es un resguardo.
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    propio = logging.getLogger("ultimo_timbre")
    propio.handlers.clear()
    propio.addHandler(handler)
    propio.setLevel(logging.DEBUG if verboso else logging.WARNING)


# Qué se le agrega al mensaje para la pantalla. Solo estos tres campos del
# período: son los que vuelven el mensaje accionable sin ser identificatorios.
# La fecha de nacimiento y el nombre del establecimiento quedan afuera incluso
# acá: no hacen falta para encontrar la línea del archivo.
CAMPOS_PARA_UBICAR = ("cargo", "desde", "hasta")


def _describir_periodo(ruta: Path, periodo_idx: int) -> str | None:
    """El cargo y las fechas del período, leídos del documento en el momento.

    Esto **no** sale del objeto de excepción, y la diferencia es el punto: una
    excepción puede terminar en un log, en una métrica o en un reporte enviado
    a otra parte, y FR-054 lo prohíbe. Esta descripción se arma acá, se imprime
    en la terminal de quien corrió el comando —su propio dato, su propia
    pantalla— y no se guarda en ningún lado.

    Devuelve `None` si el documento no se puede leer o el índice no existe: el
    mensaje sale sin enriquecer, que sigue siendo accionable por el índice.
    """
    periodos = leer_documento(ruta).get("historia", {})
    if not isinstance(periodos, dict):
        return None
    lista = periodos.get("periodos")
    if not isinstance(lista, list) or not 0 <= periodo_idx < len(lista):
        return None
    periodo = lista[periodo_idx]
    if not isinstance(periodo, dict):
        return None

    cargo = periodo.get("cargo")
    desde, hasta = periodo.get("desde"), periodo.get("hasta")

    partes = [str(cargo)] if cargo is not None else []
    if desde is not None and hasta is not None:
        partes.append(f"{desde} a {hasta}")
    elif desde is not None:
        partes.append(f"desde {desde}")
    elif hasta is not None:
        partes.append(f"hasta {hasta}")
    return ", ".join(partes) or None


def _error(
    mensaje: str,
    *,
    campo: str | None = None,
    periodo_idx: int | None = None,
    ruta: Path | None = None,
) -> NoReturn:
    """Imprime un error accionable en stderr y termina con exit 2.

    Ubica el problema por el índice anónimo del período y, cuando puede, lo
    enriquece con el cargo y las fechas de ese período para que el usuario
    encuentre la línea sin contar renglones (FR-057, Principio VIII).
    """
    ubicacion = ""
    if periodo_idx is not None:
        ubicacion = f" en el período {periodo_idx}"
        detalle = _describir_periodo(ruta, periodo_idx) if ruta is not None else None
        if detalle is not None:
            ubicacion += f" ({detalle})"
    elif campo is not None:
        ubicacion = f" en '{campo}'"

    typer.secho(f"Error{ubicacion}:", fg=typer.colors.RED, err=True)
    typer.secho(f"  {mensaje}", err=True)
    raise typer.Exit(code=EXIT_ENTRADA_INVALIDA)


def _cargar(ruta: Path, fecha_calculo: dt.datetime | None) -> Caso:
    """Carga el caso resolviendo la fecha de cálculo (FR-001a).

    La precedencia es **explícita > la del archivo > la del sistema**, y la
    aplica `entrada.cargar_caso`. Esta función es el único punto del paquete que
    consulta el reloj: el motor nunca lo hace, y la fecha resuelta queda
    asentada dentro del `Caso` y por lo tanto en el informe.
    """
    try:
        return cargar_caso(
            ruta,
            fecha_de_calculo=fecha_calculo.date() if fecha_calculo is not None else None,
            # DTZ011: `date.today()` usa la hora local, que es exactamente lo
            # que «hoy» significa para quien corre la CLI. En UTC, una corrida
            # cerca de medianoche en Buenos Aires caería en otro día.
            fecha_de_calculo_si_falta=dt.date.today(),  # noqa: DTZ011
        )
    except CasoInvalido as exc:
        # El mensaje ya es accionable; el sufijo técnico `[campo=...]` que
        # agrega la excepción no le aporta nada a quien lee la terminal.
        _error(
            str(exc).split(" [")[0],
            campo=exc.campo,
            periodo_idx=exc.periodo_idx,
            ruta=ruta,
        )


def _reglas(version: str | None) -> ConjuntoDeReglas:
    try:
        return versiones.cargar_reglas(version)
    except (ReglasNoDisponibles, FileNotFoundError) as exc:
        disponibles = ", ".join(versiones.versiones_de_reglas()) or "ninguna"
        _error(
            f"la versión de reglas pedida no existe. Disponibles: {disponibles}.",
            campo="reglas",
        )
        raise AssertionError from exc  # pragma: no cover - `_error` siempre sale


def _grilla(version: str | None) -> GrillaSalarial | None:
    """La grilla pedida, o ninguna.

    Sin `--grilla` no se busca ninguna: el informe sale sin montos, que es el
    comportamiento correcto mientras la US4 no esté implementada y el único
    posible si no hay grilla aprobada todavía.
    """
    if version is None:
        return None
    try:
        return versiones.cargar_grilla(version)
    except (GrillaInvalida, ReglasNoDisponibles, FileNotFoundError) as exc:
        disponibles = ", ".join(versiones.versiones_de_grillas()) or "ninguna"
        _error(
            f"la versión de grilla pedida no existe o no está aprobada. "
            f"Disponibles: {disponibles}.",
            campo="grilla",
        )
        raise AssertionError from exc  # pragma: no cover - `_error` siempre sale


def _emitir(informe: Informe, formato: Formato, salida: Path | None) -> None:
    texto = informe_a_json(informe) if formato is Formato.JSON else informe_a_texto(informe)
    if salida is None:
        typer.echo(texto)
        return
    try:
        salida.write_text(texto + "\n", encoding="utf-8")
    except OSError:
        _error(
            "el archivo de salida no se puede escribir. Revisá la ruta y los permisos.",
            campo="salida",
        )


@app.command()
def calcular(
    caso: Annotated[Path, typer.Argument(help="Ruta al archivo de caso (.yaml, .yml o .json)")],
    *,
    formato: Annotated[
        Formato, typer.Option("--formato", help="Formato del informe")
    ] = Formato.TEXTO,
    salida: Annotated[
        Path | None, typer.Option("--salida", help="Archivo donde escribir el informe")
    ] = None,
    reglas: Annotated[
        str | None, typer.Option("--reglas", help="Versión del conjunto de reglas")
    ] = None,
    grilla: Annotated[
        str | None, typer.Option("--grilla", help="Versión de grilla salarial")
    ] = None,
    fecha_calculo: Annotated[
        dt.datetime | None,
        typer.Option(
            "--fecha-calculo",
            formats=["%Y-%m-%d"],
            help="Fecha respecto de la cual se evalúa todo lo relativo a hoy",
        ),
    ] = None,
    verboso: Annotated[
        bool, typer.Option("--verboso", help="Diagnóstico detallado en stderr")
    ] = False,
) -> None:
    """Calcula el informe de un caso y lo emite."""
    _forzar_utf8()
    _configurar_logging(verboso)

    if formato is Formato.YAML:
        _error(
            "'yaml' no es un formato de salida del informe. Usá 'json' o 'texto'.",
            campo="formato",
        )

    entrada = _cargar(caso, fecha_calculo)
    conjunto = _reglas(reglas)
    escala = _grilla(grilla)

    try:
        informe = calcular_informe(entrada, reglas=conjunto, grilla=escala)
    except UltimoTimbreError:
        _log.exception("error interno del motor")
        typer.secho(
            "Error interno del motor. El caso no se pudo calcular; "
            "no es un problema del archivo de caso.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=EXIT_ERROR_INTERNO) from None

    _emitir(informe, formato, salida)

    if informe.tiene_bloqueos:
        raise typer.Exit(code=EXIT_FUERA_DE_ALCANCE)
    raise typer.Exit(code=EXIT_OK)


@app.command()
def validar(
    caso: Annotated[Path, typer.Argument(help="Ruta al archivo de caso")],
    *,
    verboso: Annotated[bool, typer.Option("--verboso", help="Diagnóstico detallado")] = False,
) -> None:
    """Valida el archivo de caso sin calcular nada.

    Pensado para que un gremio revise una carga antes de procesarla: verifica la
    estructura y la coherencia temporal de cada período (FR-003).
    """
    _forzar_utf8()
    _configurar_logging(verboso)
    entrada = _cargar(caso, None)
    typer.echo(
        f"El caso es válido: {len(entrada.historia.periodos)} período(s), "
        f"{len(entrada.fechas_cese)} fecha(s) de cese."
    )
    raise typer.Exit(code=EXIT_OK)


def _comando_versiones(
    *,
    verboso: Annotated[bool, typer.Option("--verboso", help="Diagnóstico detallado")] = False,
) -> None:
    """Lista las versiones de reglas y de grillas disponibles."""
    _forzar_utf8()
    _configurar_logging(verboso)
    disponibles = versiones.versiones_disponibles()

    typer.echo(f"ultimo-timbre {__version__}")
    typer.echo("")
    typer.echo("Conjuntos de reglas:")
    for version in disponibles.reglas or ("(ninguno)",):
        typer.echo(f"  {version}")
    typer.echo("")
    typer.echo("Grillas salariales aprobadas:")
    for version in disponibles.grillas or ("(ninguna)",):
        typer.echo(f"  {version}")
    raise typer.Exit(code=EXIT_OK)


# El nombre del comando lo fija el contrato (`ultimo-timbre versiones`); el de
# la función no puede ser `versiones` porque colisionaría con el módulo
# `rules.versiones` que este archivo importa.
app.command(name="versiones")(_comando_versiones)


if __name__ == "__main__":  # pragma: no cover - lo cubre `__main__.py`
    app()
