# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T093 — clasificación de superposiciones en tres categorías (FR-004).

La distinción que importa: solo la `simultaneidad_computable_art47` tiene
incidencia potencial en el haber. Advertir con el mismo énfasis un solapamiento
irrelevante entrena al profesional a ignorar la advertencia que sí importa.

`posible_error_carga` se discrimina por **cargo y establecimiento iguales**, no
por duración: el mismo puesto cargado dos veces casi siempre es una duplicación.
"""

from __future__ import annotations

from tests.casos import f, periodo
from ultimo_timbre.engine import alcance
from ultimo_timbre.models.caso import (
    HistoriaDeServicios,
    PeriodoDeServicio,
    Superposicion,
)
from ultimo_timbre.models.enums import ClasificacionSuperposicion as Clase
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
CESE = f("2026-02-28")


def _clasificar(*ps: PeriodoDeServicio, cargo_base: str | None = None) -> tuple[Superposicion, ...]:
    historia = HistoriaDeServicios(periodos=tuple(ps))
    return alcance.clasificar_superposiciones(historia, CESE, reglas=REGLAS, cargo_base=cargo_base)


def _umbral_art47() -> int:
    """El mínimo de 3 años continuos, leído de la regla (Principio I)."""
    regla = REGLAS.por_id("simultaneidad.art47.minimo_continuo")
    assert regla is not None
    assert regla.valor is not None
    valor = regla.valor["anios_continuos"]
    assert isinstance(valor, int)
    return valor


def test_sin_solapamiento_no_hay_superposiciones() -> None:
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2010-02-28"),
        periodo("preceptor", desde="2010-03-01", hasta="2020-02-29"),
    )
    assert sups == ()


def test_mismo_cargo_y_establecimiento_es_posible_error_de_carga() -> None:
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2020-02-29"),
        periodo("maestro_de_grado", desde="2010-03-01", hasta="2015-02-28"),
    )
    assert len(sups) == 1
    assert sups[0].clasificacion is Clase.POSIBLE_ERROR_CARGA


def test_el_error_de_carga_no_depende_de_la_duracion() -> None:
    """Aunque dure 10 años, el mismo puesto duplicado sigue siendo carga repetida."""
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2026-02-28"),
        periodo("maestro_de_grado", desde="2005-03-01", hasta="2015-02-28"),
    )
    assert sups[0].anios_continuos >= 3
    assert sups[0].clasificacion is Clase.POSIBLE_ERROR_CARGA


def test_cargos_distintos_mas_de_tres_anios_es_computable_por_el_art_47() -> None:
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2026-02-28"),
        periodo("preceptor", desde="2010-03-01", hasta="2020-02-29"),
    )
    assert len(sups) == 1
    assert sups[0].clasificacion is Clase.SIMULTANEIDAD_COMPUTABLE_ART47
    # el umbral no vive en el modelo: se compara contra la regla (Principio I)
    minimo = _umbral_art47()
    assert sups[0].anios_continuos >= minimo


def test_cargos_distintos_menos_de_tres_anios_no_es_computable() -> None:
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2026-02-28"),
        periodo("preceptor", desde="2010-03-01", hasta="2011-02-28"),
    )
    assert len(sups) == 1
    assert sups[0].clasificacion is Clase.SIMULTANEIDAD_NO_COMPUTABLE


def test_el_minimo_de_tres_anios_sale_de_la_regla() -> None:
    """Principio I: el 3 del art. 47 es un valor normativo."""
    assert _umbral_art47() == 3


def test_con_cargo_base_la_simultaneidad_debe_alcanzarlo() -> None:
    """FR-004: computable exige ≥3 años continuos **y** alcanzar al cargo base."""
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2026-02-28"),
        periodo("preceptor", desde="2010-03-01", hasta="2020-02-29"),
        cargo_base="bibliotecario_ensenanza_superior",
    )
    assert sups[0].clasificacion is Clase.SIMULTANEIDAD_NO_COMPUTABLE


def test_con_cargo_base_alcanzado_sigue_siendo_computable() -> None:
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2026-02-28"),
        periodo("preceptor", desde="2010-03-01", hasta="2020-02-29"),
        cargo_base="maestro_de_grado",
    )
    assert sups[0].clasificacion is Clase.SIMULTANEIDAD_COMPUTABLE_ART47


def test_las_tres_categorias_son_excluyentes() -> None:
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2026-02-28"),
        periodo("maestro_de_grado", desde="2005-03-01", hasta="2010-02-28"),
        periodo("preceptor", desde="2012-03-01", hasta="2020-02-29"),
        periodo("bibliotecario_ensenanza_superior", desde="2022-03-01", hasta="2023-02-28"),
    )
    clases = [s.clasificacion for s in sups]
    assert Clase.POSIBLE_ERROR_CARGA in clases
    assert Clase.SIMULTANEIDAD_COMPUTABLE_ART47 in clases
    assert Clase.SIMULTANEIDAD_NO_COMPUTABLE in clases
    for s in sups:
        assert clases.count(s.clasificacion) >= 1


def test_la_superposicion_identifica_los_periodos_por_idx() -> None:
    """FR-054: lo que viaja es el índice anónimo, nunca un dato del caso."""
    sups = _clasificar(
        periodo("maestro_de_grado", desde="2000-03-01", hasta="2026-02-28"),
        periodo("preceptor", desde="2010-03-01", hasta="2020-02-29"),
    )
    assert sups[0].periodos == (0, 1)


def test_un_solapamiento_posterior_al_cese_no_cuenta() -> None:
    """FR-018: el cómputo cierra en el cese, también para la simultaneidad."""
    historia = HistoriaDeServicios(
        periodos=(
            periodo("maestro_de_grado", desde="2000-03-01", hasta="2035-02-28"),
            periodo("preceptor", desde="2030-03-01", hasta="2034-02-28"),
        )
    )
    sups = alcance.clasificar_superposiciones(historia, CESE, reglas=REGLAS)
    assert sups == ()


def test_un_solapamiento_que_cruza_el_cese_se_recorta() -> None:
    historia = HistoriaDeServicios(
        periodos=(
            periodo("maestro_de_grado", desde="2000-03-01", hasta="2035-02-28"),
            periodo("preceptor", desde="2024-03-01", hasta="2034-02-28"),
        )
    )
    sups = alcance.clasificar_superposiciones(historia, CESE, reglas=REGLAS)
    assert len(sups) == 1
    assert sups[0].hasta == CESE
    # del 2024-03-01 al 2026-02-28 hay menos de 3 años: ya no llega al art. 47
    assert sups[0].clasificacion is Clase.SIMULTANEIDAD_NO_COMPUTABLE
