---

description: "Task list template for feature implementation"
---

# Tasks: Motor de cálculo de jubilación ordinaria docente (IPS PBA)

**Input**: Design documents from `/specs/001-motor-calculo-jubilacion/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: OBLIGATORIOS y PRIMERO (Principio VI: test-first con casos reales). En este proyecto
las tareas de test NO son opcionales: toda tarea de test DEBE aparecer **antes** de la tarea de
implementación que cubre, y DEBE fallar antes de implementar. Una lista de tareas que ponga
implementación antes que su test no pasa `/speckit-analyze`.

**Cobertura exigida**: ramas ≥95 % en motor y parser, ≥80 % en el resto.

**Casos dorados**: cada regla de cálculo necesita al menos un caso de prueba con su fundamento
normativo citado. Los casos reales del IPS (anonimizados) son la prueba de aceptación máxima.
Los fixtures de recibos DEBEN estar anonimizados — nunca se suben recibos con datos reales.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/ultimo_timbre/`, `tests/` at repository root
- Datos normativos: `rules/<version>/`, `grids/<version>.yaml`, `schemas/`
- ADR: `docs/adr/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Esqueleto del paquete, licencia y el pipeline de CI completo. El CI se arma **antes**
que el código para que los gates existan desde el primer commit, no después.

- [ ] T001 Crear estructura `src/ultimo_timbre/{models,rules,engine,render,cli}/`, `tests/{golden,properties,contract,unit}/`, `rules/`, `grids/`, `schemas/`, `examples/`, `docs/adr/` con sus `__init__.py`
- [ ] T002 Configurar `pyproject.toml` con uv: Python 3.12, dependencias (pydantic>=2, python-dateutil, pyyaml, typer) y extras de desarrollo (pytest, hypothesis, pytest-cov, jsonschema, check-jsonschema, ruff, mypy, bandit, pip-audit, reuse, cyclonedx-py)
- [ ] T003 [P] Crear `LICENSE` con el texto AGPL-3.0-or-later y declarar `license = "AGPL-3.0-or-later"` en `pyproject.toml`
- [ ] T004 [P] Agregar encabezado `SPDX-License-Identifier: AGPL-3.0-or-later` como primera línea de todo archivo fuente y configurar `REUSE.toml`
- [ ] T005 [P] Configurar ruff (lint + format) en `pyproject.toml`
- [ ] T006 [P] Configurar `mypy --strict` en `pyproject.toml` con el plugin `pydantic.mypy` habilitado y `disallow_any_explicit` en `ultimo_timbre.engine` (research R9)
- [ ] T007 [P] Configurar pytest y pytest-cov en `pyproject.toml` con `--cov-branch` y umbrales **por paquete**: 95 % en `ultimo_timbre/engine` y `ultimo_timbre/rules`, 80 % en el resto
- [ ] T008 Crear `.github/workflows/ci.yml` con matriz `ubuntu-latest / macos-latest / windows-latest` × Python 3.12 usando uv, ejecutando tests y cobertura
- [ ] T009 [P] Agregar al CI el job de calidad: `ruff check`, `ruff format --check` y `mypy --strict`
- [ ] T010 [P] Agregar al CI el job de seguridad: `bandit -r src/`, `pip-audit` y `gitleaks detect`; un hallazgo alto o crítico bloquea el merge (Principio VII)
- [ ] T011 [P] Agregar al CI el job de licencia (`reuse lint`) y el de SBOM (`cyclonedx-py environment -o sbom.cdx.json` como artifact)
- [ ] T012 [P] Agregar al CI el job `validate-schemas` que corre `check-jsonschema` sobre `rules/**/*.yaml`, `rules/**/cargos.yaml` y `grids/*.yaml`
- [ ] T013 [P] Crear `docs/adr/0000-plantilla.md` y `docs/adr/0001-stack-y-decisiones-base.md` registrando R1 a R13 de `research.md`

**Checkpoint**: el repositorio tiene licencia, calidad, seguridad y SBOM verificados en CI antes de existir una sola línea de dominio.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos, schemas, loaders y los datos normativos versionados. Sin esto ninguna
historia puede empezar.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests fundacionales (OBLIGATORIO — van ANTES de la implementación) ⚠️

> **Principio VI: escribí estos tests PRIMERO y verificá que FALLAN antes de implementar.**

- [ ] T014 [P] Test de contrato: `contracts/caso.schema.json` es un schema Draft 2020-12 válido y acepta/rechaza los ejemplos mínimos, en `tests/contract/test_caso_schema.py`
- [ ] T015 [P] Test de contrato: `contracts/informe.schema.json` es un schema Draft 2020-12 válido y rechaza un `monto` con `estado: provisional` y `condicionantes: []`, en `tests/contract/test_informe_schema.py` (FR-046a, I5)
- [ ] T016 [P] Test: el loader YAML/JSON entrega `str` y nunca `float` para importes y porcentajes, en `tests/unit/test_loader_decimal.py` (research R1, Principio II)
- [ ] T017 [P] Test negativo: un importe o porcentaje **sin comillas** en un YAML de reglas hace fallar la validación de schema, en `tests/contract/test_schema_rechaza_float.py` (research R1)
- [ ] T018 [P] Test: una `Regla` con `estado: no_verificada` y sin `impacto_si_no_verificada` es rechazada por el modelo, en `tests/unit/test_regla_impacto.py` (FR-046b)
- [ ] T019 [P] Property test: `Monto.estado == provisional` ⟺ `condicionantes` no vacía, en `tests/properties/test_monto_invariante.py` (invariante I5, FR-046a)
- [ ] T020 [P] Test: no existe ningún acceso al reloj del sistema en `src/ultimo_timbre/engine/` ni `src/ultimo_timbre/rules/` —`date.today()`, `date.fromtimestamp()`, `datetime.now()`, `datetime.utcnow()`, `datetime.today()`, `datetime.fromtimestamp()` ni `time.time()`—, por inspección del AST, en `tests/test_sin_reloj.py` (FR-001a, research R13)
- [ ] T021 [P] Test: el catálogo deriva `al_frente_de_alumnos` y `naturaleza` desde el cargo; un cargo ausente queda indeterminado y no se asume, en `tests/unit/test_catalogo.py` (FR-002a, FR-002d)
- [ ] T022 [P] Test: `HistoriaDeServicios` normaliza orden y asigna `idx` de forma estable, en `tests/unit/test_normalizacion.py` (FR-049)
- [ ] T023 [P] Test de aislamiento: `calcular` no escribe a disco, no abre sockets y no importa nada de la aplicación web, de una base de datos ni de ningún componente probabilístico o LLM, en `tests/test_aislamiento.py` (FR-050, FR-052, FR-053, Principio V)
- [ ] T024 [P] Test: el loader de `grids/` **rechaza** toda grilla que declare `ficticia: true`, de modo que una grilla de prueba nunca pueda usarse en una corrida real, en `tests/unit/test_grilla_ficticia_rechazada.py` (Principio IX)

### Implementación fundacional

> **Regla para los datos normativos**: creá la **estructura completa** y cargá **únicamente** los
> valores que figuran literalmente en `spec.md` o en la constitución —las edades, los años de
> servicio y los porcentajes de los arts. 24, 41, 42 y 43—. Todo otro valor (importes de grilla,
> jerarquías numéricas, códigos de concepto, fechas `verificada_en` no documentadas) queda en
> `null` o como regla `NO_VERIFICADA` con su `sentido_impacto` y su `que_falta_verificar`.
> **Nunca se completa con un valor plausible**: una vez escrito en el archivo, un número inventado
> que parece correcto es indistinguible de uno verificado, y el Principio I existe precisamente
> para que eso no pase.

> Requiere T014–T024 escritas y fallando.

- [ ] T025 [P] Crear `schemas/rule.schema.json`: `id`, `norma` (ley/artículo/inciso/enlace), `tipo` (`letra_ley`/`interpretacion`), `estado` (`verificado`/`no_verificada`), `vigencia_desde`, `vigencia_hasta`, `verificada_en` (requerido si `verificado`), `impacto_si_no_verificada` (requerido si `no_verificada`), `valor`; importes y porcentajes con `"type": "string"` y patrón numérico
- [ ] T026 [P] Crear `schemas/cargo.schema.json`: `cargo`, `jerarquia`, `al_frente_de_alumnos` (`bool | null`, `null` = indeterminado), `naturaleza` (`docente`/`no_docente`/`null`), `norma`, `estado`, `regla_id`
- [ ] T027 [P] Crear `schemas/grid.schema.json`: `version`, `norma`, `enlace`, `vigencia_desde`, `vigencia_hasta`, `extraida_en`, `aprobada_por`, `aprobada_en`, y `valores` como mapa de cargo a lista de componentes con `codigo_concepto`, `descripcion`, `importe` (string numérico), `bonificable`, `remunerativo`, `regla_id` (FR-031a)
- [ ] T028 [P] Implementar enums en `src/ultimo_timbre/models/enums.py`: `SituacionRevista` (`titular`, `provisional`, `suplente`), `TipoLicencia` (`con_goce`, `sin_goce`), `TipoEstablecimiento` (`estatal_dgcye`, `privado`, `otra_jurisdiccion`), `CajaAportes` (`ips`, `anses`, `otra_caja`), `NaturalezaServicio` (`docente`, `no_docente`), `ClasificacionSuperposicion` (`simultaneidad_computable_art47`, `simultaneidad_no_computable`, `posible_error_carga`), `EstadoResultado` (`definitivo`, `provisional`), `SentidoImpacto` (`al_alza`, `a_la_baja`, `indeterminado`), `ClaseCondicionante`, `CodigoAdvertencia`, `TipoFuente`, `ViaCargoBase`, `TipoEscenario`, `Formato`
- [ ] T029 [P] Implementar `Caso`, `PeriodoDeServicio`, `Licencia`, `Establecimiento` en `src/ultimo_timbre/models/caso.py` con `ConfigDict(strict=True, frozen=True)`: `Caso.fecha_de_calculo` requerido, `fecha_nacimiento` anterior a `fecha_de_calculo`, `fechas_cese` con ≥1 elemento y únicas; `PeriodoDeServicio.hasta` es `date | None` (`None` = período en curso), `caja_aportes` requerido, `al_frente_override` y `naturaleza_override` por defecto `None`; el modelo no admite rutas de carga de PDF (FR-001, FR-002, FR-003, FR-005)
- [ ] T030 [P] Implementar `Regla`, `Norma`, `ConjuntoDeReglas`, `CatalogoDeCargos`, `EntradaCatalogo` en `src/ultimo_timbre/models/normativa.py`, con validador que exige `impacto_si_no_verificada` cuando `estado == no_verificada` (FR-006)
- [ ] T031 [P] Implementar `GrillaSalarial`, `ValorCargo` y `ComponenteSalarial` en `src/ultimo_timbre/models/grilla.py` (FR-031a)
- [ ] T032 Implementar `Monto`, `Condicionante`, `Advertencia`, `Procedencia`, `PasoDelDesglose`, `Escenario`, `Elegibilidad`, `CargoBase`, `Informe` en `src/ultimo_timbre/models/informe.py`, con validador que rechaza `estado=provisional` con `condicionantes` vacía y deriva `Informe.estado_general` en lugar de aceptarlo como entrada (FR-046a, FR-046c)
- [ ] T033 Implementar `HistoriaDeServicios` en `src/ultimo_timbre/models/caso.py` con normalización (orden por `(desde, hasta, cargo)` y asignación de `idx`) y los métodos `tramos_unidos(hasta)` y `meses_cubiertos(hasta)` que computan sobre la **unión**, nunca sumando duraciones (FR-004a, I9)
- [ ] T034 Implementar `src/ultimo_timbre/errors.py`: `UltimoTimbreError`, `CasoInvalido`, `ReglasNoDisponibles` y `FueraDeAlcance` (reservada para errores de programación, no para casos de usuario)
- [ ] T035 Implementar los loaders en `src/ultimo_timbre/rules/loader.py`: `yaml.safe_load` con resolver que desactiva la conversión implícita a float y `json.load(parse_float=Decimal)` (research R1)
- [ ] T036 Implementar `src/ultimo_timbre/rules/versiones.py` con `cargar_reglas`, `cargar_grilla`, `grilla_vigente_a` y `versiones_disponibles`, rechazando con error toda grilla cargada desde `grids/` que declare `ficticia: true` (Principio IX)
- [ ] T037 Implementar `src/ultimo_timbre/rules/catalogo.py` con la derivación de `al_frente_de_alumnos` y `naturaleza` desde el cargo, respetando los `*_override` y marcando su uso como dato manual (FR-002a, FR-002b, FR-002d)
- [ ] T038 Crear `tests/fixtures/grilla-ficticia-test.yaml` con `ficticia: true` y valores **redondos y evidentemente inventados** (por ejemplo componentes de `"100000.00"` y `"50000.00"`), con la estructura completa de `schemas/grid.schema.json`. Es la grilla que usan los tests de US4 y US5; vive en `tests/fixtures/`, **nunca** en `grids/`, y el loader la rechaza si alguien la mueve allí (T024, T036)
- [ ] T039 [P] Crear `rules/v1/requisitos.yaml` con el art. 24 incs. b, c y d (50/25, 50/25 con 10 al frente, 55/30) y el mínimo de 22 años con aportes, cada regla con su norma y `estado: verificado` `[DL 9650/80, art. 24]`. Estos umbrales sí están documentados: transcribilos literalmente y no agregues ningún otro
- [ ] T040 [P] Crear `rules/v1/haber.yaml` con el 70 % del art. 41, los 75 %/80 % del art. 42, los 75/80/85 % del art. 43 y el criterio de cómputo del excedente `[Res. IPS 995/2021, Anexo, punto 2.1.a]` marcado `tipo: interpretacion` (FR-027a). Son los únicos porcentajes documentados: la política de redondeo y los conceptos que integran la remuneración quedan `NO_VERIFICADA`, no se estiman
- [ ] T041 [P] Crear `rules/v1/cargos.yaml` con el catálogo: preceptores y bibliotecarios `[Ley 13469]`, técnico-docentes de Psicología y Educación Especial `[Ley 10745]`, visitadoras de higiene escolar `[Ley 11860]`, y la regla de extensión de la Ley 13469 a otros cargos con `estado: no_verificada` e `impacto_si_no_verificada` de 70 % vs 75 % `[SCBA causa A 74801 (2020), Cuestión abierta #8]`. **`jerarquia` queda en `null` para todos los cargos**: el criterio de comparación es la Cuestión abierta #4 y no hay ningún orden numérico documentado que transcribir
- [ ] T042 [P] Crear `rules/v1/no_verificadas.yaml` con las reglas de las Cuestiones abiertas #1 a #6, cada una con `valor: null`, su `sentido_impacto` y su `que_falta_verificar`: tope de antigüedad, remuneración del cargo, horas cátedra, criterio de jerarquía, licencias y situación de revista, y redondeo. Ninguna lleva un valor tentativo

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Verificar elegibilidad y fecha de habilitación (Priority: P1) 🎯 MVP

**Goal**: Responder "¿puede jubilarse, por cuál inciso y desde qué fecha?" con cada requisito
fundado en su artículo, sin necesitar grilla salarial.

**Independent Test**: Cargar una historia de servicios conocida y una fecha de cese, y verificar
el inciso aplicable y la fecha de habilitación con el detalle normativo, sin grilla ni montos.

### Tests for User Story 1 (OBLIGATORIO — va ANTES de la implementación) ⚠️

> **Principio VI: escribí estos tests PRIMERO y verificá que FALLAN antes de implementar.**

- [ ] T043 [P] [US1] Property test del invariante I9: períodos superpuestos nunca computan más años ni más meses que la unión de sus tramos, en `tests/properties/test_union_tramos.py` (FR-004a, SC-014)
- [ ] T044 [P] [US1] Property test del invariante I1: permutar el orden de los períodos no altera ningún campo del informe, en `tests/properties/test_orden_carga.py` (FR-049, SC-010)
- [ ] T045 [P] [US1] Property test del invariante I3: mismas entradas y mismas versiones producen informes idénticos byte a byte, en `tests/properties/test_determinismo.py` (FR-048, SC-003)
- [ ] T046 [P] [US1] Property test del invariante I4: agregar períodos **estatales DGCyE con aportes al IPS** nunca retrasa la habilitación, en `tests/properties/test_monotonia.py`
- [ ] T047 [P] [US1] Caso dorado: docente nacida 1980-03-15 con 26 años al frente de alumnos cumple el inc. b al 2030-03-31, en `tests/golden/test_inc_b.py` `[DL 9650/80, art. 24 inc. b]` (US1 esc. 1)
- [ ] T048 [P] [US1] Caso dorado: con 24 años de servicio y 52 de edad no cumple ningún inciso y se informa el faltante, en `tests/golden/test_no_cumple.py` (US1 esc. 2, FR-016)
- [ ] T049 [P] [US1] Caso dorado: cumple inc. b e inc. d en fechas distintas y se señala el más favorable, en `tests/golden/test_incisos_multiples.py` (US1 esc. 4, FR-017)
- [ ] T050 [P] [US1] Unitario: `tramos_unidos` y `meses_cubiertos` sobre períodos contiguos, disjuntos y superpuestos, en `tests/unit/test_calendario_union.py` (FR-004a)
- [ ] T051 [P] [US1] Unitario: recorte de un período que supera la fecha de cese, independiente por cada fecha evaluada, en `tests/unit/test_recorte_cese.py` (FR-018a)
- [ ] T052 [P] [US1] Unitario: proyección de un período en curso (`hasta is None`) bajo supuesto de continuidad, con su `Procedencia` y la advertencia `supuesto_continuidad`, en `tests/unit/test_periodo_en_curso.py` (FR-002e)
- [ ] T053 [P] [US1] Unitario: edad al cese y fecha de habilitación por inciso con `relativedelta`, en `tests/unit/test_elegibilidad.py` (FR-011 a FR-016)
- [ ] T054 [P] [US1] Test de contrato: el informe de elegibilidad sin grilla valida contra `informe.schema.json`, en `tests/contract/test_informe_sin_grilla.py`
- [ ] T055 [P] [US1] Test: el informe declara `fecha_de_calculo`, y correrlo con dos fechas distintas solo cambia los campos que dependen de ella, en `tests/unit/test_fecha_calculo.py` (FR-001a)
- [ ] T056 [P] [US1] Test: todo informe declara `version_reglas` y, cuando hay grilla, `version_grilla`, en `tests/unit/test_versiones_informe.py` (FR-009)
- [ ] T057 [P] [US1] Property test del invariante I6: `Informe.estado_general == definitivo` si y solo si ningún componente del informe es provisional, en `tests/properties/test_estado_general.py` (FR-046c)

### Implementation for User Story 1

> Requiere T043–T057 escritas y fallando.

- [ ] T058 [US1] Implementar `src/ultimo_timbre/engine/calendario.py`: proyección de períodos a meses calendario, unión de tramos, cierre de cómputos a la fecha de cese sin computar servicios posteriores, recorte y proyección de períodos en curso (FR-004a, FR-018, FR-018a, FR-002e, research R2)
- [ ] T059 [US1] Implementar `src/ultimo_timbre/engine/elegibilidad.py` con los incisos b, c y d y el mínimo de 22 años, leyendo los umbrales desde `rules/v1/requisitos.yaml` y sin ningún valor normativo embebido (FR-011, FR-012, FR-013, FR-014, FR-007)
- [ ] T060 [US1] Implementar en `engine/elegibilidad.py` la fecha de habilitación por inciso y el cálculo del faltante en edad y servicios (FR-016)
- [ ] T061 [US1] Implementar la selección del inciso más favorable y su justificación en `engine/elegibilidad.py` (FR-017)
- [ ] T062 [US1] Implementar `src/ultimo_timbre/engine/desglose.py`: registro de cada paso con `regla_id`, `norma` y `tipo_fuente` distinguiendo letra de la ley de interpretación (FR-038, FR-040)
- [ ] T063 [US1] Implementar el registro de `Procedencia` por dato (manual o derivado, con `derivado_de` y `difiere_del_catalogo`) en `engine/desglose.py` (FR-039)
- [ ] T064 [US1] Implementar `calcular(caso, *, reglas, grilla=None) -> Informe` en `src/ultimo_timbre/engine/__init__.py`, sin I/O, sin red y sin reloj, aceptando `grilla=None` para producir informe sin montos (FR-051, contrato `library-api.md`)
- [ ] T065 [US1] Implementar la derivación de `Informe.estado_general` a partir de los estados de sus componentes en `src/ultimo_timbre/models/informe.py` (FR-046c, I6)
- [ ] T066 [US1] Implementar `src/ultimo_timbre/render/json_out.py` determinista: `sort_keys=True`, `ensure_ascii=False`, `Decimal` serializado como string y colecciones con orden explícito (FR-048, SC-003)
- [ ] T067 [US1] Exponer la superficie pública en `src/ultimo_timbre/__init__.py` con `__all__` y agregar `py.typed` (PEP 561) (contrato `library-api.md`)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Detectar los límites del motor antes de dar un número (Priority: P2)

**Goal**: Que el motor nunca adivine: detectar simultaneidad, servicios fuera de alcance y reglas
sin verificar, y devolver el análisis parcial que sí puede sostener.

**Independent Test**: Correr un conjunto de casos deliberadamente fuera de alcance o afectados por
reglas `NO_VERIFICADA` y verificar que ninguno recibe resultado definitivo y todos reciben una
advertencia que nombra la situación y su norma.

### Tests for User Story 2 (OBLIGATORIO — va ANTES de la implementación) ⚠️

> **Escribí estos tests PRIMERO y verificá que FALLAN antes de implementar (Principio VI).**

- [ ] T068 [P] [US2] Property test del invariante I7: si existe una advertencia con `bloquea_calculo`, ningún escenario tiene `haber`, en `tests/properties/test_bloqueo.py` (FR-044, FR-045)
- [ ] T069 [P] [US2] Caso dorado: dos cargos superpuestos más de 3 años continuos que alcanzan al cargo base se clasifican `simultaneidad_computable_art47` y no se calcula el incremento, en `tests/golden/test_simultaneidad.py` `[DL 9650/80, art. 47; Res. IPS 995/2021]` (US2 esc. 1, FR-043)
- [ ] T070 [P] [US2] Caso dorado: períodos con `caja_aportes` distinta de `ips` se reportan fuera de alcance sin computarse, en `tests/golden/test_otra_caja.py` `[DL 9650/80, arts. 66 y 67]` (US2 esc. 2, FR-044)
- [ ] T071 [P] [US2] Caso dorado: establecimiento de gestión privada se detecta y se informa sin calcular, en `tests/golden/test_privado.py` (US2 esc. 4, FR-045)
- [ ] T072 [P] [US2] Caso dorado: si los servicios docentes no alcanzan ningún inciso y existen no docentes, la advertencia nombra el prorrateo como vía posible y la elegibilidad queda no definitiva, en `tests/golden/test_prorrateo_posible.py` `[DL 9650/80, art. 27]` (US2 esc. 5, FR-015a)
- [ ] T073 [P] [US2] Test: un caso fuera de alcance **igual devuelve un `Informe`** con elegibilidad parcial, detecciones y desglose, sin `haber`, y no lanza excepción, en `tests/unit/test_informe_parcial.py` (FR-045a)
- [ ] T074 [P] [US2] Unitario: clasificación de superposiciones en las tres categorías, con el mismo cargo en el mismo establecimiento cayendo en `posible_error_carga`, en `tests/unit/test_superposiciones.py` (FR-004)
- [ ] T075 [P] [US2] Unitario: toda regla `NO_VERIFICADA` que interviene produce un `Condicionante` de clase `regla_no_verificada` con su `sentido_impacto`, en `tests/unit/test_condicionantes_regla.py` (FR-046, FR-046b)
- [ ] T076 [P] [US2] Unitario: las situaciones del caso (`cargo_fuera_de_catalogo`, `override_manual`, `supuesto_continuidad`) producen `Condicionante` de clase `situacion_del_caso`, en `tests/unit/test_condicionantes_situacion.py` (FR-046b)
- [ ] T077 [P] [US2] Caso dorado: un haber que depende de la escala de antigüedad sale marcado provisional con su explicación, en `tests/golden/test_provisional_antiguedad.py` (US2 esc. 3, Cuestión abierta #1)

### Implementation for User Story 2

> Requiere T068–T077 escritas y fallando.

- [ ] T078 [US2] Implementar la detección y clasificación de superposiciones en `src/ultimo_timbre/engine/alcance.py` con las tres categorías de FR-004, discriminando `posible_error_carga` por cargo y establecimiento iguales
- [ ] T079 [US2] Implementar en `engine/alcance.py` la detección de servicios fuera de alcance: `caja_aportes != ips` (FR-044), `tipo != estatal_dgcye` (FR-045) y el promedio de 36 meses del tercer párrafo del art. 41 (FR-020b)
- [ ] T080 [US2] Implementar en `engine/alcance.py` la detección de servicios no docentes y la advertencia condicional de prorrateo cuando los docentes no alcanzan ningún inciso (FR-015, FR-015a)
- [ ] T081 [US2] Implementar el emisor de advertencias con `codigo`, `norma`, `sentido_impacto` y `bloquea_calculo` en `src/ultimo_timbre/engine/advertencias.py` (FR-041)
- [ ] T082 [US2] Implementar la construcción de `Condicionante` para ambas clases y su propagación a cada `Monto` en `src/ultimo_timbre/engine/condicionantes.py` (FR-046a, FR-046b)
- [ ] T083 [US2] Implementar en `calcular()` el camino de informe parcial: ante advertencias bloqueantes se omite el haber y se conserva todo lo demás explicado, sin lanzar excepción (FR-045a, FR-047)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Determinar el cargo base y el porcentaje aplicable (Priority: P3)

**Goal**: Elegir el cargo base del art. 41 explicando qué períodos lo sustentan y por qué se
descartaron los otros, y determinar el porcentaje de los arts. 41 a 43.

**Independent Test**: Historias donde el cargo base correcto es conocido: el motor lo elige,
enumera los meses que lo sustentan y descarta candidatos con su razón, sin grilla salarial.

### Tests for User Story 3 (OBLIGATORIO — va ANTES de la implementación) ⚠️

> **Escribí estos tests PRIMERO y verificá que FALLAN antes de implementar (Principio VI).**

- [ ] T084 [P] [US3] Property test del invariante I2: el porcentaje nunca supera el máximo legal del artículo aplicable, cualquiera sea la entrada, en `tests/properties/test_tope_porcentaje.py` (FR-028)
- [ ] T085 [P] [US3] Caso dorado: Director 40 meses consecutivos frente a Maestro 25 años elige el de mayor jerarquía con los meses que lo sustentan, en `tests/golden/test_cargo_base_36.py` `[DL 9650/80, art. 41 (texto Ley 13968); Res. IPS 14/10]` (US3 esc. 1)
- [ ] T086 [P] [US3] Caso dorado: cargo con 60 meses alternados y nunca 36 consecutivos califica por la vía alternada, en `tests/golden/test_cargo_base_60.py` (US3 esc. 2, FR-019)
- [ ] T087 [P] [US3] Caso dorado: Director 20 meses y Vicedirector 48 consecutivos regula por el **cargo inferior** y lo explica, en `tests/golden/test_cargo_inferior.py` `[DL 9650/80, art. 41]` (US3 esc. 3, FR-020a)
- [ ] T088 [P] [US3] Caso dorado: ningún cargo alcanza 36/60 y se informa el promedio de 36 meses como fuera de alcance v1 sin calcular, en `tests/golden/test_promedio_36.py` `[DL 9650/80, art. 41, tercer párrafo]` (US3 esc. 4, FR-020b)
- [ ] T089 [P] [US3] Caso dorado: acceso por inc. b con todas las condiciones cumplidas 5 años antes aplica 85 %, en `tests/golden/test_porcentaje_inc_b.py` `[DL 9650/80, art. 43; Res. IPS 995/2021, Anexo, punto 2.1.a]` (US3 esc. 5)
- [ ] T090 [P] [US3] Caso dorado: docente que completa 25 años de servicio **a los 54 años** obtiene 75 % al habilitarse y 80 % tres años después, con la advertencia de la lectura literal, en `tests/golden/test_excedente_54.py` (US3 esc. 6, FR-027a, FR-027b)
- [ ] T091 [P] [US3] Caso dorado: acceso por inc. d sin excedente aplica 70 %, en `tests/golden/test_porcentaje_inc_d.py` `[DL 9650/80, art. 41]` (US3 esc. 7)
- [ ] T092 [P] [US3] Caso dorado: cargo cuya condición de al frente de alumnos depende de la extensión discutida de la Ley 13469 sale provisional con impacto 70 % vs 75 %, en `tests/golden/test_ley_13469.py` `[SCBA causa A 74801 (2020), Cuestión abierta #8]` (US3 esc. 8, FR-002c)
- [ ] T093 [P] [US3] Unitario: racha máxima de meses consecutivos y cardinalidad de meses alternados sobre el conjunto unión, en `tests/unit/test_cargo_base_conteo.py` (FR-019, FR-004a)
- [ ] T094 [P] [US3] Unitario: el excedente se cuenta desde que se cumplen **todas** las condiciones del inciso, no solo la edad, en `tests/unit/test_excedente.py` (FR-027a)
- [ ] T095 [P] [US3] Unitario: cálculo del porcentaje de la lectura literal alternativa con `sentido_impacto: al_alza`, en `tests/unit/test_lectura_literal.py` (FR-027b)
- [ ] T096 [P] [US3] Unitario: empate de jerarquía entre dos cargos emite `empate_jerarquia` y deja el cargo base provisional, en `tests/unit/test_empate_jerarquia.py` (FR-022, Cuestión abierta #4)

### Implementation for User Story 3

> Requiere T084–T096 escritas y fallando.

- [ ] T097 [US3] Implementar `src/ultimo_timbre/engine/cargo_base.py`: identificación del cargo de mayor jerarquía con 36 meses consecutivos o 60 alternados sobre el conjunto unión de meses (FR-019, research R2)
- [ ] T098 [US3] Implementar la exposición de los meses que sustentan el cargo base y la vía por la que califica en `engine/cargo_base.py` (FR-020)
- [ ] T099 [US3] Implementar el descenso al cargo inferior cuando el de mayor jerarquía no alcanza los 36/60, con su explicación en el desglose (FR-020a)
- [ ] T100 [US3] Implementar la detección del caso del tercer párrafo del art. 41 (promedio de 36 meses) como fuera de alcance v1, reusando `engine/alcance.py` (FR-020b)
- [ ] T101 [US3] Implementar la lista de candidatos descartados con su razón y meses alcanzados en `engine/cargo_base.py` (FR-021)
- [ ] T102 [US3] Implementar el marcado provisional del cargo base por las Cuestiones abiertas #3, #4 y #5, incluida la situación de revista, en `engine/cargo_base.py` (FR-022, FR-023, FR-024, FR-024a)
- [ ] T103 [US3] Implementar `src/ultimo_timbre/engine/porcentaje.py` con el 70 % del art. 41, los excedentes del art. 42 y los porcentajes docentes del art. 43, leyendo los valores desde `rules/v1/haber.yaml` (FR-025, FR-026, FR-027)
- [ ] T104 [US3] Implementar el cómputo del excedente desde que se cumplen todas las condiciones del inciso en `engine/porcentaje.py` (FR-027a, `Res. IPS 995/2021, Anexo, punto 2.1.a`)
- [ ] T105 [US3] Implementar la advertencia `lectura_literal_excedente` con el porcentaje alternativo y su `sentido_impacto` en `engine/porcentaje.py` (FR-027b)
- [ ] T106 [US3] Implementar el tope del porcentaje por artículo aplicable y la fecha exacta de cada excedente en `engine/porcentaje.py` (FR-028, FR-029)

**Checkpoint**: MVP completo (US1 + US2 + US3). El motor responde elegibilidad, límites, cargo base y porcentaje **sin necesitar grilla salarial**.

---

## Phase 6: User Story 4 - Estimar el haber con la grilla aprobada (Priority: P4)

**Goal**: Emitir el monto estimado valuando el cargo base con la grilla aprobada, con su versión,
su norma de origen y su estado inseparable del valor.

**Independent Test**: Con un cargo base y un porcentaje fijos y una grilla aprobada conocida,
verificar el monto y que el informe declara la versión de grilla usada.

### Carga de la primera grilla aprobada

- [ ] T107 [US4] Crear `.github/CODEOWNERS` cubriendo `grids/**` y `rules/**`
- [ ] T108 [US4] Implementar el check de CI `validate-grid-approval` en `.github/workflows/ci.yml`: falla si un PR que toca `grids/**` deja `aprobada_por` o `aprobada_en` vacíos, y con un solo mantenedor valida que `aprobada_por` coincida con quien **fusiona** el PR (research R4)
- [ ] T109 [US4] Escribir `docs/adr/0002-aprobacion-de-grillas.md` registrando la política escalonada y su disparador explícito: **el segundo mantenedor con permiso de merge** activa la exigencia de aprobador distinto del autor vía CODEOWNERS (research R4, Principio IX)
- [ ] T110 [MANUAL] [US4] **Tarea del mantenedor, no del agente**: transcribir desde el texto de la norma salarial vigente la primera `grids/2026-01.yaml`, con norma de origen, enlace, vigencia, `extraida_en`, `aprobada_por`, `aprobada_en` y los valores por cargo descompuestos en componentes con `bonificable` y `remunerativo` (FR-008, FR-031a). Ningún importe puede inventarse ni inferirse. **No bloquea los tests de US4**, que corren con la grilla ficticia de T038

### Tests for User Story 4 (OBLIGATORIO — va ANTES de la implementación) ⚠️

> **Escribí estos tests PRIMERO y verificá que FALLAN antes de implementar (Principio VI).**

- [ ] T111 [PENDIENTE-DATOS] [US4] Caso dorado con una resolución **real del IPS anonimizada**, valuado con la **grilla histórica vigente a la fecha del cese real de ese caso** (SC-002), en `tests/golden/test_haber_historico.py`. Requiere que el mantenedor consiga la resolución: **no bloquea US4 ni el release del MVP**, y hasta entonces queda marcado `xfail` con su motivo

> **Los demás casos dorados de US4 son sintéticos** y usan la grilla ficticia de T038.
> Verifican la mecánica del cálculo, que es lo que puede verificarse sin datos reales; lo que no
> pueden verificar es la coincidencia con el IPS, que es exactamente lo que espera T111.
- [ ] T112 [P] [US4] Caso dorado: grilla vigente ausente o no aprobada produce advertencia `grilla_ausente`, indica con qué grilla se calculó y marca el monto provisional, en `tests/golden/test_grilla_ausente.py` (US4 esc. 2, FR-034)
- [ ] T113 [P] [US4] Test: ninguna vía de salida entrega el valor del monto sin su `estado` y sus `condicionantes` —informe, exportación JSON, texto y lectura por librería—, en `tests/properties/test_monto_inseparable.py` (FR-046a, SC-011, US4 esc. 5)
- [ ] T114 [P] [US4] Test: el informe expone `estado_general` legible por máquina con valor `definitivo` o `provisional`, en `tests/contract/test_estado_general.py` (FR-046c, SC-012, US4 esc. 6)
- [ ] T115 [P] [US4] Unitario: la antigüedad se aplica **solo sobre los componentes bonificables**, nunca sobre el total del cargo, en `tests/unit/test_antiguedad_componentes.py` (FR-031b)
- [ ] T116 [P] [US4] Unitario: el redondeo se aplica en un único punto con política explícita y sale marcado provisional, en `tests/unit/test_redondeo.py` (FR-033, Cuestión abierta #6)
- [ ] T117 [P] [US4] Unitario: el aviso de estimación orientativa y el de movilidad del art. 50 están presentes en todo informe con montos, en `tests/unit/test_avisos.py` (FR-042, FR-030c)
- [ ] T118 [P] [US4] Test: una grilla sin `aprobada_por` no puede cargarse, en `tests/unit/test_grilla_no_aprobada.py` (FR-010, Principio IX)

### Implementation for User Story 4

> Requiere T111–T118 escritas y fallando.

- [ ] T119 [US4] Implementar `src/ultimo_timbre/engine/haber.py`: valuación del cargo base sumando los componentes que el conjunto de reglas marca como integrantes de la remuneración, y aplicación del porcentaje (FR-030, FR-031, FR-031a)
- [ ] T120 [US4] Implementar la aplicación de la antigüedad solo sobre componentes bonificables, con el paso correspondiente en el desglose (FR-031b)
- [ ] T121 [US4] Implementar el `quantize()` centralizado en `engine/haber.py` con política parametrizada desde el conjunto de reglas y `ROUND_HALF_UP` por defecto declarado como provisional (FR-033, research R1)
- [ ] T122 [US4] Implementar la advertencia `grilla_ausente` y el condicionante asociado cuando la grilla vigente al cese no está cargada (FR-034)
- [ ] T123 [US4] Implementar la construcción de `Monto` con `grilla_version`, `a_valores_de`, `estado` y `condicionantes` siempre poblados (FR-046a)
- [ ] T124 [US4] Implementar los avisos de estimación orientativa y de movilidad del art. 50 en `engine/haber.py` (FR-042, FR-030c)

**Checkpoint**: el motor emite montos, siempre con su estado y sus condicionantes inseparables.

---

## Phase 7: User Story 5 - Comparar escenarios de cese (Priority: P5)

**Goal**: Responder "¿me conviene esperar?" con escenarios comparables entre sí.

**Independent Test**: Un caso con habilitación y excedentes conocidos: verificar las tres fechas,
sus porcentajes y el orden cronológico de la comparación.

### Tests for User Story 5 (OBLIGATORIO — va ANTES de la implementación) ⚠️

> **Escribí estos tests PRIMERO y verificá que FALLAN antes de implementar (Principio VI).**

- [ ] T125 [P] [US5] Caso dorado: habilitación 75 %, excedente de 3 años 80 % y de 5 años 85 %, cada uno con su monto, en `tests/golden/test_escenarios.py` (US5 esc. 1, FR-036)
- [ ] T126 [P] [US5] Test: todos los escenarios usan la **misma** `grilla_version` y el mismo `a_valores_de`, de modo que la diferencia de monto se explique solo por porcentaje y antigüedad, en `tests/properties/test_escenarios_comparables.py` (FR-036a)
- [ ] T127 [P] [US5] Unitario: la antigüedad se proyecta a la fecha de cada escenario y crece mientras no se alcance el tope, apareciendo como paso del desglose, en `tests/unit/test_antiguedad_proyectada.py` (FR-030b, US5 esc. 5)
- [ ] T128 [P] [US5] Unitario: una fecha de cese anterior a la habilitación informa que no hay derecho y cuánto falta, sin emitir monto, en `tests/unit/test_cese_temprano.py` (US5 esc. 3, FR-035)
- [ ] T129 [P] [US5] Test: los escenarios futuros declaran `montos_a_valores_de_hoy` y `haber_movil_art_50`, en `tests/unit/test_avisos_escenarios.py` (FR-030a, FR-030c, US5 esc. 4 y 6)
- [ ] T130 [P] [US5] Unitario: ordenamiento cronológico estable de escenarios provistos y derivados, en `tests/unit/test_orden_escenarios.py` (FR-037)

### Implementation for User Story 5

> Requiere T125–T130 escritas y fallando.

- [ ] T131 [US5] Implementar `src/ultimo_timbre/engine/escenarios.py`: derivación de los escenarios de habilitación y de excedentes de 3 y 5 años, además de las fechas provistas (FR-036)
- [ ] T132 [US5] Implementar la valuación de escenarios futuros con la **última grilla aprobada**, sin proyección salarial, declarando `a_valores_de` (FR-030a)
- [ ] T133 [US5] Implementar la proyección de la antigüedad a la fecha de cada escenario, con su paso en el desglose y el condicionante por el tope `NO_VERIFICADA` (FR-030b, FR-032, Cuestión abierta #1)
- [ ] T134 [US5] Implementar la garantía de comparabilidad: todos los escenarios con la misma grilla (FR-036a)
- [ ] T135 [US5] Implementar el ordenamiento cronológico de escenarios y el caso sin derecho a la fecha evaluada (FR-035, FR-037)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 8: User Story 6 - Ejecutar el motor desde la línea de comandos (Priority: P6)

**Goal**: Correr el motor sobre un archivo de caso desde una terminal, sin red, con códigos de
salida distinguibles.

**Independent Test**: Invocar el ejecutable con un caso de ejemplo y verificar el informe completo
y el código de salida correcto, con la máquina desconectada de la red.

### Tests for User Story 6 (OBLIGATORIO — va ANTES de la implementación) ⚠️

> **Escribí estos tests PRIMERO y verificá que FALLAN antes de implementar (Principio VI).**

- [ ] T136 [P] [US6] Test: `calcular` con un caso válido emite el informe completo y termina con exit 0, incluso si `estado_general` es `provisional`, en `tests/cli/test_exit_exito.py` (US6 esc. 1, FR-056)
- [ ] T137 [P] [US6] Test: entrada inválida devuelve exit 2 con un mensaje que nombra el campo y el período y describe la corrección, en `tests/cli/test_exit_invalido.py` (US6 esc. 2, FR-057)
- [ ] T138 [P] [US6] Test: un informe con al menos una advertencia `bloquea_calculo` devuelve exit 3 **y emite igualmente el informe parcial**, en `tests/cli/test_exit_fuera_de_alcance.py` (FR-045b)
- [ ] T139 [P] [US6] Test: el motor produce el mismo informe con los sockets bloqueados, en `tests/test_sin_red.py` (US6 esc. 3, SC-007)
- [ ] T140 [P] [US6] Test de canarios: ningún dato personal marcado aparece en la salida de diagnóstico de una corrida completa, en `tests/properties/test_canarios.py` (invariante I8, FR-054, SC-008, US6 esc. 4)
- [ ] T141 [P] [US6] Test: `--fecha-calculo` fija produce informes idénticos en dos corridas separadas, en `tests/cli/test_reproducibilidad.py` (FR-001a)
- [ ] T142 [P] [US6] Test: la salida de texto y la JSON derivan del mismo `Informe` y ninguna recalcula, en `tests/unit/test_render_equivalente.py` (research R5)
- [ ] T143 [P] [US6] Test: `calcular` por librería y por CLI producen resultados idénticos, en `tests/test_equivalencia_cli_libreria.py` (FR-051)

### Implementation for User Story 6

> Requiere T136–T143 escritas y fallando.

- [ ] T144 [US6] Implementar `src/ultimo_timbre/render/texto.py`: salida legible en terminal renderizada desde el mismo `Informe`, sin lógica de cálculo propia (research R5)
- [ ] T145 [US6] Implementar `ultimo-timbre calcular` en `src/ultimo_timbre/cli/main.py` con Typer y las opciones `--formato`, `--salida`, `--reglas`, `--grilla` y `--fecha-calculo` (FR-055, contrato `cli.md`)
- [ ] T146 [US6] Implementar el relleno de `fecha_de_calculo` con la fecha del sistema **en la CLI** cuando el caso no la declara, dejándola asentada en el informe (FR-001a)
- [ ] T147 [US6] Implementar los códigos de salida 0, 2, 3 y 4 en `cli/main.py`, derivando el 3 de la presencia de advertencias bloqueantes y dejando el 1 sin asignar (FR-056, FR-045b)
- [ ] T148 [US6] Implementar los mensajes de error que nombran campo y período y describen la corrección posible en `cli/main.py` (FR-057, Principio VIII)
- [ ] T149 [US6] Implementar `ultimo-timbre validar` y `ultimo-timbre versiones` en `cli/main.py` (contrato `cli.md`)
- [ ] T150 [US6] Configurar `logging.NullHandler()` en la librería y la configuración de logging solo en la CLI, con identificadores técnicos anónimos (FR-054, research R12)
- [ ] T151 [US6] Registrar el entry point `ultimo-timbre` en `pyproject.toml`

**Checkpoint**: motor completo, usable como librería y desde terminal.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T152 [P] Crear los casos de ejemplo en `examples/` que usa `quickstart.md`: `caso-inc-b.yaml`, `caso-escenarios.yaml`, `caso-54-anios.yaml`, `caso-otra-caja.yaml`, `caso-privado.yaml`, `caso-simultaneo.yaml`, `caso-provisional.yaml`
- [ ] T153 [P] Documentar la interfaz pública de librería en `docs/api.md` con ejemplos de uso sin I/O
- [ ] T154 [P] Escribir `README.md` con instalación por uv, uso de CLI y de librería, y el aviso de estimación orientativa
- [ ] T155 [P] Publicar `SECURITY.md` con la política de divulgación responsable (Principio VII)
- [ ] T156 [P] Completar los ADR faltantes en `docs/adr/` para R2, R5, R7, R12 y R13
- [ ] T157 Agregar al CI el test de determinismo multiplataforma que compara el informe del mismo caso producido en Linux, macOS y Windows (SC-003, SC-007)
- [ ] T158 [P] Unit tests adicionales en `tests/unit/` hasta alcanzar la cobertura exigida
- [ ] T159 Verificar cobertura de ramas: ≥95 % en `ultimo_timbre/engine` y `ultimo_timbre/rules`, ≥80 % resto (Principio VI)
- [ ] T160 Security hardening: confirmar bandit, pip-audit, gitleaks y SBOM sin hallazgos altos/críticos (Principio VII)
- [ ] T161 Ejecutar la validación completa de `quickstart.md` (verificaciones 1 a 8) y corregir desvíos

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Solo depende de Foundational. Entrega `engine/calendario.py`, que US3 y US5 reutilizan.
- **User Story 2 (P2)**: Depende de Foundational. Usa el informe de US1 para colgar advertencias, pero sus detecciones son testeables por separado.
- **User Story 3 (P3)**: Depende de Foundational y del calendario de US1 (unión de tramos y conteo de meses). El marcado provisional del cargo base usa los condicionantes de US2.
- **User Story 4 (P4)**: Depende de US3 (cargo base y porcentaje). La carga de la primera grilla aprobada es T107–T110; sus **tests no la esperan**, porque corren con la grilla ficticia de T038.
- **User Story 5 (P5)**: Depende de US4 para los montos por escenario; la derivación de fechas de excedente ya existe desde US3 (FR-029).
- **User Story 6 (P6)**: Depende de que exista un `Informe` que renderizar; funciona con el alcance de US1 en adelante.

### Within Each User Story

- **Tests PRIMERO**: las tareas de test DEBEN escribirse y FALLAR antes de cualquier tarea de
  implementación de esa historia (Principio VI). Esto no es opcional ni reordenable.
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel (y se escriben antes que su implementación)
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# PASO 1 — Lanzar todos los tests de User Story 1 juntos (van primero, deben fallar):
Task: "Property test del invariante I9 en tests/properties/test_union_tramos.py"
Task: "Property test del invariante I1 en tests/properties/test_orden_carga.py"
Task: "Property test del invariante I3 en tests/properties/test_determinismo.py"
Task: "Caso dorado inc. b en tests/golden/test_inc_b.py"
Task: "Caso dorado sin cumplir incisos en tests/golden/test_no_cumple.py"
Task: "Unitario de unión de tramos en tests/unit/test_calendario_union.py"

# PASO 2 — Recién con los tests en rojo, implementar en orden de dependencia:
Task: "engine/calendario.py"        # bloquea a elegibilidad
Task: "engine/elegibilidad.py"      # depende de calendario
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 — primero sus tests (en rojo), después la implementación
4. Complete Phase 4: User Story 2 — los límites del motor, que vuelven confiable a US1
5. Complete Phase 5: User Story 3 — cargo base y porcentaje
6. **STOP and VALIDATE**: casos dorados en verde y cobertura cumplida (Principio VI)
7. Deploy/demo si está listo

**El MVP no necesita grilla salarial.** US1 a US3 responden elegibilidad, límites, cargo base y
porcentaje con `grilla=None`. Eso ya permite que un abogado asesore: sabe si puede jubilarse,
desde cuándo, sobre qué cargo y con qué porcentaje. El monto es la cuarta entrega, no la primera.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 → elegibilidad fundada → Demo
3. Add US2 → el motor deja de adivinar → Demo
4. Add US3 → cargo base y porcentaje → **MVP**
5. Add US4 → montos (requiere la primera grilla aprobada) → Demo
6. Add US5 → comparación de escenarios → Demo
7. Add US6 → uso operativo desde terminal → Release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (calendario y elegibilidad)
   - Developer B: User Story 2 (alcance y advertencias)
   - Developer C: User Story 6 (render y CLI, contra un `Informe` de prueba)
3. US3 arranca cuando US1 entrega `engine/calendario.py`
4. US4 arranca cuando US3 entrega cargo base y porcentaje

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Verificá que los tests fallan antes de implementar** — es un requisito constitucional, no una
  sugerencia (Principio VI)
- Una discrepancia con un caso real del IPS bloquea la publicación hasta explicarla
- Ninguna tarea escribe datos personales en logs, fixtures ni reportes (Principio III)
- Ningún valor normativo (porcentaje, edad, plazo, tope) puede quedar escrito en el código: todos
  vienen de `rules/` (Principio I, FR-007)
- Las Cuestiones abiertas #1 a #6 y #8 permanecen `NO_VERIFICADA` al cierre de estas tareas. No
  bloquean la entrega: su efecto está especificado (FR-046 a FR-046c). Resolver la #1 y la #2 es
  lo que más resultados convertiría de provisionales en definitivos.
