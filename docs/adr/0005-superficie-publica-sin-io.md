# ADR-0005 — La superficie pública es mínima y `calcular()` no hace I/O

**Estado**: Aceptado
**Fecha**: 2026-11-03
**Decide**: mantenedor del proyecto
**Principios en juego**: V (motor abierto y separado), X (simplicidad), II (determinismo)

## Contexto

El motor se usa de dos maneras: como librería desde otro programa y por línea de
comandos. El Principio V exige que no dependa de la aplicación web ni de nada
propietario, y FR-051 exige que las dos vías produzcan **el mismo informe para
el mismo caso**.

Hay dos formas de conseguir esa equivalencia. Una es escribirla en un test y
confiar. La otra es hacer que sea estructuralmente imposible de romper.

## Decisión

`ultimo_timbre/__init__.py` declara un `__all__` explícito con un único punto
de entrada de cálculo:

```python
calcular(caso: Caso, *, reglas: ConjuntoDeReglas, grilla: GrillaSalarial | None = None) -> Informe
```

`calcular()` **no lee archivos, no abre sockets, no escribe logs y no consulta
el reloj**. Los cargadores de datos normativos (`cargar_reglas`,
`cargar_grilla`) y el de casos (`cargar_caso`) son funciones separadas que el
llamador invoca antes, y la fecha de cálculo entra dentro del `Caso`
(ADR-0007). El paquete declara `py.typed` (PEP 561) y exporta todos los tipos
públicos.

Lo que no está en `__all__` es interno: `ultimo_timbre.engine.*`,
`ultimo_timbre.rules.*` y los módulos privados pueden cambiar en un MINOR.

## Por qué

Si `calcular()` no hace I/O, la equivalencia de FR-051 deja de ser una promesa y
pasa a ser una consecuencia: **la CLI es un cargador más un renderizador**, y no
hay un segundo camino de cálculo que pueda divergir del primero. Un test de
equivalencia sigue existiendo, pero verifica algo que ya es cierto por
construcción en lugar de sostenerlo solo.

Sin I/O tampoco hay nada que mockear para testear el motor. Los tests
construyen un `Caso` y un `ConjuntoDeReglas` y llaman a la función: no hay
sistema de archivos virtual, no hay `monkeypatch` sobre `open`, no hay orden de
inicialización. Eso es lo que permite tener cientos de casos dorados sin
infraestructura de test.

La superficie mínima responde al Principio X por una razón concreta: cada
nombre exportado es un compromiso de compatibilidad. Exportar `engine.haber`
porque «puede ser útil» convierte un detalle de implementación en contrato, y
después un refactor interno exige un MAJOR.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| `calcular(ruta_caso)` que lea el archivo | La CLI y la librería tendrían caminos distintos y la equivalencia de FR-051 quedaría dependiendo de un test. Además obliga a mockear el disco en toda la suite |
| Carga perezosa de reglas dentro de `calcular()` | Esconde I/O en una función pura. El informe dejaría de poder declarar con certeza qué versión usó, porque la decisión ocurriría adentro |
| Exportar todo el paquete sin `__all__` | Cada módulo interno pasa a ser contrato por omisión; cualquier refactor rompe a alguien |
| Una clase `Motor` con configuración y estado | Agrega ciclo de vida a algo que es una función. El estado compartido entre llamadas es precisamente lo que rompería el determinismo |

## Consecuencias

Queda más fácil usar el motor desde cualquier contexto: un notebook, un
servidor, un script, un test. Nada que inicializar.

Queda más difícil el uso casual: quien quiera calcular un caso tiene que cargar
las reglas primero, en dos líneas en lugar de una. Es una fricción real y se
asume, porque esa segunda línea es la que deja registrado **qué versión de
datos** se usó.

La consecuencia incómoda: `cargar_reglas` **sí** lee el disco, y la frontera
entre lo puro y lo impuro queda en manos de quien llame. Nada impide escribir un
envoltorio que mezcle las dos cosas y pierda la ventaja. Lo que el proyecto
garantiza es que el motor no lo hace; lo que haga el llamador es del llamador.

## Disparador de revisión

Si alguna vez hace falta que el motor consulte una fuente externa durante el
cálculo —una grilla remota, un servicio de actualización de reglas— esta
decisión no sobrevive y hay que rediseñar el determinismo completo. Hoy no hay
nada que lo pida, y el Principio V empuja en la dirección contraria.
