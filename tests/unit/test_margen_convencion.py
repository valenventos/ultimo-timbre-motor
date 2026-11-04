# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T073, T075 — margen de sensibilidad a la convención de conteo.

La idea: si un requisito se cumple (o se incumple) por un margen más chico que
el desplazamiento que puede producir el cambio de convención, entonces **la
convención está decidiendo el resultado**, y eso no se puede presentar como
definitivo. Lejos del umbral la convención es irrelevante y el resultado sigue
siendo definitivo.
"""

from __future__ import annotations

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import ClaseCondicionante, EstadoResultado
from ultimo_timbre.models.informe import Informe, ResultadoRequisito
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
REGLA_CONVENCION = "computo.convencion_de_conteo"


def _informe(desde: str, hasta: str, nacimiento: str, cese: str) -> Informe:
    return calcular(
        caso(
            periodo(desde=desde, hasta=hasta),
            nacimiento=nacimiento,
            ceses=[cese],
            fecha_de_calculo="2030-12-31",
        ),
        reglas=REGLAS,
    )


def _req(informe: Informe, inciso: str, nombre: str) -> ResultadoRequisito:
    res = next(i for i in informe.elegibilidad.incisos if i.inciso == inciso)
    return next(r for r in res.requisitos if r.nombre.startswith(nombre))


# --------------------------------------------------------------------------- #
# T073 — a 3 días del umbral, provisional
# --------------------------------------------------------------------------- #


def test_un_requisito_a_tres_dias_del_umbral_sale_provisional() -> None:
    """25 años de servicio alcanzados 3 días antes del cese."""
    # 2005-03-01 + 25 años = 2030-03-01, así que al 2030-03-03 hay 25 años y 2 días
    informe = _informe("2005-03-01", "2030-03-03", "1975-01-10", "2030-03-03")
    requisito = _req(informe, "b", "años al frente")
    assert requisito.cumple is True
    assert requisito.estado is EstadoResultado.PROVISIONAL


def test_el_informe_queda_provisional_cerca_del_umbral() -> None:
    informe = _informe("2005-03-01", "2030-03-03", "1975-01-10", "2030-03-03")
    assert informe.estado_general is EstadoResultado.PROVISIONAL
    assert informe.elegibilidad.estado is EstadoResultado.PROVISIONAL


def test_el_condicionante_es_la_regla_de_la_convencion() -> None:
    """FR-046b: el informe tiene que decir qué lo condiciona."""
    informe = _informe("2005-03-01", "2030-03-03", "1975-01-10", "2030-03-03")
    refs = {c.referencia for c in informe.condicionantes}
    assert REGLA_CONVENCION in refs
    cond = next(c for c in informe.condicionantes if c.referencia == REGLA_CONVENCION)
    assert cond.clase is ClaseCondicionante.REGLA_NO_VERIFICADA
    assert cond.que_falta_verificar


def test_un_requisito_incumplido_al_borde_tambien_es_provisional() -> None:
    """La sensibilidad vale en los dos sentidos, no solo cuando cumple."""
    # 3 días antes de alcanzar los 25 años
    informe = _informe("2005-03-05", "2030-03-01", "1975-01-10", "2030-03-01")
    requisito = _req(informe, "b", "años al frente")
    assert requisito.cumple is False
    assert requisito.estado is EstadoResultado.PROVISIONAL


# --------------------------------------------------------------------------- #
# T075 — cada requisito declara su estado y su margen
# --------------------------------------------------------------------------- #


def test_cada_requisito_de_servicio_declara_su_margen() -> None:
    informe = _informe("2004-03-01", "2030-03-31", "1980-03-15", "2030-03-31")
    requisito = _req(informe, "b", "años de servicio")
    assert requisito.margen_dias is not None
    assert requisito.margen_dias > 0


def test_el_requisito_de_edad_no_es_sensible_a_la_convencion() -> None:
    """La edad se cuenta desde la fecha de nacimiento: no hay convención en juego."""
    informe = _informe("2004-03-01", "2030-03-31", "1980-03-15", "2030-03-31")
    requisito = _req(informe, "b", "edad")
    assert requisito.estado is EstadoResultado.DEFINITIVO


def test_lejos_del_umbral_el_requisito_es_definitivo() -> None:
    """26 años contra 25 requeridos: la convención no mueve nada."""
    informe = _informe("2004-03-01", "2030-03-31", "1980-03-15", "2030-03-31")
    requisito = _req(informe, "b", "años al frente")
    assert requisito.cumple is True
    assert requisito.estado is EstadoResultado.DEFINITIVO


def test_lejos_del_umbral_el_informe_sigue_definitivo() -> None:
    informe = _informe("2004-03-01", "2030-03-31", "1980-03-15", "2030-03-31")
    assert informe.estado_general is EstadoResultado.DEFINITIVO
    assert informe.condicionantes == ()


def test_el_inciso_declara_su_estado() -> None:
    informe = _informe("2005-03-01", "2030-03-03", "1975-01-10", "2030-03-03")
    inciso = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inciso.estado is EstadoResultado.PROVISIONAL
