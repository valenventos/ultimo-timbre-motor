# Contrato de librería

**Feature**: `001-motor-calculo-jubilacion` · Implementa FR-051, FR-052, Principio V

Paquete `ultimo_timbre`, tipado (PEP 561, `py.typed`), publicado bajo AGPL-3.0-or-later.

## Superficie pública

Todo lo exportado está en `ultimo_timbre.__all__`. Nada fuera de esa lista es contrato: los
submódulos internos pueden cambiar sin MAJOR.

### Cálculo

```python
def calcular(
    caso: Caso,
    *,
    reglas: ConjuntoDeReglas,
    grilla: GrillaSalarial | None = None,
) -> Informe: ...
```

**`calcular` no hace I/O**: no lee archivos, no abre sockets, no escribe logs. Recibe datos ya
cargados y devuelve un `Informe`. Es lo que hace que la equivalencia entre CLI y librería
(FR-051) sea estructural y no una coincidencia: la CLI es un cargador más un renderizador
alrededor de esta misma función.

`grilla=None` es válido: produce un informe sin montos, que es exactamente lo que necesitan las
historias US1 a US3 (elegibilidad, cargo base y porcentaje sin grilla).

### Carga de datos

```python
def cargar_caso(ruta: Path) -> Caso: ...
def cargar_caso_desde_texto(texto: str, formato: Formato) -> Caso: ...
def cargar_reglas(version: str | None = None) -> ConjuntoDeReglas: ...
def cargar_grilla(version: str | None = None) -> GrillaSalarial: ...
def grilla_vigente_a(fecha: date) -> GrillaSalarial | None: ...
def versiones_disponibles() -> Versiones: ...
```

Separadas de `calcular` a propósito (research R7). Un consumidor que ya tiene los datos en memoria
—la futura app web, que no puede tocar disco por caso— usa solo `calcular`.

`grilla_vigente_a` devuelve `None` cuando no hay grilla aprobada para esa fecha; el llamador
decide, y `calcular` emite la advertencia `grilla_ausente` con el monto marcado provisional
(FR-034).

### Serialización

```python
def informe_a_json(informe: Informe) -> str: ...   # determinista, sort_keys
def informe_a_texto(informe: Informe) -> str: ...  # legible en terminal
```

Ambas renderizan el **mismo** modelo `Informe`. Ninguna recalcula nada.

### Modelos exportados

`Caso`, `HistoriaDeServicios`, `PeriodoDeServicio`, `Licencia`, `Establecimiento`,
`ConjuntoDeReglas`, `Regla`, `Norma`, `CatalogoDeCargos`, `GrillaSalarial`,
`Informe`, `Elegibilidad`, `CargoBase`, `Escenario`, `Monto`, `ReglaCondicionante`,
`PasoDelDesglose`, `Procedencia`, `Advertencia`, `Versiones`.

Enums: `SituacionRevista`, `TipoLicencia`, `TipoEstablecimiento`, `CajaAportes`,
`NaturalezaServicio`, `EstadoResultado`, `SentidoImpacto`, `CodigoAdvertencia`, `TipoFuente`,
`ViaCargoBase`, `TipoEscenario`, `Formato`.

Ver [`data-model.md`](../data-model.md) para los campos de cada uno.

## Excepciones

| Excepción | Cuándo | Exit code CLI |
|---|---|---|
| `CasoInvalido` | Schema o coherencia temporal (FR-003) | 2 |
| `FueraDeAlcance` | Otra caja, privado, promedio art. 41 (FR-044, FR-045, FR-020b) | 3 |
| `ReglasNoDisponibles` | Versión de reglas inexistente | 2 |

Todas derivan de `UltimoTimbreError`. Llevan el `periodo_idx` y el campo afectado, nunca valores
de dominio (FR-054).

**`FueraDeAlcance` es una excepción y no un informe vacío** a propósito: el Principio X exige que
esos casos se detecten e informen sin calcular, y una excepción tipada hace imposible que el flujo
continúe y produzca un número por accidente.

## Garantías

| Garantía | Verificación |
|---|---|
| `calcular` es pura: mismas entradas ⇒ mismo `Informe` | property test (I3) |
| El orden de los períodos no afecta el resultado | property test (I1) |
| Sin red en ninguna ruta | test con sockets bloqueados |
| Sin logging propio (solo `NullHandler`) | test de canarios (I8) |
| Sin escritura a disco desde `calcular` | test con filesystem de solo lectura |
| `Monto` nunca existe sin su estado | invariante de tipo (I5) |

## Estabilidad

`schema_version` del informe y del caso siguen semver propio, independiente del paquete. Un cambio
incompatible en cualquiera de los dos exige MAJOR del paquete y un ADR en `docs/adr/`.
