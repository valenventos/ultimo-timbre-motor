# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T073, T074, T075 — estimación de la habilitación futura (FR-016, US1 esc. 2).

Cuando no hay derecho a la fecha evaluada, informar solo el faltante deja al
profesional con la mitad de la respuesta. El motor estima **cuándo** se
cumpliría cada inciso, proyectando los períodos en curso bajo supuesto de
continuidad — y lo declara como supuesto, no como dato.

Si lo que falta es servicio y no hay ningún período en curso, la fecha no se
puede estimar: sin servicios futuros el requisito no avanza. Si lo único que
falta es edad, sí se estima, porque la edad avanza sola.
"""

from __future__ import annotations

from tests.casos import caso, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.enums import CodigoAdvertencia, EstadoResultado
from ultimo_timbre.models.informe import Informe, ResultadoInciso
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def _inc(informe: Informe, letra: str) -> ResultadoInciso:
    return next(i for i in informe.elegibilidad.incisos if i.inciso == letra)


def _con_periodo_en_curso() -> Informe:
    """24 años de servicio, 52 de edad, todavía trabajando."""
    return calcular(
        caso(
            periodo(desde="2002-06-01", hasta=None),
            nacimiento="1974-05-01",
            ceses=["2026-05-31"],
            fecha_de_calculo="2026-06-01",
        ),
        reglas=REGLAS,
    )


def _sin_periodo_en_curso() -> Informe:
    """Mismo caso pero con el período cerrado: ya no suma servicio."""
    return calcular(
        caso(
            periodo(desde="2002-06-01", hasta="2026-05-31"),
            nacimiento="1974-05-01",
            ceses=["2026-05-31"],
            fecha_de_calculo="2026-06-01",
        ),
        reglas=REGLAS,
    )


# --------------------------------------------------------------------------- #
# T073 — con período en curso se estima
# --------------------------------------------------------------------------- #


def test_se_estima_la_fecha_de_cada_inciso_no_cumplido() -> None:
    informe = _con_periodo_en_curso()
    for letra in ("b", "c", "d"):
        inc = _inc(informe, letra)
        assert inc.cumple is False
        assert inc.estimado_para is not None, letra
        assert inc.estimado_para > f("2026-05-31"), letra


def test_la_estimacion_del_inciso_b_es_un_anio_mas_de_servicio() -> None:
    """Le faltaba 1 año de servicio al frente; la edad ya la tenía."""
    inc = _inc(_con_periodo_en_curso(), "b")
    assert inc.estimado_para == f("2027-05-31")


def test_el_inciso_d_se_estima_por_la_condicion_mas_tardia() -> None:
    """Le faltan 3 años de edad y 6 de servicio: manda el servicio."""
    inc = _inc(_con_periodo_en_curso(), "d")
    assert inc.estimado_para is not None
    assert inc.estimado_para >= f("2032-05-31")


def test_la_estimacion_no_pisa_el_faltante() -> None:
    """FR-016 pide las dos cosas: cuánto falta y cuándo se cumpliría."""
    inc = _inc(_con_periodo_en_curso(), "d")
    assert inc.falta is not None
    assert inc.falta.anios_edad > 0
    assert inc.estimado_para is not None


def test_un_inciso_cumplido_no_lleva_estimacion() -> None:
    informe = calcular(
        caso(
            periodo(desde="2004-03-01", hasta="2030-03-31"),
            nacimiento="1980-03-15",
            ceses=["2030-03-31"],
            fecha_de_calculo="2030-04-01",
        ),
        reglas=REGLAS,
    )
    assert _inc(informe, "b").estimado_para is None


# --------------------------------------------------------------------------- #
# T074 — la estimación lleva su condicionante
# --------------------------------------------------------------------------- #


def test_la_estimacion_advierte_el_supuesto_de_continuidad() -> None:
    informe = _con_periodo_en_curso()
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.SUPUESTO_CONTINUIDAD in codigos


def test_la_estimacion_lleva_el_condicionante_de_continuidad() -> None:
    informe = _con_periodo_en_curso()
    refs = {c.referencia for c in informe.condicionantes}
    assert CodigoAdvertencia.SUPUESTO_CONTINUIDAD.value in refs


def test_el_informe_con_estimacion_es_provisional() -> None:
    assert _con_periodo_en_curso().estado_general is EstadoResultado.PROVISIONAL


# --------------------------------------------------------------------------- #
# T075 — sin período en curso
# --------------------------------------------------------------------------- #


def test_sin_periodo_en_curso_no_se_estima_lo_que_depende_de_servicio() -> None:
    inc = _inc(_sin_periodo_en_curso(), "b")
    assert inc.cumple is False
    assert inc.estimado_para is None
    assert inc.motivo_sin_estimacion is not None
    assert "servicios futuros" in inc.motivo_sin_estimacion


def test_sin_periodo_en_curso_si_se_estima_lo_que_solo_depende_de_edad() -> None:
    """La edad avanza sola: si es lo único que falta, la fecha es calculable."""
    informe = calcular(
        caso(
            # 31 años de servicio cerrados, pero solo 52 de edad
            periodo(desde="1995-06-01", hasta="2026-05-31"),
            nacimiento="1974-05-01",
            ceses=["2026-05-31"],
            fecha_de_calculo="2026-06-01",
        ),
        reglas=REGLAS,
    )
    inc_d = _inc(informe, "d")
    assert inc_d.cumple is False
    assert inc_d.falta is not None
    assert inc_d.falta.anios_servicio == 0
    assert inc_d.estimado_para == f("2029-05-01")
    assert inc_d.motivo_sin_estimacion is None


def test_el_motivo_no_aparece_cuando_si_se_pudo_estimar() -> None:
    assert _inc(_con_periodo_en_curso(), "b").motivo_sin_estimacion is None
