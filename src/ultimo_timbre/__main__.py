# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Permite `python -m ultimo_timbre`, equivalente al ejecutable instalado.

Existe porque la alternativa es peor: sin esto, `python -m ultimo_timbre.cli.main`
importa el módulo, no corre nada y **termina con exit 0**, que es exactamente el
código que significa «informe emitido». Un script que invocara el motor así
creería que todo salió bien sin haber calculado nada.
"""

from __future__ import annotations

from ultimo_timbre.cli.main import app

if __name__ == "__main__":
    app()
