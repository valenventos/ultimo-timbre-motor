# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: debe pasar antes de la Fase 0 (research). Se vuelve a verificar después de la Fase 1 (design).*

Marcá cada principio como PASA / NO APLICA / VIOLACIÓN. Toda VIOLACIÓN debe justificarse en
*Complexity Tracking* o el plan se rechaza. Referencia: `.specify/memory/constitution.md` v1.0.0.

| # | Principio | Qué verificar en este plan | Estado |
|---|---|---|---|
| I | Toda regla tiene fuente normativa | Cada regla de cálculo que introduce el plan cita ley/artículo/inciso (o resolución IPS/decreto) y vive como dato versionado, no hardcodeada. Las reglas sin fuente verificable quedan `NO_VERIFICADA`. | [PASA/NO APLICA/VIOLACIÓN] |
| II | Cálculo determinístico y exacto | Aritmética `Decimal` (nunca float binario), redondeo en un único lugar documentado, fechas con librería probada, sin LLM ni componentes probabilísticos en extracción ni cálculo. | [ ] |
| III | Privacidad por diseño: no guardamos casos | PDFs solo en memoria y descartados al terminar; cero persistencia de datos de casos; logs/métricas/trazas sin datos personales (CUIL, nombres, montos, cargos, fechas). | [ ] |
| IV | Transparencia total del resultado | El plan preserva escenarios, desglose paso a paso, procedencia de cada dato, versión de reglas y de grilla, advertencias y el aviso de estimación orientativa. | [ ] |
| V | Motor abierto, separado e independiente | El motor y las reglas no dependen de la web, la BD de organizaciones ni la facturación; interfaz pública tipada; ejecutable localmente sin red con idéntico resultado. | [ ] |
| VI | Test-first con casos reales | Las tareas de test preceden a las de implementación; casos dorados con fundamento normativo; fixtures de recibos anonimizados; property-based para invariantes; cobertura de ramas ≥95 % motor/parser, ≥80 % resto. | [ ] |
| VII | Seguridad como requisito | OWASP ASVS L2; archivos subidos tratados como hostiles (tipo real, tamaño, páginas, rechazo de PDF cifrado/JS/formularios/embebidos, límites de tiempo y memoria, parseo aislado); CI con SAST, dependencias, secretos y SBOM. | [ ] |
| VIII | Pensado para docentes | Diseño propio (no plantillas genéricas), mobile-first, WCAG 2.2 AA, español rioplatense claro con términos explicados, estado del flujo siempre visible, ningún error sin acción posible. | [ ] |
| IX | Grillas con revisión humana | Ninguna grilla se usa sin aprobación humana vía PR; cada versión registra norma, enlace, vigencia, extracción, aprobador y diffs; el informe advierte si la grilla vigente no está cargada. | [ ] |
| X | Simplicidad y alcance acotado | Solo lo que la v1 necesita; entre diseños equivalentes gana el más simple; lo fuera de alcance se detecta y se informa, no se aproxima. | [ ] |

**Alcance v1**: confirmá que la funcionalidad cae dentro del *Alcance de la v1*. Si toca algo
listado como fuera de alcance (simultaneidad calculada, otras cajas, privados, invalidez, OCR,
docentes individuales), el plan debe detectarlo e informarlo, nunca calcularlo aproximadamente.

**Cuestiones abiertas del dominio**: listá cuáles de las 7 cuestiones abiertas afectan a esta
funcionalidad y cómo se resuelven (fuente verificable) o se difieren (regla `NO_VERIFICADA`).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Completar SOLO si el Constitution Check tiene VIOLACIONES que deban justificarse.**
> Una violación sin justificación escrita y aceptada rechaza el plan (Principio X).

| Principio violado | Violación | Por qué es necesaria | Alternativa más simple rechazada porque |
|---|---|---|---|
| [p. ej. X] | [p. ej. 4º proyecto] | [necesidad concreta] | [por qué 3 proyectos no alcanzan] |
| [p. ej. II] | [p. ej. patrón Repository] | [problema específico] | [por qué el acceso directo no alcanza] |
