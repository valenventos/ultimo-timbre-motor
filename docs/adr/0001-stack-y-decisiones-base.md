# ADR-0001 — Stack y decisiones base del motor

**Estado**: Aceptado
**Fecha**: 2026-11-01
**Decide**: mantenedor del proyecto
**Principios en juego**: I, II, III, IV, V, VI, VII, IX, X

## Contexto

El motor de cálculo de la jubilación ordinaria docente del IPS debe ser auditable por un abogado
previsional, reproducible años después, y utilizable sin red. La constitución v1.1.0 fija diez
principios no negociables; este ADR registra las trece decisiones técnicas (R1 a R13 de
`specs/001-motor-calculo-jubilacion/research.md`) que las hacen verificables.

## Decisión

Paquete Python 3.12 independiente, gestionado con uv, con los siguientes compromisos:

| # | Decisión | Principio |
|---|---|---|
| R1 | `Decimal` de punta a punta. Los loaders entregan `str`, nunca `float`: `yaml.safe_load` con resolver que desactiva la conversión implícita, y `json.load(parse_float=Decimal)`. Un único `quantize()` centralizado | II |
| R2 | Fechas con `datetime.date` y `dateutil.relativedelta`. El conteo de 36/60 meses se resuelve sobre **conjuntos de meses calendario**, computando siempre la **unión** de tramos y nunca la suma de duraciones | II |
| R3 | Reglas, catálogo de cargos y grillas como YAML versionados en el repo, cada familia con su JSON Schema validado en CI. Importes y porcentajes siempre entre comillas | I, IX |
| R4 | La aprobación de una grilla es el **merge del PR**, no un campo autodeclarado. Política escalonada según cantidad de mantenedores (ver ADR-0002) | IX |
| R5 | Una sola fuente de salida: el modelo `Informe`. JSON y texto lo renderizan sin recalcular. El monto es un tipo que lleva su `estado` y sus `condicionantes` incorporados | IV |
| R6 | Códigos de salida 0 / 2 / 3 / 4, con el 1 deliberadamente sin asignar. El 3 se deriva de la presencia de advertencias bloqueantes, no de una excepción | IV, X |
| R7 | `calcular()` sin I/O, sin red y sin reloj. Los cargadores son funciones separadas | V |
| R8 | Cuatro capas de prueba (dorados, propiedades, contrato, unitarias), todas escritas antes. Cobertura de ramas ≥95 % en `engine` y `rules`, ≥80 % en el resto | VI |
| R9 | `mypy --strict` con el plugin `pydantic.mypy`, y `disallow_any_explicit` en `engine` y `rules` | — |
| R10 | AGPL-3.0-or-later con encabezado SPDX en cada archivo, verificado con `reuse` en CI | V |
| R11 | CI en GitHub Actions: matriz de tres plataformas, tests, cobertura, schemas, bandit, pip-audit, gitleaks, reuse y SBOM CycloneDX | VII |
| R12 | La librería no emite logs (`NullHandler`); la CLI configura el logging. Diagnóstico con identificadores técnicos anónimos y test de canarios | III |
| R13 | La **fecha de cálculo es una entrada del caso**, no el reloj del sistema | II |

## Por qué

Las decisiones que más cuestan de entender son las tres que convierten un principio en una
garantía estructural en lugar de una convención:

**R1 — los loaders entregan `str`.** El riesgo del Principio II no está en el cálculo sino en los
bordes. Un `0.75` escrito sin comillas en un YAML de reglas ya es un float binario antes de que
Pydantic lo vea, y en ese punto el error es invisible. Interceptarlo en el loader, y además
rechazarlo en el JSON Schema, es el único lugar donde se puede garantizar.

**R5 — el monto lleva su estado adentro.** La exigencia de que la marca de provisional sea
inseparable del monto (FR-046a) es incumplible si el estado viaja al lado: depende de que cada
serializador se acuerde de incluirlo. Embebiéndolo en el tipo, omitirlo deja de ser posible.

**R13 — el reloj como entrada.** Sin esto, el determinismo valdría solo dentro de la misma
jornada. Un caso archivado junto a un expediente tiene que producir el mismo informe cuando se lo
vuelva a correr dentro de un año, tanto para auditar el consejo que se dio como para reproducir un
resultado discutido. Un `date.today()` escondido en una validación rompe eso de un modo
particularmente difícil de detectar, porque los tests pasan todos los días menos uno.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| `float` con redondeo tardío | Viola el Principio II |
| `fractions.Fraction` | Exacto, pero sin semántica de redondeo monetario ni representación natural en YAML |
| Reglas normativas en código Python | Viola el Principio I: una regla sin dato versionado no es auditable |
| Base de datos para reglas y grillas | Viola la restricción de "sin base de datos" y el Principio V |
| Aritmética de días convertida a meses | Inexacta y no auditable; el Principio II prohíbe "un mes = 30 días" |
| `pandas` para los períodos | Dependencia pesada para un motor sin dataframes |
| Inyectar un `clock` como parámetro de `calcular()` | Igual de determinista, pero deja la fecha fuera del archivo de caso: el caso archivado deja de ser autosuficiente |
| `FueraDeAlcance` como excepción para casos de usuario | Le quita al profesional el análisis parcial que el motor ya tenía; el Principio IV prefiere un resultado parcial explicado |

## Consecuencias

**Más fácil**: auditar cualquier número hasta su norma; reproducir un informe años después;
correr el motor sin red ni servicios; cambiar una regla sin tocar código.

**Más difícil**: todo valor normativo exige una fila en un YAML con su fuente, lo que agrega
fricción a cada cambio de regla — deliberadamente. El `Decimal` obliga a cuidar cada borde de
serialización. La prohibición del reloj obliga a pasar `fecha_de_calculo` por toda la cadena, lo
que incomoda en los tests hasta que se vuelve costumbre. El umbral de 95 % en `engine` y `rules`
necesita un paso de CI aparte, porque `--cov-fail-under` es un único valor global.

## Disparador de revisión

- R3 y R4: cuando haya un segundo mantenedor con permiso de merge (ver ADR-0002).
- R1 (política de redondeo): cuando se verifique la Cuestión abierta #6.
- R2 (cómputo de licencias y situación de revista): cuando se verifique la Cuestión abierta #5.
- R8 (casos dorados reales): cuando se consiga la primera resolución del IPS anonimizada, que es
  además el gate del release comercial (SC-002).
