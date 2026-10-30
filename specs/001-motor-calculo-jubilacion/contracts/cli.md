# Contrato de CLI

**Feature**: `001-motor-calculo-jubilacion` · Implementa FR-055, FR-056, FR-057, FR-051

Ejecutable `ultimo-timbre`, construido con Typer. Sin red, sin base de datos, sin escritura a
disco salvo el informe que el usuario pide explícitamente.

## Comandos

### `ultimo-timbre calcular`

```
ultimo-timbre calcular CASO [--formato json|texto] [--salida ARCHIVO]
                             [--reglas VERSION] [--grilla VERSION]
```

| Opción | Default | Descripción |
|---|---|---|
| `CASO` | — | Ruta al archivo de caso (`.yaml`, `.yml` o `.json`) |
| `--formato` | `texto` | `json` para el informe estructurado; `texto` para la salida legible |
| `--salida` | stdout | Archivo donde escribir el informe |
| `--reglas` | última | Versión del conjunto de reglas |
| `--grilla` | última aprobada | Versión de grilla salarial |

### `ultimo-timbre validar`

```
ultimo-timbre validar CASO
```

Valida el archivo contra `caso.schema.json` y las reglas de coherencia temporal (FR-003), sin
calcular. Pensado para que un gremio revise una carga antes de procesarla.

### `ultimo-timbre versiones`

```
ultimo-timbre versiones
```

Lista las versiones de reglas y de grillas disponibles, con su norma de origen, vigencia y
aprobador (FR-008, Principio IX).

## Códigos de salida

| Código | Significado | Cuándo |
|---|---|---|
| `0` | Éxito | Informe emitido, **incluso si `estado_general` es `provisional`** |
| `2` | Entrada inválida | Schema no valida, fechas incoherentes, campo faltante (FR-003, FR-057) |
| `3` | Caso fuera de alcance v1 | Otra caja, privado, invalidez, promedio de 36 meses del art. 41 (FR-044, FR-045, FR-020b) |
| `4` | Error interno | Excepción no prevista |

El `1` queda deliberadamente sin asignar: Python y Typer lo usan para fallos no controlados, y
reservarlo evita que un crash se confunda con un caso fuera de alcance.

Un resultado provisional sale con **0** porque es un resultado válido del motor (decisión Q3). Lo
que lo distingue es `estado_general` en el JSON, no el código de salida. Un script que quiera
rechazar resultados provisionales lee ese campo.

## Mensajes de error

Todo error de entrada nombra **el campo y el período afectado**, y describe la corrección posible
(FR-057, Principio VIII):

```
Error en el período 3 (Maestro de grado, 2015-03-01 a 2014-12-31):
  la fecha de fin es anterior a la de inicio.
  Corregí 'hasta' para que sea posterior a 'desde'.
```

Ningún mensaje de error deja al usuario sin una acción posible.

## Garantías

| Garantía | Origen |
|---|---|
| Sin acceso a red en ninguna ruta de ejecución | FR-051, SC-007, Principio V |
| Idénticos resultados que la vía de librería | FR-051 |
| Sin persistencia del caso ni de resultados | FR-053, Principio III |
| Sin datos personales en la salida de diagnóstico | FR-054, SC-008 |
| Salida JSON determinista (`sort_keys`, colecciones ordenadas) | FR-048, SC-003 |
