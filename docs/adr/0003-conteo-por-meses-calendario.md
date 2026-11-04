# ADR-0003 — El cómputo de períodos se hace sobre conjuntos de meses calendario

**Estado**: Aceptado
**Fecha**: 2026-11-03
**Decide**: mantenedor del proyecto
**Principios en juego**: II (determinismo y exactitud), IV (transparencia total)

## Contexto

El art. 41 del DL 9650/80 define el cargo base como el desempeñado durante **36
meses consecutivos** o **60 meses alternados**, y el art. 24 exige mínimos de
años de servicio y de años al frente de alumnos. Hay que decidir cómo se
representa y se cuenta el tiempo.

Dos restricciones lo acotan. El Principio II prohíbe explícitamente las
aproximaciones del tipo «un mes = 30 días». Y FR-004a, junto con el invariante
I9, exige que el tiempo se cuente sobre la **unión** de los tramos cubiertos y
nunca sobre la suma de sus duraciones: dos cargos simultáneos durante un año
aportan un año, no dos.

## Decisión

Las fechas se representan con `datetime.date` y la aritmética de calendario
—edad al cese, aniversarios, excedentes— con `dateutil.relativedelta`. El
cómputo de los 36 y los 60 meses se resuelve sobre una **grilla discreta de
meses calendario**: cada período de servicio se proyecta al conjunto de meses
que cubre, y los algoritmos operan sobre ese conjunto.

Así, «60 meses alternados» es la **cardinalidad** de un conjunto y «36
consecutivos» es la **racha máxima** en una secuencia ordenada.

## Por qué

El conteo por días con conversión posterior a meses es inexacto y, peor,
inauditable: nadie puede verificar a mano por qué 1.096 días son «36 meses».
Discretizar a mes calendario hace que cada paso del cómputo sea verificable con
un calendario en la mano.

Y es lo que vuelve el invariante I9 difícil de violar por accidente. Con
conjuntos de meses, la unión **es** la operación: `set.union` descarta los
solapamientos sin que nadie tenga que acordarse. Una implementación por
duraciones tendría que descontar solapamientos a mano en cada camino de
cómputo, y el día en que se agregue un camino nuevo alguien se va a olvidar.
Esa es la razón principal de la elección, más que la exactitud.

Además habilita FR-020: el informe puede decir **qué meses concretos**
sustentan el cargo base —«2004-03 a 2030-03»— en lugar de un número de meses
sin trazabilidad. Eso es Principio IV aplicado al conteo.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Aritmética de días con conversión a meses | Viola el Principio II: cualquier factor de conversión es una aproximación, y el resultado no se puede verificar a mano |
| Intervalos con duración (`timedelta` por tramo) | Obliga a descontar solapamientos manualmente en cada camino de cómputo; el invariante I9 pasaría a depender de que nadie se olvide |
| `pandas` con `PeriodIndex` | Resuelve el problema, pero es una dependencia pesada para un motor sin dataframes, y agrega su propia semántica de bordes que habría que verificar |
| Contar meses como pares (año, mes) sin conjunto | Es casi la decisión tomada; sin la estructura de conjunto se pierde la unión gratuita, que es el punto |

## Consecuencias

Queda más fácil auditar: el desglose puede enumerar los meses que sustentan
cada cómputo. Queda más fácil también sostener la monotonía (invariante I4), que
sobre conjuntos es casi evidente.

Queda más difícil expresar un requisito que no esté alineado a mes. Si alguna
norma exigiera «25 años y 4 días», la representación no lo alcanza y habría que
mezclar dos mecanismos. No hay ningún requisito así hoy en el régimen.

La consecuencia incómoda: la discretización **decide** en los bordes. Un
período del 15 de marzo al 20 de abril cubre dos meses calendario, y si el día
de alta o de baja importara, el conteo por meses lo perdería. El proyecto
asume que no importa, porque la norma habla de meses de desempeño, pero es un
supuesto y está documentado como tal en `tests/unit/test_convencion_conteo.py`.

Qué meses aporta un período con licencia, suplencia o interinato es la
**Cuestión abierta #5**. El proyector recibe esa regla como dato; mientras sea
`NO_VERIFICADA`, el resultado sale provisional (FR-024, FR-024a).

## Disparador de revisión

Si alguna regla del régimen pasa a exigir un plazo con granularidad menor al
mes, o si al verificarse la Cuestión abierta #5 resulta que un período aporta
**fracciones** de mes —medio mes por una licencia, por ejemplo—, la
representación por conjunto de meses deja de alcanzar y hay que volver sobre
esta decisión.
