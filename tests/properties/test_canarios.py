# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T171 — invariante I8: ningún dato de dominio en diagnóstico (FR-054, SC-008).

El método es el de research R12: se corre un caso con valores **marcados**
—«canarios»— y se falla si alguno aparece en la salida de diagnóstico. Lo que
convierte el Principio III en verificable y no en una promesa es justamente
esto: no alcanza con no escribir `logger.debug(cargo)` hoy, hace falta que un
test lo detecte si alguien lo escribe mañana.

**Qué cuenta como diagnóstico y qué no**: los logs, las métricas, las trazas y
los reportes de error. El **informe no** — es el producto que el usuario pidió,
y por supuesto contiene cargos y fechas. La distinción es a quién va dirigido:
el informe, a quien cargó el caso; el log, a un archivo que puede terminar en
cualquier parte.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.casos import ESTATAL, caso, periodo
from ultimo_timbre.cli.main import app
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Establecimiento
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

# Los canarios: valores inventados y buscables. Si alguno aparece en un log,
# es porque un valor de dominio se filtró por ahí.
CANARIO_ESTABLECIMIENTO = "ZZCANARIOESCUELAZZ"
CANARIO_NACIMIENTO = "1973-07-19"
CANARIO_CESE = "2029-11-23"
CANARIOS = (CANARIO_ESTABLECIMIENTO, CANARIO_NACIMIENTO, CANARIO_CESE)

CASO_CON_CANARIOS = f"""\
schema_version: "1.0.0"
fecha_de_calculo: 2029-12-01
fecha_nacimiento: {CANARIO_NACIMIENTO}
fechas_cese:
  - {CANARIO_CESE}
historia:
  periodos:
    - cargo: maestro_de_grado
      establecimiento:
        tipo: estatal_dgcye
        nombre: {CANARIO_ESTABLECIMIENTO}
      desde: 2000-03-01
      hasta: {CANARIO_CESE}
      caja_aportes: ips
      situacion_revista: titular
"""


class _Capturador(logging.Handler):
    """Captura todo lo que cualquier logger emita durante la corrida."""

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.lineas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lineas.append(self.format(record))

    @property
    def texto(self) -> str:
        return "\n".join(self.lineas)


@pytest.fixture
def diagnostico() -> Any:
    """Engancha un handler a la raíz y deja pasar todos los niveles."""
    handler = _Capturador()
    raiz = logging.getLogger()
    nivel_previo = raiz.level
    raiz.addHandler(handler)
    raiz.setLevel(logging.NOTSET)
    try:
        yield handler
    finally:
        raiz.removeHandler(handler)
        raiz.setLevel(nivel_previo)


def test_la_libreria_no_emite_ningun_log(diagnostico: _Capturador) -> None:
    """R12: el motor no loguea por sí mismo; solo `NullHandler`."""
    c = caso(
        periodo(
            desde="2000-03-01",
            hasta=CANARIO_CESE,
            establecimiento=Establecimiento(tipo=ESTATAL.tipo, nombre=CANARIO_ESTABLECIMIENTO),
        ),
        nacimiento=CANARIO_NACIMIENTO,
        ceses=[CANARIO_CESE],
        fecha_de_calculo="2029-12-01",
    )
    calcular(c, reglas=REGLAS)
    assert diagnostico.lineas == [], diagnostico.texto


def test_ningun_canario_aparece_en_el_diagnostico_de_la_cli(
    diagnostico: _Capturador, tmp_path: Path
) -> None:
    """Corrida completa por CLI, con logging al máximo detalle."""
    ruta = tmp_path / "caso.yaml"
    ruta.write_text(CASO_CON_CANARIOS, encoding="utf-8")
    r = CliRunner().invoke(app, ["calcular", str(ruta), "--formato", "json", "--verboso"])
    assert r.exit_code == 0, r.output
    for canario in CANARIOS:
        assert canario not in diagnostico.texto, f"{canario} se filtró al diagnóstico"


def test_ningun_canario_llega_al_diagnostico_en_un_camino_de_error(
    diagnostico: _Capturador, tmp_path: Path
) -> None:
    """FR-054 alcanza al logging también cuando la corrida falla.

    La **pantalla** sí puede llevar el cargo y las fechas del período afectado
    —lo agrega la CLI al imprimir, para que el mensaje sea accionable (FR-057)—,
    y eso se verifica en `tests/cli/test_error_enriquecido.py`. Lo que no puede
    llevar ninguna de las dos salidas es la fecha de nacimiento ni el nombre del
    establecimiento, y el logging no puede llevar nada del caso.
    """
    roto = CASO_CON_CANARIOS.replace("desde: 2000-03-01", "desde: 2031-03-01")
    ruta = tmp_path / "roto.yaml"
    ruta.write_text(roto, encoding="utf-8")
    r = CliRunner().invoke(app, ["calcular", str(ruta), "--verboso"])
    assert r.exit_code == 2, r.output

    for canario in CANARIOS:
        assert canario not in diagnostico.texto, f"{canario} se filtró al diagnóstico"

    # En la pantalla, estos dos tampoco: no ayudan a ubicar la línea.
    assert CANARIO_NACIMIENTO not in r.output
    assert CANARIO_ESTABLECIMIENTO not in r.output


def test_el_informe_si_puede_llevar_datos_del_caso(tmp_path: Path) -> None:
    """Resguardo de la distinción: el informe es el producto, no diagnóstico.

    Si este test fallara, el motor estaría censurando su propia salida, que es
    lo contrario de lo que FR-054 pide.
    """
    ruta = tmp_path / "caso.yaml"
    ruta.write_text(CASO_CON_CANARIOS, encoding="utf-8")
    r = CliRunner().invoke(app, ["calcular", str(ruta), "--formato", "json"])
    assert r.exit_code == 0, r.output
    assert CANARIO_CESE in r.stdout


def test_el_capturador_detecta_un_canario_plantado(diagnostico: _Capturador) -> None:
    """Resguardo: sin esto, los tests de arriba podrían pasar en vacío."""
    logging.getLogger("prueba").error("valor %s", CANARIO_ESTABLECIMIENTO)
    assert CANARIO_ESTABLECIMIENTO in diagnostico.texto
