# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cuestión abierta #9 — acceso por el inc. b con cargo base directivo.

`[DL 9650/80, arts. 41 y 43 — NO_VERIFICADA]`

El caso: una docente que cumple el art. 24 inc. b **por sus años al frente de
alumnos**, pero cuyo cargo base —el de los 36/60 meses del art. 41— es un cargo
que **no** cuenta al frente, típicamente un directivo. 26 años de maestra de
grado y 4 de vicedirectora es exactamente eso.

No está verificado si en ese caso corresponde el 75 % del art. 43 sobre ese
cargo base, o el 70 % del art. 41. Son dos lecturas razonables:

* el art. 43 rige «el personal del art. 24 inc. b», y ella lo es;
* pero el 75 % del art. 43 se pensó para el cargo al frente de alumnos, y el
  cargo base no lo es.

El motor aplica el **70 %**, que es el criterio más conservador, lo declara
como valor por defecto aplicado y marca el resultado provisional. Aplicar el 75
% sin verificarlo sería prometer un haber mayor que el que el IPS puede
liquidar, y de los dos errores posibles ese es el que le cuesta plata al
docente.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.casos import caso, f, periodo
from tests.catalogos import con_jerarquia_ficticia
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import (
    CodigoAdvertencia,
    EstadoRegla,
    EstadoResultado,
    SentidoImpacto,
)
from ultimo_timbre.models.informe import Condicionante, Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")
REGLAS_JER = con_jerarquia_ficticia(REGLAS)
REGLA = "porcentaje.art43.cargo_base_no_al_frente"


def _caso() -> Caso:
    """26 años de maestra de grado y 4 de vicedirectora, 50 de edad al cese.

    La habilitación del inc. b coincide con el cese —la última condición es la
    edad— así que el excedente es 0 y el porcentaje queda en la base: 70 % o
    75 %, que es justo lo que la Cuestión #9 discute, sin excedentes de por
    medio que confundan la comparación.
    """
    return caso(
        periodo("maestro_de_grado", desde="1994-01-01", hasta="2019-12-31"),
        periodo("vicedirector", desde="2020-01-01", hasta="2023-12-31"),
        nacimiento="1973-12-31",
        ceses=["2023-12-31"],
        fecha_de_calculo="2024-01-02",
    )


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(_caso(), reglas=REGLAS_JER)


def _cond(informe: Informe) -> Condicionante:
    return next(c for c in informe.condicionantes if c.referencia == REGLA)


# ---------------------------------------------------------------------------
# El escenario, antes de lo que se verifica de él
# ---------------------------------------------------------------------------


def test_cumple_el_inciso_b_por_sus_anios_al_frente(informe: Informe) -> None:
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.cumple is True
    al_frente = next(r for r in inc_b.requisitos if "al frente" in r.nombre)
    assert al_frente.valor_alcanzado == "26"
    assert al_frente.valor_requerido == "25"


def test_accede_por_el_inciso_b(informe: Informe) -> None:
    assert informe.elegibilidad.inciso_mas_favorable == "b"
    assert informe.escenarios[0].inciso == "b"


def test_el_cargo_base_es_la_vicedireccion(informe: Informe) -> None:
    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "vicedirector"


def test_el_cargo_base_no_cuenta_al_frente_de_alumnos() -> None:
    """Resguardo del escenario: si contara, la Cuestión #9 no se plantearía."""
    entrada = REGLAS.catalogo_cargos.buscar("vicedirector")
    assert entrada is not None
    assert entrada.al_frente_de_alumnos is False


def test_el_excedente_es_cero(informe: Informe) -> None:
    """Para que la comparación sea 70 % contra 75 % y no 80 % contra 85 %."""
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.habilitado_desde == f("2023-12-31")
    assert informe.escenarios[0].fecha_cese == f("2023-12-31")


# ---------------------------------------------------------------------------
# Lo que la Cuestión #9 cambia
# ---------------------------------------------------------------------------


def test_se_aplica_el_criterio_conservador_del_70_por_ciento(informe: Informe) -> None:
    """El 75 % del art. 43 queda sin aplicar hasta que se verifique."""
    assert informe.escenarios[0].porcentaje == Decimal("0.70")


def test_la_regla_esta_cargada_como_no_verificada() -> None:
    regla = REGLAS.por_id(REGLA)
    assert regla is not None
    assert regla.estado is EstadoRegla.NO_VERIFICADA
    assert regla.cuestion_abierta == 9


def test_la_regla_declara_que_aplico_un_valor_por_defecto() -> None:
    """Distingue «sin verificar y sin valor» de «sin verificar pero hubo que elegir»."""
    regla = REGLAS.por_id(REGLA)
    assert regla is not None
    assert regla.valor_por_defecto_aplicado is True


def test_el_condicionante_declara_sentido_indeterminado(informe: Informe) -> None:
    """No es al alza ni a la baja: las dos lecturas son defendibles."""
    assert _cond(informe).sentido_impacto is SentidoImpacto.INDETERMINADO


def test_el_condicionante_declara_la_magnitud(informe: Informe) -> None:
    """FR-046b: la dirección sola no alcanza; hace falta cuánto."""
    assert _cond(informe).magnitud_estimada == "70 % vs 75 % sobre el cargo base"


def test_el_condicionante_cita_los_arts_41_y_43(informe: Informe) -> None:
    cond = _cond(informe)
    assert cond.norma is not None
    assert cond.norma.articulo == "41-43"


def test_el_resultado_es_provisional(informe: Informe) -> None:
    assert informe.estado_general is EstadoResultado.PROVISIONAL


def test_se_advierte_la_regla_sin_verificar(informe: Informe) -> None:
    """Y el mensaje nombra los dos porcentajes en juego (Principio VIII)."""
    avisos = [
        a
        for a in informe.advertencias
        if a.codigo is CodigoAdvertencia.REGLA_NO_VERIFICADA and "cargo base" in a.mensaje
    ]
    assert avisos
    assert "70" in avisos[0].mensaje
    assert "75" in avisos[0].mensaje


def test_el_desglose_explica_por_que_no_se_aplico_el_art_43(informe: Informe) -> None:
    """Principio IV: el audit trail no puede decir «inc. b» y liquidar 70 % sin más."""
    pasos = [p for p in informe.desglose if p.regla_id == REGLA]
    assert pasos
    assert pasos[0].norma.articulo == "41-43"
    assert "70" in (pasos[0].salida or "")


# ---------------------------------------------------------------------------
# El contraste: con un cargo base que sí cuenta al frente, el art. 43 se aplica
# ---------------------------------------------------------------------------


def test_si_el_cargo_base_cuenta_al_frente_se_aplica_el_75_por_ciento() -> None:
    """La misma historia con el catálogo real elige maestro_de_grado como base.

    Sin jerarquía cargada los dos cargos empatan y el desempate por meses toma
    la maestra de grado, que sí cuenta al frente. Ahí la Cuestión #9 no se
    plantea y el art. 43 se aplica derecho.
    """
    informe = calcular(_caso(), reglas=REGLAS)
    assert informe.cargo_base is not None
    assert informe.cargo_base.cargo == "maestro_de_grado"
    assert informe.escenarios[0].porcentaje == Decimal("0.75")
    assert REGLA not in {c.referencia for c in informe.condicionantes}


def test_el_inciso_d_no_activa_la_cuestion_9() -> None:
    """La #9 es del art. 43: quien accede por el art. 41 ya está en el 70 %."""
    informe = calcular(
        caso(
            periodo("director", desde="1995-01-01", hasta="2025-01-10"),
            nacimiento="1969-01-10",
            ceses=["2025-01-10"],
            fecha_de_calculo="2025-01-11",
        ),
        reglas=REGLAS,
    )
    assert informe.escenarios[0].inciso == "d"
    assert REGLA not in {c.referencia for c in informe.condicionantes}
