# Quickstart — validación del motor de cálculo

**Feature**: `001-motor-calculo-jubilacion` · **Fecha**: 2026-10-30

Guía para verificar que el motor funciona de punta a punta. No contiene implementación: los
detalles de modelos están en [`data-model.md`](./data-model.md) y los de interfaces en
[`contracts/`](./contracts/).

## Prerrequisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Windows, macOS o Linux (el motor debe dar resultados idénticos en los tres)

```bash
git clone <repo> && cd ultimo-timbre-motor
uv sync --all-extras
```

## Verificación 1 — Calidad y tipos

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/
```

**Esperado**: sin hallazgos. `mypy --strict` con el plugin de Pydantic v2 habilitado
(research R9).

## Verificación 2 — Esquemas de datos normativos

```bash
uv run check-jsonschema --schemafile schemas/rule.schema.json   rules/**/*.yaml
uv run check-jsonschema --schemafile schemas/cargo.schema.json  rules/**/cargos.yaml
uv run check-jsonschema --schemafile schemas/grid.schema.json   grids/*.yaml
```

**Esperado**: todo valida. Un importe o porcentaje escrito **sin comillas** en un YAML debe hacer
fallar este paso (research R1): es el gate que impide que un float binario entre por el borde.

**Prueba negativa deliberada**: sacale las comillas a un porcentaje de `rules/` y confirmá que
falla. Si pasa, el schema no está cumpliendo su función.

## Verificación 3 — Suite de pruebas y cobertura

```bash
uv run pytest --cov=ultimo_timbre --cov-branch --cov-report=term-missing
```

**Esperado**:
- Todos los tests en verde.
- Cobertura de ramas **≥95 %** en `ultimo_timbre/engine` y `ultimo_timbre/rules`, ≥80 % en el
  resto (Principio VI).

Por capa (research R8):

```bash
uv run pytest tests/golden/     # casos reales del IPS, anonimizados
uv run pytest tests/properties/ # invariantes con hypothesis
uv run pytest tests/contract/   # informe y caso validan contra su schema
uv run pytest tests/unit/
```

## Verificación 4 — Elegibilidad sin grilla (US1)

```bash
uv run ultimo-timbre calcular examples/caso-inc-b.yaml --formato texto
```

**Esperado**: el informe determina el inciso aplicable y la fecha de habilitación, con cada
requisito y su artículo citado. **No requiere grilla salarial**: las historias US1 a US3 se
validan sin montos.

## Verificación 5 — Escenarios y comparación (US5)

```bash
uv run ultimo-timbre calcular examples/caso-escenarios.yaml --formato json | jq '.escenarios'
```

**Esperado**: escenarios de habilitación, excedente de 3 y de 5 años, en orden cronológico, cada
uno con su porcentaje y `antiguedad_anios` proyectada. Todos con la **misma** `grilla_version` y
el mismo `a_valores_de` (FR-036a): la diferencia de monto entre escenarios debe explicarse solo
por el porcentaje y la antigüedad.

Verificá también que aparece `lectura_literal` con `sentido_impacto: "al_alza"` (FR-027b) y las
advertencias `montos_a_valores_de_hoy` y `haber_movil_art_50`.

### Caso de referencia: 25 años de servicio a los 54

`examples/caso-54-anios.yaml` cubre el escenario de la spec (US3 nº 6):

**Esperado**: 75 % al habilitarse (excedente 0, porque recién allí se cumplen **todas** las
condiciones, por `Res. IPS 995/2021, Anexo, punto 2.1.a`) y 80 % tres años después. El informe
debe advertir que bajo la lectura literal de los arts. 42 y 43 el porcentaje inicial sería mayor.

## Verificación 6 — Fuera de alcance y provisionalidad

```bash
uv run ultimo-timbre calcular examples/caso-otra-caja.yaml ; echo "exit=$?"
uv run ultimo-timbre calcular examples/caso-privado.yaml   ; echo "exit=$?"
uv run ultimo-timbre calcular examples/caso-simultaneo.yaml --formato json | jq '.advertencias'
```

**Esperado**:
- Los dos primeros salen con **exit 3** y explican la situación sin emitir monto.
- El tercero detecta la simultaneidad, advierte el impacto citando `art. 47; Res. IPS 995/2021`,
  y **no** calcula el incremento (FR-043).

```bash
uv run ultimo-timbre calcular examples/caso-provisional.yaml --formato json \
  | jq '{estado: .estado_general, reglas: [.escenarios[].haber.reglas_condicionantes[]?.regla_id]}'
```

**Esperado**: `estado_general: "provisional"`, exit **0**, y cada monto con sus
`reglas_condicionantes` pobladas y su `sentido_impacto` (FR-046a, FR-046b).

**Prueba clave**: no debe existir ninguna forma de obtener el valor del monto sin su estado. Si
encontrás una ruta de salida que lo entregue desnudo, es un defecto bloqueante (FR-046a).

## Verificación 7 — Determinismo y privacidad

```bash
uv run pytest tests/properties/test_determinismo.py tests/properties/test_orden_carga.py
uv run pytest tests/properties/test_canarios.py
```

**Esperado**:
- Dos corridas del mismo caso producen JSON idéntico byte a byte (SC-003).
- Permutar el orden de los períodos no cambia ningún valor (SC-010).
- Ningún dato marcado como canario aparece en la salida de diagnóstico (SC-008).

### Sin red

```bash
uv run pytest tests/test_sin_red.py
```

**Esperado**: el motor produce el mismo informe con los sockets bloqueados (SC-007).

### Multiplataforma

El determinismo entre Windows, macOS y Linux lo verifica CI comparando el informe del mismo caso
en los tres sistemas. Localmente solo podés validar el tuyo.

## Verificación 8 — Seguridad, licencia y SBOM

```bash
uv run bandit -r src/
uv run pip-audit
uv run reuse lint
uv run cyclonedx-py environment -o sbom.cdx.json
gitleaks detect --no-git
```

**Esperado**: sin hallazgos alto/crítico, todos los archivos con encabezado SPDX
`AGPL-3.0-or-later`, SBOM generado (Principios V y VII).

## Lista de verificación final

| # | Verificación | Principio / criterio |
|---|---|---|
| 1 | ruff + mypy strict sin hallazgos | Restricciones técnicas |
| 2 | Schemas validan; porcentaje sin comillas falla | I, II |
| 3 | Cobertura ≥95 % motor | VI |
| 4 | Elegibilidad sin grilla | V, US1 |
| 5 | Escenarios comparables, misma grilla | FR-036a, SC-003 |
| 6 | Fuera de alcance con exit 3, sin monto | X, I7 |
| 7 | Determinismo, orden, canarios, sin red | II, III, SC-003/007/008/010 |
| 8 | bandit, pip-audit, gitleaks, reuse, SBOM | V, VII |
