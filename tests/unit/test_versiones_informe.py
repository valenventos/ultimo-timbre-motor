# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T056 — el informe declara con qué versiones se produjo (FR-009).

Sin esto, un informe no es auditable: dos resultados distintos del mismo caso
podrían venir de dos conjuntos de reglas y no habría forma de saberlo.
"""

from __future__ import annotations

import json

from tests.casos import caso_inc_b
from ultimo_timbre.engine import calcular
from ultimo_timbre.render import json_out
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def test_el_informe_declara_la_version_de_reglas() -> None:
    assert calcular(caso_inc_b(), reglas=REGLAS).version_reglas == "v1"


def test_la_version_de_reglas_es_la_del_conjunto_recibido() -> None:
    """No se lee del disco por su cuenta: sale del `ConjuntoDeReglas` que entró."""
    informe = calcular(caso_inc_b(), reglas=REGLAS)
    assert informe.version_reglas == REGLAS.version


def test_sin_grilla_la_version_de_grilla_es_none() -> None:
    assert calcular(caso_inc_b(), reglas=REGLAS).version_grilla is None


def test_las_versiones_aparecen_en_el_json() -> None:
    datos = json.loads(json_out.informe_a_json(calcular(caso_inc_b(), reglas=REGLAS)))
    assert datos["version_reglas"] == "v1"
    assert datos["version_grilla"] is None
