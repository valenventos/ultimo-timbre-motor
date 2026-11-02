# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Catálogo de cargos con jerarquía **ficticia**. No es un módulo de test.

Por qué existe: `rules/v1/cargos.yaml` lleva `jerarquia: null` en **todos** los
cargos, y no por descuido. El criterio de comparación entre cargos es la
Cuestión abierta #4 y ninguna norma citada documenta un orden numérico que
transcribir, así que la regla de datos del proyecto obliga a dejarlo nulo. La
consecuencia en producción es correcta y está verificada aparte: con jerarquía
nula el motor **no puede rankear**, emite `empate_jerarquia` y marca el cargo
base provisional (`tests/unit/test_empate_jerarquia.py`).

Pero la mecánica de rankear y de descender al cargo inferior (FR-019, FR-020a)
tiene que estar implementada y probada igual, porque entra en servicio el día
que el criterio se verifique, y porque es lo que piden los escenarios 1 y 3 de
la US3.

Este módulo cumple para la jerarquía el mismo papel que
`tests/fixtures/grilla-ficticia-test.yaml` para los importes: valores
**evidentemente inventados** —múltiplos de diez, sin ninguna fuente— que viven
en `tests/` y nunca en `rules/`.

Convención del número: **mayor entero = mayor jerarquía**. Eso es una decisión
de representación, no un valor normativo, y está documentada en
`schemas/cargo.schema.json`.
"""

from __future__ import annotations

from ultimo_timbre.models.normativa import ConjuntoDeReglas

JERARQUIA_FICTICIA: dict[str, int] = {
    "director": 40,
    "vicedirector": 30,
    "maestro_de_grado": 20,
    "preceptor": 10,
    "bibliotecario": 10,
    "horas_catedra_secundario": 10,
    "tecnico_docente_psicologia": 10,
    "tecnico_docente_educacion_especial": 10,
    "visitadora_higiene_escolar": 10,
}


def con_jerarquia_ficticia(reglas: ConjuntoDeReglas) -> ConjuntoDeReglas:
    """El mismo conjunto de reglas, con el catálogo rankeable.

    Solo cambia `jerarquia`: la condición de al frente de alumnos, la
    naturaleza, la norma y el estado de cada entrada quedan como en `rules/`.
    """
    entradas = tuple(
        e.model_copy(update={"jerarquia": JERARQUIA_FICTICIA.get(e.cargo)})
        for e in reglas.catalogo_cargos.entradas
    )
    catalogo = reglas.catalogo_cargos.model_copy(
        update={
            "entradas": entradas,
            "version": f"{reglas.catalogo_cargos.version}-jerarquia-ficticia",
        }
    )
    return reglas.model_copy(update={"catalogo_cargos": catalogo})
