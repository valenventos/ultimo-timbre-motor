# Phase 0 — Research: Motor de cálculo de jubilación ordinaria docente (IPS PBA)

**Feature**: `001-motor-calculo-jubilacion`
**Fecha**: 2026-10-30
**Entrada**: [spec.md](./spec.md) · [constitution.md](../../.specify/memory/constitution.md) v1.1.0

El stack vino decidido en la invocación de `/speckit-plan`, así que este documento no elige
tecnologías base: resuelve **cómo usarlas** para que cada decisión quede atada a un principio
constitucional verificable. Cada ítem se registrará como ADR en `docs/adr/`.

---

## R1 — Aritmética decimal sin contaminación de float

**Decisión**: `Decimal` en todo el camino del dato. Pydantic v2 con
`model_config = ConfigDict(strict=True)` y campos `Decimal`. Los YAML/JSON se cargan con loaders
que entregan **str**, nunca float: `yaml.safe_load` con un resolver que desactiva la conversión
implícita a float, y `json.load(parse_float=Decimal)`. La serialización de salida usa
`json.dumps(default=str)` sobre `Decimal`.

**Por qué**: el Principio II prohíbe el punto flotante binario. El riesgo real no está en el
cálculo sino en los **bordes**: un `0.75` escrito en un YAML de reglas se convierte en float antes
de que Pydantic lo vea, y el error ya entró. Interceptarlo en el loader es el único punto donde se
puede garantizar.

**Contexto de redondeo**: la política de redondeo del IPS es `NO_VERIFICADA` (Cuestión abierta
#6). El motor expone un único `quantize()` centralizado, parametrizado desde el conjunto de
reglas, con `ROUND_HALF_UP` como valor por defecto declarado y marcado como provisional.

**Alternativas descartadas**: `float` con redondeo tardío (viola el Principio II);
`fractions.Fraction` (exacto pero sin semántica de redondeo monetario ni representación natural en
YAML).

---

## R2 — Conteo de fechas y períodos

**Decisión**: `datetime.date` de la librería estándar para representar fechas;
`dateutil.relativedelta` para aritmética de calendario (edad al cese, excedentes, aniversarios).
El cómputo de los 36 meses consecutivos / 60 alternados se resuelve sobre una
**grilla de meses calendario** discreta: cada período de servicio se proyecta a los meses que
cubre, y los algoritmos operan sobre ese conjunto, no sobre deltas de días.

**Por qué**: el Principio II prohíbe aproximaciones del tipo "un mes = 30 días". Discretizar a mes
calendario hace que el conteo sea exacto, auditable y trivialmente determinista: "60 meses
alternados" es la cardinalidad de un conjunto, y "36 consecutivos" es la racha máxima en una
secuencia ordenada. Además permite exponer en el desglose **qué meses concretos** sustentan el
cargo base, que es lo que exige FR-020.

**Pendiente normativo**: qué meses aporta un período con licencia, suplencia o interinato es la
Cuestión abierta #5 (ampliada con la situación de revista). El proyector mes-a-mes recibe esa
regla como dato; mientras sea `NO_VERIFICADA`, el resultado se marca provisional (FR-024,
FR-024a).

**Alternativas descartadas**: aritmética de días con conversión a meses (inexacta y no auditable);
`pandas` con periodos (dependencia pesada e innecesaria para un motor sin dataframes).

---

## R3 — Reglas, catálogo de cargos y grillas como datos YAML validados

**Decisión**: tres familias de archivos YAML versionados en el repo del motor, cada una con su
JSON Schema en `schemas/`:

| Familia | Ruta | Schema | Contenido |
|---|---|---|---|
| Reglas del régimen | `rules/<version>/*.yaml` | `schemas/rule.schema.json` | norma, vigencia desde/hasta, fecha de verificación, estado, tipo |
| Catálogo de cargos | `rules/<version>/cargos.yaml` | `schemas/cargo.schema.json` | cargo, jerarquía, condición al frente de alumnos, norma que la sostiene, estado |
| Grillas salariales | `grids/<version>.yaml` | `schemas/grid.schema.json` | norma de origen, enlace, vigencia, fecha de extracción, aprobador, valores por cargo |

Validación en CI con `check-jsonschema`. Los montos y porcentajes se escriben **siempre entre
comillas** en el YAML para que lleguen como `str` al loader (ver R1); el schema lo fuerza con
`"type": "string"` y `pattern` numérico, de modo que un valor sin comillas falla en CI, no en
producción.

**Por qué**: el Principio I exige que ninguna regla viva en el código y que cada una declare su
norma. El Principio IX exige que las grillas tengan procedencia y aprobador. El schema convierte
ambos mandatos en un gate automático.

**Alternativas descartadas**: TOML (sin schema estándar maduro); reglas en Python (viola el
Principio I); base de datos (viola la restricción de "sin base de datos" y el Principio V).

---

## R4 — Aprobación de grillas por pull request

**Decisión**: la aprobación es **el merge del PR**, y se hace verificable así:

1. `CODEOWNERS` cubre `grids/**` y `rules/**`, exigiendo revisión humana obligatoria.
2. Cada archivo de grilla declara en su cuerpo `aprobada_por` y `aprobada_en`.
3. Un check de CI (`validate-grid-approval`) falla si un PR que toca `grids/**` deja esos campos
   vacíos, y verifica que `aprobada_por` coincida con quien aprobó el PR.
4. El motor **solo carga grillas presentes en `grids/`**: no existe mecanismo para inyectar una
   grilla en tiempo de ejecución.

**Por qué**: el Principio IX dice que ninguna grilla no aprobada puede usarse. Un campo booleano
`aprobada: true` dentro del archivo sería autodeclarado y falsificable por quien edita el archivo;
atarlo al control de versiones lo hace auditable por un tercero sin confiar en el contenido.

**Consecuencia para el motor**: no hay estado "pendiente" en tiempo de ejecución. Si la grilla
vigente a la fecha de cese no está en el repo, se aplica FR-034 (advertir, indicar con qué grilla
se calculó, marcar provisional).

---

## R5 — Formato del informe y estado legible por máquina

**Decisión**: dos salidas desde **un único modelo Pydantic** `Informe`:

- **JSON estructurado** (contrato estable, versionado con `schema_version`), con
  `estado_general: "definitivo" | "provisional"` en la raíz.
- **Texto para terminal**, renderizado desde el mismo modelo, sin lógica de cálculo propia.

El monto nunca es un escalar suelto: se modela como un objeto `Monto { valor, moneda, estado,
reglas_condicionantes[] }`. Esto implementa FR-046a a nivel de tipo — no existe una representación
del monto sin su marca, así que ninguna vía de salida puede perderla por olvido.

**Por qué**: FR-046a exige que la marca sea inseparable del monto "en toda vía de salida". Un
`Decimal` desnudo más un flag aparte depende de que cada serializador recuerde incluir el flag;
embeber el estado en el tipo lo hace estructuralmente imposible de omitir. Es la diferencia entre
una convención y una garantía.

**Determinismo de la salida**: `json.dumps(..., sort_keys=True, ensure_ascii=False)` y orden
explícito en toda colección (escenarios por fecha, advertencias por código). Sin timestamps de
corrida dentro del informe comparable; si se incluye uno, va en un sobre externo excluido de la
comparación byte a byte de SC-003.

**Alternativas descartadas**: JSON como fuente y texto parseado de él (frágil); dos modelos
paralelos (riesgo de divergencia).

---

## R6 — CLI y códigos de salida

**Decisión**: Typer con códigos de salida explícitos:

| Código | Significado | Origen |
|---|---|---|
| 0 | Éxito (incluye resultado provisional) | — |
| 2 | Entrada inválida (schema, coherencia temporal) | FR-003, FR-057 |
| 3 | Caso fuera de alcance v1 | FR-044, FR-045, FR-020b |
| 4 | Error interno | excepción no prevista |

**Por qué**: FR-056 pide códigos distinguibles. El 1 se deja libre deliberadamente: Typer y Python
lo usan para errores no controlados, y reservarlo evita que un fallo del runtime se confunda con
un caso fuera de alcance. Un resultado provisional sale con **0**, porque es un resultado válido
del motor (decisión Q3) — lo que lo distingue es `estado_general`, no el exit code.

---

## R7 — Interfaz pública de librería

**Decisión**: superficie mínima y explícita en `ultimo_timbre/__init__.py`, con `__all__`,
`py.typed` (PEP 561) y todos los tipos públicos exportados. Punto de entrada único:

```
calcular(caso: Caso, *, reglas: VersionReglas, grilla: VersionGrilla) -> Informe
```

Sin I/O, sin red, sin lectura de disco: los cargadores de reglas y grillas son funciones
separadas que el llamador invoca antes. El motor recibe datos ya cargados.

**Por qué**: el Principio V exige que el motor no dependa de la app web ni de nada propietario, y
que corra igual como librería y por CLI. Si `calcular()` no hace I/O, la equivalencia entre ambas
vías (FR-051) es estructural: la CLI es solo un cargador más un renderizador.

---

## R8 — Estrategia de pruebas

**Decisión**: cuatro capas, todas con los tests escritos antes (Principio VI):

| Capa | Herramienta | Qué prueba | Ubicación |
|---|---|---|---|
| Casos dorados | pytest + fixtures YAML | Casos reales del IPS anonimizados, valuados con la **grilla histórica de su fecha de cese real** (SC-002) | `tests/golden/` |
| Propiedades | hypothesis | Orden de carga irrelevante (SC-010, FR-049), tope de porcentaje nunca superado (FR-028), determinismo (SC-003, FR-048), monotonía: más servicios nunca reduce el resultado | `tests/properties/` |
| Contrato | pytest + jsonschema | Informe valida contra su schema; archivo de caso valida contra el suyo | `tests/contract/` |
| Unitarias | pytest | Conteo de meses, elección de cargo base, derivación de condición al frente de alumnos | `tests/unit/` |

**Cobertura**: `pytest-cov` con `--cov-branch`, umbral **95 % en `ultimo_timbre/engine` y
`ultimo_timbre/rules`**, 80 % en el resto, configurado por paquete para que el umbral del motor no
se diluya con el de la CLI.

**Estrategias de hypothesis**: generadores de historias de servicios válidas (períodos no
superpuestos, fechas coherentes) construidos con `st.builds` sobre los modelos Pydantic, más un
generador de permutaciones para la propiedad de orden.

**Por qué**: el Principio VI exige casos dorados con fundamento normativo y property-based para
invariantes. La separación por capas permite que la US1 se complete con `unit` + `golden` sin
necesitar grilla, respetando la independencia de historias.

---

## R9 — Calidad estática y mypy strict con Pydantic v2

**Decisión**: `ruff` (lint + format) y `mypy --strict` con el plugin `pydantic.mypy` habilitado en
`pyproject.toml`. `disallow_any_explicit` activado en `ultimo_timbre/engine`.

**Por qué**: sin el plugin, mypy strict no entiende los validadores ni los campos generados de
Pydantic v2 y produce falsos positivos que terminan en `# type: ignore` masivos — que es
exactamente lo que hace inútil el modo strict. El plugin es lo que vuelve sostenible la
combinación.

---

## R10 — Licencia AGPL y encabezados SPDX

**Decisión**: `LICENSE` con AGPL-3.0-or-later, `SPDX-License-Identifier: AGPL-3.0-or-later` como
primera línea de cada archivo fuente, y verificación en CI con la herramienta `reuse` (REUSE 3.0).
`pyproject.toml` declara `license = "AGPL-3.0-or-later"`.

**Por qué**: el Principio V fija la licencia. Verificarlo en CI evita que archivos nuevos entren
sin encabezado, que es como se erosiona el cumplimiento con el tiempo.

---

## R11 — Pipeline de CI

**Decisión**: GitHub Actions, matriz `ubuntu-latest / macos-latest / windows-latest` × Python
3.12, con `uv` para instalación reproducible. Jobs:

| Job | Herramienta | Gate |
|---|---|---|
| tests | pytest + pytest-cov | 95 % ramas motor, 80 % resto |
| schemas | check-jsonschema | reglas, cargos, grillas y casos de ejemplo validan |
| aprobación de grillas | script propio | `aprobada_por` / `aprobada_en` presentes y consistentes (R4) |
| lint/tipos | ruff, mypy --strict | sin hallazgos |
| SAST | bandit | sin hallazgos alto/crítico |
| dependencias | pip-audit | sin vulnerabilidades alto/crítico |
| secretos | gitleaks | sin hallazgos |
| licencia | reuse lint | todos los archivos con SPDX |
| SBOM | cyclonedx-py | genera `sbom.cdx.json` como artifact |

**Por qué**: el Principio VII exige SAST, escaneo de dependencias, detección de secretos y SBOM, y
que un hallazgo alto o crítico bloquee el despliegue. La matriz multiplataforma cubre el requisito
de compatibilidad Windows/macOS/Linux y, de paso, detecta dependencias accidentales del separador
de rutas o de la zona horaria local.

**Determinismo multiplataforma**: un test dedicado compara el informe JSON producido en los tres
sistemas operativos contra el mismo caso, para que SC-003 y SC-007 se verifiquen de verdad y no
por confianza.

---

## R12 — Privacidad operativa: logs sin datos personales

**Decisión**: el motor **no emite logs** por sí mismo. Expone eventos de diagnóstico estructurados
con identificadores técnicos anónimos (`periodo_idx`, `regla_id`, `codigo_advertencia`) y nunca
valores de dominio. La CLI configura el logging; la librería solo usa `logging.NullHandler()`.
Un test de CI corre un caso con datos marcados y falla si alguno aparece en la salida de
diagnóstico (SC-008).

**Por qué**: el Principio III prohíbe datos personales en logs, métricas y trazas. Dejar que la
librería loguee libremente delega el cumplimiento en cada `logger.debug()` que alguien escriba; no
loguear desde la librería lo hace cumplible por construcción. El test con datos marcados
("canarios") es lo que lo convierte en verificable y no en una promesa.

---

## Unknowns pendientes

Ninguno de tipo técnico: el stack vino especificado y las decisiones de arquitectura se resuelven
arriba.

**Los pendientes son de dominio, no de ingeniería** — las Cuestiones abiertas #1 a #8 de la
constitución. No bloquean el diseño: el motor las trata como datos (`estado: NO_VERIFICADA`) y su
efecto está especificado (FR-046 a FR-046c). Sí determinan cuántos resultados de la v1 salen
provisionales:

| Cuestión | Afecta | Efecto si no se resuelve |
|---|---|---|
| #8 Alcance Ley 13469 | Elegibilidad y porcentaje | Mayor impacto: decide inciso b (75 %) vs c/d (70 %) |
| #2 Remuneración del cargo | Monto | Todo haber sale provisional |
| #1 Tope de antigüedad | Monto y escenarios futuros | Todo escenario futuro sale provisional |
| #4 Criterio de jerarquía | Cargo base | Elección de cargo base provisional |
| #5 Licencias y revista | Cargo base y años de servicio | Conteo de meses provisional |
| #3 Horas cátedra | Cargo base | Casos con horas cátedra provisionales |
| #6 Redondeo | Monto | Último decimal no garantizado |
