# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T055 — la fecha de cálculo entra como dato, no desde el reloj (FR-001a).

Sin esto el determinismo valdría solo dentro de la misma jornada: un caso
archivado junto a un expediente tiene que producir el mismo informe cuando se lo
vuelva a correr dentro de un año.
"""

from __future__ import annotations

import datetime as dt
import json

from tests.casos import caso, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.render import json_out
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def _caso(fecha_de_calculo: str) -> Caso:
    return caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo=fecha_de_calculo,
    )


def test_el_informe_declara_la_fecha_de_calculo() -> None:
    informe = calcular(_caso("2030-04-01"), reglas=REGLAS)
    assert informe.fecha_de_calculo == f("2030-04-01")


def test_la_fecha_de_calculo_aparece_en_el_json() -> None:
    datos = json.loads(json_out.informe_a_json(calcular(_caso("2030-04-01"), reglas=REGLAS)))
    assert datos["fecha_de_calculo"] == "2030-04-01"


def test_dos_fechas_de_calculo_solo_cambian_ese_campo() -> None:
    a = json.loads(json_out.informe_a_json(calcular(_caso("2030-04-01"), reglas=REGLAS)))
    b = json.loads(json_out.informe_a_json(calcular(_caso("2035-09-20"), reglas=REGLAS)))
    assert a["fecha_de_calculo"] != b["fecha_de_calculo"]
    del a["fecha_de_calculo"], b["fecha_de_calculo"]
    assert a == b


def test_la_elegibilidad_no_depende_de_la_fecha_de_calculo() -> None:
    """Depende de la fecha de cese, que es lo que cierra los cómputos."""
    temprana = calcular(_caso("2030-04-01"), reglas=REGLAS).elegibilidad
    tardia = calcular(_caso("2040-01-01"), reglas=REGLAS).elegibilidad
    assert temprana == tardia


def test_el_caso_exige_la_fecha_de_calculo() -> None:
    """La librería la pide; la CLI es la que la completa (FR-001a)."""
    import pytest  # noqa: PLC0415
    from pydantic import ValidationError  # noqa: PLC0415

    from ultimo_timbre.models.caso import Caso, HistoriaDeServicios  # noqa: PLC0415

    with pytest.raises(ValidationError):
        Caso(  # type: ignore[call-arg]
            fecha_nacimiento=dt.date(1980, 3, 15),
            historia=HistoriaDeServicios(periodos=(periodo(),)),
            fechas_cese=(dt.date(2030, 3, 31),),
        )
