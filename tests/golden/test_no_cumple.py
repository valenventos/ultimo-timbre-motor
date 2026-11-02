# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T048 — caso dorado sin derecho (US1 esc. 2, FR-016).

24 años de servicio y 52 de edad al cese: no alcanza ningún inciso del art. 24.
Lo que el informe debe entregar es **el faltante de cada inciso**, no un «no».
"""

from __future__ import annotations

import pytest

from tests.casos import caso_no_cumple
from ultimo_timbre.engine import calcular
from ultimo_timbre.models.informe import Informe
from ultimo_timbre.rules import versiones

pytestmark = pytest.mark.golden

REGLAS = versiones.cargar_reglas("v1")


@pytest.fixture(scope="module")
def informe() -> Informe:
    return calcular(caso_no_cumple(), reglas=REGLAS)


def test_ningun_inciso_se_cumple(informe: Informe) -> None:
    assert all(not i.cumple for i in informe.elegibilidad.incisos)


def test_no_hay_inciso_mas_favorable(informe: Informe) -> None:
    assert informe.elegibilidad.inciso_mas_favorable is None


def test_cada_inciso_informa_su_faltante(informe: Informe) -> None:
    for inc in informe.elegibilidad.incisos:
        assert inc.falta is not None, inc.inciso


def test_al_inciso_b_le_falta_servicio_pero_no_edad(informe: Informe) -> None:
    """52 años de edad superan los 50 que pide el inciso; faltan servicios."""
    inc_b = next(i for i in informe.elegibilidad.incisos if i.inciso == "b")
    assert inc_b.falta is not None
    assert inc_b.falta.anios_edad == 0
    assert inc_b.falta.anios_servicio > 0


def test_al_inciso_d_le_faltan_edad_y_servicio(informe: Informe) -> None:
    inc_d = next(i for i in informe.elegibilidad.incisos if i.inciso == "d")
    assert inc_d.falta is not None
    assert inc_d.falta.anios_edad > 0
    assert inc_d.falta.anios_servicio > 0


def test_el_minimo_de_22_anios_si_se_cumple(informe: Informe) -> None:
    """24 años de servicio superan el mínimo general, pero no alcanzan un inciso."""
    assert informe.elegibilidad.minimo_22_anios.cumple is True


def test_no_hay_derecho_en_el_escenario(informe: Informe) -> None:
    assert all(not e.hay_derecho for e in informe.escenarios)
    assert all(e.inciso is None for e in informe.escenarios)


def test_sin_derecho_no_se_emite_haber(informe: Informe) -> None:
    assert all(e.haber is None for e in informe.escenarios)


def test_informa_la_fecha_estimada_de_cada_inciso(informe: Informe) -> None:
    """T076, FR-016: el faltante no alcanza; hay que decir cuándo se cumpliría.

    Este caso tiene el período **cerrado** al cese, así que lo que depende de
    servicio no se puede estimar y el informe lo dice.
    """
    for inc in informe.elegibilidad.incisos:
        assert inc.falta is not None
        if inc.estimado_para is None:
            assert inc.motivo_sin_estimacion is not None, inc.inciso
            assert "servicios futuros" in inc.motivo_sin_estimacion


def test_el_informe_igual_entrega_el_analisis(informe: Informe) -> None:
    """Principio IV: un resultado parcial explicado, no una negativa seca."""
    assert informe.desglose
    assert informe.elegibilidad.incisos
