# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T173 — las dos salidas derivan del mismo `Informe` (research R5).

«Ninguna recalcula nada» no es una buena intención: se verifica de dos maneras
complementarias.

1. **Estructural**: `render/` no importa `engine/`. Si no puede llamar al motor,
   no puede recalcular. Es la versión del argumento que no depende de que
   alguien lea el código con atención.
2. **De comportamiento**: los números que aparecen en el texto son los mismos
   que están en el JSON, y renderizar dos veces el mismo informe da el mismo
   string.

Por qué importa: una salida de texto que recalculara el porcentaje «para
mostrarlo lindo» podría mostrar 75 % mientras el JSON dice 70 %, y el
profesional no tendría forma de saber cuál leyó el IPS.
"""

from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path

import pytest

from tests.casos import caso_inc_b, caso_otra_caja
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.render.json_out import informe_a_json
from ultimo_timbre.render.texto import informe_a_texto
from ultimo_timbre.rules import versiones

RAIZ = Path(__file__).resolve().parent.parent.parent
RENDER = RAIZ / "src" / "ultimo_timbre" / "render"
REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(caso_inc_b(), reglas=REGLAS)


def _imports(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
    return nombres


def test_render_no_importa_el_motor() -> None:
    """Lo estructural: si no puede llamar al motor, no puede recalcular."""
    for ruta in sorted(RENDER.rglob("*.py")):
        for nombre in _imports(ruta):
            assert not nombre.startswith("ultimo_timbre.engine"), (
                f"{ruta.name} importa {nombre}: el renderizador no puede recalcular"
            )


def test_render_no_importa_las_reglas() -> None:
    """Tampoco puede ir a buscar un valor normativo por su cuenta."""
    for ruta in sorted(RENDER.rglob("*.py")):
        for nombre in _imports(ruta):
            assert not nombre.startswith("ultimo_timbre.rules"), (
                f"{ruta.name} importa {nombre}: todo valor tiene que venir en el Informe"
            )


def test_el_texto_es_una_funcion_pura_del_informe(informe: Informe) -> None:
    assert informe_a_texto(informe) == informe_a_texto(informe)


def test_el_texto_no_muta_el_informe(informe: Informe) -> None:
    antes = informe_a_json(informe)
    informe_a_texto(informe)
    assert informe_a_json(informe) == antes


def test_el_porcentaje_del_texto_es_el_del_json(informe: Informe) -> None:
    """El número que lee el profesional tiene que ser el que liquidaría el IPS."""
    datos = json.loads(informe_a_json(informe))
    esperado = datos["escenarios"][0]["porcentaje"]
    assert esperado is not None
    porcentaje = (Decimal(esperado) * 100).quantize(Decimal("1"))
    assert f"{porcentaje} %" in informe_a_texto(informe)


def test_el_inciso_del_texto_es_el_del_json(informe: Informe) -> None:
    datos = json.loads(informe_a_json(informe))
    assert f"inc. {datos['elegibilidad']['inciso_mas_favorable']}" in informe_a_texto(informe)


def test_el_estado_general_aparece_en_el_texto(informe: Informe) -> None:
    """FR-046a: la marca es inseparable del resultado en toda vía de salida."""
    datos = json.loads(informe_a_json(informe))
    assert datos["estado_general"] in informe_a_texto(informe).lower()


def test_el_texto_declara_las_versiones_usadas(informe: Informe) -> None:
    assert "v1" in informe_a_texto(informe)


def test_el_texto_del_caso_bloqueado_declara_el_bloqueo() -> None:
    """Un informe parcial tiene que verse como parcial, no como completo."""
    texto = informe_a_texto(calcular(caso_otra_caja(), reglas=REGLAS))
    assert "fuera del Alcance" in texto or "fuera de alcance" in texto.lower()


def test_el_texto_lleva_los_avisos_obligatorios(informe: Informe) -> None:
    """FR-042 y FR-030c: estimación orientativa y movilidad del art. 50."""
    texto = informe_a_texto(informe)
    assert "estimación orientativa" in texto
    assert "art. 50" in texto
