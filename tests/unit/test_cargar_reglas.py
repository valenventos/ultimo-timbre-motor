# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Carga de los datos normativos reales del repositorio.

Cierra un hueco de `tasks.md`: la Fase 2 crea `cargar_reglas` (T036) y los
cuatro YAML de `rules/v1` (T039 a T042), pero ninguna tarea verifica que se
carguen juntos. Sin este test, un YAML mal formado o una regla sin fuente
recién aparecería en la US1.

Lo que fija, además de la carga: **ninguna regla sin norma**, y **ningún valor
inventado** — toda regla sin fuente verificable tiene `valor: null` y declara su
impacto (Principio I, FR-006, FR-046b).
"""

from __future__ import annotations

import pytest

from ultimo_timbre.errors import ReglasNoDisponibles
from ultimo_timbre.models.enums import (
    CondicionAlFrente,
    EstadoRegla,
    SentidoImpacto,
    TipoFuente,
)
from ultimo_timbre.models.normativa import ConjuntoDeReglas
from ultimo_timbre.rules import versiones


@pytest.fixture(scope="module")
def reglas() -> ConjuntoDeReglas:
    return versiones.cargar_reglas()


def test_carga_la_version_v1(reglas: ConjuntoDeReglas) -> None:
    assert reglas.version == "v1"
    assert len(reglas.reglas) > 0


def test_versiones_disponibles_incluye_v1() -> None:
    assert "v1" in versiones.versiones_disponibles().reglas


def test_los_ids_de_regla_son_unicos(reglas: ConjuntoDeReglas) -> None:
    ids = [r.id for r in reglas.reglas]
    assert len(ids) == len(set(ids))


def test_toda_regla_declara_su_norma(reglas: ConjuntoDeReglas) -> None:
    """Principio I: una regla sin fuente es una opinión."""
    for regla in reglas.reglas:
        assert regla.norma.texto.strip()
        assert regla.norma.ley.strip()


def test_ninguna_regla_no_verificada_lleva_valor(reglas: ConjuntoDeReglas) -> None:
    """La regla de datos: nada se completa con un valor plausible.

    La excepción son las reglas que declaran `valor_por_defecto_aplicado`: el
    motor no puede *no* elegir una convención de conteo, así que la elección se
    declara en lugar de esconderse en el código.
    """
    for regla in reglas.no_verificadas:
        if regla.valor_por_defecto_aplicado:
            assert regla.valor is not None, f"{regla.id} declara un default sin valor"
            continue
        assert regla.valor is None, f"{regla.id} tiene un valor tentativo"


def test_toda_regla_no_verificada_declara_impacto_y_que_falta(
    reglas: ConjuntoDeReglas,
) -> None:
    """FR-046b: sin esto el informe no puede explicar la provisionalidad."""
    for regla in reglas.no_verificadas:
        assert regla.impacto_si_no_verificada is not None
        assert regla.que_falta_verificar


def test_estan_las_seis_cuestiones_abiertas_del_dominio(
    reglas: ConjuntoDeReglas,
) -> None:
    abiertas = {r.cuestion_abierta for r in reglas.no_verificadas if r.cuestion_abierta}
    assert {1, 2, 3, 4, 5, 6} <= abiertas


def test_los_umbrales_del_art_24_son_los_documentados(reglas: ConjuntoDeReglas) -> None:
    """50/25, 50/25 con 10 al frente, 55/30 y el mínimo de 22 años."""
    inc_b = reglas.por_id("requisitos.art24.inc_b")
    inc_c = reglas.por_id("requisitos.art24.inc_c")
    inc_d = reglas.por_id("requisitos.art24.inc_d")
    minimo = reglas.por_id("requisitos.art24.minimo_con_aportes")
    assert inc_b is not None
    assert inc_b.valor == {
        "edad": 50,
        "anios_servicio": 25,
        "anios_al_frente": 25,
        "horas_catedra": 20,
    }
    assert inc_c is not None
    assert inc_c.valor == {"edad": 50, "anios_servicio": 25, "anios_al_frente": 10}
    assert inc_d is not None
    assert inc_d.valor == {"edad": 55, "anios_servicio": 30}
    assert minimo is not None
    assert minimo.valor == {"anios_con_aportes": 22}


@pytest.mark.parametrize(
    ("regla_id", "porcentaje"),
    [
        ("haber.art41.base", "0.70"),
        ("haber.art42.excedente_3", "0.75"),
        ("haber.art42.excedente_5", "0.80"),
        ("haber.art43.base", "0.75"),
        ("haber.art43.excedente_3", "0.80"),
        ("haber.art43.excedente_5", "0.85"),
        ("haber.art43.excedente_3.lectura_multiplicativa", "0.7875"),
        ("haber.art43.excedente_5.lectura_multiplicativa", "0.825"),
    ],
)
def test_los_porcentajes_son_los_documentados(
    reglas: ConjuntoDeReglas, regla_id: str, porcentaje: str
) -> None:
    regla = reglas.por_id(regla_id)
    assert regla is not None
    assert regla.valor is not None
    assert regla.valor["porcentaje"] == porcentaje


def test_los_porcentajes_llegan_como_str_no_como_float(reglas: ConjuntoDeReglas) -> None:
    """Principio II: el borde del YAML es donde el float se cuela."""
    for regla in reglas.reglas:
        if not regla.valor:
            continue
        for clave, valor in regla.valor.items():
            assert not isinstance(valor, float), f"{regla.id}.{clave} llegó como float"


def test_los_plazos_del_cargo_base_son_36_y_60(reglas: ConjuntoDeReglas) -> None:
    regla = reglas.por_id("haber.art41.cargo_base")
    assert regla is not None
    assert regla.valor == {"meses_consecutivos": 36, "meses_alternados": 60}


def test_el_computo_del_excedente_es_una_interpretacion(reglas: ConjuntoDeReglas) -> None:
    """FR-027a: criterio del IPS, no letra de la ley (Principio I)."""
    regla = reglas.por_id("excedente.computo_desde")
    assert regla is not None
    assert regla.tipo is TipoFuente.INTERPRETACION
    assert regla.norma.ley == "Res. IPS 995/2021"


# --------------------------------------------------------------------------- #
# Catálogo de cargos
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("cargo", "ley"),
    [
        ("preceptor", "Ley 13469"),
        ("bibliotecario_ensenanza_superior", "Ley 13469"),
        ("tecnico_docente_psicologia", "Ley 10745"),
        ("tecnico_docente_educacion_especial", "Ley 10745"),
        ("visitadora_higiene_escolar", "Ley 11860"),
    ],
)
def test_los_cargos_con_ley_expresa_estan_verificados(
    reglas: ConjuntoDeReglas, cargo: str, ley: str
) -> None:
    """FR-002a: los que una ley nombrada en spec.md asimila expresamente."""
    entrada = reglas.catalogo_cargos.buscar(cargo)
    assert entrada is not None
    assert entrada.al_frente_de_alumnos is True
    assert entrada.estado is EstadoRegla.VERIFICADO
    assert entrada.norma.ley == ley


def test_maestro_de_grado_esta_al_frente_por_el_inciso_b(
    reglas: ConjuntoDeReglas,
) -> None:
    """El art. 24 inc. b nombra a los maestros al frente directo de alumnos."""
    entrada = reglas.catalogo_cargos.buscar("maestro_de_grado")
    assert entrada is not None
    assert entrada.al_frente_de_alumnos is True
    assert entrada.estado is EstadoRegla.VERIFICADO
    assert entrada.norma.articulo == "24"
    assert entrada.norma.inciso == "b"
    assert entrada.condiciona_resultado is False


@pytest.mark.parametrize("cargo", ["director_primera", "vicedirector_primera"])
def test_director_y_vicedirector_no_estan_al_frente_pero_quedan_condicionados(
    reglas: ConjuntoDeReglas, cargo: str
) -> None:
    """False por la letra del inc. b; condicionados por la extensión de la Ley 13469."""
    entrada = reglas.catalogo_cargos.buscar(cargo)
    assert entrada is not None
    assert entrada.al_frente_de_alumnos is False
    assert entrada.estado is EstadoRegla.VERIFICADO
    assert entrada.regla_id == "al_frente.ley_13469.extension"
    assert entrada.condiciona_resultado is True


def test_la_extension_de_la_ley_13469_tiene_impacto_al_alza(
    reglas: ConjuntoDeReglas,
) -> None:
    """Si alcanzara, el acceso pasaría del art. 41 (70 %) al art. 43 (75 %)."""
    regla = reglas.por_id("al_frente.ley_13469.extension")
    assert regla is not None
    assert regla.impacto_si_no_verificada is SentidoImpacto.AL_ALZA
    assert regla.cuestion_abierta == 8


def test_horas_catedra_se_modela_como_umbral_no_como_booleano(
    reglas: ConjuntoDeReglas,
) -> None:
    """El art. 24 inc. b asimila a los profesores que reúnen veinte horas cátedra."""
    entrada = reglas.catalogo_cargos.buscar("hora_catedra_secundaria")
    assert entrada is not None
    assert entrada.condicion is CondicionAlFrente.POR_HORAS_CATEDRA
    assert entrada.al_frente_de_alumnos is None
    assert entrada.regla_umbral == "requisitos.art24.inc_b"
    assert entrada.norma.inciso == "b"


def test_el_umbral_de_horas_catedra_sale_de_la_regla_no_del_catalogo(
    reglas: ConjuntoDeReglas,
) -> None:
    """Principio I: el 20 es un valor normativo y vive en la regla."""
    entrada = reglas.catalogo_cargos.buscar("hora_catedra_secundaria")
    assert entrada is not None
    assert entrada.regla_umbral is not None
    regla = reglas.por_id(entrada.regla_umbral)
    assert regla is not None
    assert regla.valor is not None
    assert regla.valor["horas_catedra"] == 20


# ---------------------------------------------------------------------------
# Art. 43: los porcentajes del excedente son interpretación
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("regla_id", ["haber.art43.excedente_3", "haber.art43.excedente_5"])
def test_los_excedentes_del_art_43_son_interpretacion(
    reglas: ConjuntoDeReglas, regla_id: str
) -> None:
    """La letra dice «se incrementará en un cinco por ciento»; leerlo como puntos
    porcentuales es una interpretación, y el informe lo declara como tal."""
    regla = reglas.por_id(regla_id)
    assert regla is not None
    assert regla.tipo is TipoFuente.INTERPRETACION
    assert regla.norma.ley == "Res. IPS 995/2021"
    assert "CARGO BASE" in regla.norma.texto
    assert regla.valor is not None
    assert regla.valor["lectura"] == "puntos_porcentuales"


@pytest.mark.parametrize(
    ("regla_id", "porcentaje", "alternativa_de"),
    [
        ("haber.art43.excedente_3.lectura_multiplicativa", "0.7875", "haber.art43.excedente_3"),
        ("haber.art43.excedente_5.lectura_multiplicativa", "0.825", "haber.art43.excedente_5"),
    ],
)
def test_la_lectura_multiplicativa_del_art_43_se_registra_a_la_baja(
    reglas: ConjuntoDeReglas, regla_id: str, porcentaje: str, alternativa_de: str
) -> None:
    """FR-027b: la lectura alternativa se informa, no se aplica."""
    regla = reglas.por_id(regla_id)
    assert regla is not None
    assert regla.valor is not None
    assert regla.valor["porcentaje"] == porcentaje
    assert regla.valor["lectura"] == "multiplicativa"
    assert regla.valor["sentido"] == SentidoImpacto.A_LA_BAJA.value
    assert regla.valor["alternativa_de"] == alternativa_de


@pytest.mark.parametrize(
    "regla_id",
    [
        "haber.art43.base",
        "haber.art43.excedente_3.lectura_multiplicativa",
        "haber.art43.excedente_5.lectura_multiplicativa",
    ],
)
def test_el_art_43_no_se_cita_con_inciso(reglas: ConjuntoDeReglas, regla_id: str) -> None:
    """El art. 43 no tiene incisos: refiere al personal del art. 24 inc. b."""
    regla = reglas.por_id(regla_id)
    assert regla is not None
    assert regla.norma.inciso is None
    assert "art. 24 inc. b" in regla.norma.texto


def test_ninguna_entrada_del_catalogo_declara_jerarquia(reglas: ConjuntoDeReglas) -> None:
    """Cuestión abierta #4: no hay orden numérico documentado que transcribir."""
    for entrada in reglas.catalogo_cargos.entradas:
        assert entrada.jerarquia is None


def test_toda_entrada_no_verificada_apunta_a_una_regla_existente(
    reglas: ConjuntoDeReglas,
) -> None:
    for entrada in reglas.catalogo_cargos.entradas:
        if entrada.estado is EstadoRegla.NO_VERIFICADA:
            assert entrada.regla_id is not None
            assert reglas.por_id(entrada.regla_id) is not None, entrada.regla_id


def test_una_version_inexistente_falla_con_reglas_no_disponibles() -> None:
    with pytest.raises(ReglasNoDisponibles):
        versiones.cargar_reglas("v999")


def test_no_hay_ninguna_grilla_aprobada_todavia() -> None:
    """La primera grilla llega con la US4 (T118), y es tarea manual."""
    assert versiones.versiones_disponibles().grillas == ()
