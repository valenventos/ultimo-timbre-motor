# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T179 — los caminos de error del cargador de casos (FR-003, FR-057).

Este módulo existe para dos cosas: convertir el borde —fechas y enums que
llegan como texto— y dar mensajes accionables. La segunda es la que necesita
tests propios: un cargador que acepta lo correcto pero explica mal lo
incorrecto cumple la mitad de su trabajo, y es la mitad que el usuario ve
cuando algo sale mal.

Cada aserción verifica las tres cosas que FR-057 pide —campo, período y
corrección— y la que FR-054 prohíbe: ningún valor del caso en el mensaje.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from ultimo_timbre.entrada import CORRECCIONES, cargar_caso, cargar_caso_desde_texto
from ultimo_timbre.errors import CasoInvalido
from ultimo_timbre.models.enums import (
    CajaAportes,
    Formato,
    SituacionRevista,
    TipoEstablecimiento,
)

VALIDO = """\
schema_version: "1.0.0"
fecha_de_calculo: 2030-04-01
fecha_nacimiento: 1980-03-15
fechas_cese:
  - 2030-03-31
historia:
  periodos:
    - cargo: maestro_de_grado
      establecimiento:
        tipo: estatal_dgcye
      desde: 2004-03-01
      hasta: 2030-03-31
      caja_aportes: ips
      situacion_revista: titular
"""


def _cargar(texto: str) -> object:
    return cargar_caso_desde_texto(texto, Formato.YAML)


def test_un_caso_valido_carga() -> None:
    caso = cargar_caso_desde_texto(VALIDO, Formato.YAML)
    assert caso.fecha_de_calculo == dt.date(2030, 4, 1)
    assert len(caso.historia.periodos) == 1


def test_las_fechas_entrecomilladas_tambien_se_aceptan() -> None:
    """Un YAML con fechas entre comillas las entrega como `str`."""
    caso = cargar_caso_desde_texto(VALIDO.replace("2004-03-01", '"2004-03-01"'), Formato.YAML)
    assert caso.historia.periodos[0].desde == dt.date(2004, 3, 1)


def test_una_fecha_mal_formada_nombra_el_campo_y_el_periodo() -> None:
    with pytest.raises(CasoInvalido) as exc:
        _cargar(VALIDO.replace("desde: 2004-03-01", 'desde: "01/03/2004"'))
    assert exc.value.campo == "desde"
    assert exc.value.periodo_idx == 0
    assert "YYYY-MM-DD" in str(exc.value)


def test_un_enum_desconocido_enumera_las_opciones() -> None:
    """Principio VIII: decir «inválido» sin decir qué vale no sirve."""
    with pytest.raises(CasoInvalido) as exc:
        _cargar(VALIDO.replace("caja_aportes: ips", "caja_aportes: banco_nacion"))
    assert exc.value.campo == "caja_aportes"
    assert "ips" in str(exc.value)
    assert "banco_nacion" not in str(exc.value)


def test_un_tipo_de_establecimiento_desconocido_se_explica() -> None:
    with pytest.raises(CasoInvalido) as exc:
        _cargar(VALIDO.replace("tipo: estatal_dgcye", "tipo: cooperativa"))
    assert exc.value.campo == "tipo"
    assert "estatal_dgcye" in str(exc.value)


def test_un_archivo_vacio_dice_que_falta_la_historia() -> None:
    with pytest.raises(CasoInvalido) as exc:
        _cargar("")
    assert "vacío" in str(exc.value)


def test_un_yaml_sintacticamente_roto_se_explica() -> None:
    with pytest.raises(CasoInvalido) as exc:
        _cargar("historia: [[[")
    assert "indentación" in str(exc.value) or "sintaxis" in str(exc.value)


def test_el_formato_texto_no_es_una_entrada() -> None:
    with pytest.raises(CasoInvalido) as exc:
        cargar_caso_desde_texto(VALIDO, Formato.TEXTO)
    assert ".yaml" in str(exc.value)


def test_una_extension_no_soportada_lista_las_validas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.csv"
    ruta.write_text("nada", encoding="utf-8")
    with pytest.raises(CasoInvalido) as exc:
        cargar_caso(ruta)
    assert ".json" in str(exc.value)


def test_un_archivo_inexistente_se_explica(tmp_path: Path) -> None:
    with pytest.raises(CasoInvalido) as exc:
        cargar_caso(tmp_path / "no-esta.yaml")
    assert "no existe" in str(exc.value)


def test_un_archivo_que_no_esta_en_utf8_se_explica(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.yaml"
    ruta.write_bytes(VALIDO.encode("latin-1").replace(b"maestro", b"maestr\xf3"))
    with pytest.raises(CasoInvalido) as exc:
        cargar_caso(ruta)
    assert "UTF-8" in str(exc.value)


def test_las_licencias_se_convierten_en_el_borde() -> None:
    con_licencia = VALIDO + (
        "      licencias:\n"
        "        - tipo: sin_goce\n"
        '          desde: "2010-05-01"\n'
        '          hasta: "2010-07-31"\n'
    )
    caso = cargar_caso_desde_texto(con_licencia, Formato.YAML)
    licencia = caso.historia.periodos[0].licencias[0]
    assert licencia.desde == dt.date(2010, 5, 1)


def test_una_licencia_con_tipo_desconocido_se_explica() -> None:
    con_licencia = VALIDO + (
        "      licencias:\n"
        "        - tipo: sabatico\n"
        "          desde: 2010-05-01\n"
        "          hasta: 2010-07-31\n"
    )
    with pytest.raises(CasoInvalido) as exc:
        _cargar(con_licencia)
    assert exc.value.periodo_idx == 0


def test_la_fecha_de_calculo_explicita_reemplaza_la_del_archivo() -> None:
    caso = cargar_caso_desde_texto(VALIDO, Formato.YAML, fecha_de_calculo=dt.date(2031, 1, 15))
    assert caso.fecha_de_calculo == dt.date(2031, 1, 15)


def test_la_fecha_de_respaldo_solo_se_usa_si_falta() -> None:
    """Precedencia: explícita > la del archivo > la de respaldo (FR-001a)."""
    con_fecha = cargar_caso_desde_texto(
        VALIDO, Formato.YAML, fecha_de_calculo_si_falta=dt.date(2031, 1, 15)
    )
    assert con_fecha.fecha_de_calculo == dt.date(2030, 4, 1)

    sin_fecha = cargar_caso_desde_texto(
        VALIDO.replace("fecha_de_calculo: 2030-04-01\n", ""),
        Formato.YAML,
        fecha_de_calculo_si_falta=dt.date(2031, 1, 15),
    )
    assert sin_fecha.fecha_de_calculo == dt.date(2031, 1, 15)


def test_sin_fecha_de_calculo_ni_respaldo_se_explica() -> None:
    with pytest.raises(CasoInvalido) as exc:
        _cargar(VALIDO.replace("fecha_de_calculo: 2030-04-01\n", ""))
    assert "fecha_de_calculo" in str(exc.value)
    assert "--fecha-calculo" in str(exc.value)


def test_el_json_se_acepta_con_fechas_como_string() -> None:
    texto = (
        '{"schema_version": "1.0.0", "fecha_de_calculo": "2030-04-01",'
        ' "fecha_nacimiento": "1980-03-15", "fechas_cese": ["2030-03-31"],'
        ' "historia": {"periodos": [{"cargo": "maestro_de_grado",'
        ' "establecimiento": {"tipo": "estatal_dgcye"}, "desde": "2004-03-01",'
        ' "hasta": "2030-03-31", "caja_aportes": "ips",'
        ' "situacion_revista": "titular"}]}}'
    )
    caso = cargar_caso_desde_texto(texto, Formato.JSON)
    assert caso.historia.periodos[0].hasta == dt.date(2030, 3, 31)


def test_ningun_mensaje_de_error_lleva_valores_del_caso() -> None:
    """FR-054, barrido sobre varias entradas rotas a la vez."""
    rotos = [
        VALIDO.replace("desde: 2004-03-01", 'desde: "01/03/2004"'),
        VALIDO.replace("caja_aportes: ips", "caja_aportes: banco_nacion"),
        VALIDO.replace("hasta: 2030-03-31", "hasta: 2003-01-01"),
        VALIDO.replace("fecha_nacimiento: 1980-03-15\n", ""),
    ]
    for texto in rotos:
        with pytest.raises(CasoInvalido) as exc:
            _cargar(texto)
        mensaje = str(exc.value)
        assert "maestro_de_grado" not in mensaje
        assert "1980-03-15" not in mensaje


# ---------------------------------------------------------------------------
# Los valores de las enumeraciones no se transcriben a mano
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("campo", "enumeracion"),
    [
        ("caja_aportes", CajaAportes),
        ("situacion_revista", SituacionRevista),
        ("tipo", TipoEstablecimiento),
    ],
)
def test_la_correccion_no_transcribe_los_valores_del_enum(
    campo: str, enumeracion: type[CajaAportes | SituacionRevista | TipoEstablecimiento]
) -> None:
    """Resguardo contra el desfasaje que ya ocurrió una vez.

    La lista de valores válidos la arma `_enum` desde la enumeración. Si además
    estuviera escrita a mano en `CORRECCIONES`, las dos podrían divergir —y
    divergieron: la corrección de `caja_aportes` nombraba un «otra_provincial»
    que no existe—. Este test exige que no se vuelva a transcribir.
    """
    texto = CORRECCIONES[campo]
    for miembro in enumeracion:
        assert miembro.value not in texto, (
            f"CORRECCIONES['{campo}'] transcribe '{miembro.value}': "
            "dejá que `_enum` liste los valores desde la enumeración"
        )


def test_el_error_de_enum_lista_los_valores_reales() -> None:
    """Y los lista bien, porque los toma del enum."""
    with pytest.raises(CasoInvalido) as exc:
        _cargar(VALIDO.replace("caja_aportes: ips", "caja_aportes: inexistente"))
    mensaje = str(exc.value)
    for miembro in CajaAportes:
        assert miembro.value in mensaje
