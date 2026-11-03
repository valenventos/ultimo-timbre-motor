# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T175 — ramas de la salida de texto que los casos dorados no recorren.

`test_render_equivalente.py` verifica que el texto no recalcula y que coincide
con el JSON. Acá se cubren los caminos que no aparecen en un caso feliz: un
monto presente, un informe sin cargo base, un escenario sin derecho y las
secciones vacías.

La rama del monto importa más que las otras: codifica FR-046a —el valor nunca
sale sin su estado— en la única vía de salida que una persona lee de corrido.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from tests.casos import caso, periodo
from tests.catalogos import con_indices_ficticios
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    EstadoResultado,
    SentidoImpacto,
    TipoEscenario,
)
from ultimo_timbre.models.informe import Condicionante, Escenario, Informe, Monto
from ultimo_timbre.render.texto import informe_a_texto
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def _informe_base() -> Informe:
    return calcular(
        caso(
            periodo("maestro_de_grado", desde="1995-01-01", hasta="2025-01-10"),
            nacimiento="1970-01-10",
            ceses=["2025-01-10"],
            fecha_de_calculo="2025-01-11",
        ),
        reglas=REGLAS,
    )


def test_el_monto_nunca_se_muestra_sin_su_estado() -> None:
    """FR-046a e invariante I5, en la vía de salida que se lee de corrido."""
    condicionante = Condicionante(
        clase=ClaseCondicionante.REGLA_NO_VERIFICADA,
        referencia="antiguedad.escala_y_tope",
        sentido_impacto=SentidoImpacto.INDETERMINADO,
        que_falta_verificar="el tope de la escala de antigüedad",
    )
    monto = Monto(
        valor=Decimal("1234567.89"),
        estado=EstadoResultado.PROVISIONAL,
        condicionantes=(condicionante,),
        grilla_version="ficticia-test",
        a_valores_de=dt.date(2025, 1, 1),
    )
    base = _informe_base()
    escenario = base.escenarios[0].model_copy(update={"haber": monto})
    informe = base.model_copy(update={"escenarios": (escenario,)})

    texto = informe_a_texto(informe)
    assert "1234567.89" in texto
    assert "provisional" in texto
    assert "ficticia-test" in texto


def test_un_informe_sin_cargo_base_lo_dice() -> None:
    """El caso del promedio de 36 meses del art. 41 (FR-020b)."""
    informe = calcular(
        caso(
            periodo("maestro_de_grado", desde="2020-01-01", hasta="2021-12-31"),
            nacimiento="1968-01-10",
            ceses=["2021-12-31"],
            fecha_de_calculo="2022-01-02",
        ),
        reglas=REGLAS,
    )
    assert informe.cargo_base is None
    texto = informe_a_texto(informe)
    assert "No se pudo determinar un cargo base" in texto


def test_un_escenario_sin_derecho_lo_dice() -> None:
    base = _informe_base()
    sin_derecho = Escenario(
        fecha_cese=dt.date(2026, 1, 10),
        tipo=TipoEscenario.PROVISTA,
        hay_derecho=False,
    )
    informe = base.model_copy(update={"escenarios": (sin_derecho,)})
    assert "No hay derecho a la fecha evaluada." in informe_a_texto(informe)


def test_el_descenso_al_cargo_inferior_se_muestra() -> None:
    informe = calcular(
        caso(
            periodo("maestro_de_grado", desde="1996-03-01", hasta="2016-12-31"),
            periodo("vicedirector_primera", desde="2017-01-01", hasta="2020-12-31"),
            periodo("director_primera", desde="2021-01-01", hasta="2022-08-31"),
            nacimiento="1970-01-10",
            ceses=["2022-08-31"],
            fecha_de_calculo="2022-09-01",
        ),
        reglas=con_indices_ficticios(REGLAS),
    )
    texto = informe_a_texto(informe)
    assert "Descenso al cargo inferior" in texto
    assert "Candidatos descartados:" in texto


def test_el_informe_sin_grilla_lo_declara() -> None:
    assert "ninguna (informe sin montos)" in informe_a_texto(_informe_base())


def test_un_informe_sin_advertencias_no_abre_la_seccion() -> None:
    informe = _informe_base()
    assert informe.advertencias == ()
    assert "Advertencias" not in informe_a_texto(informe)


def test_las_procedencias_se_listan() -> None:
    texto = informe_a_texto(_informe_base())
    assert "Procedencia de los datos" in texto
    assert "al_frente[0]" in texto
