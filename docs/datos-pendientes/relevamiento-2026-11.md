<!--
SPDX-FileCopyrightText: Último Timbre
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Relevamiento de la grilla salarial y de los índices escalafonarios

**Fecha del relevamiento**: 2026-11-03 · **Para**: T135 (primera grilla aprobada) y T153
(índices del nomenclador) · **Estado**: incompleto, no apto para valuar

Este documento **no es una grilla**. Es el resultado de buscar las fuentes en línea, con cada
valor citado, y la lista explícita de lo que no se encontró. Existe para que la tarea `[MANUAL]`
del mantenedor arranque de datos verificados en lugar de una página en blanco.

## Por qué no hay archivo en `grids/`

Tres razones, en orden de gravedad:

1. **No se encontró la norma que aprueba la escala vigente.** El campo `norma` es obligatorio en
   `schemas/grid.schema.json` y el Principio I exige fuente normativa. La escala se publica en el
   sitio del Ministerio de Economía sin citar el decreto ni el acta paritaria que la aprueba.
2. **Las bonificaciones en porcentaje no declaran su base de cálculo.** Los códigos 653/663
   (114,15 %), 451 (74,50 %) y 667 (43,50 %) aparecen como porcentajes sin decir sobre qué
   importe se aplican. Sin la base, el componente no se puede expresar como `importe`.
3. **El sueldo básico por cargo depende del índice escalafonario**, y el índice vigente por cargo
   no está en una norma que haya podido verificar (ver abajo).

Una grilla con el básico del Preceptor y sin los códigos 653/663 produciría un haber **menor** que
el real, con la apariencia de ser correcto. El Principio X prefiere no calcular a calcular mal, y
por eso el archivo no se crea. Además, `aprobada_por` vacío es inválido para el schema y rompería
el job `validate-schemas` de CI.

## Lo que sí está verificado

**Fuente**: Escala salarial Ley Nº 10.579 — Noviembre 2026, Subsecretaría de Política y
Coordinación Económica, Ministerio de Economía de la Provincia de Buenos Aires. PDF de 2 páginas.
`https://www.ec.gba.gov.ar/areas/Sub_Politica_Coord_Eco/economialaboral/archivos/Escala%20salarial%20Ley%20N%C2%BA%2010.579%20-%20Noviembre%202026.pdf`
Enlazada desde `https://www.gba.gob.ar/economia/escala_salarial_ley_n%C2%B0_10579_personal_docente`

| Código | Concepto (literal) | Importe | Vigencia declarada | Pág. |
|---|---|---|---|---|
| — | Sueldo básico del Preceptor (Índice Escalafonario 1.1) | $ 370.675,00 | 1º nov 2026 | 1 |
| 455 | Bonificación Remunerativa No Bonificable de Suma Fija | $ 150.393,00 | 1º nov 2026 | 1 |
| 438 | Bonif. Rem. No Bonificable para cargos con Índice Escalafonario 1.1 | $ 295.476,00 | 1º nov 2026 | 1 |
| 653 y 663 | Bonif. Rem. No Bonificable para Preceptores | **114,15 %** | 1º ago 2026 | 1 |
| 456 | Bonif. Rem. No Bonificable para Directores y Vicedirectores | $ 7.667,00 | 1º mar 2024 | 1 |
| 668 | Bonif. Rem. No Bonificable para Secretarios y Prosecretarios | $ 1.740,00 | 1º mar 2024 | 1 |
| 451 | Bonif. Rem. No Bonificable para cargos con Índice >= 1.20 y <= 1.33, excepto Subjefe de Preceptores y Preceptor residente | **74,50 %** | 1º feb 2024 | 2 |
| 667 | Bonif. Rem. No Bonificable para Horas Cátedra y/o Módulos, cargos no jerárquicos sin concurso ni prueba de selección, de Secundaria, Secundaria de Adultos, Formación Profesional, Artística y Superior, excluyendo Preceptores | **43,50 %** | 1º ago 2026 | 2 |
| — (Decreto 1712/16 art. 8º) | Bonif. Rem. No Bonificable para Secretario y Prosecretario de Secundaria, Secundaria de Adultos, FP, Artística, Superior y Educación Física | **37,00 %** | 1º jul 2016 | 2 |
| — (Decreto 1712/16 art. 6º) | Bonif. Rem. No Bonificable por función diferenciada, Niveles Inicial y Primaria y modalidades de Psicología Comunitaria y Pedagogía Social y de Educación Especial | **Inicial y Primario 67 % · Psicología y Asistencia Social 74 % · Enseñanza Especial 78 %** | 1º jul 2016 | 2 |
| — | Bonificación **No Remunerativa** No Bonificable en concepto de Compensación FONID / Conectividad | $ 32.551,00 | 1º nov 2026 | 2 |

Los importes en negrita son **porcentajes**, no importes: ver el bloqueante 2.

### Dos hallazgos que importan al modelo

**Todas** las bonificaciones de la escala se llaman «No Bonificable». Si eso significa lo que
parece —que la antigüedad no se aplica sobre ellas—, el único componente con `bonificable: true`
sería el sueldo básico. Es exactamente la distinción que FR-031b necesita, y conviene confirmarla
contra un recibo real antes de cargarla.

El FONID / Conectividad es el único componente **no remunerativo** de la escala, y la escala
remite al Decreto Nº 1230/14 para su modalidad de liquidación.

## Índices escalafonarios: lo que se encontró y por qué no se cargó

### Fuente normativa (dos decretos, encadenados)

* **Decreto 1301/2005**, Anexo I «Nomenclador de cargos docentes Provincia de Buenos Aires»,
  vigencia 1º de abril de 2005. `https://normas.gba.gob.ar/documentos/xaE1dU4x.html`
  * Sección XV, Ingreso por cargo de base: **Maestro / Maestro Especial / Técnico Docente 1,00**
  * Sección b, Preceptores: **Preceptor 0,90** · Preceptor Residente 1,10 · Subjefe 1,21 · Jefe 1,32
  * Sección c, Medios de apoyo: **Bibliotecario 1,10 a 1,20** (rango)
  * Servicios educativos: **Director de Primera 1,93 a 2,75** · **Vicedirector de Primera 1,65 a
    2,48** · Director de Segunda 1,56 a 2,48 · Vicedirector de Segunda 1,56 a 2,20 · Director de
    Tercera 1,56 a 1,98 (todos **rangos** según modalidad y cantidad de secciones)
  * Sección XVI, hora cátedra: Profesor hora cátedra 1/15 a 1/12 · Profesor módulo 1/12 a 1/8
* **Decreto 2397/2005**. `https://normas.gba.gob.ar/documentos/0Yy6jTd0.html`
  * Art. 1º: salario básico docente de $364 asignado al cargo «Preceptor ítem IV» como **cargo testigo**
  * Art. 2º: «fija en 1,1 el índice escalafonario para los cargos que al 31 de julio de 2005
    tienen el valor 1» → el Maestro pasa de 1,00 a **1,10**
  * Art. 3º: incrementa en 20 % los índices del personal jerárquico
  * Art. 9º: aprueba el texto ordenado del nomenclador «conforme el Anexo» — **el Anexo no está
    reproducido en la versión en línea**

### Fuente administrativa, no normativa

«ESCALA SALARIAL DOCENTE ENERO 2026. Instructivo 13/01/2026», publicado en
`https://www.gba.gob.ar/static/salud/docs/HORAS%20CATEDRA%20ENERO%202026.pdf`, página 1, trae una
tabla de índices por cargo: Preceptor Enseñanza Media **1,00** · Maestro de grado **1,10** ·
Bibliotecario del Instituto de Menores **1,32** · Bibliotecario de Enseñanza Superior **1,44** ·
Director de Tercera **1,70** · Director de Segunda **1,80** · Vicedirector de Primera **1,86** ·
Director de Primera **2,16** · Jefe de Servicio 2,10 · Secretario 1,64 · Jefe de Taller 1,98 ·
Regente 2,16 · Asistente Coordinador 3,00 · Inspector de Enseñanza 3,60 · Asesor Docente 4,08.
Página 2, horas cátedra: 1,15 Enseñanza Media · 1,18 Adultos · 1,12 Enseñanza Superior.

**Es un instructivo administrativo, no una norma**, y además está publicado bajo la sección de
Salud del portal. No cumple el Principio I.

### Por qué queda todo en `null`

| Cargo del catálogo | Índice hallado | Por qué no se carga |
|---|---|---|
| `maestro_de_grado` | 1,10 | Es el único con cadena normativa completa (Dec. 1301/05 Anexo I sección XV + Dec. 2397/05 art. 2) y corroborado por el instructivo y por la aritmética de la escala oficial. Pero es una **composición de dos artículos de 2005** y no se pudo verificar que ningún decreto posterior lo haya cambiado en veinte años |
| `preceptor` | 0,90 ó 1,00 | **Las fuentes se contradicen**: Dec. 1301/05 dice 0,90; el instructivo lo usa como cargo testigo con 1,00; la escala de noviembre lo rotula «Índice Escalafonario 1.1» |
| `director` | 1,70 / 1,80 / 2,16 | **No hay un índice único**: depende de la categoría del establecimiento (Primera, Segunda, Tercera) y de la cantidad de secciones. El catálogo tiene un solo cargo `director` |
| `vicedirector` | 1,86 y rangos | Igual que `director` |
| `bibliotecario` | 1,32 / 1,44 | **Dos índices** según sea de Instituto de Menores o de Enseñanza Superior |
| `horas_catedra_secundario` | 1,15 / 1,18 / 1,12 | Tres valores según modalidad, y de naturaleza distinta: son índices **por hora**, no por cargo |
| `tecnico_docente_psicologia` | — | **No encontrado.** El nomenclador de 2005 tiene «Técnico Docente» genérico (1,00) pero no el cargo de Psicología |
| `tecnico_docente_educacion_especial` | — | **No encontrado** |
| `visitadora_higiene_escolar` | — | **No encontrado** |

## Una decisión de diseño que hace falta antes de cargar índices

`EntradaCatalogo.jerarquia` es `int | None`, con la convención «mayor entero = mayor jerarquía»
(`schemas/cargo.schema.json`). Pero los índices reales son **decimales**: 1,10 · 1,32 · 2,16. No
entran en un entero sin una decisión:

* **a)** guardar el índice como `str` decimal, igual que todo importe del proyecto (research R1), y
  renombrar el campo a algo como `indice_escalafonario`. Es lo que la Res. IPS 995/2021 necesita
  para comparar por remuneración (T155), y lo que el art. 41 llama «mayor jerarquía»;
* **b)** escalar a entero (1,10 → 110), que preserva el orden pero pierde el significado y vuelve
  el valor incomparable con la escala salarial;
* **c)** dejar `jerarquia` como orden abstracto y agregar `indice_escalafonario` aparte.

La **a)** parece la correcta —el índice *es* el criterio de comparación y además multiplica el
básico—, pero cambia el modelo, el schema y el contrato, así que no se decide acá.

## Lo que falta conseguir, en orden de utilidad

1. **El decreto o acta paritaria que aprueba la escala vigente**, para el campo `norma`. La página
   del Ministerio de Economía no lo cita en ninguna de las 15 escalas publicadas.
2. **La base de cálculo de las bonificaciones en porcentaje** (códigos 653/663, 451, 667). Un
   recibo real lo resolvería de inmediato.
3. **El nomenclador vigente con los índices por cargo.** El Anexo del art. 9º del Decreto
   2397/2005 es el candidato; no está reproducido en línea.
4. **La categoría de establecimiento** que corresponde a `director` y `vicedirector`, o bien
   desdoblar esos cargos del catálogo en sus categorías reales.
5. **Los cargos faltantes**: técnico docente de Psicología y de Educación Especial, y visitadora
   de higiene escolar. Las Leyes 10745 y 11860 los asimilan al frente de alumnos, pero no se
   encontró su índice.
6. **Confirmar que «No Bonificable» significa que la antigüedad no se aplica**, contra un recibo.

## Fuentes consultadas

* Escala salarial Ley Nº 10.579, Ministerio de Economía PBA — índice de publicaciones:
  <https://www.gba.gob.ar/economia/escala_salarial_ley_n%C2%B0_10579_personal_docente>
* Escala de noviembre 2026 (PDF):
  <https://www.ec.gba.gov.ar/areas/Sub_Politica_Coord_Eco/economialaboral/archivos/Escala%20salarial%20Ley%20N%C2%BA%2010.579%20-%20Noviembre%202026.pdf>
* Decreto 1301/2005: <https://normas.gba.gob.ar/documentos/xaE1dU4x.html>
* Decreto 2397/2005: <https://normas.gba.gob.ar/documentos/0Yy6jTd0.html>
* Ley 10579, texto actualizado: <https://normas.gba.gob.ar/documentos/xkdoDUAB.html>
* Instructivo escala salarial docente enero 2026 (administrativo):
  <https://www.gba.gob.ar/static/salud/docs/HORAS%20CATEDRA%20ENERO%202026.pdf>
