# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T021 — el catálogo deriva la condición del cargo (FR-002a, FR-002b, FR-002d).

Dos reglas que el motor no puede romper:
  * un cargo ausente del catálogo **no se asume**: queda indeterminado y se
    advierte, pero no invalida el caso;
  * un override del usuario se respeta y deja rastro de dato manual.
"""

from __future__ import annotations

import datetime as dt

from ultimo_timbre.models.caso import Establecimiento, PeriodoDeServicio
from ultimo_timbre.models.enums import (
    CajaAportes,
    CodigoAdvertencia,
    CondicionAlFrente,
    EstadoRegla,
    NaturalezaServicio,
    OrigenDato,
    SituacionRevista,
    TipoEstablecimiento,
)
from ultimo_timbre.models.normativa import CatalogoDeCargos, EntradaCatalogo, Norma
from ultimo_timbre.rules import catalogo as cat

LEY_13469 = Norma(texto="Ley 13469", ley="Ley 13469")
ART24_INC_B = Norma(texto="DL 9650/80, art. 24 inc. b", ley="DL 9650/80", articulo="24", inciso="b")

CATALOGO = CatalogoDeCargos(
    entradas=(
        EntradaCatalogo(
            cargo="maestro_de_grado",
            jerarquia=None,
            regla_indice="jerarquia.indices_escalafonarios",
            al_frente_de_alumnos=True,
            naturaleza=NaturalezaServicio.DOCENTE,
            norma=LEY_13469,
            estado=EstadoRegla.VERIFICADO,
        ),
        EntradaCatalogo(
            cargo="preceptor",
            jerarquia=None,
            regla_indice="jerarquia.indices_escalafonarios",
            al_frente_de_alumnos=True,
            naturaleza=NaturalezaServicio.DOCENTE,
            norma=LEY_13469,
            estado=EstadoRegla.VERIFICADO,
        ),
        EntradaCatalogo(
            cargo="administrativo",
            jerarquia=None,
            regla_indice="jerarquia.indices_escalafonarios",
            al_frente_de_alumnos=False,
            naturaleza=NaturalezaServicio.NO_DOCENTE,
            norma=LEY_13469,
            estado=EstadoRegla.VERIFICADO,
        ),
        EntradaCatalogo(
            cargo="secretario_tecnico",
            jerarquia=None,
            regla_indice="jerarquia.indices_escalafonarios",
            al_frente_de_alumnos=True,
            naturaleza=NaturalezaServicio.DOCENTE,
            norma=LEY_13469,
            estado=EstadoRegla.NO_VERIFICADA,
            regla_id="al_frente.ley_13469.extension",
        ),
        # Verificado por la letra del art. 24 inc. b, pero condicionado por la
        # extensión discutida de la Ley 13469 (Cuestión abierta #8).
        EntradaCatalogo(
            cargo="director_primera",
            jerarquia=None,
            regla_indice="jerarquia.indices_escalafonarios",
            al_frente_de_alumnos=False,
            naturaleza=NaturalezaServicio.DOCENTE,
            norma=ART24_INC_B,
            estado=EstadoRegla.VERIFICADO,
            regla_id="al_frente.ley_13469.extension",
        ),
        # La condición no es booleana: es un umbral de horas cátedra.
        EntradaCatalogo(
            cargo="hora_catedra_secundaria",
            jerarquia=None,
            regla_indice="jerarquia.indices_escalafonarios",
            al_frente_de_alumnos=None,
            naturaleza=NaturalezaServicio.DOCENTE,
            norma=ART24_INC_B,
            estado=EstadoRegla.VERIFICADO,
            condicion=CondicionAlFrente.POR_HORAS_CATEDRA,
            regla_umbral="requisitos.art24.inc_b",
            regla_id="horas_catedra.como_carrera",
        ),
    )
)


def construir_periodo(cargo: str, **kw: object) -> PeriodoDeServicio:
    base: dict[str, object] = {
        "cargo": cargo,
        "establecimiento": Establecimiento(tipo=TipoEstablecimiento.ESTATAL_DGCYE),
        "desde": dt.date(2010, 3, 1),
        "hasta": dt.date(2020, 2, 28),
        "caja_aportes": CajaAportes.IPS,
        "situacion_revista": SituacionRevista.TITULAR,
    }
    base.update(kw)
    return PeriodoDeServicio(**base)  # type: ignore[arg-type]


def test_deriva_al_frente_y_naturaleza_desde_el_cargo() -> None:
    d = cat.derivar(CATALOGO, construir_periodo("maestro_de_grado"))
    assert d.al_frente_de_alumnos is True
    assert d.naturaleza is NaturalezaServicio.DOCENTE
    assert d.origen is OrigenDato.DERIVADO
    assert d.en_catalogo is True


def test_deriva_un_cargo_no_docente() -> None:
    d = cat.derivar(CATALOGO, construir_periodo("administrativo"))
    assert d.al_frente_de_alumnos is False
    assert d.naturaleza is NaturalezaServicio.NO_DOCENTE


def test_un_cargo_ausente_queda_indeterminado_y_no_se_asume() -> None:
    """FR-002a: el motor no adivina la condición de un cargo que no conoce."""
    d = cat.derivar(CATALOGO, construir_periodo("cargo_inexistente"))
    assert d.al_frente_de_alumnos is None
    assert d.naturaleza is None
    assert d.en_catalogo is False
    assert CodigoAdvertencia.CARGO_FUERA_DE_CATALOGO in d.advertencias


def test_un_cargo_ausente_no_invalida_el_caso() -> None:
    """El resto de la historia sigue siendo computable (Principio IV)."""
    d = cat.derivar(CATALOGO, construir_periodo("cargo_inexistente"))
    assert d.al_frente_de_alumnos is None  # no lanza excepción


def test_el_override_de_al_frente_se_respeta_y_queda_como_manual() -> None:
    d = cat.derivar(CATALOGO, construir_periodo("administrativo", al_frente_override=True))
    assert d.al_frente_de_alumnos is True
    assert d.origen is OrigenDato.MANUAL
    assert d.difiere_del_catalogo is True
    assert CodigoAdvertencia.DATO_CORREGIDO_A_MANO in d.advertencias


def test_el_override_de_naturaleza_se_respeta() -> None:
    d = cat.derivar(
        CATALOGO,
        construir_periodo("maestro_de_grado", naturaleza_override=NaturalezaServicio.NO_DOCENTE),
    )
    assert d.naturaleza is NaturalezaServicio.NO_DOCENTE
    assert d.origen is OrigenDato.MANUAL


def test_un_override_que_coincide_con_el_catalogo_no_difiere() -> None:
    d = cat.derivar(CATALOGO, construir_periodo("maestro_de_grado", al_frente_override=True))
    assert d.difiere_del_catalogo is False
    assert d.origen is OrigenDato.MANUAL


def test_un_cargo_con_regla_no_verificada_condiciona_el_resultado() -> None:
    """Cuestión abierta #8: la extensión de la Ley 13469 está discutida."""
    d = cat.derivar(CATALOGO, construir_periodo("secretario_tecnico"))
    assert d.al_frente_de_alumnos is True
    assert d.regla_id == "al_frente.ley_13469.extension"
    assert d.condiciona_resultado is True


def test_un_cargo_verificado_no_condiciona_el_resultado() -> None:
    d = cat.derivar(CATALOGO, construir_periodo("maestro_de_grado"))
    assert d.condiciona_resultado is False


def test_la_derivacion_declara_la_norma_que_la_sostiene() -> None:
    """Principio I: la condición no es una opinión del motor."""
    d = cat.derivar(CATALOGO, construir_periodo("preceptor"))
    assert d.norma is not None
    assert d.norma.ley == "Ley 13469"


# ---------------------------------------------------------------------------
# Entradas verificadas que igual quedan condicionadas (Cuestión abierta #8)
# ---------------------------------------------------------------------------


def test_director_no_esta_al_frente_por_la_letra_del_inciso_b() -> None:
    """El art. 24 inc. b enumera a quiénes alcanza y no incluye a director."""
    d = cat.derivar(CATALOGO, construir_periodo("director_primera"))
    assert d.al_frente_de_alumnos is False
    assert d.en_catalogo is True
    assert d.norma is not None
    assert d.norma.inciso == "b"


def test_director_queda_condicionado_por_la_extension_de_la_ley_13469() -> None:
    """Verificado por la letra, pero una regla sin verificar lo discute."""
    d = cat.derivar(CATALOGO, construir_periodo("director_primera"))
    assert d.condiciona_resultado is True
    assert d.regla_id == "al_frente.ley_13469.extension"
    assert CodigoAdvertencia.REGLA_NO_VERIFICADA in d.advertencias


# ---------------------------------------------------------------------------
# Condición por umbral de horas cátedra (art. 24 inc. b)
# ---------------------------------------------------------------------------


def test_horas_catedra_no_es_booleano_y_declara_su_condicion() -> None:
    d = cat.derivar(CATALOGO, construir_periodo("hora_catedra_secundaria"))
    assert d.condicion is CondicionAlFrente.POR_HORAS_CATEDRA


def test_horas_catedra_alcanza_el_umbral() -> None:
    d = cat.derivar(
        CATALOGO,
        construir_periodo("hora_catedra_secundaria"),
        horas_catedra_simultaneas=20,
        umbral_horas_catedra=20,
    )
    assert d.al_frente_de_alumnos is True
    assert d.horas_catedra_evaluadas == 20
    assert d.umbral_horas_catedra == 20
    assert d.requiere_umbral_horas_catedra is False


def test_horas_catedra_no_alcanza_el_umbral() -> None:
    d = cat.derivar(
        CATALOGO,
        construir_periodo("hora_catedra_secundaria"),
        horas_catedra_simultaneas=19,
        umbral_horas_catedra=20,
    )
    assert d.al_frente_de_alumnos is False


def test_horas_catedra_sin_umbral_queda_indeterminado() -> None:
    """El motor no completa un umbral normativo por su cuenta (Principio I)."""
    d = cat.derivar(
        CATALOGO, construir_periodo("hora_catedra_secundaria"), horas_catedra_simultaneas=20
    )
    assert d.al_frente_de_alumnos is None
    assert d.requiere_umbral_horas_catedra is True
    assert d.condiciona_resultado is True


def test_horas_catedra_sin_horas_queda_indeterminado() -> None:
    d = cat.derivar(CATALOGO, construir_periodo("hora_catedra_secundaria"), umbral_horas_catedra=20)
    assert d.al_frente_de_alumnos is None
    assert d.requiere_umbral_horas_catedra is True


def test_horas_catedra_usa_las_del_periodo_si_no_se_pasan_las_simultaneas() -> None:
    d = cat.derivar(
        CATALOGO,
        construir_periodo("hora_catedra_secundaria", horas_catedra=24),
        umbral_horas_catedra=20,
    )
    assert d.horas_catedra_evaluadas == 24
    assert d.al_frente_de_alumnos is True


def test_el_umbral_se_evalua_sobre_las_horas_simultaneas_no_las_del_periodo() -> None:
    """Veinte horas cátedra se reúnen sumando cargos simultáneos."""
    d = cat.derivar(
        CATALOGO,
        construir_periodo("hora_catedra_secundaria", horas_catedra=12),
        horas_catedra_simultaneas=22,
        umbral_horas_catedra=20,
    )
    assert d.horas_catedra_evaluadas == 22
    assert d.al_frente_de_alumnos is True


def test_el_override_tambien_pisa_la_condicion_por_umbral() -> None:
    d = cat.derivar(
        CATALOGO,
        construir_periodo("hora_catedra_secundaria", al_frente_override=True),
        horas_catedra_simultaneas=10,
        umbral_horas_catedra=20,
    )
    assert d.al_frente_de_alumnos is True
    assert d.origen is OrigenDato.MANUAL
    assert d.difiere_del_catalogo is True
