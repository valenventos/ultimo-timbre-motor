# Contratos — Motor de cálculo de jubilación ordinaria docente (IPS PBA)

**Feature**: `001-motor-calculo-jubilacion` · **Fecha**: 2026-10-30

El motor expone **cuatro** interfaces públicas. Las cuatro son contratos estables, versionados con
semver propio, y las cuatro tienen tests de contrato antes que implementación (Principio VI).

| # | Contrato | Archivo | Consumidor |
|---|---|---|---|
| 1 | Archivo de caso (entrada) | [`caso.schema.json`](./caso.schema.json) | profesional, app web futura |
| 2 | Informe (salida) | [`informe.schema.json`](./informe.schema.json) | herramientas aguas abajo |
| 3 | CLI | [`cli.md`](./cli.md) | gremios, scripts |
| 4 | Librería | [`library-api.md`](./library-api.md) | app web, otras herramientas |

Los datos normativos (reglas, catálogo de cargos, grillas) tienen sus propios schemas internos en
`schemas/` del repo del motor. No son contratos públicos: son el formato de un dato versionado que
solo el motor consume, y pueden evolucionar sin romper a nadie externo.

## Reglas comunes

**Versionado**: cada contrato lleva `schema_version` en semver. Un cambio incompatible exige MAJOR
y una nota en el ADR correspondiente.

**Números como string**: todo importe y porcentaje viaja como `string` con patrón numérico, nunca
como `number` de JSON. Un `number` sería parseado como float binario por cualquier consumidor y
rompería el Principio II en el borde. El patrón lo fuerza el schema y lo valida CI.

**Determinismo**: las colecciones tienen orden definido (escenarios por fecha, advertencias por
código, pasos del desglose por `orden`). Dos corridas iguales producen JSON idéntico byte a byte
con `sort_keys=True` (SC-003).

**Sin datos personales en diagnóstico**: los identificadores que cruzan hacia logs son técnicos
y anónimos (`periodo_idx`, `regla_id`, `codigo`). El contrato de informe sí lleva datos del caso
—es para el usuario— pero nada de lo que va a un log sale de él (FR-054).
