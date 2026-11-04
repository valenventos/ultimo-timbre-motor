# ADR-0006 — El motor no emite logs; la CLI configura el logging

**Estado**: Aceptado
**Fecha**: 2026-11-03
**Decide**: mantenedor del proyecto
**Principios en juego**: III (privacidad por diseño), VII (seguridad como requisito)

## Contexto

El Principio III prohíbe datos personales en logs, métricas y trazas. Los datos
que este motor procesa son la fecha de nacimiento, la historia laboral completa
y los cargos de una docente identificable: una línea de log con el cargo y las
fechas de un período alcanza para reconocer a una persona en una escuela chica.

El problema es **dónde** se hace cumplir eso. Una librería que loguea libremente
delega el cumplimiento del principio en cada `logger.debug()` que alguien
escriba de ahora en adelante, incluido el que se agregue apurado para depurar
algo un martes.

## Decisión

El motor **no emite logs**. Expone eventos de diagnóstico estructurados con
identificadores técnicos anónimos —`periodo_idx`, `regla_id`,
`codigo_advertencia`— y **nunca** valores de dominio. La librería solo instala
`logging.NullHandler()`; la **CLI** es la que configura el logging.

Un test canario corre un caso con datos marcados y falla si alguno aparece en la
salida de diagnóstico (SC-008, `tests/properties/test_canarios.py`).

## Por qué

No loguear desde la librería convierte el Principio III en algo **cumplible por
construcción**: no hay un lugar donde la omisión pueda ocurrir, porque no hay
llamada a logging que revisar. La alternativa —revisar cada línea de log en cada
revisión de código— funciona hasta que no funciona, y el modo de falla es que
un dato personal quede escrito en el disco de alguien y nadie se entere.

El test canario es lo que separa esto de una promesa. Afirma sobre la salida
observada, no sobre la intención: si mañana alguien agrega un `logger.info` con
el cargo, el canario lo encuentra.

Esta decisión tiene un hermano en el diseño de los mensajes de error, y vale
distinguirlos porque la diferencia es sutil y deliberada. El **objeto de error**
y todo lo que pueda llegar a logging llevan índice anónimo, campo y corrección
(FR-054). La **pantalla de la CLI** enriquece ese mensaje en el momento con el
cargo y las fechas de ese período, tomados del caso que el usuario tiene en la
mano, porque FR-057 exige que el mensaje sea accionable y porque mostrarle a
alguien su propio dato en su propia pantalla no es filtrarlo. Lo que no puede
pasar nunca es que ese enriquecimiento viaje: el test
`tests/cli/test_error_enriquecido.py` verifica las dos mitades, que aparezca en
la pantalla y que no aparezca en logging.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Loguear con un filtro que redacte datos personales | El filtro es una lista de lo que se conoce. El dato nuevo que nadie previó pasa, y el fallo es silencioso |
| Loguear solo en `DEBUG` | `DEBUG` se activa justo cuando hay un problema, que es cuando el caso real está cargado. Es la peor combinación posible |
| Dejar que la librería loguee y documentar la responsabilidad | Delega un principio constitucional en la disciplina de quien integre. No es verificable |
| Eventos de diagnóstico con los valores, anonimizados al salir | Mueve el riesgo al borde: cualquier camino que no pase por el anonimizador filtra |

## Consecuencias

Queda más fácil integrar el motor en un sistema con requisitos de privacidad:
no hay que auditar qué loguea, porque no loguea.

Queda más difícil **depurar un caso real**. Cuando algo sale mal con la historia
de servicios de una persona concreta, no hay traza con los valores. Lo que hay
es el desglose del informe, que es estructurado, y el `periodo_idx` para ubicar
dónde mirar. En la práctica alcanza, porque el informe ya explica cada paso,
pero es una limitación real y no conviene fingir que no.

La consecuencia incómoda: la CLI configura el logging **sin** `propagate=False`,
a propósito, para que el test canario pueda observar la salida. Eso significa
que un integrador que configure su propio logging raíz va a recibir los eventos
de diagnóstico de la CLI. Son anónimos por diseño, así que no filtran nada, pero
es un acoplamiento que existe y conviene conocer.

## Disparador de revisión

Si alguna vez el motor corre como servicio —no como librería ni CLI— hará falta
observabilidad real y habrá que diseñar un canal de diagnóstico con la misma
garantía, probablemente con identificadores de correlación opacos. Esta decisión
no cubre ese caso.
