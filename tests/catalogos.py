# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Catálogo con índices escalafonarios **ficticios**. No es un módulo de test.

Por qué existe: `rules/v1/cargos.yaml` lleva `indice_escalafonario: null` en
todas las entradas, y no por descuido. El Anexo del art. 9º del Decreto
2397/2005, que aprueba el texto ordenado del nomenclador, no está publicado; lo
relevado y por qué no alcanza está en
`docs/datos-pendientes/relevamiento-2026-11.md`.

La consecuencia en producción es correcta y está verificada aparte: sin índices
y sin grilla el motor **no puede comparar cargos**, emite `empate_jerarquia` y
marca el cargo base provisional (`tests/golden/test_jerarquia_por_remuneracion.py`).

Pero la mecánica de rankear y de descender al cargo inferior (FR-019, FR-020a)
tiene que estar implementada y probada igual, porque entra en servicio el día
que el nomenclador se consiga.

Este módulo cumple para los índices el mismo papel que
`tests/fixtures/grilla-ficticia-test.yaml` para los importes: valores
**evidentemente inventados** que viven en `tests/` y nunca en `rules/`.

Son decimales porque el índice real lo es —multiplica el sueldo básico del cargo
testigo— y están espaciados de a 0,50 para que ninguno coincida por casualidad
con un índice real del nomenclador (1,10 · 1,32 · 1,70 · 1,86 · 2,16).
"""

from __future__ import annotations

from decimal import Decimal

from ultimo_timbre.models.normativa import ConjuntoDeReglas

INDICES_FICTICIOS: dict[str, Decimal] = {
    "director_primera": Decimal("5.00"),
    "director_segunda": Decimal("4.50"),
    "director_tercera": Decimal("4.00"),
    "vicedirector_primera": Decimal("3.50"),
    "vicedirector_segunda": Decimal("3.00"),
    "maestro_de_grado": Decimal("2.50"),
    "bibliotecario_ensenanza_superior": Decimal("2.00"),
    "bibliotecario_instituto_menores": Decimal("1.50"),
    "preceptor": Decimal("0.50"),
    "tecnico_docente_psicologia": Decimal("0.50"),
    "tecnico_docente_educacion_especial": Decimal("0.50"),
    "visitadora_higiene_escolar": Decimal("0.50"),
    # Las horas cátedra quedan afuera a propósito: su índice es por hora y no
    # compite con uno por cargo (`indice_es_por_hora`).
}


def con_indices_ficticios(reglas: ConjuntoDeReglas) -> ConjuntoDeReglas:
    """El mismo conjunto de reglas, con el catálogo comparable.

    Solo cambia `indice_escalafonario`. La condición de al frente de alumnos, la
    naturaleza, la norma y el estado de cada entrada quedan como en `rules/`.
    """
    entradas = tuple(
        e.model_copy(update={"indice_escalafonario": INDICES_FICTICIOS.get(e.cargo)})
        for e in reglas.catalogo_cargos.entradas
    )
    catalogo = reglas.catalogo_cargos.model_copy(
        update={
            "entradas": entradas,
            "version": f"{reglas.catalogo_cargos.version}-indices-ficticios",
        }
    )
    return reglas.model_copy(update={"catalogo_cargos": catalogo})
