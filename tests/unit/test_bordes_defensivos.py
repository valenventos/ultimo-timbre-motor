# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T190 — los caminos defensivos que ningún caso dorado recorre.

El motor está lleno de guardas del estilo «si este valor no es un entero, usá
el valor por omisión». Los casos dorados nunca las pisan, porque los datos del
repositorio están bien formados —es justamente lo que validan los schemas—.

Eso deja una pregunta abierta que importa: **¿la guarda hace lo que dice?** Una
guarda equivocada es peor que ninguna, porque convierte un dato corrupto en un
número plausible en lugar de en un error. Acá se la ejercita a propósito,
construyendo reglas y grillas deformes que el schema jamás dejaría pasar.

Lo que **no** se hace acá es perseguir cobertura por la cobertura. Cada test
afirma sobre un comportamiento que alguien podría romper: si una guarda se
cambia por otra que devuelve `0` en lugar del valor por omisión, o que levanta
en lugar de devolver `None`, algún test de este módulo lo nota.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from tests.casos import ESTATAL, f, periodo
from ultimo_timbre.engine import calendario as cal
from ultimo_timbre.engine import cargo_base as cb
from ultimo_timbre.engine import condicionantes as cond
from ultimo_timbre.engine import haber
from ultimo_timbre.engine.desglose import Trazador
from ultimo_timbre.models.caso import HistoriaDeServicios, PeriodoDeServicio
from ultimo_timbre.models.enums import (
    CajaAportes,
    CodigoAdvertencia,
    EstadoRegla,
    SituacionRevista,
    TipoFuente,
)
from ultimo_timbre.models.normativa import Norma, Regla
from ultimo_timbre.rules import versiones

REGLAS = versiones.cargar_reglas("v1")

NORMA = Norma(texto="Norma de prueba", ley="N/A — construida en un test")


def _regla(regla_id: str, valor: object) -> Regla:
    """Una regla con un `valor` deforme, por lo demás bien formada.

    `verificada_en` es obligatoria para una regla `VERIFICADO`: el modelo no
    acepta una verificación sin fecha, porque entonces no se podría auditar
    cuándo se comprobó la fuente. Acá se pone una fecha cualquiera, porque lo
    que se está ejercitando es la lectura del `valor`, no la trazabilidad.
    """
    return Regla(
        id=regla_id,
        norma=NORMA,
        tipo=TipoFuente.LETRA_LEY,
        estado=EstadoRegla.VERIFICADO,
        verificada_en=dt.date(2026, 11, 3),
        valor=valor,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Duracion: los comparadores
# ---------------------------------------------------------------------------
#
# `Duracion` ordena por (años, meses, días) y el motor compara duraciones en
# varios lugares. Los casos dorados usan sobre todo `cumple_anios`, así que los
# operadores quedan sin ejercitar. Un `__le__` mal escrito —comparando solo
# años, por ejemplo— haría que «24 años 11 meses» pasara por «25 años».


def _veinticinco() -> cal.Duracion:
    return cal.Duracion(anios=25, meses=0, dias=0)


def _casi_veinticinco() -> cal.Duracion:
    """Un día menos de lo que exige el art. 24. El borde que importa."""
    return cal.Duracion(anios=24, meses=11, dias=30)


def test_el_orden_mira_los_tres_componentes_y_no_solo_los_anios() -> None:
    casi, justo = _casi_veinticinco(), _veinticinco()
    assert casi < justo
    assert casi <= justo
    assert justo > casi
    assert justo >= casi


def test_dos_duraciones_iguales_satisfacen_le_y_ge() -> None:
    una, otra = _veinticinco(), _veinticinco()
    assert una <= otra
    assert una >= otra
    assert not una < otra
    assert not una > otra


def test_la_duracion_cero_es_menor_que_cualquier_servicio() -> None:
    cero = cal.Duracion.cero()
    assert cero.clave == (0, 0, 0)
    assert cero < _casi_veinticinco()
    assert not cero.cumple_anios(1)


def test_la_duracion_se_describe_en_lenguaje_claro() -> None:
    """Principio VIII: lo que se muestra se lee, no se decodifica."""
    assert str(_casi_veinticinco()) == "24 años, 11 meses, 30 días"


# ---------------------------------------------------------------------------
# Horas cátedra simultáneas: el período que no está
# ---------------------------------------------------------------------------
#
# Las dos funciones reciben un `idx` y buscan el período. Si no lo encuentran
# devuelven 0, no levantan: el llamador está recorriendo índices que vienen del
# propio caso, así que un índice ausente sería un error de programación, pero
# devolver 0 es lo seguro —no inventa horas que nadie trabajó—.


@pytest.fixture
def historia() -> HistoriaDeServicios:
    return HistoriaDeServicios(
        periodos=(
            PeriodoDeServicio(
                cargo="hora_catedra_secundaria",
                establecimiento=ESTATAL,
                desde=f("2010-03-01"),
                hasta=f("2015-02-28"),
                caja_aportes=CajaAportes.IPS,
                situacion_revista=SituacionRevista.TITULAR,
                horas_catedra=12,
            ),
        )
    )


def test_un_indice_inexistente_no_suma_horas(historia: HistoriaDeServicios) -> None:
    assert cal.horas_catedra_simultaneas(historia, 99, f("2012-06-01")) == 0


def test_un_indice_inexistente_tampoco_tiene_maximo(historia: HistoriaDeServicios) -> None:
    assert cal.max_horas_catedra_simultaneas(historia, 99, f("2015-02-28")) == 0


def test_el_indice_que_si_existe_suma_sus_horas(historia: HistoriaDeServicios) -> None:
    """El contraste que vuelve significativos los dos tests anteriores."""
    assert cal.horas_catedra_simultaneas(historia, 0, f("2012-06-01")) == 12


# ---------------------------------------------------------------------------
# Lectura de valores de regla: lo que no es entero
# ---------------------------------------------------------------------------
#
# `_entero` existe porque `ValorRegla` admite varios tipos y el código necesita
# un entero. El detalle que importa: en Python `True` **es** un entero, y un
# `bool` colado donde va una cantidad de meses daría 1 en silencio. La guarda lo
# excluye explícitamente.


@pytest.mark.parametrize(
    "valor",
    [
        {"meses": "36"},  # el número como texto
        {"meses": True},  # bool, que en Python pasa por int
        {"meses": None},
        {"otra_clave": 36},
        {},
        None,
    ],
)
def test_un_valor_que_no_es_entero_se_lee_como_ausente(valor: object) -> None:
    assert cb._entero(_regla("prueba.meses", valor), "meses") is None


def test_un_entero_de_verdad_se_lee() -> None:
    assert cb._entero(_regla("prueba.meses", {"meses": 36}), "meses") == 36


# ---------------------------------------------------------------------------
# Escala de antigüedad deforme
# ---------------------------------------------------------------------------
#
# La escala del Decreto 818/13 vive en los datos. Si el archivo trajera algo que
# no es una lista de tramos, el motor no puede inventar la escala: devuelve
# vacío, y el llamador deja la bonificación sin aplicar y lo advierte. Lo que no
# puede hacer es aplicar un porcentaje a medias.


@pytest.mark.parametrize(
    "valor",
    [
        {"escala": "13 % a los 0 años"},  # texto en lugar de lista
        {"escala": None},
        {"sin_escala": True},
        {},
        None,
    ],
)
def test_una_escala_que_no_es_lista_queda_vacia(valor: object) -> None:
    assert haber._escala(_regla("antiguedad.escala_y_tope", valor)) == ()


def test_un_tramo_sin_anios_entero_se_descarta_y_los_demas_sobreviven() -> None:
    """Descartar el tramo roto y conservar el resto, no tirar la escala entera.

    Un tramo con `anios` escrito como texto es representable en el modelo
    —`TramoDeEscala` admite `str | int`— y por lo tanto podría llegar desde un
    YAML mal transcrito. La escala conserva los tramos buenos: perderla entera
    por un tramo dejaría la bonificación en cero, que es peor que aplicarla con
    un tramo menos y advertirlo.

    El caso de un tramo **sin porcentaje** no se prueba acá porque el modelo no
    lo admite: `porcentaje: None` ni siquiera se puede construir. La guarda de
    `_escala` que lo contempla es defensa en profundidad, no un camino alcanzable.
    """
    escala = haber._escala(
        _regla(
            "antiguedad.escala_y_tope",
            {
                "escala": [
                    {"anios": 0, "porcentaje": "0.13"},
                    {"anios": "veinte", "porcentaje": "1.05"},  # roto
                    {"anios": 24, "porcentaje": "1.25"},
                ]
            },
        )
    )
    assert escala == ((24, Decimal("1.25")), (0, Decimal("0.13")))


def test_la_escala_sale_de_mayor_a_menor_antiguedad() -> None:
    """El orden no es cosmético: la búsqueda toma el primer tramo alcanzado."""
    escala = haber._escala(
        _regla(
            "antiguedad.escala_y_tope",
            {
                "escala": [
                    {"anios": 2, "porcentaje": "0.23"},
                    {"anios": 20, "porcentaje": "1.05"},
                    {"anios": 10, "porcentaje": "0.54"},
                ]
            },
        )
    )
    assert [anios for anios, _ in escala] == [20, 10, 2]


# ---------------------------------------------------------------------------
# Redondeo con la política deforme
# ---------------------------------------------------------------------------
#
# La política de redondeo del IPS es la Cuestión abierta #6: el motor aplica
# `ROUND_HALF_UP` a dos decimales y lo declara. Si el dato trajera una política
# desconocida o una cantidad de decimales que no es entera, el motor cae a los
# valores por omisión en lugar de fallar: el monto ya sale provisional por la
# #6, así que el condicionante ya está puesto.


def test_una_cantidad_de_decimales_que_no_es_entera_cae_al_valor_por_omision() -> None:
    reglas = REGLAS.model_copy(
        update={
            "reglas": tuple(
                _regla(
                    "redondeo.politica_ips",
                    {"politica_aplicada": "ROUND_HALF_UP", "decimales": "dos"},
                )
                if r.id == "redondeo.politica_ips"
                else r
                for r in REGLAS.reglas
            )
        }
    )
    assert haber.redondear(Decimal("1234.5678"), reglas=reglas) == Decimal("1234.57")


def test_una_politica_desconocida_cae_a_round_half_up() -> None:
    reglas = REGLAS.model_copy(
        update={
            "reglas": tuple(
                _regla(
                    "redondeo.politica_ips",
                    {"politica_aplicada": "ROUND_INVENTADO", "decimales": 2},
                )
                if r.id == "redondeo.politica_ips"
                else r
                for r in REGLAS.reglas
            )
        }
    )
    # 0.125 sube a 0.13 con HALF_UP y bajaría a 0.12 con HALF_EVEN.
    assert haber.redondear(Decimal("0.125"), reglas=reglas) == Decimal("0.13")


def test_el_redondeo_del_repositorio_es_el_declarado() -> None:
    """El contraste: con los datos reales, la política es la que dice la regla."""
    assert haber.redondear(Decimal("0.125"), reglas=REGLAS) == Decimal("0.13")
    assert haber.redondear(Decimal("1234.5678"), reglas=REGLAS) == Decimal("1234.57")


# ---------------------------------------------------------------------------
# Remuneración de un cargo que la grilla no trae
# ---------------------------------------------------------------------------


def test_sin_grilla_no_hay_remuneracion_con_la_que_comparar() -> None:
    """Sin grilla el comparador cae al índice escalafonario, no a cero."""
    assert cb._remuneracion("maestro_de_grado", grilla=None, reglas=REGLAS) is None


def test_un_cargo_que_la_grilla_no_trae_no_tiene_remuneracion() -> None:
    """`None` y no `0`: un cargo ausente no es un cargo que paga nada.

    La diferencia decide el cargo base. Con `0`, el cargo ausente perdería toda
    comparación y el motor elegiría otro en silencio; con `None`, el criterio
    de remuneración no se puede aplicar y el motor lo informa.
    """
    grilla = versiones.cargar_grilla_de_prueba(Path("tests/fixtures/grilla-ficticia-test.yaml"))
    assert cb._remuneracion("cargo_que_no_existe", grilla=grilla, reglas=REGLAS) is None
    assert cb._remuneracion("maestro_de_grado", grilla=grilla, reglas=REGLAS) is not None


# ---------------------------------------------------------------------------
# Un período que no cubre el horizonte
# ---------------------------------------------------------------------------


def test_un_servicio_que_no_llega_al_umbral_no_tiene_fecha() -> None:
    """FR-016: si el umbral no se alcanza al límite, no hay fecha que informar.

    Es el borde de la bisección. Devolver una fecha ahí sería inventar una
    habilitación que no existe, que es el peor error posible del motor.
    """
    historia = HistoriaDeServicios(periodos=(periodo(desde="2020-03-01", hasta="2022-02-28"),))
    assert cal.fecha_al_alcanzar_servicio(historia, 25, limite=dt.date(2022, 2, 28)) is None


def test_un_servicio_que_si_llega_informa_la_primera_fecha_exacta() -> None:
    """El contraste: la bisección devuelve el primer día, no uno posterior."""
    historia = HistoriaDeServicios(periodos=(periodo(desde="2000-03-01", hasta="2026-02-28"),))
    alcanza = cal.fecha_al_alcanzar_servicio(historia, 25, limite=dt.date(2026, 2, 28))
    assert alcanza is not None

    # El día anterior todavía no alcanza: eso es lo que hace exacta la fecha.
    anterior = alcanza - dt.timedelta(days=1)
    assert not cal.servicio_total(historia, anterior).cumple_anios(25)
    assert cal.servicio_total(historia, alcanza).cumple_anios(25)


# ---------------------------------------------------------------------------
# Valuar un cargo que la grilla no trae
# ---------------------------------------------------------------------------
#
# Es distinto de «no hay grilla»: la grilla está, se cargó, se citó su versión,
# y simplemente no tiene ese cargo. Pasa de verdad en cuanto el catálogo crece
# más rápido que la grilla, y es el borde donde la tentación de estimar es más
# fuerte: «el cargo parecido paga tanto». El motor no estima.


def test_una_grilla_sin_el_cargo_base_no_emite_monto() -> None:
    """FR-031a: sin el cargo en la grilla no hay haber, y se dice por qué."""
    grilla = versiones.cargar_grilla_de_prueba(Path("tests/fixtures/grilla-ficticia-test.yaml"))
    traza = Trazador()

    monto = haber.valuar(
        "cargo_que_la_grilla_no_trae",
        dt.date(2030, 3, 31),
        Decimal("0.75"),
        antiguedad_anios=26,
        grilla=grilla,
        reglas=REGLAS,
        traza=traza,
    )

    assert monto is None, "un cargo ausente no puede producir un importe"


def test_la_grilla_sin_el_cargo_lo_advierte_citando_su_version() -> None:
    """Principio IV: el motor dice qué grilla miró y qué no encontró en ella."""
    grilla = versiones.cargar_grilla_de_prueba(Path("tests/fixtures/grilla-ficticia-test.yaml"))
    traza = Trazador()

    haber.valuar(
        "cargo_que_la_grilla_no_trae",
        dt.date(2030, 3, 31),
        Decimal("0.75"),
        antiguedad_anios=26,
        grilla=grilla,
        reglas=REGLAS,
        traza=traza,
    )

    avisos = [a for a in traza.advertencias if a.codigo is CodigoAdvertencia.GRILLA_AUSENTE]
    assert avisos, "la ausencia del cargo tiene que quedar advertida, no silenciosa"
    assert grilla.version in avisos[0].mensaje


def test_el_mismo_camino_con_un_cargo_que_si_esta_produce_monto() -> None:
    """El contraste: lo que falla arriba es el cargo, no el camino de valuación."""
    grilla = versiones.cargar_grilla_de_prueba(Path("tests/fixtures/grilla-ficticia-test.yaml"))
    monto = haber.valuar(
        "maestro_de_grado",
        dt.date(2030, 3, 31),
        Decimal("0.75"),
        antiguedad_anios=26,
        grilla=grilla,
        reglas=REGLAS,
        traza=Trazador(),
        # Sin esto el `Monto` no se puede construir: `valuar` lo marca
        # provisional —ningun haber de la v1 es definitivo— y el invariante I5
        # exige que un monto provisional declare al menos un condicionante. El
        # motor pasa siempre los de las Cuestiones #1, #2 y #6; acá se hace lo
        # mismo en lugar de esquivarlo.
        condicionantes_previos=cond.del_monto(REGLAS),
    )
    assert monto is not None
    assert monto.valor > 0
    assert monto.grilla_version == grilla.version
