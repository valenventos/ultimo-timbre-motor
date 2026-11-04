# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""T188 — la mitad local del determinismo multiplataforma (SC-003, SC-007).

La comparación de verdad —el mismo informe producido en Linux, macOS y
Windows, enfrentado byte a byte— solo puede ocurrir en CI, donde hay tres
sistemas operativos. El job `determinismo-multiplataforma` de
`.github/workflows/ci.yml` la hace: cada sistema de la matriz emite el informe
canónico, lo sube como artefacto, y un job final compara las huellas SHA-256.

Lo que este módulo verifica es lo que *sí* se puede verificar desde un solo
sistema: que nada en el camino de salida introduzca algo dependiente de la
plataforma. Son tres cosas concretas, y cada una fue un bug posible:

1. **los fines de línea**: `Path.write_text` traduce `\\n` a `\\r\\n` en
   Windows, así que el mismo informe tenía distinta huella según el sistema.
   Se encontró al escribir esta tarea y se corrigió con `newline=""`;
2. **los separadores de ruta**: si una ruta entrara al informe, `\\` contra `/`
   lo partiría en dos;
3. **el orden de las colecciones**: si algo dependiera del orden de iteración
   de un `set`, cambiaría entre corridas antes que entre sistemas.

El contrato entre este módulo y el CI es el **caso canónico**: los dos usan
`examples/caso-inc-b.yaml` con `--formato json`. Si cambia acá, cambia allá.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess  # nosec B404 - se invoca el propio paquete, sin shell
import sys
from pathlib import Path

import pytest

CASO_CANONICO = Path("examples/caso-inc-b.yaml")


def _emitir(destino: Path) -> subprocess.CompletedProcess[str]:
    """Corre la CLI igual que el CI, en un proceso aparte.

    Un proceso aparte y no una llamada en memoria: lo que se está verificando
    es justamente lo que pasa al cruzar el borde del proceso —codificación de
    la consola, fines de línea, locale—, y eso no se observa desde adentro.
    """
    return subprocess.run(  # nosec B603 - argumentos fijos, sin shell
        [
            sys.executable,
            "-m",
            "ultimo_timbre",
            "calcular",
            str(CASO_CANONICO),
            "--formato",
            "json",
            "--salida",
            str(destino),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def informe(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    destino = tmp_path_factory.mktemp("determinismo") / "informe.json"
    resultado = _emitir(destino)
    assert resultado.returncode == 0, resultado.stderr
    return destino.read_bytes()


def test_el_archivo_no_lleva_cr(informe: bytes) -> None:
    """Un solo CR cambiaría la huella entre Windows y el resto."""
    assert b"\r" not in informe


def test_la_huella_es_estable_entre_corridas(
    tmp_path_factory: pytest.TempPathFactory, informe: bytes
) -> None:
    """Invariante I3 sobre el borde del proceso, no solo en memoria."""
    otro = tmp_path_factory.mktemp("determinismo2") / "informe.json"
    assert _emitir(otro).returncode == 0
    assert hashlib.sha256(otro.read_bytes()).hexdigest() == (hashlib.sha256(informe).hexdigest())


def test_el_informe_no_contiene_separadores_de_ruta_nativos(informe: bytes) -> None:
    """Si una ruta se filtrara al informe, partiría la comparación en dos.

    Se afirma sobre el separador nativo del sistema donde corre el test: en
    Windows es `os.sep == '\\\\'` y en POSIX es `'/'`, que igual aparece dentro
    de los textos de las normas. Por eso la afirmación se acota a Windows, que
    es donde el separador es un carácter que no tiene por qué estar.
    """
    if os.sep == "/":
        pytest.skip("en POSIX el separador coincide con un carácter legítimo del texto")
    assert os.sep.encode() not in informe


def test_las_colecciones_del_informe_salen_ordenadas(informe: bytes) -> None:
    """Orden explícito, no orden de iteración (research R5).

    Si los escenarios salieran del orden de un `set`, la comparación fallaría
    entre corridas del mismo sistema antes de fallar entre sistemas.
    """
    datos = json.loads(informe)
    fechas = [e["fecha_cese"] for e in datos["escenarios"]]
    assert fechas == sorted(fechas)

    codigos = [a["codigo"] for a in datos["advertencias"]]
    assert codigos == sorted(codigos)


def test_el_json_esta_en_utf8_sin_bom(informe: bytes) -> None:
    """Un BOM es un cambio de bytes invisible en el visor y fatal en la huella."""
    assert not informe.startswith(b"\xef\xbb\xbf")
    informe.decode("utf-8")  # levanta si no es UTF-8 válido
