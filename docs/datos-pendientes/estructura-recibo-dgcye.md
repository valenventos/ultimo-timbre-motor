# Estructura del recibo de sueldo de la DGCyE

**Para**: la funcionalidad **002**, lectura de recibos.
**Estado**: relevado sobre una muestra de **un** recibo (período 09/2026).
**Fecha**: 2026-11-04.

Este documento describe **solo la estructura** del comprobante: qué campos trae
y cómo se agrupan. No contiene ningún dato personal ni ningún importe, y no
debe contenerlos nunca. El recibo que sirvió de muestra no está en el
repositorio y no se persiste en ninguna parte.

> **Advertencia de alcance.** Se relevó **un** recibo, de un cargo de nivel
> secundario por módulos. No se sabe si un recibo de maestra de grado, de
> directivo o de un cargo con más de una secuencia tiene la misma disposición.
> Todo lo que sigue es «así venía este», no «así vienen todos».

## Lo que importa entender antes de escribir el lector

**Un recibo es la foto de un mes, no una historia de servicios.** Esta es la
idea que gobierna el diseño de la funcionalidad 002, y conviene decirla antes
que cualquier detalle de campos.

El motor necesita, por cada período de servicio: el cargo, la carga horaria, la
situación de revista, el establecimiento y las fechas de inicio y fin. Un
recibo trae esos datos **de un solo mes**. No dice desde cuándo la docente está
en ese cargo ni hasta cuándo va a estar, ni cuántos módulos tenía dos años
antes.

De donde sale un período es de la **secuencia de recibos**: el cargo, la carga
y la revista de un período se reconstruyen viendo cuándo cambian a lo largo de
muchos meses consecutivos. Un cambio de carga horaria entre dos meses es el
borde entre dos períodos; un cambio de cargo, también.

Las consecuencias prácticas para el lector:

- **nunca** se puede inferir un período de un solo recibo. Con uno solo, lo
  honesto es cargar un período de un mes, o pedir más recibos;
- **los huecos importan**. Un mes sin recibo no es un mes sin servicio: puede
  ser un recibo que la docente no conserva. El lector tiene que distinguir «no
  trabajó» de «no tengo el papel», y por omisión suponer lo segundo;
- **el orden no se puede dar por sentado.** El período de liquidación viene en
  el recibo (`AAAAMM`), así que se ordena por ese campo y no por el orden en
  que los archivos se cargaron.

### El campo que sirve de control

El pie del recibo trae la **antigüedad en años**. Es el único dato del
comprobante que el motor puede usar para **verificarse a sí mismo**: si la
antigüedad que calcula a partir de los períodos reconstruidos no coincide con
la que el recibo declara, la reconstrucción está mal —falta un recibo, hay un
período mal cortado, o la convención de conteo es otra—.

Conviene tratarlo como una afirmación del empleador y no como una entrada: no
se carga como dato del caso, se compara contra el resultado. Una discrepancia
es un hallazgo que el informe tiene que mostrar, no un valor a adoptar.

## Estructura

### Encabezado

| Campo | Qué es |
|---|---|
| Organismo | la repartición que liquida (DGCyE) |
| Mes de pago | el mes en que se paga, que puede no ser el de liquidación |

### Tabla de líquidos por secuencia

Un recibo puede liquidar **varias secuencias**: cada una es un desempeño
distinto, y es la unidad que se corresponde con un período de servicio del
motor. La tabla resume el líquido de cada una.

Para un caso con cargos simultáneos, esto es lo que permite detectarlos desde
el comprobante: dos secuencias en el mismo mes son dos cargos a la vez.

### Por cada secuencia

**Establecimiento**

| Campo | Qué es |
|---|---|
| Distrito | el distrito escolar |
| Código | el código del establecimiento |
| Características | categoría, desfavorabilidad, cantidad de secciones, turnos |

Las características no son decorativas: la **categoría** y la cantidad de
**secciones** son las que determinan el índice escalafonario de los cargos
directivos, que el Decreto 1301/2005 da por rangos y no por valor único (ver
`relevamiento-2026-11.md`). La **desfavorabilidad** afecta la remuneración.

**Desempeño**

| Campo | Qué es |
|---|---|
| Secuencia | el identificador de este desempeño dentro del recibo |
| Revista | la situación de revista (`TIT.`, y presumiblemente otras) |
| Cargo real | el cargo que la docente efectivamente desempeña |
| Carga horaria | la cantidad, en la unidad del cargo (módulos, en la muestra) |
| Cargo interino | el cargo que ocupa de forma interina, si corresponde |
| Período de liquidación | `AAAAMM` |

Dos campos de cargo, **real** e **interino**, y la distinción importa para el
art. 41: el cargo base es el que la docente desempeñó, y cuál de los dos
cuenta cuando difieren es parte de la Cuestión abierta #5 (situación de
revista y su efecto en el cargo base). El lector tiene que conservar los dos y
no colapsarlos.

La **unidad** de la carga horaria no está rotulada en el recibo de la muestra:
se infiere del cargo. Es un problema para el lector, porque módulos y horas
cátedra no son lo mismo (Cuestión abierta #3) y confundirlos cambia si se
alcanza el umbral de veinte horas del art. 24 inc. b. El lector no debería
adivinar la unidad: si no la puede determinar del cargo, tiene que pedirla.

**Conceptos**

Una lista de líneas, cada una con:

| Campo | Qué es |
|---|---|
| Código | el código numérico del concepto |
| Descripción | el nombre del concepto |
| Haber o descuento | de qué lado de la liquidación está |

El **código** es la clave: es lo que permite mapear cada línea a un
`ComponenteSalarial` de la grilla, con su `bonificable`, su `remunerativo` y su
`aporte_ips`. Las descripciones varían y no sirven como identificador.

Qué se verificó sobre los códigos de la muestra está en las reglas de
`rules/v1/`, no acá: `antiguedad.base_bonificable`,
`remuneracion.conceptos_del_cargo` y `componentes.porcentuales_sobre_basico`
citan cada una su evidencia.

### Pie

| Campo | Qué es |
|---|---|
| Antigüedad en años | la que el empleador reconoce (ver «El campo que sirve de control») |
| Inasistencias | las del período |

## Lo que este relevamiento no resuelve

- **el significado de la sigla del cargo.** En la muestra el cargo aparece con
  una sigla de dos letras cuyo desarrollo no se pudo verificar. El catálogo la
  nombra por lo que hace (`modulos_secundaria`) y no por la sigla, justamente
  para no fijar una interpretación sin fuente;
- **el repertorio de valores de «revista».** Se vio `TIT.`; los demás se
  presumen por el modelo del motor (provisional, suplente) pero no se
  observaron;
- **si el recibo declara las fechas de alta del cargo.** En la muestra no
  aparecen, y es la razón por la que la historia necesita muchos recibos;
- **la disposición en recibos de otros niveles o con varias secuencias.** Un
  solo recibo no alcanza para fijar un formato.

Nada de esto bloquea el motor actual: la funcionalidad 002 es posterior, y la
carga manual de la historia de servicios no depende de leer recibos.
