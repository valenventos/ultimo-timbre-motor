# SPDX-FileCopyrightText: Último Timbre
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Último Timbre — motor de cálculo de la jubilación ordinaria docente del IPS.

Superficie pública del paquete (T070). Todo lo que no esté en `__all__` es
interno y puede cambiar sin un MAJOR.

`calcular` no hace I/O, no abre sockets y no consulta el reloj: la fecha de
cálculo entra dentro del `Caso` (FR-001a) y los datos normativos se cargan
aparte con las funciones de `ultimo_timbre.rules`.

    >>> from ultimo_timbre import calcular, cargar_reglas
    >>> informe = calcular(caso, reglas=cargar_reglas())   # doctest: +SKIP
"""

from __future__ import annotations

from ultimo_timbre.engine import calcular
from ultimo_timbre.entrada import cargar_caso, cargar_caso_desde_texto
from ultimo_timbre.errors import (
    CasoInvalido,
    FueraDeAlcance,
    GrillaInvalida,
    ReglasNoDisponibles,
    UltimoTimbreError,
)
from ultimo_timbre.models.caso import (
    CargoRef,
    Caso,
    Establecimiento,
    HistoriaDeServicios,
    Licencia,
    MesCalendario,
    PeriodoDeServicio,
    Superposicion,
    Tramo,
)
from ultimo_timbre.models.enums import (
    CajaAportes,
    ClaseCondicionante,
    ClasificacionSuperposicion,
    CodigoAdvertencia,
    CondicionAlFrente,
    EstadoRegla,
    EstadoResultado,
    Formato,
    NaturalezaServicio,
    OrigenDato,
    SentidoImpacto,
    SituacionRevista,
    TipoEscenario,
    TipoEstablecimiento,
    TipoFuente,
    TipoLicencia,
    UnidadDeCarga,
    ViaCargoBase,
)
from ultimo_timbre.models.grilla import (
    ComponenteSalarial,
    GrillaSalarial,
    ValorCargo,
)
from ultimo_timbre.models.informe import (
    Advertencia,
    CandidatoDescartado,
    CargoBase,
    Condicionante,
    Elegibilidad,
    Escenario,
    Faltante,
    Informe,
    LecturaAlternativa,
    Monto,
    PasoDelDesglose,
    Procedencia,
    ResultadoInciso,
    ResultadoRequisito,
    Versiones,
)
from ultimo_timbre.models.normativa import (
    CatalogoDeCargos,
    ConjuntoDeReglas,
    EntradaCatalogo,
    Norma,
    Regla,
)
from ultimo_timbre.render.json_out import informe_a_dict, informe_a_json
from ultimo_timbre.render.texto import informe_a_texto
from ultimo_timbre.rules.versiones import (
    cargar_grilla,
    cargar_reglas,
    grilla_vigente_a,
    versiones_disponibles,
)

__version__ = "0.1.0"

__all__ = [
    # salida
    "Advertencia",
    # enumeraciones
    "CajaAportes",
    "CandidatoDescartado",
    "CargoBase",
    # entrada
    "CargoRef",
    "Caso",
    # errores
    "CasoInvalido",
    # datos normativos
    "CatalogoDeCargos",
    "ClaseCondicionante",
    "ClasificacionSuperposicion",
    "CodigoAdvertencia",
    "ComponenteSalarial",
    "CondicionAlFrente",
    "Condicionante",
    "ConjuntoDeReglas",
    "Elegibilidad",
    "EntradaCatalogo",
    "Escenario",
    "Establecimiento",
    "EstadoRegla",
    "EstadoResultado",
    "Faltante",
    "Formato",
    "FueraDeAlcance",
    "GrillaInvalida",
    "GrillaSalarial",
    "HistoriaDeServicios",
    "Informe",
    "LecturaAlternativa",
    "Licencia",
    "MesCalendario",
    "Monto",
    "NaturalezaServicio",
    "Norma",
    "OrigenDato",
    "PasoDelDesglose",
    "PeriodoDeServicio",
    "Procedencia",
    "Regla",
    "ReglasNoDisponibles",
    "ResultadoInciso",
    "ResultadoRequisito",
    "SentidoImpacto",
    "SituacionRevista",
    "Superposicion",
    "TipoEscenario",
    "TipoEstablecimiento",
    "TipoFuente",
    "TipoLicencia",
    "Tramo",
    "UltimoTimbreError",
    "UnidadDeCarga",
    "ValorCargo",
    "Versiones",
    "ViaCargoBase",
    "__version__",
    # cálculo
    "calcular",
    # carga de datos normativos
    "cargar_caso",
    "cargar_caso_desde_texto",
    "cargar_grilla",
    "cargar_reglas",
    "grilla_vigente_a",
    # serialización
    "informe_a_dict",
    "informe_a_json",
    "informe_a_texto",
    "versiones_disponibles",
]
