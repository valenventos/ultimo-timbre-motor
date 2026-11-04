# Último Timbre — motor de cálculo

Estima la **jubilación ordinaria docente** del régimen del IPS de la Provincia
de Buenos Aires (Decreto-Ley 9650/80), con el desglose paso a paso y la norma
de cada regla aplicada.

Está pensado para abogados previsionales y gremios docentes que necesitan un
cálculo **auditable**: no alcanza con el número, hace falta poder mostrar de
dónde sale cada paso y qué artículo lo sostiene.

> **Este informe es una estimación orientativa. No reemplaza el cálculo oficial
> del IPS ni el asesoramiento profesional.**
>
> El motor lo repite en cada informe, y no es una fórmula de descargo: hay
> reglas del régimen que todavía no están verificadas contra fuente oficial, y
> el motor las declara una por una en lugar de disimularlas. Ver
> [Pendientes de datos](#pendientes-de-datos).

## Qué responde

- si se cumplen los requisitos del **art. 24, incisos b, c o d**, y desde qué
  fecha exacta;
- cuál es el **cargo base** del art. 41 (36 meses consecutivos o 60 alternados)
  y **por qué se eligió ese** y no otro;
- el **porcentaje** aplicable según los arts. 41, 42 y 43, con el excedente de
  3 y de 5 años;
- el **haber estimado**, cuando hay una grilla salarial aprobada;
- los **escenarios de cese**: la fecha en que nace el derecho y las fechas de
  los excedentes, cada una con su porcentaje y su monto, todas valuadas con la
  misma grilla para que sean comparables;
- el **desglose paso a paso**, la **procedencia de cada dato**, las **versiones**
  de reglas y de grilla usadas, y **todas** las advertencias.

Lo que **no** hace: no lee PDF, no tiene interfaz web, no calcula el incremento
por cargos simultáneos (los detecta y lo advierte), y no calcula los casos
fuera de alcance (otras cajas, establecimientos privados, invalidez, edad
avanzada): los detecta y lo informa.

## Instalación

Hace falta [uv](https://docs.astral.sh/uv/) y Python 3.12 o superior. Funciona
igual en Windows, macOS y Linux.

```bash
git clone https://github.com/valenventos/ultimo-timbre-motor.git
cd ultimo-timbre-motor
uv sync --all-extras --dev
```

Para usarlo como dependencia de otro proyecto:

```bash
uv add git+https://github.com/valenventos/ultimo-timbre-motor.git
```

## Uso desde la línea de comandos

Un caso es un archivo `.yaml` o `.json`. En `examples/` hay siete, uno por cada
situación que vale la pena ver.

```bash
uv run ultimo-timbre calcular examples/caso-inc-b.yaml --formato texto
```

En PowerShell es igual:

```powershell
uv run ultimo-timbre calcular examples\caso-inc-b.yaml --formato texto
```

Salida (recortada):

```text
INFORME DE JUBILACIÓN ORDINARIA DOCENTE — IPS Provincia de Buenos Aires
==============================================================================
Fecha de cálculo: 2030-04-01
Versión de reglas: v1
Versión de grilla: ninguna (informe sin montos)
Estado general: DEFINITIVO

Elegibilidad
============
Accede por el inc. b del art. 24 del DL 9650/80.
Estado de la elegibilidad: definitivo.
Mínimo general de años con aportes: 26 de 22 (cumple).
  inc. b: cumple, habilitado desde 2030-03-15
      edad: 50 de 50
      años de servicio: 26 de 25 (margen 396 días)
      años al frente de alumnos (o 20 horas cátedra): 26 de 25 (margen 396 días)

Escenarios de cese
==================
Esperar no aumenta la bonificación por antigüedad (ya está en el máximo); lo que aumenta es el porcentaje del haber.

Cese 2030-03-15 (habilitacion)
------------------------------
Inciso aplicable: inc. b
Porcentaje: 75 %

Cese 2033-03-15 (excedente_3)
-----------------------------
Porcentaje: 80 %

Cese 2035-03-15 (excedente_5)
-----------------------------
Porcentaje: 85 %
```

### Los tres comandos

```bash
# El informe completo. --formato texto es el valor por omisión.
uv run ultimo-timbre calcular CASO [--formato texto|json|yaml] [--salida ARCHIVO]
                                   [--reglas VERSION] [--grilla VERSION]
                                   [--fecha-calculo YYYY-MM-DD] [--verboso]

# Solo valida el archivo, sin calcular nada. Útil antes de cargar 30 casos.
uv run ultimo-timbre validar CASO

# Qué datos normativos tiene este repositorio a mano.
uv run ultimo-timbre versiones
```

```text
$ uv run ultimo-timbre versiones
ultimo-timbre 0.1.0

Conjuntos de reglas:
  v1

Grillas salariales aprobadas:
  (ninguna)
```

### Códigos de salida

Están separados a propósito: un script que procese muchos casos tiene que poder
distinguir «este archivo está mal escrito» de «este caso el motor no lo cubre».

| Código | Significado |
|---|---|
| `0` | el informe se produjo |
| `2` | la entrada es inválida: el archivo no se puede interpretar |
| `3` | el caso está **fuera de alcance**: se entiende, pero el motor no lo calcula |
| `4` | error interno |

El `3` no es un fallo del usuario ni del programa: es el motor negándose a
calcular lo que no sabe. Igual emite el informe parcial, con la advertencia.

## Uso como librería

`calcular()` no lee archivos, no abre sockets y **no consulta el reloj**: la
fecha de cálculo entra dentro del caso. Por eso el mismo caso con las mismas
reglas da el mismo informe byte a byte, hoy y en dos años.

```python
from pathlib import Path

from ultimo_timbre import calcular, cargar_caso, cargar_reglas, informe_a_texto

caso = cargar_caso(Path("examples/caso-inc-b.yaml"))  # el único I/O, explícito
informe = calcular(caso, reglas=cargar_reglas("v1"))

print(informe.elegibilidad.inciso_mas_favorable)  # 'b'
print(informe_a_texto(informe))
```

La guía completa, con ejemplos que la suite ejecuta en cada corrida, está en
[`docs/api.md`](docs/api.md). El contrato formal —firmas, excepciones,
estabilidad— en
[`contracts/library-api.md`](specs/001-motor-calculo-jubilacion/contracts/library-api.md).

## Cómo está hecho

Lo que hace a este motor distinto de una planilla no es el cálculo, es qué
queda registrado:

- **Las reglas son datos, no código.** `rules/v1/*.yaml` versionado, cada regla
  con su norma, su estado (`verificado` / `interpretacion` / `no_verificada`) y
  el sentido en que su incertidumbre movería el resultado. Las grillas
  salariales, igual: `grids/<vigencia>.yaml`, validadas por JSON Schema en CI.
- **Aritmética exacta.** Todo `Decimal`. Nada de `float`, ni «el mes son 30
  días»: los plazos se cuentan con fechas calendario reales.
- **Nada se inventa.** Si una regla no está verificada, el informe sale
  `provisional` y dice por qué. Si falta la grilla, no hay monto. Un número
  plausible sin respaldo sería el peor resultado posible.
- **Un monto nunca viaja solo.** Lleva su fecha de valores, su estado y sus
  condicionantes, y los renderizadores no saben imprimirlo sin ellos.
- **Privacidad por diseño.** Sin red, sin base de datos, sin persistencia de
  casos. Los diagnósticos y los logs llevan índice anónimo del período, nunca
  el nombre, el cargo ni las fechas (ver [`SECURITY.md`](SECURITY.md)).

Las decisiones técnicas están en [`docs/adr/`](docs/adr/), una por archivo, con
sus alternativas descartadas y su disparador de revisión. Las reglas de juego
del proyecto, en [`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Desarrollo

```bash
uv run pytest                     # la suite completa, con cobertura
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src tests
uv run bandit -c pyproject.toml -r src
uv run pip-audit
uv run reuse lint
```

Cobertura exigida: **95 % de ramas** en `ultimo_timbre/engine` y
`ultimo_timbre/rules`, 80 % en el resto. Los tests de cada historia de usuario
se escriben **antes** de su implementación y tienen que fallar primero.

Para agregar una grilla salarial: abrir un PR. **Fusionar el PR es el acto de
aprobación**, y el check `validate-grid-approval` rechaza toda grilla que no
diga quién la aprobó y cuándo. La política completa, con su escalón pendiente,
está en [ADR-0002](docs/adr/0002-aprobacion-de-grillas.md).

## Pendientes de datos

Esta sección existe porque el motor está **técnicamente completo y
normativamente incompleto**, y eso hay que poder leerlo antes de usarlo, no
después.

Cuatro tareas no las puede hacer el agente ni el código: necesitan un dato que
solo existe en una fuente oficial o en un expediente real. Están **sin marcar**
en [`tasks.md`](specs/001-motor-calculo-jubilacion/tasks.md) y van a seguir así
hasta que alguien consiga el dato.

| Tarea | Qué falta | Por qué bloquea |
|---|---|---|
| **T138** | la primera grilla salarial real en `grids/`, transcrita de la norma con enlace y artículo por cada valor | sin grilla aprobada el motor **no emite ningún monto**. Responde elegibilidad, cargo base y porcentaje, y para el haber dice «no se calcula» |
| **T153** | el **índice escalafonario** de cada cargo, desde el nomenclador docente vigente | sin él, dos cargos de jerarquía distinta pueden empatar al elegir el cargo base, y el informe sale `provisional` por Cuestión abierta #4 |
| **T139** | un **caso dorado con una resolución real del IPS**, anonimizada, valuado con la grilla histórica vigente al cese de ese caso | es la única prueba de que el motor coincide con el IPS. Todo lo demás verifica coherencia interna, no acierto |
| **T194** | la verificación del gate de release | es el acto de constatar que las tres anteriores están resueltas |

El relevamiento que ya se hizo está en
[`docs/datos-pendientes/relevamiento-2026-11.md`](docs/datos-pendientes/relevamiento-2026-11.md),
con los tres bloqueos que impidieron armar la grilla y las fuentes consultadas
una por una. No se cargó ningún valor estimado: **`grids/` está vacío a
propósito**, y un valor inventado ahí produciría un haber convincente y falso.

### El gate de release comercial está cerrado

Mientras T138, T139 y T153 sigan sin resolver:

- el motor **puede** usarse internamente, para desarrollo y para demostración;
- **no puede** ofrecerse a gremios ni a estudios jurídicos, ni presentarse como
  estimación profesional.

La razón es una sola: **ninguna versión que no haya reproducido un cálculo real
del IPS puede presentarse como estimación profesional.** La suite tiene cientos
de tests en verde y eso prueba que el motor es coherente consigo mismo y con el
texto de las normas tal como el proyecto las leyó. No prueba que el IPS calcule
igual. Lo único que puede probar eso es T139.

El gate completo, con la decisión del mantenedor que lo fijó, está al final de
[`tasks.md`](specs/001-motor-calculo-jubilacion/tasks.md).

## Licencia

[AGPL-3.0-or-later](LICENSE). El motor es software libre y se mantiene separado
de cualquier aplicación que lo use: quien reciba un informe tiene que poder
auditar cómo se produjo.
