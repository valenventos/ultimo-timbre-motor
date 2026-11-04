# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T135 a T137 — la política de aprobación de grillas existe de verdad.

Estas tres tareas no producen código importable: un archivo `CODEOWNERS`, un
job de CI y un ADR. Nada en la suite las tocaba, así que podían quedar
«hechas» sin estar hechas —y de hecho pasó: estuvieron marcadas como
completas durante una fase entera sin que ninguno de los tres archivos
existiera.

Este módulo es el resguardo contra eso. No prueba comportamiento del motor:
prueba que el andamiaje que custodia el Principio IX está en el repositorio y
dice lo que la política dice. Es el único lugar de la suite donde afirmar sobre
archivos de infraestructura es lo correcto, porque son el artefacto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

CODEOWNERS = Path(".github/CODEOWNERS")
WORKFLOW = Path(".github/workflows/ci.yml")
ADR = Path("docs/adr/0002-aprobacion-de-grillas.md")


def _texto(p: Path) -> str:
    assert p.exists(), f"{p} no existe"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T135 — CODEOWNERS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["/grids/", "/rules/"])
def test_codeowners_cubre_los_datos_normativos(ruta: str) -> None:
    """FR-010, Principio IX: grillas y reglas no se cambian sin revisión."""
    lineas = [
        linea
        for linea in _texto(CODEOWNERS).splitlines()
        if linea.strip() and not linea.startswith("#")
    ]
    cubiertas = [linea for linea in lineas if linea.split()[0] == ruta]
    assert cubiertas, f"CODEOWNERS no cubre {ruta}"
    assert cubiertas[0].split()[1].startswith("@"), "el dueño tiene que ser un usuario o equipo"


# ---------------------------------------------------------------------------
# T136 — el check de CI
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pasos() -> list[dict[str, Any]]:
    """Los pasos del job, ya extraídos: lo que se afirma es su contenido."""
    ci: dict[str, Any] = yaml.safe_load(_texto(WORKFLOW))
    jobs: dict[str, Any] = ci["jobs"]
    assert "validate-grid-approval" in jobs, "falta el job validate-grid-approval"
    return [dict(paso) for paso in jobs["validate-grid-approval"]["steps"]]


def test_el_check_exige_los_dos_campos_de_aprobacion(pasos: list[dict[str, Any]]) -> None:
    guion = "\n".join(str(paso.get("run", "")) for paso in pasos)
    assert "aprobada_por" in guion
    assert "aprobada_en" in guion


def test_el_check_compara_con_quien_fusiona() -> None:
    """Research R4: con un solo mantenedor, la aprobación se ata al merge.

    Sin esta comparación el campo sería decorativo: cualquier nombre pasaría y
    la grilla podría declarar un aprobador que nunca la miró.
    """
    bruto = _texto(WORKFLOW)
    assert "github.actor" in bruto
    assert "QUIEN_FUSIONA" in bruto


def test_el_check_necesita_el_historial_para_saber_que_cambio(
    pasos: list[dict[str, Any]],
) -> None:
    """Sin historial no hay diff, y sin diff el check miraría el archivo equivocado."""
    checkout = next(p for p in pasos if "checkout" in str(p.get("uses", "")))
    assert checkout["with"]["fetch-depth"] == 0


# ---------------------------------------------------------------------------
# T137 — el ADR
# ---------------------------------------------------------------------------


def test_el_adr_registra_el_disparador_del_segundo_mantenedor() -> None:
    """El escalón a revisión de terceros no se activa «cuando parezca maduro».

    Tiene un hecho objetivo que lo dispara, y el ADR tiene que nombrarlo, o la
    política de hoy —autorrevisión— se vuelve permanente por omisión.
    """
    texto = _texto(ADR).lower()
    assert "disparador de revisión" in texto
    assert "segundo mantenedor" in texto
    assert "merge" in texto


def test_el_adr_admite_que_hoy_la_revision_es_autorrevision() -> None:
    """Principio IV: un ADR que solo lista ventajas no sirve para revisarlo."""
    texto = _texto(ADR).lower()
    assert "autorrevisión" in texto
