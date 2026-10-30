# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?
- ¿Qué pasa cuando el caso cae **fuera del Alcance de la v1** (simultaneidad a calcular, otras
  cajas, establecimientos privados, invalidez, recibos escaneados)? El sistema lo **detecta y lo
  informa**; nunca lo aproxima (Principio X).
- ¿Qué pasa cuando falta un dato o un período no está cubierto por los recibos? El resultado
  parcial se explica con su advertencia (Principio IV).

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.

  PRINCIPIO I (obligatorio): todo requisito que describa una regla de CÁLCULO
  (requisitos de acceso, porcentajes, plazos mínimos, topes, escalas, conteo de
  períodos, redondeo, valuación de cargos) DEBE citar su fuente normativa exacta
  en el propio requisito: ley/decreto-ley, artículo, inciso y, si corresponde,
  resolución del IPS o decreto. Formato: `[DL 9650/80, art. 41]`.
  Un requisito de cálculo sin cita normativa es un requisito incompleto y la
  especificación no pasa `/speckit-analyze`.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

*Ejemplo de requisito de cálculo con cita normativa (Principio I):*

- **FR-008**: El sistema DEBE aplicar un haber base del 70 % de la remuneración del cargo de mayor
  jerarquía desempeñado durante 36 meses consecutivos o 60 alternados
  `[DL 9650/80, art. 41 (texto Ley 13968); Res. IPS 14/10]`.
- **FR-009**: El sistema DEBE elevar el porcentaje al 75 % y 80 % por excedente de edad de 3 y 5
  años respectivamente `[DL 9650/80, art. 42]`.
- **FR-010**: El sistema DEBE marcar como `NO_VERIFICADA` y NO calcular la bonificación por
  antigüedad hasta confirmar el tope vigente `[Ley 10579 art. 33; Decreto 818/13 — NO_VERIFICADA:
  tope 120 % vs 125 %, ver Cuestiones abiertas del dominio #1]`.

### Fundamento normativo *(obligatorio si la funcionalidad calcula algo)*

<!--
  Una fila por cada norma que esta funcionalidad aplica. Sin esta tabla completa,
  una especificación de cálculo no puede pasar a /speckit-plan (Principio I).
  Estado: Verificado | NO_VERIFICADA | Fuera de alcance v1.
  Las interpretaciones (criterio IPS, jurisprudencia, práctica administrativa) van
  en la columna Tipo como "Interpretación", nunca mezcladas con la letra de la ley.
-->

| Requisito | Norma (ley, art., inc. / resolución) | Tipo | Estado | Verificada el |
|---|---|---|---|---|
| FR-00X | [DL 9650/80, art. XX inc. Y] | Letra de la ley / Interpretación | Verificado / NO_VERIFICADA | YYYY-MM-DD |

**Reglas `NO_VERIFICADA` en esta funcionalidad**: [listar, o "ninguna"]. Para cada una, indicar qué
informa el sistema en lugar de un resultado definitivo (Principio I).

**Cuestiones abiertas del dominio que afectan a esta especificación**: [listar por número, o
"ninguna"].

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]
