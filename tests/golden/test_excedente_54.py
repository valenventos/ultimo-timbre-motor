# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T114 — 25 años de servicio a los 54 (US3 esc. 6, FR-027a, FR-027b).

Es el caso que distingue las dos lecturas y por eso es el más importante de la
US3. Una docente que completa sus 25 años **a los 54** tiene cuatro años de
edad por encima de los 50 que pide el inc. b, pero recién ese día reúne todas
las condiciones:

* **criterio aplicado** (`Res. IPS 995/2021, Anexo, punto 2.1.a`): excedente 0
  al habilitarse → **75 %**, y 3 años después → **80 %**;
* **lectura literal** de los arts. 42 y 43, que mediría el excedente solo por
  la edad: 4 años → **80 %** desde el día uno.

El motor aplica la primera y **advierte** la segunda con su impacto al alza.
Los escenarios derivados llegan con la US5; acá las dos fechas de cese se
pasan como entrada, que es lo que la US3 ya permite.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.casos import caso, escenario_de, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, SentidoImpacto, TipoFuente
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    """Nacida 1969-06-15, maestra desde 1999-01-01.

    Completa 25 años de servicio el 2023-12-31, con 54 años de edad.
    """
    return calcular(
        caso(
            periodo("maestro_de_grado", desde="1999-01-01", hasta="2026-12-31"),
            nacimiento="1969-06-15",
            ceses=["2023-12-31", "2026-12-31"],
            fecha_de_calculo="2023-01-02",
        ),
        reglas=REGLAS,
    )


def test_la_habilitacion_es_la_fecha_del_servicio_no_la_de_la_edad(
    informe: Informe,
) -> None:
    """FR-027a: la última condición es el servicio, a los 54 años."""
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.habilitado_desde == f("2023-12-31")


def test_al_habilitarse_aplica_el_75_por_ciento(informe: Informe) -> None:
    """Excedente 0: recién ese día se cumplen todas las condiciones."""
    primero = escenario_de(informe, "2023-12-31")
    assert primero.inciso == "b"
    assert primero.porcentaje == Decimal("0.75")


def test_tres_anios_despues_aplica_el_80_por_ciento(informe: Informe) -> None:
    segundo = escenario_de(informe, "2026-12-31")
    assert segundo.porcentaje == Decimal("0.80")


def test_se_advierte_la_lectura_literal(informe: Informe) -> None:
    """FR-027b: existe y el profesional tiene que poder discutirla."""
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.LECTURA_LITERAL_EXCEDENTE in codigos


def test_la_advertencia_declara_impacto_al_alza(informe: Informe) -> None:
    adv = next(
        a for a in informe.advertencias if a.codigo is CodigoAdvertencia.LECTURA_LITERAL_EXCEDENTE
    )
    assert adv.sentido_impacto is SentidoImpacto.AL_ALZA
    assert adv.norma is not None
    assert adv.norma.articulo == "42-43"


def test_el_escenario_lleva_el_porcentaje_de_la_lectura_alternativa(
    informe: Informe,
) -> None:
    """FR-027b: el número alternativo, no solo la mención de que existe."""
    primero = escenario_de(informe, "2023-12-31")
    assert primero.lectura_literal is not None
    assert primero.lectura_literal.porcentaje == Decimal("0.80")
    assert primero.lectura_literal.sentido_impacto is SentidoImpacto.AL_ALZA


def test_el_desglose_declara_la_interpretacion_como_tal(informe: Informe) -> None:
    """FR-040: distinguir letra de ley de interpretación."""
    pasos = [p for p in informe.desglose if p.tipo_fuente is TipoFuente.INTERPRETACION]
    assert any("995/2021" in p.norma.texto for p in pasos)
