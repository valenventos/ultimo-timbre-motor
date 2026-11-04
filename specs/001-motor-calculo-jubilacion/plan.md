# Implementation Plan: Motor de cálculo de jubilación ordinaria docente (IPS PBA)

**Branch**: `001-motor-calculo-jubilacion` | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-motor-calculo-jubilacion/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Motor de cálculo de la jubilación ordinaria docente del IPS de la Provincia de Buenos Aires,
entregado como paquete Python independiente usable como librería y desde la línea de comandos.
Determina elegibilidad por los incisos b, c y d del art. 24 del DL 9650/80, el cargo base del
art. 41, el porcentaje de los arts. 41 a 43 y el haber estimado con grillas aprobadas, emitiendo
un informe auditable que cita la norma de cada regla.

Enfoque técnico: reglas, catálogo de cargos y grillas viven como **datos YAML versionados**
validados por JSON Schema en CI, nunca en el código. El cálculo es determinístico sobre `Decimal`
y conjuntos de meses calendario, computando siempre sobre la **unión** de tramos y nunca sobre la
suma de duraciones. El motor no consulta el reloj: la fecha de cálculo entra en el caso. El monto
se modela como un tipo que lleva su estado (`definitivo`/`provisional`) y sus **condicionantes**
incorporados, de modo que ninguna vía de salida pueda entregarlo sin ellos. Un caso fuera de
alcance no aborta: devuelve el análisis parcial sostenible, sin haber, con advertencias
bloqueantes. Decisiones de diseño en [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Pydantic v2 (modelos, validación), python-dateutil (aritmética de
calendario), PyYAML (carga de datos normativos), Typer (CLI). Gestión con `uv`.

**Storage**: Ninguna base de datos. Datos normativos en archivos YAML versionados en el repo
(`rules/`, `grids/`), validados con JSON Schema. Cero persistencia de casos (Principio III).

**Testing**: pytest, hypothesis (propiedades), pytest-cov (cobertura de ramas), jsonschema
(contratos).

**Target Platform**: Windows, macOS y Linux. Sin red en ninguna ruta de ejecución.

**Project Type**: Librería Python + CLI. Paquete independiente, sin dependencia de la app web ni
de componentes propietarios (Principio V).

**Performance Goals**: Informe completo de un caso de 30 años de historia con 5 escenarios en
menos de 5 segundos en una computadora de escritorio común (SC-006).

**Constraints**: Aritmética exclusivamente `Decimal`; sin punto flotante binario en ningún borde.
Sin LLM ni componentes probabilísticos. Sin datos personales en logs, métricas ni trazas.
AGPL-3.0-or-later con encabezado SPDX en cada archivo.

**Scale/Scope**: Un caso por corrida, sin concurrencia. 82 requisitos funcionales, 6 historias
de usuario, 19 entidades de dominio, 9 invariantes verificables por property test.

## Constitution Check

*GATE: debe pasar antes de la Fase 0 (research). Se vuelve a verificar después de la Fase 1 (design).*

Marcá cada principio como PASA / NO APLICA / VIOLACIÓN. Toda VIOLACIÓN debe justificarse en
*Complexity Tracking* o el plan se rechaza. Referencia: `.specify/memory/constitution.md` v1.1.0.

| # | Principio | Qué verificar en este plan | Estado |
|---|---|---|---|
| I | Toda regla tiene fuente normativa | Reglas, catálogo de cargos y grillas son YAML versionados con `norma`, `vigencia`, `verificada_en` y `estado`, validados por JSON Schema en CI (R3). El schema exige `impacto_si_no_verificada` en toda regla `NO_VERIFICADA`. Ningún valor normativo en el código (FR-007). | **PASA** |
| II | Cálculo determinístico y exacto | `Decimal` de punta a punta, con loaders que entregan `str` para que ningún float entre por el borde (R1). Conjuntos de meses calendario en lugar de deltas de días, con cómputo sobre la unión de tramos (R2, I9). `quantize()` centralizado. **La fecha de cálculo es entrada, no ambiente**: no hay `date.today()` en `engine/` ni `rules/`, verificado por AST (R13). Sin LLM. Modelos `frozen=True`. | **PASA** |
| III | Privacidad por diseño: no guardamos casos | Sin base de datos ni persistencia. `calcular()` no hace I/O. La librería no loguea (`NullHandler`); la CLI configura el logging. Diagnóstico con identificadores anónimos (`periodo_idx`, `regla_id`, `codigo`) y test de canarios (R12). | **PASA** |
| IV | Transparencia total del resultado | `Informe` lleva desglose paso a paso con `norma` y `tipo_fuente` por paso, procedencia por dato, fecha de cálculo, versión de reglas y grilla, advertencias, aviso de estimación y aviso de movilidad del art. 50. Un caso fuera de alcance recibe igualmente el análisis parcial sostenible (FR-045a), que es lo que este principio prefiere frente a una negativa total. El valor del cargo se descompone en componentes, de modo que el desglose pueda mostrar sobre qué base se aplicó la antigüedad (FR-031a). | **PASA** |
| V | Motor abierto, separado e independiente | Paquete autónomo AGPL-3.0-or-later con SPDX por archivo, verificado con `reuse` en CI. Sin dependencia de web, BD de organizaciones ni facturación. `calcular()` sin I/O hace estructural la equivalencia CLI/librería (R7). Corre sin red (test con sockets bloqueados). | **PASA** |
| VI | Test-first con casos reales | Cuatro capas de prueba, todas escritas antes (R8): casos dorados con fundamento normativo, propiedades con hypothesis para los 9 invariantes (incluido I9: cómputo sobre la unión de tramos), contrato contra los schemas, unitarias. Cobertura de ramas ≥95 % en `engine` y `rules`, ≥80 % resto, con umbral por paquete. Fixtures anonimizados. | **PASA** |
| VII | Seguridad como requisito | CI con bandit (SAST), pip-audit (dependencias), gitleaks (secretos) y cyclonedx-py (SBOM); hallazgo alto/crítico bloquea (R11). *Nota*: la cláusula de archivos subidos hostiles no aplica — esta funcionalidad no acepta PDF ni carga de archivos binarios (FR-005). | **PASA** (parcialmente NO APLICA) |
| VIII | Pensado para docentes | Alcance reducido: esta funcionalidad no tiene interfaz visual, así que diseño propio, mobile-first y WCAG 2.2 AA **no aplican**. Sí aplica el lenguaje claro en español rioplatense y que ningún error deje al usuario sin acción posible: los mensajes de CLI nombran campo y período y describen la corrección (FR-057). | **PASA** (parcialmente NO APLICA) |
| IX | Grillas con revisión humana | Aprobación atada al merge del PR, no a un campo autodeclarado: campos `aprobada_por`/`aprobada_en` y check de CI que los verifica (R4). Con **un solo mantenedor**, el check valida contra quien **fusiona** el PR; la exigencia de un aprobador distinto del autor vía CODEOWNERS se activa con el segundo mantenedor, y el ADR registra ese disparador. El motor solo carga grillas presentes en el repo; no hay inyección en runtime. | **PASA** |
| X | Simplicidad y alcance acotado | Sin base de datos, sin red, sin servicios. Una sola función de cálculo. Lo fuera de alcance se **detecta y se informa sin calcular**: el informe sale con advertencias `bloquea_calculo` y sin haber, y la CLI traduce eso a exit 3 (FR-045a, FR-045b). La excepción `FueraDeAlcance` queda reservada para errores de programación —que una ruta interna valúe un tramo fuera de alcance es un bug, no un caso de usuario—, de modo que el flujo igual no puede producir un número por accidente (invariante I7). | **PASA** |

**Alcance v1**: confirmá que la funcionalidad cae dentro del *Alcance de la v1*. Si toca algo
listado como fuera de alcance (simultaneidad calculada, otras cajas, privados, invalidez, OCR,
docentes individuales), el plan debe detectarlo e informarlo, nunca calcularlo aproximadamente.

> **Confirmado.** La funcionalidad está dentro del alcance. Los cinco casos fuera de alcance que
> toca se detectan e informan sin calcular: simultaneidad (FR-043, advertencia sin incremento),
> otras cajas (FR-044, exit 3), establecimientos privados (FR-045, exit 3), servicios no docentes
> del IPS (FR-015, se advierte el prorrateo posible sin computarlo) y el promedio de 36 meses del
> tercer párrafo del art. 41 (FR-020b, exit 3). El motor **no lee PDF** (FR-005), así que OCR y
> formatos de recibo quedan fuera por construcción.

**Cuestiones abiertas del dominio**: listá cuáles de las 7 cuestiones abiertas afectan a esta
funcionalidad y cómo se resuelven (fuente verificable) o se difieren (regla `NO_VERIFICADA`).

> La constitución v1.1.0 enumera **8** cuestiones abiertas (la #8 se incorporó en esa enmienda).
> Siete afectan a esta funcionalidad; la #7 (formatos de recibo) no, porque el motor no lee
> recibos. Las siete se **difieren**, no se resuelven: viven como reglas `NO_VERIFICADA` en los
> YAML, con `impacto_si_no_verificada` obligatorio, y su efecto sobre el resultado está
> especificado (FR-046 a FR-046c). Ver la tabla de impacto en [research.md](./research.md).
>
> La de mayor peso es la **#8** (alcance de la Ley 13469): no mueve el monto al margen, decide si
> el acceso es por el inciso b (art. 43, 75 % base) o por los incisos c/d (art. 41, 70 % base).
> Resolver la #1 y la #2 es lo que más resultados convertiría de provisionales en definitivos.

## Project Structure

### Documentation (this feature)

```text
specs/001-motor-calculo-jubilacion/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── README.md
│   ├── caso.schema.json
│   ├── informe.schema.json
│   ├── cli.md
│   └── library-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/ultimo_timbre/
├── __init__.py          # superficie pública: __all__, py.typed
├── models/              # Pydantic v2, frozen, strict
│   ├── enums.py         # SituacionRevista, CajaAportes, CodigoAdvertencia, ...
│   ├── caso.py          # Caso, HistoriaDeServicios, PeriodoDeServicio, Licencia
│   ├── normativa.py     # Regla, Norma, ConjuntoDeReglas, CatalogoDeCargos
│   ├── grilla.py        # GrillaSalarial, ValorCargo
│   └── informe.py       # Informe, Monto, Escenario, Advertencia, PasoDelDesglose
├── rules/               # carga y validación de datos normativos (≥95 % cobertura)
│   ├── loader.py        # loaders que entregan str, nunca float (R1)
│   ├── catalogo.py      # derivación de "al frente de alumnos" (FR-002a)
│   └── versiones.py
├── engine/              # cálculo puro, sin I/O ni reloj (≥95 % cobertura)
│   ├── calendario.py    # unión de tramos, meses, 36 consecutivos / 60 alternados (R2, I9)
│   ├── elegibilidad.py  # art. 24 incs. b, c, d + mínimo 22 años
│   ├── cargo_base.py    # art. 41, incluido descenso al cargo inferior (FR-020a)
│   ├── porcentaje.py    # arts. 41-43 + excedente según Res. 995/2021 (FR-027a)
│   ├── haber.py         # valuación por componentes, antigüedad sobre bonificables, quantize
│   ├── escenarios.py    # habilitación, excedentes 3 y 5 años
│   ├── alcance.py       # detección de situaciones fuera de alcance (FR-043 a FR-045b, FR-020b)
│   ├── advertencias.py  # emisión de advertencias con norma y bloquea_calculo (FR-041)
│   ├── condicionantes.py # condicionantes de regla y de situación del caso (FR-046a/b)
│   └── desglose.py      # trazado de pasos con norma
├── render/
│   ├── json_out.py      # determinista: sort_keys, Decimal como str
│   └── texto.py         # salida legible en terminal
├── cli/
│   └── main.py          # Typer: calcular, validar, versiones
└── errors.py            # UltimoTimbreError, CasoInvalido, FueraDeAlcance

rules/<version>/         # datos normativos versionados (YAML)
grids/<version>.yaml     # grillas salariales aprobadas (YAML)
schemas/                 # JSON Schema de rules, cargos y grids
examples/                # casos de ejemplo para quickstart
docs/adr/                # un ADR por decisión técnica (R1-R12)

tests/
├── golden/              # casos reales del IPS, anonimizados, con grilla histórica
├── properties/          # hypothesis: invariantes I1-I8
├── contract/            # validación contra caso.schema.json e informe.schema.json
└── unit/
```

**Structure Decision**: Opción 1 (proyecto único), con `src/` layout. La separación entre
`engine/` (puro, sin I/O ni reloj) y `rules/`+`cli/` (que sí tocan disco) es lo que hace
verificable el Principio V: la cobertura del 95 % se exige sobre `engine/` y `rules/`, y los tests
de "sin I/O" y "sin reloj" apuntan por ruta de paquete. `render/` existe separado para que las dos
salidas —JSON y texto— rendericen el mismo modelo sin que ninguna pueda recalcular (R5).

**Re-verificación post-diseño (Fase 1)**: el Constitution Check se volvió a correr después de
incorporar las correcciones de dominio (unión de tramos, períodos en curso, fecha de cálculo como
entrada, grilla por componentes, condicionantes generalizados, informe parcial para casos fuera de
alcance y política de aprobación escalonada). **Los diez principios siguen pasando y no
aparecieron violaciones nuevas.** Tres cambios *reforzaron* el cumplimiento: la fecha de cálculo
como dato (II), el cómputo sobre la unión (II), y el informe parcial en lugar de la excepción
(IV).

## Complexity Tracking

> **Completar SOLO si el Constitution Check tiene VIOLACIONES que deban justificarse.**
> Una violación sin justificación escrita y aceptada rechaza el plan (Principio X).

Sin violaciones. Los diez principios pasan; los principios VII y VIII pasan con cláusulas que
**no aplican** a esta funcionalidad (validación de archivos subidos hostiles, y diseño visual /
accesibilidad), por razones de alcance y no por desvío: el motor no acepta archivos binarios ni
tiene interfaz gráfica. Ambas cláusulas vuelven a ser exigibles cuando se construya la aplicación
web.
