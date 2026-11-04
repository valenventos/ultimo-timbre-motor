# ADR-0002 — La aprobación de una grilla salarial es la fusión de su pull request

**Estado**: Aceptado
**Fecha**: 2026-11-03
**Decide**: mantenedor del repositorio
**Principios en juego**: I (fuente normativa), IV (transparencia total), IX (grillas aprobadas por revisión humana)

## Contexto

El Principio IX exige que ninguna grilla salarial valúe un informe sin haber
pasado por revisión humana. Hace falta decidir **dónde ocurre** esa revisión y
**qué la deja probada**, porque un valor equivocado en una grilla no produce un
error visible: produce un haber convincente y falso, firmado por un abogado.

La restricción que condiciona todo lo demás es que **hoy hay un solo
mantenedor**. GitHub no puede exigir la revisión de un tercero cuando no hay
tercero: CODEOWNERS no bloquea al dueño del repositorio, y una regla de
protección de rama que pida una aprobación ajena sería imposible de satisfacer
o se desactivaría en el primer apuro, que es peor que no tenerla.

## Decisión

El acto de aprobación de una grilla es **la fusión de su pull request**. Cada
grilla declara `aprobada_por` y `aprobada_en`, el check `validate-grid-approval`
rechaza el PR si alguno de los dos está vacío, y mientras haya un solo
mantenedor exige además que `aprobada_por` **coincida con quien fusiona**.
`CODEOWNERS` cubre `grids/`, `rules/`, `schemas/`, la constitución y los
contratos, para que la plataforma pida la revisión en cuanto exista alguien que
pueda darla.

## Por qué

La aprobación tiene que dejar un rastro que no dependa de la memoria de nadie.
Un PR fusionado tiene autor, fecha, revisor, diff y discusión: es el registro
más completo que el proyecto puede producir sin montar un sistema aparte, y es
exactamente lo que el Principio IV pide para que un informe sea auditable años
después.

Atar `aprobada_por` a quien fusiona es lo que vuelve **verificable** la promesa
con un solo mantenedor. Sin eso, el campo sería decorativo: cualquier nombre
pasaría el check y la grilla diría «aprobada por» alguien que nunca la miró.
Con eso, el campo afirma algo que la plataforma puede contradecir.

Lo que esta política **no** hace es fingir que una persona revisándose a sí
misma equivale a la revisión de un tercero. No equivale. La política está
diseñada en dos escalones justamente para no mentir sobre eso: el escalón de
hoy deja el acto registrado y atribuido; el de mañana agrega el control
cruzado. El disparador del segundo escalón está al final de este ADR, y es un
hecho objetivo, no un juicio sobre cuándo el proyecto «ya está maduro».

| Escalón | `aprobada_por` | Quién revisa | Cómo se exige |
|---|---|---|---|
| Un mantenedor (hoy) | igual a quien fusiona | el mismo mantenedor, con el PR como registro | `validate-grid-approval` compara con `github.actor` |
| Dos o más mantenedores | **distinto** del autor del PR | un tercero | CODEOWNERS + rama protegida, y el check pasa a exigir que difiera del autor |

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Rama protegida que exija la aprobación de otra persona, ya | Hoy es insatisfacible con un solo mantenedor: bloquearía toda carga de grillas o se desactivaría, y una regla que se desactiva no protege nada |
| Confiar en que el mantenedor complete `aprobada_por` a conciencia | El campo quedaría sin verificación: cualquier texto pasaría, y una grilla podría declarar un aprobador que nunca la revisó |
| Firmar las grillas criptográficamente | Resuelve autenticidad, no revisión: una firma prueba quién subió el archivo, no que alguien comparó sus valores contra la norma. Agrega gestión de claves a cambio de nada que el Principio IX pida |
| Aprobar por fuera del repo (acta, planilla, correo) | Rompe el Principio IV: el informe cita una versión de grilla y el lector no puede llegar desde ahí a la aprobación. Lo que no está en el repo, para un auditor no existe |
| Permitir grillas no aprobadas marcándolas como provisionales | Un monto provisional sigue siendo un número en pantalla. El Principio IX no admite grado: sin aprobación no se carga |

## Consecuencias

Queda más fácil auditar: desde la versión de grilla que cita un informe se
llega al PR, al diff, a la discusión y a la fecha. Queda más fácil también
cerrar el paso a una grilla a medias, porque el check falla en CI y no en una
revisión manual que puede saltearse.

Queda más difícil cargar una grilla con apuro: hay que abrir un PR, completar
los dos campos y esperar a CI, incluso para corregir un solo importe. Es el
costo buscado.

La consecuencia incómoda: **mientras haya un solo mantenedor, la revisión es
autorrevisión**. El check verifica que el acto existió y quién lo hizo, no que
los valores sean correctos. Eso lo cubre, por ahora, la exigencia de citar
norma y enlace por cada valor (T138) y el hecho de que `grids/` esté vacío: el
motor no emite montos reales todavía. No hay que leer esta política como si ya
diera control cruzado.

Además, el check depende de `github.actor`, que en una fusión por la interfaz
de GitHub es quien fusiona, pero en un push directo a la rama es quien
empujó. Un push directo a `main` que agregue una grilla pasaría el check con el
nombre del mantenedor. Lo cierra la protección de rama, no este check.

## Disparador de revisión

**Cuando exista un segundo mantenedor con permiso de merge.** Ese día hay que:

1. exigir en `validate-grid-approval` que `aprobada_por` sea **distinto** del
   autor del PR, en lugar de igual a quien fusiona;
2. activar la protección de rama sobre `main` con revisión obligatoria de
   CODEOWNERS;
3. actualizar la tabla de escalones de este ADR y dejarlo como reemplazado si
   la política cambia en algo más que ese detalle.

Un segundo disparador: si alguna vez se carga una grilla real en `grids/`
—hoy está vacío— conviene revisar si la autorrevisión sigue siendo aceptable
para datos que ya producen montos en informes firmados.
