# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T024 — `grids/` rechaza toda grilla ficticia (Principio IX).

La grilla de prueba vive en `tests/fixtures/`. Si alguien la copia a `grids/`,
el loader tiene que negarse: un informe real valuado con importes inventados es
el peor resultado posible del motor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ultimo_timbre.errors import GrillaInvalida
from ultimo_timbre.rules import versiones

GRILLA = """\
version: "2026-01-test"
ficticia: {ficticia}
norma:
  texto: "Grilla de prueba — valores inventados"
  ley: "N/A"
enlace: null
vigencia_desde: "2026-01-01"
vigencia_hasta: null
extraida_en: "2026-01-01"
aprobada_por: "nadie"
aprobada_en: "2026-01-01"
valores:
  maestro_de_grado:
    - codigo_concepto: "001"
      descripcion: "Básico"
      importe: "100000.00"
      bonificable: true
      remunerativo: true
      regla_id: null
"""


def _escribir(directorio: Path, ficticia: bool) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / "2026-01-test.yaml"
    ruta.write_text(GRILLA.format(ficticia=str(ficticia).lower()), encoding="utf-8")
    return ruta


def test_rechaza_una_grilla_ficticia_en_grids(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "grids", ficticia=True)
    with pytest.raises(GrillaInvalida, match="ficticia"):
        versiones.cargar_grilla_desde(ruta)


def test_acepta_una_grilla_no_ficticia(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "grids", ficticia=False)
    grilla = versiones.cargar_grilla_desde(ruta)
    assert grilla.version == "2026-01-test"
    assert grilla.ficticia is False


def test_una_grilla_sin_el_campo_ficticia_se_considera_real(tmp_path: Path) -> None:
    """El default seguro es «real»: una grilla de prueba debe declararse como tal."""
    ruta = tmp_path / "grids" / "sin-campo.yaml"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = "\n".join(
        linea
        for linea in GRILLA.format(ficticia="false").splitlines()
        if not linea.startswith("ficticia:")
    )
    ruta.write_text(texto + "\n", encoding="utf-8")
    grilla = versiones.cargar_grilla_desde(ruta)
    assert grilla.ficticia is False


def test_la_grilla_ficticia_de_fixtures_se_puede_cargar_para_tests(tmp_path: Path) -> None:
    """Los tests de US4 y US5 sí la necesitan: el veto es solo para `grids/`."""
    ruta = _escribir(tmp_path / "fixtures", ficticia=True)
    grilla = versiones.cargar_grilla_de_prueba(ruta)
    assert grilla.ficticia is True


def test_rechaza_una_grilla_sin_aprobador(tmp_path: Path) -> None:
    """FR-010, Principio IX: sin aprobador no hay grilla."""
    ruta = tmp_path / "grids" / "sin-aprobador.yaml"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = "\n".join(
        linea
        for linea in GRILLA.format(ficticia="false").splitlines()
        if not linea.startswith("aprobada_por:")
    )
    ruta.write_text(texto + "\n", encoding="utf-8")
    with pytest.raises(GrillaInvalida):
        versiones.cargar_grilla_desde(ruta)


def test_la_grilla_real_del_repo_no_es_ficticia() -> None:
    """Gate del repositorio: ninguna grilla versionada puede ser de prueba."""
    grids = Path(__file__).resolve().parent.parent.parent / "grids"
    for ruta in grids.glob("*.yaml"):
        assert "ficticia: true" not in ruta.read_text(encoding="utf-8"), ruta
