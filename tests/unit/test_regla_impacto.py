# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T018 — una regla NO_VERIFICADA sin impacto declarado es inválida (FR-006, FR-046b).

Sin `impacto_si_no_verificada` el motor no puede cumplir FR-046b, que obliga a
informar en qué sentido una regla sin verificar podría alterar el resultado.
Entonces el modelo no la acepta.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ultimo_timbre.models.enums import EstadoRegla, SentidoImpacto, TipoFuente
from ultimo_timbre.models.normativa import Norma, Regla

NORMA = Norma(texto="Ley 10579, art. 33", ley="Ley 10579", articulo="33")


def test_regla_verificada_valida() -> None:
    regla = Regla(
        id="haber.base",
        norma=Norma(texto="DL 9650/80, art. 41", ley="DL 9650/80", articulo="41"),
        tipo=TipoFuente.LETRA_LEY,
        estado=EstadoRegla.VERIFICADO,
        verificada_en=__import__("datetime").date(2026, 10, 30),
        valor={"porcentaje": "0.70"},
    )
    assert regla.estado is EstadoRegla.VERIFICADO
    assert regla.impacto_si_no_verificada is None


def test_regla_no_verificada_sin_impacto_es_rechazada() -> None:
    with pytest.raises(ValidationError, match="impacto_si_no_verificada"):
        Regla(
            id="antiguedad.tope",
            norma=NORMA,
            tipo=TipoFuente.LETRA_LEY,
            estado=EstadoRegla.NO_VERIFICADA,
            valor=None,
        )


def test_regla_no_verificada_con_impacto_es_valida() -> None:
    regla = Regla(
        id="antiguedad.tope",
        norma=NORMA,
        tipo=TipoFuente.LETRA_LEY,
        estado=EstadoRegla.NO_VERIFICADA,
        impacto_si_no_verificada=SentidoImpacto.INDETERMINADO,
        que_falta_verificar="si el tope vigente es 120 % o 125 %",
        valor=None,
    )
    assert regla.impacto_si_no_verificada is SentidoImpacto.INDETERMINADO


def test_regla_no_verificada_sin_que_falta_verificar_es_rechazada() -> None:
    """Decir «no verificada» sin decir qué falta no sirve a nadie."""
    with pytest.raises(ValidationError, match="que_falta_verificar"):
        Regla(
            id="antiguedad.tope",
            norma=NORMA,
            tipo=TipoFuente.LETRA_LEY,
            estado=EstadoRegla.NO_VERIFICADA,
            impacto_si_no_verificada=SentidoImpacto.INDETERMINADO,
            valor=None,
        )


def test_regla_verificada_sin_fecha_de_verificacion_es_rechazada() -> None:
    with pytest.raises(ValidationError, match="verificada_en"):
        Regla(
            id="haber.base",
            norma=NORMA,
            tipo=TipoFuente.LETRA_LEY,
            estado=EstadoRegla.VERIFICADO,
            valor={"porcentaje": "0.70"},
        )


def test_la_regla_es_inmutable() -> None:
    """Principio II: una regla mutada a mitad de cálculo no aparecería en el desglose."""
    regla = Regla(
        id="antiguedad.tope",
        norma=NORMA,
        tipo=TipoFuente.LETRA_LEY,
        estado=EstadoRegla.NO_VERIFICADA,
        impacto_si_no_verificada=SentidoImpacto.AL_ALZA,
        que_falta_verificar="tope vigente",
        valor=None,
    )
    with pytest.raises(ValidationError):
        regla.id = "otro"


def test_la_norma_distingue_letra_de_ley_de_interpretacion() -> None:
    """Principio I: la interpretación no se mezcla con el texto de la norma."""
    regla = Regla(
        id="excedente.computo",
        norma=Norma(texto="Res. IPS 995/2021, Anexo, punto 2.1.a", ley="Res. IPS 995/2021"),
        tipo=TipoFuente.INTERPRETACION,
        estado=EstadoRegla.VERIFICADO,
        verificada_en=__import__("datetime").date(2026, 10, 30),
        valor={"desde": "todas_las_condiciones"},
    )
    assert regla.tipo is TipoFuente.INTERPRETACION
