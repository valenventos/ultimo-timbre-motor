# Specification Quality Checklist: Motor de cálculo de jubilación ordinaria docente (IPS PBA)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-30
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Constitution Compliance (Principio I)

- [x] Todo requisito de cálculo cita su norma exacta (ley, artículo, inciso / resolución)
- [x] Sección **Fundamento normativo** completa, con tipo y estado por norma
- [x] Letra de la ley distinguida de interpretación
- [x] Reglas `NO_VERIFICADA` listadas, con el comportamiento del motor para cada una
- [x] Cuestiones abiertas del dominio que afectan a la spec, identificadas por número
- [x] Casos fuera de alcance: se detectan e informan, nunca se aproximan (Principio X)

## Validation Log

**Iteración 1 (2026-10-30)** — 16/17 ítems pasan.

Falla únicamente "No [NEEDS CLARIFICATION] markers remain": quedan 3 marcadores, todos de impacto
en alcance y sin default defendible (grilla para escenarios futuros; servicios no docentes del
IPS; comportamiento ante reglas `NO_VERIFICADA` que afectan el monto). Presentados al usuario
como Q1, Q2 y Q3.

**Iteración 2 (2026-10-30)** — 17/17 ítems pasan. ✅

Las tres preguntas fueron respondidas y quedaron registradas en la sección *Clarifications* de la
spec, con su decisión, su razón y su impacto:

- **Q1 → A + agregados**: escenarios futuros valuados con la última grilla aprobada, a valores de
  hoy, con la antigüedad proyectada a la fecha del escenario; se informa la movilidad del
  art. 50. Nuevos FR-030a, FR-030b, FR-030c, FR-036a.
- **Q2 → C + agregado**: servicios no docentes del IPS se detectan y se advierten sin computar;
  si los docentes no alcanzan y existen no docentes, la advertencia nombra el prorrateo del
  art. 27 como vía posible y la elegibilidad queda no definitiva. FR-015 reescrito, nuevo
  FR-015a.
- **Q3 → A + tres resguardos**: monto provisional admitido, con la marca inseparable del monto en
  toda salida, el sentido del impacto de cada regla `NO_VERIFICADA`, y un estado general legible
  por máquina. FR-046 reescrito, nuevos FR-046a, FR-046b, FR-046c; nuevos SC-011 a SC-013.

Totales: 6 historias, 65 requisitos funcionales, 13 criterios de éxito, 14 entidades, 18 filas en
Fundamento normativo.

**Iteración 3 (2026-10-30)** — 17/17 ítems pasan. ✅

Correcciones de dominio aportadas por el usuario, sin tocar las decisiones de *Clarifications*:

1. **Excedente de 3/5 años** — se adopta como criterio por defecto contarlo desde que se cumplen
   **todas** las condiciones del inciso (edad y servicios), registrado como *Interpretación* con
   fuente `Res. IPS 995/2021, Anexo, punto 2.1.a`. El informe advierte la lectura literal de los
   arts. 42 y 43 (excedente medido solo por edad) con impacto **al alza**. Nuevos FR-027a y
   FR-027b; US3 escenarios 5 y 6 (incluido el caso 25 años de servicio a los 54: 75 % al
   habilitarse, 80 % tres años después); US5 escenario 1 ajustado.
2. **Al frente de alumnos** — deja de ser dato libre: se deriva del cargo mediante un catálogo
   versionado con norma por cargo (Leyes 13469, 10745 y 11860), corregible por el usuario con
   marca de dato manual. Nuevos FR-002a, FR-002b, FR-002c; FR-011 y FR-012 ajustados; nueva
   entidad *Catálogo de cargos versionado*.
3. **Art. 41** — nuevo FR-020a (si el cargo de mayor jerarquía no alcanza 36/60, se considera
   comprendido en el inferior y el haber se regula por este) y FR-020b (promedio de 36 meses del
   tercer párrafo: se detecta y se informa como fuera de alcance v1). US3 escenarios 3 y 4.
4. **Cuestión abierta #5 ampliada** — nuevo FR-024a: si la situación de revista condiciona la
   elección del cargo base, dado que el art. 41 habla del cargo "de que era titular".
5. **SC-002** — los casos dorados se valúan con la grilla histórica vigente a la fecha del cese
   real de cada caso, no con la última aprobada.

Totales finales: 6 historias, **73 requisitos funcionales**, 13 criterios de éxito, 15 entidades,
**28 filas** en Fundamento normativo. Escenarios de la US3 renumerados a 1–9.

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`
- Las reglas `NO_VERIFICADA` NO son marcadores de especificación incompleta: son una decisión
  constitucional deliberada (Principio I). La spec está completa respecto de ellas porque define
  exactamente qué hace el motor cuando intervienen (FR-046 a FR-046c).
- Dependencia conocida para `/speckit-plan`: las Cuestiones abiertas del dominio #1 a #6 siguen
  sin resolverse. No bloquean la planificación, pero sí determinan cuántos resultados de la v1
  salen marcados como provisionales. Conviene atacar la #1 (tope de antigüedad) y la #2
  (conceptos que integran la remuneración) antes de implementar la US4, porque son las dos que
  más montos condicionan.
- **Pendiente de gobernanza**: la constitución v1.0.0 enumera 7 cuestiones abiertas. Esta spec
  introduce la **#8** (alcance de la Ley 13469 a otros cargos del escalafón, impacto 70 % vs
  75 %) y **amplía la #5** (incidencia de la situación de revista en el cargo base). Ambas están
  registradas en la spec con su nota de gobernanza, pero formalizarlas en la constitución
  requiere una enmienda **MINOR** vía `/speckit-constitution`. No bloquea `/speckit-plan`.
- La #8 es, de las cuestiones abiertas, la de mayor impacto sobre la elegibilidad: no mueve el
  monto al margen, decide si el acceso es por el inciso b (art. 43, 75 % base) o por los incisos
  c/d (art. 41, 70 % base).
