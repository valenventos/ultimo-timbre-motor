# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La pantalla lleva el dato; el log no (FR-054 con FR-057).

Son dos exigencias que parecen chocar y no chocan, porque hablan de destinos
distintos:

* **FR-057 y Principio VIII** piden un mensaje accionable. Para quien cargó un
  archivo de treinta períodos, «el período 1» obliga a contar renglones;
  «el período 1 (maestro_de_grado, 2015-03-01 a 2014-12-31)» lo lleva directo a
  la línea.
* **FR-054** prohíbe datos personales en logs, métricas, trazas y reportes de
  error. Eso protege lo que **viaja**: un archivo de log puede terminar en
  cualquier parte, y una excepción es lo que un `logger.exception()` captura.

La resolución: el **objeto** `CasoInvalido` lleva solo índice, campo y
corrección. El enriquecimiento lo hace la CLI en el momento de imprimir,
releyendo el documento, y no se guarda en ningún lado.

Lo que **no** se enriquece, ni en la pantalla: la fecha de nacimiento y el
nombre del establecimiento. No hacen falta para encontrar la línea del archivo y
son más identificatorios que un cargo y un par de fechas.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ultimo_timbre.cli.main import app
from ultimo_timbre.entrada import cargar_caso
from ultimo_timbre.errors import CasoInvalido

# Valores marcados, para poder buscarlos sin ambigüedad en cada salida.
CARGO = "maestro_de_grado"
DESDE = "2015-03-01"
HASTA = "2014-12-31"
NACIMIENTO = "1977-08-04"
ESTABLECIMIENTO = "ZZESCUELACANARIOZZ"

CASO_ROTO = f"""\
schema_version: "1.0.0"
fecha_de_calculo: 2030-04-01
fecha_nacimiento: {NACIMIENTO}
fechas_cese:
  - 2030-03-31
historia:
  periodos:
    - cargo: preceptor
      establecimiento:
        tipo: estatal_dgcye
        nombre: {ESTABLECIMIENTO}
      desde: 2004-03-01
      hasta: 2015-02-28
      caja_aportes: ips
      situacion_revista: titular
    - cargo: {CARGO}
      establecimiento:
        tipo: estatal_dgcye
        nombre: {ESTABLECIMIENTO}
      desde: {DESDE}
      hasta: {HASTA}
      caja_aportes: ips
      situacion_revista: titular
"""


class _Capturador(logging.Handler):
    """Captura los `LogRecord` de toda la jerarquía durante la corrida."""

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.lineas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        # Se formatea el registro **y** se guarda su crudo: un valor podría
        # colarse por los argumentos sin aparecer en el mensaje formateado.
        self.lineas.append(self.format(record))
        self.lineas.append(repr(record.args))
        self.lineas.append(str(record.msg))

    @property
    def texto(self) -> str:
        return "\n".join(self.lineas)


@pytest.fixture
def logs() -> object:
    """Engancha el capturador a la raíz y al logger del paquete.

    A los dos porque la CLI configura el suyo propio: si solo se mirara la raíz
    y alguien cortara la propagación, el test pasaría en vacío.
    """
    handler = _Capturador()
    enganchados = [logging.getLogger(), logging.getLogger("ultimo_timbre")]
    niveles = [log.level for log in enganchados]
    for log in enganchados:
        log.addHandler(handler)
        log.setLevel(logging.NOTSET)
    try:
        yield handler
    finally:
        for log, nivel in zip(enganchados, niveles, strict=True):
            log.removeHandler(handler)
            log.setLevel(nivel)


@pytest.fixture
def caso_roto(tmp_path: Path) -> Path:
    ruta = tmp_path / "caso-roto.yaml"
    ruta.write_text(CASO_ROTO, encoding="utf-8")
    return ruta


# ---------------------------------------------------------------------------
# El objeto de excepción: solo índice, campo y corrección
# ---------------------------------------------------------------------------


def test_la_excepcion_no_lleva_ningun_valor_del_caso(caso_roto: Path) -> None:
    """Es lo que podría terminar en un log, así que va limpia (FR-054)."""
    with pytest.raises(CasoInvalido) as exc:
        cargar_caso(caso_roto)

    mensaje = str(exc.value)
    for valor in (CARGO, DESDE, HASTA, NACIMIENTO, ESTABLECIMIENTO):
        assert valor not in mensaje, f"'{valor}' se filtró al objeto de excepción"


def test_la_excepcion_si_lleva_el_indice_el_campo_y_la_correccion(caso_roto: Path) -> None:
    with pytest.raises(CasoInvalido) as exc:
        cargar_caso(caso_roto)

    assert exc.value.periodo_idx == 1
    assert exc.value.campo == "hasta"
    assert "Corregí" in str(exc.value)


# ---------------------------------------------------------------------------
# La pantalla: enriquecida con el cargo y las fechas de ese período
# ---------------------------------------------------------------------------


def test_la_cli_muestra_el_cargo_y_las_fechas_del_periodo(caso_roto: Path) -> None:
    """FR-057: que el usuario encuentre la línea sin contar renglones."""
    r = CliRunner().invoke(app, ["calcular", str(caso_roto), "--verboso"])
    assert r.exit_code == 2, r.output

    assert CARGO in r.output
    assert DESDE in r.output
    assert HASTA in r.output
    assert "período 1" in r.output
    assert "Corregí" in r.output


def test_la_cli_no_muestra_el_cargo_del_periodo_que_esta_bien(caso_roto: Path) -> None:
    """Se enriquece **ese** período, no la historia entera."""
    r = CliRunner().invoke(app, ["calcular", str(caso_roto)])
    assert r.exit_code == 2
    assert "preceptor" not in r.output


def test_la_cli_no_muestra_el_nacimiento_ni_el_establecimiento(caso_roto: Path) -> None:
    """El enriquecimiento se limita a cargo, 'desde' y 'hasta'.

    La fecha de nacimiento y el nombre del establecimiento no ayudan a encontrar
    la línea y son más identificatorios, así que no entran ni en la pantalla.
    """
    r = CliRunner().invoke(app, ["calcular", str(caso_roto), "--verboso"])
    assert r.exit_code == 2
    assert NACIMIENTO not in r.output
    assert ESTABLECIMIENTO not in r.output


def test_el_comando_validar_enriquece_igual(caso_roto: Path) -> None:
    r = CliRunner().invoke(app, ["validar", str(caso_roto)])
    assert r.exit_code == 2
    assert CARGO in r.output
    assert HASTA in r.output


# ---------------------------------------------------------------------------
# El logging: nunca, ni con --verboso
# ---------------------------------------------------------------------------


def test_ningun_valor_del_caso_llega_al_logging(caso_roto: Path, logs: _Capturador) -> None:
    """El mismo dato que la pantalla sí muestra, acá no puede estar."""
    r = CliRunner().invoke(app, ["calcular", str(caso_roto), "--verboso"])
    assert r.exit_code == 2

    for valor in (CARGO, DESDE, HASTA, NACIMIENTO, ESTABLECIMIENTO):
        assert valor not in logs.texto, f"'{valor}' se filtró al logging"


def test_una_corrida_exitosa_tampoco_loguea_valores_del_caso(
    tmp_path: Path, logs: _Capturador
) -> None:
    """No es solo el camino de error: el camino feliz tampoco loguea el caso."""
    sano = CASO_ROTO.replace(f"hasta: {HASTA}", "hasta: 2030-03-31")
    ruta = tmp_path / "caso.yaml"
    ruta.write_text(sano, encoding="utf-8")

    r = CliRunner().invoke(app, ["calcular", str(ruta), "--formato", "json", "--verboso"])
    assert r.exit_code == 0, r.output

    for valor in (CARGO, NACIMIENTO, ESTABLECIMIENTO):
        assert valor not in logs.texto, f"'{valor}' se filtró al logging"


def test_el_capturador_ve_lo_que_el_paquete_loguea(logs: _Capturador) -> None:
    """Resguardo: sin esto los tests de arriba podrían pasar en vacío."""
    logging.getLogger("ultimo_timbre.prueba").warning("centinela %s", CARGO)
    assert CARGO in logs.texto
