# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T141 — ninguna vía de salida entrega el valor sin su marca (FR-046a, SC-011).

Es el resguardo que el mantenedor pidió al resolver la Q3: la marca de
provisional tiene que ser **inseparable** del monto en *todas* las salidas, no
solo en la que alguien se acordó de revisar. Un informe JSON que trae el valor
y omite el estado es un informe que invita a leer el número solo.

Se verifican las cuatro vías: el informe como objeto, el JSON, el texto y la
lectura por librería. El modelo ya lo garantiza a nivel de tipo con el
invariante I5 —`Monto` no existe sin `estado` ni `condicionantes`—; esto
verifica que ninguna **serialización** lo pierda en el camino.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from tests.casos import caso_inc_b, escenario_de
from tests.cli.conftest import CASO_INC_B
from ultimo_timbre.cli.main import app
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import EstadoResultado
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe, Monto
from ultimo_timbre.render.json_out import informe_a_json
from ultimo_timbre.render.texto import informe_a_texto
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


@pytest.fixture(scope="module")
def informe() -> Informe:
    grilla: GrillaSalarial = versiones.cargar_grilla_de_prueba(FIXTURE)
    return calcular(caso_inc_b(), reglas=REGLAS, grilla=grilla)


def test_el_informe_como_objeto_trae_la_marca(informe: Informe) -> None:
    for escenario in informe.escenarios:
        if escenario.haber is not None:
            assert escenario.haber.estado is not None
            assert escenario.haber.condicionantes


def test_el_json_nunca_trae_el_valor_sin_estado(informe: Informe) -> None:
    datos = json.loads(informe_a_json(informe))
    for escenario in datos["escenarios"]:
        haber = escenario["haber"]
        if haber is None:
            continue
        assert "valor" in haber
        assert haber.get("estado"), "el JSON entregó un valor sin estado"
        assert haber.get("condicionantes"), "el JSON entregó un valor sin condicionantes"


def test_el_texto_nunca_muestra_el_valor_sin_estado(informe: Informe) -> None:
    texto = informe_a_texto(informe)
    haber = escenario_de(informe, "2030-03-31").haber
    assert haber is not None
    assert str(haber.valor) in texto
    # En la misma línea en que aparece el valor tiene que estar el estado.
    linea = next(x for x in texto.splitlines() if str(haber.valor) in x)
    assert haber.estado.value in linea


def test_la_cli_nunca_entrega_el_valor_sin_estado(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.yaml"
    ruta.write_text(CASO_INC_B, encoding="utf-8")
    r = CliRunner().invoke(app, ["calcular", str(ruta), "--formato", "json"])
    assert r.exit_code == 0, r.output
    for escenario in json.loads(r.stdout)["escenarios"]:
        if escenario["haber"] is not None:
            assert escenario["haber"]["estado"]
            assert escenario["haber"]["condicionantes"]


def test_el_monto_no_se_puede_construir_sin_condicionantes_si_es_provisional() -> None:
    """Invariante I5, a nivel de tipo: la marca no es opcional."""
    with pytest.raises(ValidationError):
        Monto(
            valor=Decimal("1.00"),
            estado=EstadoResultado.PROVISIONAL,
            condicionantes=(),
            grilla_version="x",
            a_valores_de=dt.date(2026, 1, 1),
        )
