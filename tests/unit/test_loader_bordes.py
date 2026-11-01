# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rutas de error de los loaders y de la carga de grillas.

El Principio VI exige 95 % de cobertura de ramas en `rules/`, y las ramas que
faltaban eran justamente las de error: un loader que maneja mal un YAML
malformado es exactamente lo que conviene tener probado antes de que llegue un
archivo normativo real.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from tests.unit.test_catalogo import CATALOGO, construir_periodo
from ultimo_timbre.errors import GrillaInvalida, ReglasNoDisponibles
from ultimo_timbre.models.enums import NaturalezaServicio
from ultimo_timbre.rules import catalogo as cat
from ultimo_timbre.rules import loader, versiones

# --------------------------------------------------------------------------- #
# loader
# --------------------------------------------------------------------------- #


def test_yaml_vacio_devuelve_mapeo_vacio() -> None:
    assert loader.cargar_yaml_texto("") == {}


def test_yaml_con_lista_en_la_raiz_es_rechazado() -> None:
    with pytest.raises(ValueError, match="mapeo"):
        loader.cargar_yaml_texto("- uno\n- dos\n")


def test_json_con_lista_en_la_raiz_es_rechazado() -> None:
    with pytest.raises(ValueError, match="objeto"):
        loader.cargar_json_texto("[1, 2]")


def test_cargar_json_desde_archivo(tmp_path: Path) -> None:
    ruta = tmp_path / "d.json"
    ruta.write_text('{"porcentaje": 0.70}', encoding="utf-8")
    assert loader.cargar_json(ruta)["porcentaje"] == Decimal("0.70")


def test_a_decimal_acepta_decimal_y_int() -> None:
    assert loader.a_decimal(Decimal("1.5")) == Decimal("1.5")
    assert loader.a_decimal(25) == Decimal(25)


def test_a_decimal_rechaza_texto_no_numerico() -> None:
    with pytest.raises(ValueError, match="decimal inválido"):
        loader.a_decimal("no es un número")


# --------------------------------------------------------------------------- #
# reglas
# --------------------------------------------------------------------------- #


def test_cargar_reglas_por_version_explicita() -> None:
    assert versiones.cargar_reglas("v1").version == "v1"


def test_sin_directorio_de_reglas_falla(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(versiones, "DIR_REGLAS", tmp_path / "no-existe")
    assert versiones.versiones_de_reglas() == ()
    with pytest.raises(ReglasNoDisponibles, match="no hay ninguna versión"):
        versiones.cargar_reglas()


def test_una_fecha_sin_comillas_en_el_yaml_se_acepta(tmp_path: Path) -> None:
    """PyYAML entrega `date` para una fecha sin comillas: el loader lo tolera."""
    base = tmp_path / "rules" / "v9"
    base.mkdir(parents=True)
    (base / "r.yaml").write_text(
        "reglas:\n"
        "  - id: x.y\n"
        "    norma: {texto: 'DL 9650/80, art. 1', ley: 'DL 9650/80'}\n"
        "    tipo: letra_ley\n"
        "    estado: verificado\n"
        "    verificada_en: 2026-10-30\n"
        "    valor: null\n",
        encoding="utf-8",
    )
    original = versiones.DIR_REGLAS
    try:
        versiones.DIR_REGLAS = tmp_path / "rules"
        regla = versiones.cargar_reglas("v9").reglas[0]
        assert regla.verificada_en == dt.date(2026, 10, 30)
    finally:
        versiones.DIR_REGLAS = original


# --------------------------------------------------------------------------- #
# grillas
# --------------------------------------------------------------------------- #

GRILLA_OK = """\
version: "{version}"
norma: {{texto: "Decreto X", ley: "Decreto X"}}
vigencia_desde: "{desde}"
vigencia_hasta: {hasta}
extraida_en: "2026-01-01"
aprobada_por: "mantenedor"
aprobada_en: "2026-01-01"
valores:
  maestro_de_grado:
    - codigo_concepto: "001"
      descripcion: "Básico"
      importe: "100000.00"
      bonificable: true
      remunerativo: true
"""


def _grids(
    tmp_path: Path, *, version: str = "2026-01", desde: str = "2026-01-01", hasta: str = "null"
) -> Path:
    grids = tmp_path / "grids"
    grids.mkdir(parents=True, exist_ok=True)
    (grids / f"{version}.yaml").write_text(
        GRILLA_OK.format(version=version, desde=desde, hasta=hasta), encoding="utf-8"
    )
    return grids


def test_cargar_grilla_y_versiones(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(versiones, "DIR_GRILLAS", _grids(tmp_path))
    assert versiones.versiones_de_grillas() == ("2026-01",)
    grilla = versiones.cargar_grilla()
    assert grilla.version == "2026-01"
    assert grilla.cargo("maestro_de_grado") is not None
    assert grilla.cargo("inexistente") is None


def test_sin_grillas_falla(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(versiones, "DIR_GRILLAS", tmp_path / "vacio")
    assert versiones.versiones_de_grillas() == ()
    with pytest.raises(ReglasNoDisponibles, match="no hay ninguna grilla"):
        versiones.cargar_grilla()


def test_version_de_grilla_inexistente(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(versiones, "DIR_GRILLAS", _grids(tmp_path))
    with pytest.raises(ReglasNoDisponibles, match="inexistente"):
        versiones.cargar_grilla("1999-01")


def test_grilla_vigente_a_encuentra_la_que_cubre_la_fecha(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(versiones, "DIR_GRILLAS", _grids(tmp_path))
    assert versiones.grilla_vigente_a(dt.date(2026, 6, 1)) is not None


def test_grilla_vigente_a_devuelve_none_si_no_hay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """FR-034: devolver None en lugar de lanzar deja decidir al llamador."""
    monkeypatch.setattr(versiones, "DIR_GRILLAS", _grids(tmp_path))
    assert versiones.grilla_vigente_a(dt.date(2020, 1, 1)) is None


def test_grilla_con_vigencia_cerrada(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(versiones, "DIR_GRILLAS", _grids(tmp_path, hasta='"2026-06-30"'))
    assert versiones.grilla_vigente_a(dt.date(2026, 6, 1)) is not None
    assert versiones.grilla_vigente_a(dt.date(2026, 7, 1)) is None


def test_grilla_sin_campo_obligatorio(tmp_path: Path) -> None:
    ruta = tmp_path / "mala.yaml"
    ruta.write_text('version: "x"\naprobada_por: "quien"\n', encoding="utf-8")
    with pytest.raises(GrillaInvalida, match="falta el campo"):
        versiones.cargar_grilla_desde(ruta)


def test_grilla_con_vigencia_invertida_es_rechazada(tmp_path: Path) -> None:
    ruta = tmp_path / "invertida.yaml"
    ruta.write_text(
        GRILLA_OK.format(version="x", desde="2026-06-01", hasta='"2026-01-01"'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="vigencia_hasta"):
        versiones.cargar_grilla_desde(ruta)


def test_versiones_disponibles_reporta_ambas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(versiones, "DIR_GRILLAS", _grids(tmp_path))
    v = versiones.versiones_disponibles()
    assert "v1" in v.reglas
    assert "2026-01" in v.grillas


# --------------------------------------------------------------------------- #
# catálogo
# --------------------------------------------------------------------------- #


def test_override_sobre_un_cargo_fuera_de_catalogo() -> None:
    """Se respeta, pero el cargo sigue fuera del catálogo y condiciona el resultado."""
    d = cat.derivar(
        CATALOGO,
        construir_periodo(
            "cargo_inexistente",
            al_frente_override=True,
            naturaleza_override=NaturalezaServicio.DOCENTE,
        ),
    )
    assert d.al_frente_de_alumnos is True
    assert d.naturaleza is NaturalezaServicio.DOCENTE
    assert d.en_catalogo is False
    assert d.condiciona_resultado is True
    assert d.origen.value == "manual"
