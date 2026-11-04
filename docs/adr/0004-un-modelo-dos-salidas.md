# ADR-0004 — Un solo modelo de informe, dos salidas, y el monto nunca viaja solo

**Estado**: Aceptado
**Fecha**: 2026-11-03
**Decide**: mantenedor del proyecto
**Principios en juego**: II (determinismo), IV (transparencia total), VIII (lenguaje claro)

## Contexto

El motor tiene que entregar dos cosas distintas: un **JSON** con contrato
estable, para que otro sistema lo consuma, y un **texto legible** en terminal,
para que un abogado lo lea y lo pegue en un dictamen.

Y tiene que cumplir FR-046a, que es más exigente de lo que parece: la marca de
que un monto es provisional debe ser inseparable del monto **en toda vía de
salida**. No «en el JSON», no «cuando se acuerde el renderizador»: en todas.

## Decisión

Las dos salidas se derivan de **un único modelo Pydantic `Informe`**. El JSON
es `model_dump` con `schema_version` y `estado_general` en la raíz; el texto es
un renderizador que lee ese mismo modelo y **no tiene lógica de cálculo
propia**.

El monto no es un escalar. Es un objeto
`Monto { valor, moneda, estado, condicionantes[], grilla_version, a_valores_de }`,
y no existe ninguna representación del monto sin su marca.

Los condicionantes no son solo reglas: un condicionante es una regla
`NO_VERIFICADA` **o** una situación del caso (`grilla_ausente`,
`cargo_fuera_de_catalogo`, `override_manual`, `supuesto_continuidad`), y el
tipo lleva `clase` para discriminarlas y `norma` opcional, porque una situación
del caso no tiene norma.

## Por qué

Un `Decimal` desnudo más un flag aparte convierte FR-046a en una **convención**:
funciona mientras cada serializador se acuerde de incluir el flag. Embeber el
estado dentro del tipo lo convierte en una **garantía**: no hay forma de
imprimir el número sin tener el objeto que lo contiene, y el objeto trae sus
condicionantes. La diferencia importa porque el modo de falla de la convención
es silencioso y el resultado es un monto provisional que se ve definitivo —
exactamente el error que no se puede permitir.

Un solo modelo, por su parte, es lo que impide que las dos salidas divergan. Si
el texto se armara aparte, el día que se agregue un campo al JSON el texto
seguiría imprimiendo la versión vieja sin que nada falle. Un test verifica sobre
el AST que `render/texto.py` no importa `engine` ni `rules`: si alguna vez
calculara algo propio, las dos salidas podrían contradecirse y el lector no
tendría modo de saber cuál creer.

Modelar los condicionantes como clase más amplia que «regla» responde a
FR-046b. Si solo se modelaran reglas, las cuatro situaciones del caso tendrían
que marcar el monto como provisional **sin poder explicar por qué**, que es
precisamente lo que FR-046b prohíbe.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| JSON como fuente y texto parseado de él | Frágil: cualquier cambio de formato rompe el renderizador, y el texto quedaría dependiendo de la forma serializada en lugar del significado |
| Dos modelos paralelos, uno por salida | Divergen. El modo de falla es que una salida muestre algo que la otra no tiene, y nada lo detecta |
| `Decimal` para el monto más un campo `estado` hermano | Deja FR-046a como convención: depende de que cada vía de salida se acuerde del flag |
| Un solo campo de texto libre con las advertencias | Cumple la letra y traiciona el propósito: no se puede consumir por máquina ni verificar qué condicionante falta |

## Consecuencias

Queda más fácil agregar una salida nueva —CSV, PDF, HTML— sin riesgo de
divergencia: se escribe otro renderizador sobre el mismo modelo y hereda todas
las garantías.

Queda más difícil imprimir «solo el número». Quien quiera el importe suelto
tiene que atravesar el objeto a propósito, y eso es deliberado: la fricción
está puesta justo donde la omisión sería peligrosa.

La consecuencia incómoda: el JSON es **verboso**. Cada monto arrastra su
estado, su grilla, su fecha de valores y su lista de condicionantes, y un
informe con cuatro escenarios repite esa estructura cuatro veces. Es el precio
de que la marca sea inseparable, y se paga.

Determinismo de la salida: `json.dumps(..., sort_keys=True, ensure_ascii=False)`
y orden explícito en toda colección (escenarios por fecha, advertencias por
código). Ningún timestamp de corrida dentro del informe comparable, para que la
comparación byte a byte de SC-003 sea posible.

## Disparador de revisión

Si el contrato JSON necesita un cambio incompatible —cambiar `schema_version` de
mayor—, conviene revisar acá si la estructura del `Monto` sigue siendo la
adecuada. Fuera de eso, ninguno: la decisión no depende de nada pendiente.
