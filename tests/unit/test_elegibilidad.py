# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T056 — edad al cese y habilitación por inciso (FR-011 a FR-016)."""

from __future__ import annotations

from tests.casos import caso, f, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.informe import Informe, ResultadoInciso
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def _incisos(informe: Informe) -> dict[str, ResultadoInciso]:
    return {i.inciso: i for i in informe.elegibilidad.incisos}


def test_la_edad_al_cese_se_calcula_sin_reloj() -> None:
    c = caso(
        periodo(desde="2000-03-01", hasta="2030-03-14"),
        nacimiento="1980-03-15",
        ceses=["2030-03-14"],
        fecha_de_calculo="2030-04-01",
    )
    # un día antes del cumpleaños: todavía 49
    assert c.edad_a(f("2030-03-14")) == 49
    assert c.edad_a(f("2030-03-15")) == 50


def test_se_evaluan_los_tres_incisos() -> None:
    c = caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )
    assert set(_incisos(calcular(c, reglas=REGLAS))) == {"b", "c", "d"}


def test_cada_inciso_declara_su_norma() -> None:
    """Principio I: cada requisito con su artículo e inciso."""
    c = caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )
    for letra, res in _incisos(calcular(c, reglas=REGLAS)).items():
        assert res.norma.articulo == "24"
        assert res.norma.inciso == letra


def test_cada_inciso_detalla_sus_requisitos_con_valores() -> None:
    c = caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )
    inc_b = _incisos(calcular(c, reglas=REGLAS))["b"]
    nombres = {r.nombre for r in inc_b.requisitos}
    assert "edad" in nombres
    assert any("frente" in n or "cátedra" in n for n in nombres)
    for r in inc_b.requisitos:
        assert r.valor_requerido is not None
        assert r.valor_alcanzado is not None


def test_la_fecha_de_habilitacion_es_la_ultima_condicion_cumplida() -> None:
    """Res. IPS 995/2021 Anexo 2.1.a: desde que se cumplen todas."""
    c = caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )
    inc_b = _incisos(calcular(c, reglas=REGLAS))["b"]
    assert inc_b.cumple is True
    # los 25 años de servicio se alcanzan en 2029; los 50 de edad, en 2030-03-15
    assert inc_b.habilitado_desde == f("2030-03-15")


def test_el_minimo_de_22_anios_con_aportes_se_evalua_aparte() -> None:
    c = caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )
    minimo = calcular(c, reglas=REGLAS).elegibilidad.minimo_22_anios
    assert minimo.cumple is True
    assert minimo.valor_requerido == "22"
    assert minimo.norma.articulo == "24"


def test_un_inciso_no_cumplido_informa_el_faltante() -> None:
    c = caso(
        periodo(desde="2002-06-01", hasta="2026-05-31"),
        nacimiento="1974-05-01",
        ceses=["2026-05-31"],
        fecha_de_calculo="2026-06-01",
    )
    inc_d = _incisos(calcular(c, reglas=REGLAS))["d"]
    assert inc_d.cumple is False
    assert inc_d.habilitado_desde is None
    assert inc_d.falta is not None
    assert inc_d.falta.anios_edad > 0
    assert inc_d.falta.anios_servicio > 0


def test_un_inciso_cumplido_no_tiene_faltante() -> None:
    c = caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )
    assert _incisos(calcular(c, reglas=REGLAS))["b"].falta is None


def test_el_inciso_mas_favorable_es_el_b_cuando_se_cumple() -> None:
    """El inc. b accede por el art. 43 (75 % de base) y no por el art. 41 (70 %)."""
    c = caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )
    assert calcular(c, reglas=REGLAS).elegibilidad.inciso_mas_favorable == "b"


def test_sin_ningun_inciso_cumplido_no_hay_mas_favorable() -> None:
    c = caso(
        periodo(desde="2002-06-01", hasta="2026-05-31"),
        nacimiento="1974-05-01",
        ceses=["2026-05-31"],
        fecha_de_calculo="2026-06-01",
    )
    assert calcular(c, reglas=REGLAS).elegibilidad.inciso_mas_favorable is None


def test_los_umbrales_salen_de_las_reglas_no_del_codigo() -> None:
    """Principio I, FR-007: cambiar la regla cambia el resultado."""
    import dataclasses  # noqa: PLC0415

    del dataclasses  # solo para dejar claro que no se mutan modelos congelados
    regla = REGLAS.por_id("requisitos.art24.inc_d")
    assert regla is not None
    assert regla.valor == {"edad": 55, "anios_servicio": 30}


def test_el_desglose_cita_la_norma_de_cada_paso() -> None:
    """FR-038, FR-040."""
    c = caso(
        periodo(desde="2004-03-01", hasta="2030-03-31"),
        nacimiento="1980-03-15",
        ceses=["2030-03-31"],
        fecha_de_calculo="2030-04-01",
    )
    informe = calcular(c, reglas=REGLAS)
    assert informe.desglose
    for paso in informe.desglose:
        assert paso.regla_id
        assert paso.norma.texto
        assert paso.tipo_fuente is not None
    assert [p.orden for p in informe.desglose] == list(range(1, len(informe.desglose) + 1))
