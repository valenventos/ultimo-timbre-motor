# Phase 1 — Data Model: Motor de cálculo de jubilación ordinaria docente (IPS PBA)

**Feature**: `001-motor-calculo-jubilacion`
**Fecha**: 2026-10-30
**Deriva de**: [spec.md](./spec.md) *Key Entities* · [research.md](./research.md)

Todos los modelos son Pydantic v2 con `ConfigDict(strict=True, frozen=True)`. Inmutables porque
el Principio II exige determinismo: un modelo congelado no puede ser mutado a mitad de cálculo por
un paso que luego no aparezca en el desglose.

Los importes y porcentajes son `Decimal`, cargados desde `str` (ver research R1).

---

## 1. Entrada

### `Caso`

El documento que el usuario carga. Es la única entrada del motor.

| Campo | Tipo | Reglas | Origen |
|---|---|---|---|
| `schema_version` | `str` | semver, requerido | contrato |
| `fecha_nacimiento` | `date` | requerido, anterior a hoy | FR-001 |
| `historia` | `HistoriaDeServicios` | requerido, no vacía | FR-002 |
| `fechas_cese` | `list[date]` | ≥1, únicas, ordenadas al normalizar | FR-001 |

**Validaciones**: `fecha_nacimiento` coherente con la primera fecha de servicio (no se admite
servicio antes de los 16 años: se rechaza como error de carga, no se calcula).

---

### `PeriodoDeServicio`

| Campo | Tipo | Reglas | Origen |
|---|---|---|---|
| `idx` | `int` | asignado al normalizar; único; es el identificador anónimo usado en diagnóstico | FR-054 |
| `cargo` | `CargoRef` | requerido | FR-002 |
| `establecimiento` | `Establecimiento` | requerido | FR-002 |
| `desde` | `date` | requerido | FR-002 |
| `hasta` | `date` | requerido, `>= desde` | FR-003 |
| `situacion_revista` | `SituacionRevista` | requerido | FR-002 |
| `licencias` | `list[Licencia]` | puede ser vacía | FR-002 |
| `al_frente_override` | `bool \| None` | `None` = derivar del catálogo | FR-002b |

**Nota de diseño**: `al_frente_de_alumnos` **no es un campo de entrada** (FR-002/FR-002a). Se
deriva del catálogo de cargos. `al_frente_override` existe solo para la corrección manual de
FR-002b, y su uso deja rastro obligatorio en la procedencia.

**Validaciones**: `hasta >= desde` y ambas dentro de rangos plausibles (FR-003); el período no
puede extenderse más allá de la fecha de cese evaluada (edge case).

---

### `Licencia`

| Campo | Tipo | Reglas |
|---|---|---|
| `tipo` | `TipoLicencia` | `con_goce` / `sin_goce` |
| `desde` | `date` | dentro del período contenedor |
| `hasta` | `date` | `>= desde`, dentro del período contenedor |

Su efecto sobre el cómputo es `NO_VERIFICADA` (Cuestión abierta #5): el modelo la representa
fielmente, la regla decide qué hacer con ella.

---

### `HistoriaDeServicios`

| Campo | Tipo | Reglas |
|---|---|---|
| `periodos` | `list[PeriodoDeServicio]` | ≥1 |
| `superposiciones` | `list[Superposicion]` | derivado, no cargado |

**Normalización**: al construirse, ordena los períodos por `(desde, hasta, cargo)` y asigna `idx`.
Esto es lo que hace cumplir FR-049/SC-010 por construcción: dos historias con los mismos períodos
en distinto orden producen la misma `HistoriaDeServicios` normalizada, así que el resto del motor
ni siquiera puede observar el orden de carga.

### `Superposicion`

| Campo | Tipo | Significado |
|---|---|---|
| `periodos` | `tuple[int, int]` | `idx` de los dos períodos solapados |
| `desde` / `hasta` | `date` | tramo común |
| `clasificacion` | `simultaneidad \| posible_error_carga` | FR-004 |

Un solapamiento de ≥3 años continuos se clasifica como `simultaneidad` (FR-043); los más cortos
quedan como `posible_error_carga` para que el usuario confirme.

---

### Enumeraciones de entrada

| Enum | Valores |
|---|---|
| `SituacionRevista` | `titular`, `provisional`, `suplente` |
| `TipoLicencia` | `con_goce`, `sin_goce` |
| `TipoEstablecimiento` | `estatal_dgcye`, `privado`, `otra_jurisdiccion` |
| `CajaAportes` | `ips`, `anses`, `otra_caja` |

`TipoEstablecimiento` y `CajaAportes` son los discriminadores que disparan fuera de alcance
(FR-044, FR-045). Se modelan explícitamente en vez de inferirse, para que el caso fuera de alcance
sea **detectable**, que es lo que exige el Principio X.

---

## 2. Datos normativos versionados

### `Regla`

| Campo | Tipo | Reglas | Origen |
|---|---|---|---|
| `id` | `str` | único, estable, usado en diagnóstico | FR-054 |
| `norma` | `Norma` | requerido | FR-006 |
| `tipo` | `letra_ley \| interpretacion` | requerido | FR-040 |
| `estado` | `verificado \| no_verificada` | requerido | FR-006 |
| `vigencia_desde` / `vigencia_hasta` | `date \| None` | — | FR-006 |
| `verificada_en` | `date \| None` | requerido si `verificado` | FR-006 |
| `impacto_si_no_verificada` | `SentidoImpacto \| None` | requerido si `no_verificada` | FR-046b |
| `valor` | `Decimal \| int \| str \| dict` | el contenido de la regla | FR-007 |

`SentidoImpacto`: `al_alza`, `a_la_baja`, `indeterminado`. Es obligatorio para toda regla
`NO_VERIFICADA` — sin él, FR-046b no se puede cumplir, así que el schema lo exige y CI lo valida.

### `Norma`

| Campo | Tipo | Ejemplo |
|---|---|---|
| `texto` | `str` | `"DL 9650/80, art. 24 inc. b"` |
| `ley` | `str` | `"DL 9650/80"` |
| `articulo` | `str \| None` | `"24"` |
| `inciso` | `str \| None` | `"b"` |
| `enlace` | `str \| None` | URL al texto oficial |

### `ConjuntoDeReglas`

| Campo | Tipo |
|---|---|
| `version` | `str` (semver) |
| `reglas` | `dict[str, Regla]` |
| `catalogo_cargos` | `CatalogoDeCargos` |

---

### `CatalogoDeCargos` y `EntradaCatalogo`

Implementa FR-002a. Es la fuente de verdad de la condición "al frente de alumnos".

| Campo (`EntradaCatalogo`) | Tipo | Origen |
|---|---|---|
| `cargo` | `str` | — |
| `jerarquia` | `int \| None` | FR-022 (criterio `NO_VERIFICADA`, Cuestión #4) |
| `al_frente_de_alumnos` | `bool \| None` | `None` = indeterminado |
| `norma` | `Norma` | Ley 13469 / 10745 / 11860 |
| `estado` | `verificado \| no_verificada` | FR-002c |
| `regla_id` | `str \| None` | apunta a la regla que lo condiciona |

Un cargo ausente del catálogo **no** se asume: su condición queda indeterminada, se advierte y el
resultado sale provisional (edge case). Un cargo presente con `estado: no_verificada` dispara la
advertencia de impacto 70 % vs 75 % (FR-002c, Cuestión abierta #8).

---

### `GrillaSalarial`

| Campo | Tipo | Origen |
|---|---|---|
| `version` | `str` | FR-008 |
| `norma` / `enlace` | `Norma` / `str` | FR-008 |
| `vigencia_desde` / `vigencia_hasta` | `date` / `date \| None` | FR-008 |
| `extraida_en` | `date` | FR-008 |
| `aprobada_por` / `aprobada_en` | `str` / `date` | FR-008, Principio IX |
| `valores` | `dict[str, ValorCargo]` | — |

No existe estado "pendiente" en el modelo: el motor solo ve grillas que están en `grids/`, y estar
ahí significa haber pasado por el PR aprobado (research R4). Lo que el motor sí puede encontrar es
la **ausencia** de la grilla vigente, que dispara FR-034.

---

## 3. Salida

### `Monto` — el tipo que hace cumplir FR-046a

| Campo | Tipo | Reglas |
|---|---|---|
| `valor` | `Decimal` | requerido |
| `moneda` | `Literal["ARS"]` | requerido |
| `estado` | `definitivo \| provisional` | requerido |
| `reglas_condicionantes` | `list[ReglaCondicionante]` | no vacía si `provisional` |
| `grilla_version` | `str` | requerido |
| `a_valores_de` | `date` | fecha de la grilla usada (FR-030a) |

**Esta es la decisión de diseño central de la salida.** No existe una representación del monto sin
su estado: FR-046a ("la marca es inseparable del monto en toda vía de salida") se cumple por tipo,
no por disciplina del serializador. Un validador de modelo rechaza `estado=provisional` con
`reglas_condicionantes` vacía.

### `ReglaCondicionante`

| Campo | Tipo | Origen |
|---|---|---|
| `regla_id` | `str` | — |
| `norma` | `Norma` | FR-038 |
| `sentido_impacto` | `SentidoImpacto` | FR-046b |
| `magnitud_estimada` | `str \| None` | FR-046b ("70 % vs 75 %") |
| `que_falta_verificar` | `str` | FR-046 |

---

### `Informe`

| Campo | Tipo | Origen |
|---|---|---|
| `schema_version` | `str` | contrato |
| `estado_general` | `definitivo \| provisional` | FR-046c, SC-012 |
| `elegibilidad` | `Elegibilidad` | FR-011 a FR-018 |
| `cargo_base` | `CargoBase \| None` | FR-019 a FR-024a |
| `escenarios` | `list[Escenario]` | FR-035 a FR-037 |
| `desglose` | `list[PasoDelDesglose]` | FR-038 |
| `procedencias` | `list[Procedencia]` | FR-039 |
| `advertencias` | `list[Advertencia]` | FR-041 |
| `version_reglas` / `version_grilla` | `str` / `str \| None` | FR-009 |
| `aviso_estimacion` | `str` | FR-042 |
| `aviso_movilidad` | `str` | FR-030c (art. 50) |

`estado_general` se **deriva**, no se asigna: es `provisional` si cualquier monto, la elegibilidad
o el cargo base lo son. Derivarlo evita que queden inconsistentes.

### `Elegibilidad`

| Campo | Tipo | Origen |
|---|---|---|
| `incisos` | `list[ResultadoInciso]` | FR-011 a FR-013 |
| `minimo_22_anios` | `ResultadoRequisito` | FR-014 |
| `inciso_mas_favorable` | `str \| None` | FR-017 |
| `estado` | `definitivo \| provisional` | FR-015a, FR-002c |

### `ResultadoInciso`

| Campo | Tipo | Origen |
|---|---|---|
| `inciso` | `b \| c \| d` | — |
| `cumple` | `bool` | — |
| `habilitado_desde` | `date \| None` | FR-016 |
| `falta` | `Faltante \| None` | FR-016 (edad y servicios que faltan) |
| `requisitos` | `list[ResultadoRequisito]` | cada uno con su `Norma` |

### `CargoBase`

| Campo | Tipo | Origen |
|---|---|---|
| `cargo` | `str` | FR-019 |
| `via` | `36_consecutivos \| 60_alternados \| cargo_inferior` | FR-020, FR-020a |
| `meses_que_lo_sustentan` | `list[MesCalendario]` | FR-020 |
| `descartados` | `list[CandidatoDescartado]` | FR-021 |
| `descenso_desde` | `str \| None` | FR-020a: cargo superior que no alcanzó los 36/60 |
| `estado` | `definitivo \| provisional` | FR-022, FR-023, FR-024, FR-024a |

### `Escenario`

| Campo | Tipo | Origen |
|---|---|---|
| `fecha_cese` | `date` | FR-035 |
| `tipo` | `provista \| habilitacion \| excedente_3 \| excedente_5` | FR-036 |
| `hay_derecho` | `bool` | FR-035 |
| `inciso` | `str \| None` | — |
| `porcentaje` | `Decimal \| None` | FR-025 a FR-028 |
| `antiguedad_anios` | `int \| None` | FR-030b |
| `haber` | `Monto \| None` | FR-030 |
| `advertencias` | `list[Advertencia]` | — |
| `lectura_literal` | `LecturaAlternativa \| None` | FR-027b |

`LecturaAlternativa` lleva el porcentaje que correspondería bajo la lectura literal de los
arts. 42/43 y su sentido de impacto (`al_alza`), para cumplir FR-027b.

### `PasoDelDesglose`

| Campo | Tipo | Origen |
|---|---|---|
| `orden` | `int` | determinismo |
| `descripcion` | `str` | FR-038 |
| `entrada` / `salida` | `str` | FR-038 |
| `regla_id` | `str` | FR-038 |
| `norma` | `Norma` | FR-038 |
| `tipo_fuente` | `letra_ley \| interpretacion` | FR-040 |

### `Procedencia`

| Campo | Tipo | Origen |
|---|---|---|
| `dato` | `str` | FR-039 |
| `origen` | `manual \| derivado` | FR-039, FR-002b |
| `derivado_de` | `str \| None` | FR-039 |
| `difiere_del_catalogo` | `bool` | FR-002b |

### `Advertencia`

| Campo | Tipo | Origen |
|---|---|---|
| `codigo` | `CodigoAdvertencia` | identificador anónimo (FR-054) |
| `mensaje` | `str` | FR-041 |
| `norma` | `Norma \| None` | FR-041 |
| `sentido_impacto` | `SentidoImpacto \| None` | FR-046b |
| `bloquea_calculo` | `bool` | FR-043 a FR-045 |

`CodigoAdvertencia` cubre: `dato_faltante`, `simultaneidad_detectada`,
`servicios_no_docentes_sin_computar`, `prorrateo_podria_completar_requisitos`,
`fuera_de_alcance_otra_caja`, `fuera_de_alcance_privado`, `fuera_de_alcance_promedio_36`,
`regla_no_verificada`, `grilla_ausente`, `cargo_fuera_de_catalogo`, `empate_jerarquia`,
`lectura_literal_excedente`, `montos_a_valores_de_hoy`, `haber_movil_art_50`.

---

## 4. Invariantes verificables

Cada uno tiene su property test (research R8):

| # | Invariante | Verifica |
|---|---|---|
| I1 | El orden de carga de períodos no altera ningún campo del informe | FR-049, SC-010 |
| I2 | `porcentaje` nunca supera el máximo legal del artículo aplicable | FR-028 |
| I3 | Mismas entradas + mismas versiones ⇒ informe idéntico | FR-048, SC-003 |
| I4 | Más servicios nunca reduce el haber ni retrasa la habilitación | monotonía |
| I5 | `Monto.estado == provisional` ⟺ `reglas_condicionantes` no vacía | FR-046a |
| I6 | `Informe.estado_general == definitivo` ⟺ ningún componente es provisional | FR-046c |
| I7 | Si hay advertencia con `bloquea_calculo`, no existe `haber` en ese escenario | FR-044, FR-045 |
| I8 | Ningún valor de dominio aparece en la salida de diagnóstico | FR-054, SC-008 |
