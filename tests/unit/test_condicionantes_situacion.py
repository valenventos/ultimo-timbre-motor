# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T095 — condicionantes de clase `situacion_del_caso` (FR-046b).

La razón de que esta clase exista: un monto calculado sobre un cargo que no
está en el catálogo, o sobre un período en curso proyectado, es tan provisional
como uno que depende de una regla sin verificar — pero la fuente de la
incertidumbre no es normativa, es del caso. Si solo se modelaran las reglas,
esas situaciones tendrían que marcar el monto como provisional **sin poder
explicar por qué**.
"""

from __future__ import annotations

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.engine import condicionantes as cond
from ultimo_timbre.models.enums import (
    ClaseCondicionante,
    CodigoAdvertencia,
    NaturalezaServicio,
    SentidoImpacto,
)
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")


def _informe(
    cargo: str = "maestro_de_grado", hasta: str | None = "2026-02-28", **kw: object
) -> Informe:
    return calcular(
        caso(
            periodo(cargo, desde="1995-03-01", hasta=hasta, **kw),
            nacimiento="1970-06-20",
            ceses=["2026-02-28"],
        ),
        reglas=REGLAS,
    )


def _refs(informe: Informe) -> set[str]:
    return {
        c.referencia
        for c in informe.condicionantes
        if c.clase is ClaseCondicionante.SITUACION_DEL_CASO
    }


def test_el_constructor_de_condicionante_de_situacion() -> None:
    c = cond.de_situacion(CodigoAdvertencia.GRILLA_AUSENTE, "qué grilla rige a la fecha de cese")
    assert c.clase is ClaseCondicionante.SITUACION_DEL_CASO
    assert c.referencia == "grilla_ausente"
    assert c.que_falta_verificar
    assert c.sentido_impacto is SentidoImpacto.INDETERMINADO


def test_una_situacion_del_caso_no_lleva_norma() -> None:
    """No tiene norma asociada: no es una cuestión normativa sino del caso."""
    c = cond.de_situacion(CodigoAdvertencia.SUPUESTO_CONTINUIDAD, "la continuidad")
    assert c.norma is None


def test_cargo_fuera_de_catalogo() -> None:
    informe = _informe("cargo_que_no_existe")
    codigos = {a.codigo for a in informe.advertencias}
    assert CodigoAdvertencia.CARGO_FUERA_DE_CATALOGO in codigos
    assert informe.condicionantes


def test_override_manual() -> None:
    informe = _informe("maestro_de_grado", al_frente_override=False)
    assert CodigoAdvertencia.DATO_CORREGIDO_A_MANO.value in _refs(informe)


def test_override_de_naturaleza_tambien_condiciona() -> None:
    informe = _informe("maestro_de_grado", naturaleza_override=NaturalezaServicio.NO_DOCENTE)
    assert CodigoAdvertencia.DATO_CORREGIDO_A_MANO.value in _refs(informe)


def test_supuesto_continuidad() -> None:
    informe = _informe(hasta=None)
    assert CodigoAdvertencia.SUPUESTO_CONTINUIDAD.value in _refs(informe)


def test_las_tres_situaciones_pueden_coexistir() -> None:
    informe = _informe("cargo_que_no_existe", hasta=None, al_frente_override=True)
    refs = _refs(informe)
    assert CodigoAdvertencia.DATO_CORREGIDO_A_MANO.value in refs
    assert CodigoAdvertencia.SUPUESTO_CONTINUIDAD.value in refs


def test_toda_situacion_declara_que_falta_verificar() -> None:
    informe = _informe("cargo_que_no_existe", hasta=None, al_frente_override=True)
    situaciones = [
        c for c in informe.condicionantes if c.clase is ClaseCondicionante.SITUACION_DEL_CASO
    ]
    assert situaciones
    for c in situaciones:
        assert c.que_falta_verificar
        assert c.sentido_impacto is not None


def test_una_historia_limpia_no_tiene_situaciones_condicionantes() -> None:
    assert _refs(_informe()) == set()


@pytest.mark.parametrize(
    "codigo",
    [
        CodigoAdvertencia.GRILLA_AUSENTE,
        CodigoAdvertencia.CARGO_FUERA_DE_CATALOGO,
        CodigoAdvertencia.DATO_CORREGIDO_A_MANO,
        CodigoAdvertencia.SUPUESTO_CONTINUIDAD,
    ],
)
def test_los_codigos_de_situacion_reconocidos(codigo: CodigoAdvertencia) -> None:
    """Los cuatro que FR-046b enumera."""
    assert cond.de_situacion(codigo, "lo que falta").referencia == codigo.value
