# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T048 — invariante I3: determinismo byte a byte (FR-048, SC-003).

Mismas entradas y mismas versiones ⇒ informe idéntico. Incluye el caso que
motiva FR-001a: correr el mismo caso en otro día no puede cambiar nada, porque
la fecha de cálculo entra como dato y no desde el reloj.
"""

from __future__ import annotations

import datetime as dt

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.render import json_out
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

inicios = st.dates(min_value=dt.date(1985, 1, 1), max_value=dt.date(2010, 12, 31))
duraciones = st.integers(min_value=400, max_value=3000)


@st.composite
def casos(draw: st.DrawFn) -> Caso:
    desde = draw(inicios)
    hasta = desde + dt.timedelta(days=draw(duraciones))
    return caso(
        periodo(desde=desde.isoformat(), hasta=hasta.isoformat()),
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-11-02",
    )


@settings(max_examples=100, deadline=None)
@given(c=casos())
def test_dos_corridas_producen_el_mismo_json(c: Caso) -> None:
    uno = json_out.informe_a_json(calcular(c, reglas=REGLAS))
    otro = json_out.informe_a_json(calcular(c, reglas=REGLAS))
    assert uno == otro


@settings(max_examples=100, deadline=None)
@given(c=casos())
def test_dos_corridas_producen_el_mismo_modelo(c: Caso) -> None:
    assert calcular(c, reglas=REGLAS) == calcular(c, reglas=REGLAS)


@settings(max_examples=60, deadline=None)
@given(c=casos())
def test_el_json_tiene_las_claves_ordenadas(c: Caso) -> None:
    """Sin orden estable, el `diff` entre dos informes es ruido."""
    import json  # noqa: PLC0415

    texto = json_out.informe_a_json(calcular(c, reglas=REGLAS))
    datos = json.loads(texto)
    assert list(datos) == sorted(datos)


@settings(max_examples=60, deadline=None)
@given(c=casos())
def test_cambiar_la_fecha_de_calculo_no_cambia_lo_que_no_depende_de_ella(
    c: Caso,
) -> None:
    """FR-001a: el informe de un caso archivado se reproduce años después."""
    import json  # noqa: PLC0415

    otra = c.model_copy(update={"fecha_de_calculo": dt.date(2031, 5, 9)})
    a = json.loads(json_out.informe_a_json(calcular(c, reglas=REGLAS)))
    b = json.loads(json_out.informe_a_json(calcular(otra, reglas=REGLAS)))
    assert a["fecha_de_calculo"] != b["fecha_de_calculo"]
    del a["fecha_de_calculo"], b["fecha_de_calculo"]
    assert a == b


def test_el_informe_no_lleva_marca_de_tiempo_de_la_corrida() -> None:
    """Un timestamp dentro del informe rompería la comparación byte a byte."""
    import json  # noqa: PLC0415

    c = caso(
        periodo(desde="2000-03-01", hasta="2026-02-28"),
        nacimiento="1970-06-20",
        ceses=["2026-02-28"],
    )
    datos = json.loads(json_out.informe_a_json(calcular(c, reglas=REGLAS)))
    prohibidos = {"generado_en", "timestamp", "corrida", "ejecutado_en"}
    assert not (prohibidos & set(datos))
