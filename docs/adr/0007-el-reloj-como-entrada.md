# ADR-0007 — El reloj es un dato de entrada, no el ambiente

**Estado**: Aceptado
**Fecha**: 2026-11-03
**Decide**: mantenedor del proyecto
**Principios en juego**: II (determinismo y exactitud), IV (transparencia total)

## Contexto

Muchas decisiones del motor son relativas a «hoy»: si una fecha es plausible,
hasta dónde proyectar un período sin fecha de fin, cuál es la última grilla
aprobada, cuánto falta para habilitarse. Hay que decidir de dónde sale ese
«hoy».

La respuesta por omisión en cualquier lenguaje es `date.today()`, y es la que
rompe el Principio II de la manera más difícil de detectar: los tests pasan
todos los días menos uno.

## Decisión

`Caso.fecha_de_calculo` es **obligatoria** y el motor **nunca llama a
`date.today()` ni a `datetime.now()`**. Toda comparación relativa a «hoy» usa
ese campo. La CLI lo completa con la fecha del sistema cuando el usuario no lo
provee; la librería lo exige. El informe lo declara en su raíz.

La precedencia en la CLI es: `--fecha-calculo` explícito, después lo que diga el
archivo de caso, y solo si no hay ninguno, el reloj del sistema.

## Por qué

Sin esto, el determinismo del Principio II valdría **solo dentro de la misma
jornada**. Un caso archivado junto a un expediente tiene que producir el mismo
informe cuando se lo vuelva a correr dentro de un año: para auditar el consejo
que se dio, y para reproducir un resultado que alguien discute. Ese es el uso
que justifica todo el proyecto, y un `date.today()` escondido en una validación
de plausibilidad lo rompe sin que nada avise.

Que la fecha viva **dentro del caso** y no como parámetro de `calcular()` es la
parte menos obvia de la decisión, y es la que vuelve el archivo de caso
**autosuficiente**. Un `.yaml` archivado contiene todo lo necesario para
reproducir su informe. Si la fecha fuera un argumento, reproducir exigiría
recordar con qué fecha se corrió, y esa memoria no vive en ningún archivo.

## Verificación

No alcanza con decidirlo. Dos tests lo sostienen:

- `tests/test_sin_reloj.py` prohíbe `date.today()` y `datetime.now()` en
  `engine/` y `rules/` por inspección del **AST**, no por búsqueda de texto: un
  alias o un import indirecto no lo esquiva;
- un caso dorado se corre con dos fechas de cálculo distintas y se verifica que
  **solo** cambien los campos que dependen de ella
  (`tests/unit/test_fecha_calculo.py`).

El primero impide la regresión; el segundo confirma que la fecha realmente se
usa donde corresponde y no está decorando el informe.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Inyectar un `clock` como parámetro de `calcular()` | Equivalente en determinismo, pero deja la fecha fuera del archivo de caso: el caso archivado deja de ser autosuficiente y reproducir exige recordar con qué fecha se corrió |
| `date.today()` con posibilidad de override en tests | El comportamiento de producción sigue siendo no determinista; los tests verifican un camino que nadie usa |
| Congelar el reloj con una librería de test | Resuelve los tests y no el problema: el informe archivado sigue sin poder reproducirse |
| Guardar la fecha de corrida en el informe y usar el reloj | El informe diría con qué fecha se corrió pero no se podría volver a correr así. Documenta el problema en lugar de resolverlo |

## Consecuencias

Queda más fácil reproducir, auditar y testear. Un caso dorado no tiene fecha de
vencimiento: el que se escribió hoy sigue pasando en 2030 sin tocarlo.

Queda más difícil el uso desde librería: `fecha_de_calculo` es obligatoria y no
hay omisión cómoda. Quien quiera «hoy» tiene que escribirlo, y eso es
intencional: la decisión de usar el reloj es del llamador y queda a la vista.

La consecuencia incómoda: **la CLI sí usa el reloj** cuando el caso no trae
fecha, así que dos corridas del mismo archivo en días distintos pueden dar
informes distintos. Eso es correcto —es lo que el usuario pidió al no fijar la
fecha— pero significa que el determinismo es una propiedad del **caso
completo**, no del archivo a medias. Un caso destinado al archivo tiene que
declarar su `fecha_de_calculo`, y los siete ejemplos de `examples/` la declaran
justamente para dar el ejemplo correcto.

## Disparador de revisión

Ninguno. Esta decisión es una consecuencia directa del Principio II; revisarla
exigiría enmendar la constitución primero.
