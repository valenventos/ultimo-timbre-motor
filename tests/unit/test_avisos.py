# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T145 — los avisos obligatorios de todo informe con montos (FR-042, FR-030c).

Dos frases que no pueden faltar cuando el motor emite plata:

* que el informe es una **estimación orientativa** y no reemplaza el cálculo
  oficial del IPS ni el asesoramiento profesional (FR-042);
* que el haber es **móvil** y se actualiza por correlación con el cargo en
  actividad, y que este motor no proyecta esa movilidad
  `[DL 9650/80, art. 50]` (FR-030c).

La segunda importa especialmente en un escenario futuro: el número sale a
valores de la última grilla cargada, y sin el aviso alguien podría leerlo como
el haber que va a cobrar en 2030.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.casos import caso_inc_b
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.grilla import GrillaSalarial
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.render.texto import informe_a_texto
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")
FIXTURE = Path("tests/fixtures/grilla-ficticia-test.yaml")


@pytest.fixture(scope="module")
def con_montos() -> Informe:
    grilla: GrillaSalarial = versiones.cargar_grilla_de_prueba(FIXTURE)
    return calcular(caso_inc_b(), reglas=REGLAS, grilla=grilla)


def test_el_aviso_de_estimacion_esta_presente(con_montos: Informe) -> None:
    assert "estimación orientativa" in con_montos.aviso_estimacion
    assert "IPS" in con_montos.aviso_estimacion


def test_el_aviso_de_movilidad_cita_el_art_50(con_montos: Informe) -> None:
    assert "art. 50" in con_montos.aviso_movilidad
    assert "móvil" in con_montos.aviso_movilidad


def test_el_aviso_de_movilidad_aclara_que_no_se_proyecta(con_montos: Informe) -> None:
    """Sin esto, el número se lee como el haber que va a cobrar."""
    assert "no proyecta" in con_montos.aviso_movilidad


def test_los_avisos_llegan_a_la_salida_de_texto(con_montos: Informe) -> None:
    texto = informe_a_texto(con_montos)
    assert con_montos.aviso_estimacion in texto
    assert con_montos.aviso_movilidad in texto


def test_tambien_estan_en_un_informe_sin_montos() -> None:
    """No dependen de que haya grilla: el informe igual es una estimación."""
    informe = calcular(caso_inc_b(), reglas=REGLAS)
    assert informe.aviso_estimacion
    assert informe.aviso_movilidad
