# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixtures de la CLI: archivos de caso escritos en disco.

Los casos van como **texto literal** y no serializando un `Caso` del modelo, a
propósito: lo que la CLI tiene que aceptar es el formato que un gremio escribe
a mano, y un round-trip del modelo probaría el modelo, no el formato.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

# Caso del inc. b: 26 años al frente de alumnos, 50 de edad al cese.
# Coincide con `tests.casos.caso_inc_b()`, para poder comparar CLI y librería.
CASO_INC_B = """\
schema_version: "1.0.0"
fecha_de_calculo: 2030-04-01
fecha_nacimiento: 1980-03-15
fechas_cese:
  - 2030-03-31
historia:
  periodos:
    - cargo: maestro_de_grado
      establecimiento:
        tipo: estatal_dgcye
      desde: 2004-03-01
      hasta: 2030-03-31
      caja_aportes: ips
      situacion_revista: titular
"""

# El mismo caso en JSON, donde las fechas llegan como **string**: el cargador
# tiene que convertirlas en el borde, porque los modelos son `strict=True` y
# no coercionan (research R1, el mismo criterio que con los decimales).
CASO_INC_B_JSON = """\
{
  "schema_version": "1.0.0",
  "fecha_de_calculo": "2030-04-01",
  "fecha_nacimiento": "1980-03-15",
  "fechas_cese": ["2030-03-31"],
  "historia": {
    "periodos": [
      {
        "cargo": "maestro_de_grado",
        "establecimiento": {"tipo": "estatal_dgcye"},
        "desde": "2004-03-01",
        "hasta": "2030-03-31",
        "caja_aportes": "ips",
        "situacion_revista": "titular"
      }
    ]
  }
}
"""

# El período 1 tiene `hasta` anterior a `desde` (FR-003). El 0 es válido, así
# que el mensaje tiene que nombrar el 1 y no «la historia».
CASO_INVALIDO = """\
schema_version: "1.0.0"
fecha_de_calculo: 2030-04-01
fecha_nacimiento: 1980-03-15
fechas_cese:
  - 2030-03-31
historia:
  periodos:
    - cargo: maestro_de_grado
      establecimiento:
        tipo: estatal_dgcye
      desde: 2004-03-01
      hasta: 2015-02-28
      caja_aportes: ips
      situacion_revista: titular
    - cargo: maestro_de_grado
      establecimiento:
        tipo: estatal_dgcye
      desde: 2015-03-01
      hasta: 2014-12-31
      caja_aportes: ips
      situacion_revista: titular
"""

# 20 años al IPS y 10 a ANSES: fuera del Alcance de la v1 (FR-044) → exit 3.
CASO_OTRA_CAJA = """\
schema_version: "1.0.0"
fecha_de_calculo: 2026-11-02
fecha_nacimiento: 1970-05-10
fechas_cese:
  - 2026-02-28
historia:
  periodos:
    - cargo: maestro_de_grado
      establecimiento:
        tipo: estatal_dgcye
      desde: 2006-03-01
      hasta: 2026-02-28
      caja_aportes: ips
      situacion_revista: titular
    - cargo: maestro_de_grado
      establecimiento:
        tipo: estatal_dgcye
      desde: 1996-03-01
      hasta: 2006-02-28
      caja_aportes: anses
      situacion_revista: titular
"""

# Un caso sin `fecha_de_calculo`: la CLI la completa (FR-001a).
CASO_SIN_FECHA_DE_CALCULO = """\
schema_version: "1.0.0"
fecha_nacimiento: 1980-03-15
fechas_cese:
  - 2030-03-31
historia:
  periodos:
    - cargo: maestro_de_grado
      establecimiento:
        tipo: estatal_dgcye
      desde: 2004-03-01
      hasta: 2030-03-31
      caja_aportes: ips
      situacion_revista: titular
"""


def _escribir(directorio: Path, nombre: str, contenido: str) -> Path:
    ruta = directorio / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def caso_inc_b_yaml(tmp_path: Path) -> Path:
    return _escribir(tmp_path, "caso-inc-b.yaml", CASO_INC_B)


@pytest.fixture
def caso_inc_b_json(tmp_path: Path) -> Path:
    return _escribir(tmp_path, "caso-inc-b.json", CASO_INC_B_JSON)


@pytest.fixture
def caso_invalido_yaml(tmp_path: Path) -> Path:
    return _escribir(tmp_path, "caso-invalido.yaml", CASO_INVALIDO)


@pytest.fixture
def caso_otra_caja_yaml(tmp_path: Path) -> Path:
    return _escribir(tmp_path, "caso-otra-caja.yaml", CASO_OTRA_CAJA)


@pytest.fixture
def caso_sin_fecha_yaml(tmp_path: Path) -> Path:
    return _escribir(tmp_path, "caso-sin-fecha.yaml", CASO_SIN_FECHA_DE_CALCULO)
