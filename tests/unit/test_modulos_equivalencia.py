# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T199 — el umbral de veinte horas cátedra con carga en módulos (Cuestión #3).

El art. 24 inc. b asimila a los profesores que **reúnen veinte horas cátedra**,
y el nivel secundario liquida por **módulos**. Sin una equivalencia, el umbral
no se puede evaluar para media docencia del nivel.

La equivalencia por defecto —1 módulo = 1,5 horas cátedra— se desprende de las
duraciones: 60 minutos el módulo, 40 la hora cátedra. Es la práctica
administrativa de la DGCyE y es aritméticamente coherente, pero **no se
encontró la norma** que la fije a efectos previsionales, y de ella depende si
alguien con 14 módulos alcanza el umbral (21 horas) o no lo alcanza (14).

## Lo que este módulo verifica

El motor evalúa el umbral bajo **las dos** lecturas y las compara:

* si las dos dan el mismo resultado —cumple con ambas, o incumple con ambas—
  el inciso sale **definitivo**: una regla sin verificar que no mueve el
  resultado es informativa, no bloqueante;
* si difieren, el inciso sale **provisional** y el informe muestra las dos.

Esa asimetría es el punto. Marcar provisional todo caso con módulos, solo
porque la equivalencia está discutida, haría que el motor dijera «no sé» en
casos donde sí sabe —el de 30 módulos cumple el umbral con cualquier
equivalencia— y eso entrena al lector a ignorar la marca.

Los casos son sintéticos y están puestos **a los dos lados del umbral** a
propósito: 14 módulos (donde la lectura decide), 20 (cumple con las dos) y 10
(incumple con las dos).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.casos import caso, periodo
from ultimo_timbre.engine import calcular
from ultimo_timbre.engine import calendario as cal
from ultimo_timbre.models.caso import Caso
from ultimo_timbre.models.enums import EstadoResultado
from ultimo_timbre.models.informe import Informe, ResultadoInciso
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

REGLA = "modulos.equivalencia_horas_catedra"
ALTERNATIVA = "modulos.equivalencia_uno_a_uno"

# El umbral del art. 24 inc. b, leído de la regla y no escrito acá.
UMBRAL = 20


def _caso_con_modulos(modulos: int) -> Caso:
    """26 años de servicio por módulos, 51 de edad al cese.

    Edad y años sobran para el inc. b; lo único que decide es el umbral de
    horas, que es lo que se quiere aislar.
    """
    return caso(
        periodo(
            "modulos_secundaria",
            desde="2000-03-01",
            hasta="2026-02-28",
            modulos=modulos,
        ),
        nacimiento="1974-06-10",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-03-01",
    )


def _inc_b(informe: Informe) -> ResultadoInciso:
    return next(i for i in informe.elegibilidad.incisos if i.inciso == "b")


# ---------------------------------------------------------------------------
# La regla y su alternativa existen y dicen lo que tienen que decir
# ---------------------------------------------------------------------------


def test_la_equivalencia_es_una_regla_y_no_una_constante() -> None:
    """Principio I: el 1,5 sale de los datos, nunca del código."""
    regla = REGLAS.por_id(REGLA)
    assert regla is not None
    assert (regla.valor or {})["horas_catedra_por_modulo"] == "1.5"
    assert (regla.valor or {})["minutos_modulo"] == 60
    assert (regla.valor or {})["minutos_hora_catedra"] == 40


def test_la_equivalencia_sigue_sin_verificarse() -> None:
    """Es coherente aritméticamente y no tiene norma: eso es no_verificada."""
    regla = REGLAS.por_id(REGLA)
    assert regla is not None
    assert regla.estado.value == "no_verificada"
    assert regla.cuestion_abierta == 3
    assert regla.valor_por_defecto_aplicado is True


def test_la_lectura_conservadora_es_a_la_baja() -> None:
    """1 módulo = 1 hora cátedra deja a más docentes bajo el umbral."""
    alternativa = REGLAS.por_id(ALTERNATIVA)
    assert alternativa is not None
    assert (alternativa.valor or {})["sentido"] == "a_la_baja"
    assert (alternativa.valor or {})["alternativa_de"] == REGLA
    assert (alternativa.valor or {})["horas_catedra_por_modulo"] == "1"


# ---------------------------------------------------------------------------
# La conversión, aislada
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("modulos", "factor", "esperado"),
    [
        (14, "1.5", Decimal(21)),
        (14, "1", Decimal(14)),
        (20, "1.5", Decimal(30)),
        (20, "1", Decimal(20)),
        (2, "1.5", Decimal(3)),  # dos módulos son tres horas cátedra exactas
        (10, "1.5", Decimal(15)),
    ],
)
def test_la_conversion_es_exacta(modulos: int, factor: str, esperado: Decimal) -> None:
    """Con `Decimal`, 2 x 1,5 es 3 y no 2,9999999999999996."""
    historia = _caso_con_modulos(modulos).historia
    total = cal.horas_catedra_simultaneas(
        historia,
        0,
        historia.periodos[0].desde,
        horas_por_modulo=Decimal(factor),
    )
    assert total == esperado


def test_las_horas_catedra_y_los_modulos_se_suman_en_la_misma_unidad() -> None:
    """Quien tiene las dos cosas reúne la suma, no el máximo (art. 24 inc. b).

    El artículo habla de **reunir** veinte horas: diez horas cátedra más ocho
    módulos son diez más doce, no «ocho o diez».
    """
    mixto = caso(
        periodo(
            "hora_catedra_secundaria", desde="2000-03-01", hasta="2026-02-28", horas_catedra=10
        ),
        periodo("modulos_secundaria", desde="2000-03-01", hasta="2026-02-28", modulos=8),
        nacimiento="1974-06-10",
        ceses=["2026-02-28"],
        fecha_de_calculo="2026-03-01",
    )
    total = cal.horas_catedra_simultaneas(
        mixto.historia, 0, mixto.historia.periodos[0].desde, horas_por_modulo=Decimal("1.5")
    )
    assert total == Decimal(22)


# ---------------------------------------------------------------------------
# El umbral: los dos lados y el medio
# ---------------------------------------------------------------------------


def test_con_veinte_modulos_cumple_bajo_las_dos_lecturas_y_queda_definitivo() -> None:
    """30 horas con 1,5 y 20 con 1:1. Las dos pasan el umbral de 20.

    Se afirma sobre el estado **del inciso** y no sobre el del informe: el
    informe sale provisional igual, por `horas_catedra.como_carrera`, que es la
    otra mitad de la Cuestión #3 —si el servicio por unidades cuenta como
    carrera para el cargo base— y condiciona cualquier caso por horas o
    módulos. Es una duda legítima y ajena a la equivalencia.
    """
    informe = calcular(_caso_con_modulos(20), reglas=REGLAS)
    inc_b = _inc_b(informe)

    assert inc_b.cumple is True
    assert informe.elegibilidad.inciso_mas_favorable == "b"
    assert inc_b.estado is EstadoResultado.DEFINITIVO


def test_con_diez_modulos_incumple_bajo_las_dos_lecturas_y_queda_definitivo() -> None:
    """15 horas con 1,5 y 10 con 1:1. Ninguna alcanza: no hay duda que informar."""
    informe = calcular(_caso_con_modulos(10), reglas=REGLAS)
    inc_b = _inc_b(informe)

    assert inc_b.cumple is False
    assert inc_b.estado is EstadoResultado.DEFINITIVO


def test_con_catorce_modulos_la_lectura_decide_y_el_inciso_sale_provisional() -> None:
    """21 horas con 1,5 y 14 con 1:1: el umbral queda en medio.

    Es el caso que justifica toda la maquinaria. El motor aplica 1,5, así que
    informa que cumple, pero lo hace **provisional**: con la otra lectura esta
    docente no accedería por el inc. b.
    """
    informe = calcular(_caso_con_modulos(14), reglas=REGLAS)
    inc_b = _inc_b(informe)

    assert inc_b.cumple is True
    assert inc_b.estado is EstadoResultado.PROVISIONAL

    # Y el requisito que la equivalencia decide es el de años al frente, no
    # otro: si la marca cayera en el de servicio, el informe mandaría a
    # verificar la norma equivocada.
    frente = next(r for r in inc_b.requisitos if r.nombre.startswith("años al frente"))
    assert frente.estado is EstadoResultado.PROVISIONAL


def test_cuando_la_lectura_decide_el_informe_dice_cual_es_la_regla() -> None:
    """FR-046b: no alcanza con marcar provisional, hay que decir por qué."""
    informe = calcular(_caso_con_modulos(14), reglas=REGLAS)
    referencias = [c.referencia for c in informe.condicionantes]
    assert REGLA in referencias


def test_cuando_las_dos_lecturas_coinciden_la_regla_no_condiciona() -> None:
    """Una regla sin verificar que no mueve el resultado es informativa.

    Si condicionara igual, el motor diría «no sé» en un caso donde sabe, y eso
    entrena al lector a ignorar la marca de provisional.
    """
    informe = calcular(_caso_con_modulos(20), reglas=REGLAS)
    referencias = [c.referencia for c in informe.condicionantes]
    assert REGLA not in referencias


def test_un_caso_sin_modulos_no_arrastra_la_cuestion_tres() -> None:
    """Una maestra de grado no tiene nada que ver con la equivalencia."""
    informe = calcular(
        caso(
            periodo(desde="2000-03-01", hasta="2026-02-28"),
            nacimiento="1974-06-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=REGLAS,
    )
    referencias = [c.referencia for c in informe.condicionantes]
    assert REGLA not in referencias


# ---------------------------------------------------------------------------
# El umbral se evalúa en toda la historia, no solo en la carga actual
# ---------------------------------------------------------------------------


def test_el_umbral_se_evalua_periodo_por_periodo_en_toda_la_historia() -> None:
    """Un período con poca carga no cuenta al frente aunque el último sí.

    La docente estuvo veinte años con 8 módulos —12 horas, bajo el umbral con
    cualquier lectura— y los últimos seis con 20. Solo esos seis cuentan al
    frente, así que no llega a los 25 años del inc. b: el motor no puede tomar
    la carga del último período y extenderla hacia atrás.
    """
    informe = calcular(
        caso(
            periodo("modulos_secundaria", desde="2000-03-01", hasta="2020-02-28", modulos=8),
            periodo("modulos_secundaria", desde="2020-03-01", hasta="2026-02-28", modulos=20),
            nacimiento="1974-06-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=REGLAS,
    )
    inc_b = _inc_b(informe)
    assert inc_b.cumple is False


def test_la_equivalencia_no_le_atribuye_su_efecto_a_la_convencion_de_conteo() -> None:
    """Cada condicionante con su causa (Principio IV).

    Al volver provisional el requisito de años al frente, la equivalencia hacía
    que el filtro de sensibilidades registrara **también** la convención de
    conteo, que filtraba por «inciso provisional». El informe decía entonces
    que la convención condiciona un resultado que no condiciona.

    Una razón equivocada es peor que una razón faltante: manda al profesional a
    verificar la norma que no era, y cuando no encuentra nada raro desconfía
    del resto del informe.
    """
    informe = calcular(_caso_con_modulos(14), reglas=REGLAS)
    referencias = [c.referencia for c in informe.condicionantes]

    assert REGLA in referencias
    assert "computo.convencion_de_conteo" not in referencias


def test_la_convencion_sigue_condicionando_cuando_es_ella_la_que_decide() -> None:
    """El contraste que vuelve significativo el test anterior.

    Una docente que llega al umbral de años **justo** en la fecha de cese sí es
    sensible a la convención de conteo, y ahí el condicionante tiene que estar.
    Sin este test, el filtro nuevo podría haber apagado la convención del todo
    y los dos tests pasarían.
    """
    informe = calcular(
        caso(
            periodo(desde="2001-03-01", hasta="2026-02-28"),
            nacimiento="1974-06-10",
            ceses=["2026-02-28"],
            fecha_de_calculo="2026-03-01",
        ),
        reglas=REGLAS,
    )
    referencias = [c.referencia for c in informe.condicionantes]
    assert "computo.convencion_de_conteo" in referencias
