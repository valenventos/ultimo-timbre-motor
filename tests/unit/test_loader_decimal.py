# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T016 — los loaders nunca entregan float (research R1, Principio II).

El riesgo del Principio II no está en el cálculo sino en el borde: un `0.75`
escrito sin comillas en un YAML ya es float binario antes de que Pydantic lo
vea. Estos tests fijan el comportamiento del único lugar donde eso se puede
interceptar.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ultimo_timbre.rules import loader


def _hojas(valor: object) -> list[object]:
    if isinstance(valor, dict):
        return [h for v in valor.values() for h in _hojas(v)]
    if isinstance(valor, list):
        return [h for v in valor for h in _hojas(v)]
    return [valor]


def test_yaml_con_numero_entre_comillas_entrega_str() -> None:
    datos = loader.cargar_yaml_texto('porcentaje: "0.70"\n')
    assert datos["porcentaje"] == "0.70"
    assert isinstance(datos["porcentaje"], str)


def test_yaml_sin_comillas_no_entrega_float() -> None:
    """Un decimal sin comillas no puede llegar como float a la capa de dominio."""
    datos = loader.cargar_yaml_texto("porcentaje: 0.70\n")
    assert not isinstance(datos["porcentaje"], float)
    assert datos["porcentaje"] == "0.70"


def test_ninguna_hoja_del_yaml_es_float() -> None:
    texto = 'a: 0.70\nb: "0.75"\nc:\n  - 1.5\n  - 2\nd:\n  e: 3.25\n'
    for hoja in _hojas(loader.cargar_yaml_texto(texto)):
        assert not isinstance(hoja, float), f"{hoja!r} llegó como float"


def test_los_enteros_del_yaml_siguen_siendo_int() -> None:
    """Las edades y los años de servicio son enteros, no decimales."""
    datos = loader.cargar_yaml_texto("edad: 50\nanios: 25\n")
    assert datos["edad"] == 50
    assert isinstance(datos["edad"], int)


def test_los_booleanos_y_nulos_se_preservan() -> None:
    datos = loader.cargar_yaml_texto("bonificable: true\nvalor: null\n")
    assert datos["bonificable"] is True
    assert datos["valor"] is None


def test_json_parsea_los_decimales_como_decimal() -> None:
    datos = loader.cargar_json_texto('{"porcentaje": 0.70}')
    assert isinstance(datos["porcentaje"], Decimal)
    assert datos["porcentaje"] == Decimal("0.70")


def test_cargar_yaml_desde_archivo(tmp_path: Path) -> None:
    ruta = tmp_path / "regla.yaml"
    ruta.write_text("importe: 123456.78\n", encoding="utf-8")
    datos = loader.cargar_yaml(ruta)
    assert datos["importe"] == "123456.78"
    assert not isinstance(datos["importe"], float)


def test_a_decimal_convierte_str_exacto() -> None:
    assert loader.a_decimal("0.70") == Decimal("0.70")


def test_a_decimal_rechaza_float() -> None:
    """Aceptar un float acá reintroduciría el error que el loader evita."""
    with pytest.raises(TypeError):
        loader.a_decimal(0.70)  # type: ignore[arg-type]
