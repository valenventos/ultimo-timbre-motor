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
| `fecha_de_calculo` | `date` | requerido | FR-001a |
| `fecha_nacimiento` | `date` | requerido, anterior a `fecha_de_calculo` | FR-001 |
| `historia` | `HistoriaDeServicios` | requerido, no vacía | FR-002 |
| `fechas_cese` | `list[date]` | ≥1, únicas, ordenadas al normalizar | FR-001 |

**Validaciones**: `fecha_nacimiento` coherente con la primera fecha de servicio (no se admite
servicio antes de los 16 años: se rechaza como error de carga, no se calcula).

**`fecha_de_calculo` es obligatoria y el motor nunca lee el reloj** (FR-001a). Toda comparación
relativa a "hoy" —plausibilidad de fechas, proyección de períodos en curso, elección de la última
grilla aprobada— la usa. Es lo que hace que un caso archivado hoy produzca dentro de un año
exactamente el mismo informe: sin esto, el determinismo de SC-003 valdría solo dentro de la misma
jornada. La CLI la completa con la fecha del sistema cuando el usuario no la provee; la librería
la exige.

---

### `PeriodoDeServicio`

| Campo | Tipo | Reglas | Origen |
|---|---|---|---|
| `idx` | `int` | asignado al normalizar; único; es el identificador anónimo usado en diagnóstico | FR-054 |
| `cargo` | `CargoRef` (`str`) | requerido; validado contra el catálogo | FR-002 |
| `establecimiento` | `Establecimiento` | requerido | FR-002 |
| `desde` | `date` | requerido | FR-002 |
| `hasta` | `date \| None` | `None` = **período en curso**; si se declara, `>= desde` | FR-002e |
| `caja_aportes` | `CajaAportes` | requerido | FR-002d |
| `situacion_revista` | `SituacionRevista` | requerido | FR-002 |
| `licencias` | `list[Licencia]` | puede ser vacía | FR-002 |
| `al_frente_override` | `bool \| None` | `None` = derivar del catálogo | FR-002b |
| `naturaleza_override` | `NaturalezaServicio \| None` | `None` = derivar del catálogo | FR-002d |

**`CargoRef`** es un **`str`**: el nombre del cargo tal como lo nombra el catálogo versionado.
Se valida contra el catálogo, pero **un cargo ausente no invalida el caso**: se advierte
`cargo_fuera_de_catalogo`, su condición de al frente de alumnos y su naturaleza quedan
indeterminadas y el resultado sale provisional. Rechazar el caso obligaría al profesional a
esperar una actualización del catálogo para obtener cualquier análisis, cuando el resto de la
historia de servicios sí es computable (Principio IV).

**Nota de diseño — qué se deriva y qué se carga**: ni `al_frente_de_alumnos` ni `naturaleza`
(docente / no docente) son campos de entrada. Ambos **se derivan del cargo** vía el catálogo
versionado, porque ambos son propiedades del cargo y no del caso: un "Maestro de grado" es
docente y está al frente de alumnos con independencia de quién lo ejerza. Los dos `*_override`
existen solo para la corrección manual (FR-002b, FR-002d) y su uso deja rastro obligatorio en la
procedencia, además de condicionar el monto (`override_manual`).

`caja_aportes`, en cambio, **sí se carga**: depende de la relación de empleo, no del cargo. El
mismo cargo puede haberse ejercido con aportes al IPS o a otra caja. Vive en el período y no en
el establecimiento, porque es lo que decide si el tramo se computa (FR-044).

**Validaciones**: `hasta >= desde` cuando `hasta` está presente, y fechas dentro de rangos
plausibles respecto de `fecha_de_calculo` (FR-003). Un período que supera la fecha de cese
evaluada **no se rechaza: se recorta** a esa fecha (FR-018a), y cada fecha de cese del mismo caso
recorta de forma independiente.

**Período en curso** (`hasta is None`): se proyecta hasta cada fecha de cese bajo supuesto de
continuidad en el mismo cargo, sin ascensos ni cambio de situación de revista (FR-002e). El
supuesto entra en `Procedencia`, genera la advertencia `supuesto_continuidad` y queda como
condicionante de todo monto que dependa de él.

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

**Cómputo sobre la unión, nunca sobre la suma** (FR-004a): los años de servicio y los meses que
sustentan el cargo base se calculan sobre el **conjunto unión** de los tramos cubiertos. Dos
cargos simultáneos durante 2015 aportan el año 2015 una vez, no dos. El modelo expone
`tramos_unidos(hasta: date) -> list[Tramo]` y `meses_cubiertos(hasta: date) -> set[MesCalendario]`,
y **ningún** camino del motor suma duraciones de períodos. Sumar duraciones es el error clásico de
este dominio y produce historias de 40 años de servicio sobre una carrera de 25.

### `Superposicion`

| Campo | Tipo | Significado |
|---|---|---|
| `periodos` | `tuple[int, int]` | `idx` de los dos períodos solapados |
| `desde` / `hasta` | `date` | tramo común |
| `clasificacion` | `ClasificacionSuperposicion` | FR-004 |

`ClasificacionSuperposicion` tiene **tres** valores, y la clasificación es excluyente:

| Valor | Condición | Efecto |
|---|---|---|
| `simultaneidad_computable_art47` | ≥3 años continuos **y** alcanza al cargo base | Se advierte el impacto posible citando `art. 47; Res. IPS 995/2021`; **no** se calcula el incremento (FR-043) |
| `simultaneidad_no_computable` | Cargos distintos solapados que no reúnen lo anterior | Se informa, sin impacto en el haber |
| `posible_error_carga` | **Mismo cargo en el mismo establecimiento** solapados | Se informa para que el usuario confirme o corrija |

La distinción entre las dos primeras importa porque solo la computable tiene incidencia potencial
en el haber: advertir con el mismo énfasis un solapamiento irrelevante entrena al profesional a
ignorar la advertencia que sí importa. `posible_error_carga` se discrimina por **cargo y
establecimiento iguales**, no por duración: un solapamiento corto entre dos cargos distintos es
simultaneidad real y breve, mientras que el mismo cargo duplicado en el mismo establecimiento es
casi siempre una carga repetida.

---

### Enumeraciones de entrada

| Enum | Valores |
|---|---|
| `SituacionRevista` | `titular`, `provisional`, `suplente` |
| `TipoLicencia` | `con_goce`, `sin_goce` |
| `TipoEstablecimiento` | `estatal_dgcye`, `privado`, `otra_jurisdiccion` |
| `CajaAportes` | `ips`, `anses`, `otra_caja` |
| `NaturalezaServicio` | `docente`, `no_docente` |
| `ClasificacionSuperposicion` | `simultaneidad_computable_art47`, `simultaneidad_no_computable`, `posible_error_carga` |

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
| `naturaleza` | `NaturalezaServicio \| None` | `None` = indeterminado (FR-002d) |
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
| `valores` | `dict[str, ValorCargo]` | FR-031a |

### `ValorCargo` y `ComponenteSalarial`

El valor de un cargo **no es un importe único** (FR-031a): es un conjunto de componentes.

| Campo (`ComponenteSalarial`) | Tipo | Significado |
|---|---|---|
| `codigo_concepto` | `str` | Código del concepto en el nomenclador |
| `descripcion` | `str` | Nombre legible |
| `importe` | `Decimal` | Cargado desde `str` (R1) |
| `bonificable` | `bool` | Si la antigüedad se aplica **sobre este componente** |
| `remunerativo` | `bool` | Si integra la remuneración sujeta a aportes |
| `regla_id` | `str \| None` | Regla que sostiene su inclusión |

`ValorCargo` es `{ cargo, componentes: list[ComponenteSalarial] }`.

**Por qué compuesto**: la antigüedad se aplica solo sobre los componentes bonificables (FR-031b),
nunca sobre el total. Con un importe indiviso no hay forma de aplicarla correctamente ni de
mostrar en el desglose sobre qué base se calculó — y el desglose es el producto (Principio IV).

**Cuestión abierta #2**: qué componentes integran la "remuneración asignada al cargo" que toma el
IPS sigue sin verificarse. El modelo los representa a todos con sus flags; la **regla** decide
cuáles entran. Mientras la #2 siga abierta, todo haber queda provisional (FR-031).

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
| `condicionantes` | `list[Condicionante]` | no vacía si `provisional` |
| `grilla_version` | `str` | requerido |
| `a_valores_de` | `date` | fecha de la grilla usada (FR-030a) |

**Esta es la decisión de diseño central de la salida.** No existe una representación del monto sin
su estado: FR-046a ("la marca es inseparable del monto en toda vía de salida") se cumple por tipo,
no por disciplina del serializador. Un validador de modelo rechaza `estado=provisional` con
`condicionantes` vacía.

### `Condicionante`

Un condicionante es lo que impide que el monto sea definitivo. Son **dos clases**, discriminadas
por `clase` (FR-046b):

| Campo | Tipo | Origen |
|---|---|---|
| `clase` | `regla_no_verificada \| situacion_del_caso` | FR-046b |
| `referencia` | `str` | `regla_id` si es regla; código de situación si no |
| `norma` | `Norma \| None` | FR-038 (solo las reglas tienen norma) |
| `sentido_impacto` | `SentidoImpacto` | FR-046b |
| `magnitud_estimada` | `str \| None` | FR-046b ("70 % vs 75 %") |
| `que_falta_verificar` | `str` | FR-046 |

Situaciones del caso reconocidas: `grilla_ausente` (FR-034), `cargo_fuera_de_catalogo`,
`override_manual` (FR-002b, FR-002d) y `supuesto_continuidad` (FR-002e).

**Por qué generalizarlo**: un monto calculado sobre un cargo que no está en el catálogo, o sobre
un período en curso proyectado, es tan provisional como uno que depende de una regla sin
verificar — pero la fuente de la incertidumbre no es normativa sino del caso. Si solo se
modelaran las reglas, esas tres situaciones tendrían que marcar el monto como provisional **sin
poder explicar por qué**, que es justo lo que FR-046b prohíbe.

---

### `Informe`

| Campo | Tipo | Origen |
|---|---|---|
| `schema_version` | `str` | contrato |
| `fecha_de_calculo` | `date` | FR-001a |
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

`CodigoAdvertencia` cubre: `dato_faltante`, `simultaneidad_computable_art47`,
`simultaneidad_no_computable`, `posible_error_carga`,
`servicios_no_docentes_sin_computar`, `prorrateo_podria_completar_requisitos`,
`fuera_de_alcance_otra_caja`, `fuera_de_alcance_privado`, `fuera_de_alcance_promedio_36`,
`regla_no_verificada`, `grilla_ausente`, `cargo_fuera_de_catalogo`, `empate_jerarquia`,
`lectura_literal_excedente`, `montos_a_valores_de_hoy`, `haber_movil_art_50`,
`supuesto_continuidad`, `dato_corregido_a_mano`, `periodo_recortado_a_cese`.

**`bloquea_calculo` y el informe parcial** (FR-045a): una advertencia bloqueante impide emitir
haber, pero **no aborta el informe**. El motor devuelve todo lo que sí puede sostener —la
elegibilidad de los tramos computables, las detecciones, el desglose de lo calculado— con los
escenarios sin `haber`. Un profesional que carga un caso con un período en otra caja necesita
saber qué dicen los 25 años que sí son del IPS; negarle el informe entero le quita información
que el motor ya tenía.

---

## 4. Invariantes verificables

Cada uno tiene su property test (research R8):

| # | Invariante | Verifica |
|---|---|---|
| I1 | El orden de carga de períodos no altera ningún campo del informe | FR-049, SC-010 |
| I2 | `porcentaje` nunca supera el máximo legal del artículo aplicable | FR-028 |
| I3 | Mismas entradas + mismas versiones ⇒ informe idéntico | FR-048, SC-003 |
| I4 | Agregar períodos **estatales de la DGCyE con aportes al IPS** nunca reduce el haber ni retrasa la habilitación | monotonía acotada |
| I5 | `Monto.estado == provisional` ⟺ `condicionantes` no vacía | FR-046a |
| I6 | `Informe.estado_general == definitivo` ⟺ ningún componente es provisional | FR-046c |
| I7 | Si hay advertencia con `bloquea_calculo`, no existe `haber` en ese escenario | FR-044, FR-045 |
| I8 | Ningún valor de dominio aparece en la salida de diagnóstico | FR-054, SC-008 |
| I9 | Los años de servicio y los meses del cargo base computados sobre períodos superpuestos **nunca superan** los de la unión de sus tramos | FR-004a, SC-014 |

**Sobre I4**: la monotonía vale solo para períodos **dentro del alcance** —estatales de la DGCyE
con aportes al IPS—. Sin esa restricción el invariante es falso: agregar un período en otra caja
no mejora el resultado, lo convierte en fuera de alcance y le saca el haber (FR-044). Lo mismo un
período privado. El property test genera únicamente períodos en alcance.

**Sobre I9**: es el invariante que protege contra el error clásico del dominio. Su property test
genera pares de períodos deliberadamente superpuestos y verifica que el cómputo coincide con el
de la unión, nunca con la suma de duraciones.
