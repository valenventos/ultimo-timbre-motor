# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Carga de datos normativos sin contaminación de float (T035, research R1).

El riesgo del Principio II no está en el cálculo sino en el **borde**: un `0.70`
escrito sin comillas en un YAML ya es float binario antes de que Pydantic lo
vea, y en ese punto el error es invisible. Este módulo es el único lugar donde
se puede interceptar, así que lo hace de dos maneras:

* el resolver de YAML no convierte decimales a float: los entrega como `str`;
* `json.load` usa `parse_float=Decimal`.

Los enteros siguen siendo `int` — las edades y los años de servicio no tienen
decimal que preservar.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

import yaml

__all__ = [
    "CargadorSinFloat",
    "a_decimal",
    "cargar_json",
    "cargar_json_texto",
    "cargar_yaml",
    "cargar_yaml_texto",
]


class CargadorSinFloat(yaml.SafeLoader):
    """SafeLoader al que se le quitó la resolución implícita a float."""


def _decimal_como_str(loader: yaml.SafeLoader, nodo: yaml.ScalarNode) -> str:
    return str(loader.construct_scalar(nodo))


# yaml resuelve los decimales con el tag `tag:yaml.org,2002:float`. Se mantiene
# el tag para no romper el parseo, pero se construye como str.
CargadorSinFloat.add_constructor("tag:yaml.org,2002:float", _decimal_como_str)


def cargar_yaml_texto(texto: str) -> dict[str, Any]:
    """Parsea YAML entregando `str` para todo decimal."""
    # nosec B506 - CargadorSinFloat deriva de yaml.SafeLoader: no instancia
    # objetos arbitrarios. Lo único que cambia es el constructor de decimales.
    datos = yaml.load(texto, Loader=CargadorSinFloat)  # nosec B506
    if datos is None:
        return {}
    if not isinstance(datos, dict):
        msg = "el documento YAML debe ser un mapeo en su raíz"
        raise ValueError(msg)
    return cast(dict[str, Any], datos)


def cargar_yaml(ruta: Path) -> dict[str, Any]:
    return cargar_yaml_texto(ruta.read_text(encoding="utf-8"))


def cargar_json_texto(texto: str) -> dict[str, Any]:
    """Parsea JSON entregando `Decimal` para todo decimal."""
    datos = json.loads(texto, parse_float=Decimal)
    if not isinstance(datos, dict):
        msg = "el documento JSON debe ser un objeto en su raíz"
        raise ValueError(msg)
    return cast(dict[str, Any], datos)


def cargar_json(ruta: Path) -> dict[str, Any]:
    return cargar_json_texto(ruta.read_text(encoding="utf-8"))


def a_decimal(valor: str | int | Decimal) -> Decimal:
    """Convierte a `Decimal` exacto.

    Rechaza `float` a propósito: aceptarlo acá reintroduciría por la puerta de
    atrás el error que todo el módulo existe para evitar.
    """
    if isinstance(valor, float):
        msg = (
            "a_decimal no acepta float: el valor debe llegar como str desde el YAML "
            "o el JSON (Principio II, research R1)"
        )
        raise TypeError(msg)
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(valor)
    except InvalidOperation as exc:
        msg = f"valor decimal inválido: {valor!r}"
        raise ValueError(msg) from exc
