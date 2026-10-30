# Feature Specification: Motor de cálculo de jubilación ordinaria docente (IPS PBA)

**Feature Branch**: `001-motor-calculo-jubilacion`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "Motor de cálculo de la jubilación ordinaria docente del IPS de la Provincia de Buenos Aires, usable como librería y desde línea de comandos, sin interfaz web ni lectura de PDF."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verificar elegibilidad y fecha de habilitación (Priority: P1)

Una abogada previsional carga la fecha de nacimiento de su clienta y su historia de servicios
período por período, indica una fecha de cese a evaluar, y obtiene una respuesta fundada a la
pregunta más básica: ¿puede jubilarse, por cuál inciso del art. 24, y desde qué fecha? El motor
informa los años de servicio computados, los años al frente de alumnos, la edad al cese y qué
requisito de cada inciso se cumple o falta, citando la norma de cada uno.

**Why this priority**: Es la pregunta que abre toda consulta previsional. Sin monto, saber si el
derecho está habilitado y desde cuándo ya permite asesorar. Es la porción más chica que entrega
valor real y de la que dependen todas las demás.

**Independent Test**: Se prueba cargando una historia de servicios conocida y una fecha de cese,
y verificando que el motor determina el inciso aplicable y la fecha de habilitación, con el
detalle de cada requisito y su artículo, sin necesidad de grilla salarial ni cálculo de monto.

**Acceptance Scenarios**:

1. **Given** una docente nacida el 1980-03-15 con 26 años de servicios al frente de alumnos al
   2030-03-31, **When** se evalúa el cese al 2030-03-31, **Then** el motor informa que cumple el
   art. 24 inc. b (50 años de edad y 25 de servicios al frente de alumnos), indica la fecha desde
   la cual quedó habilitada y cita `[DL 9650/80, art. 24 inc. b]`.
2. **Given** una docente con 24 años de servicios y 52 de edad al cese evaluado, **When** se
   evalúa ese cese, **Then** el motor informa que NO cumple ningún inciso, detalla cuánto falta
   para cada uno y estima la fecha en que cumpliría el primero.
3. **Given** una historia de servicios con períodos docentes y no docentes aportados al IPS,
   **When** se evalúa la elegibilidad, **Then** el motor computa solo los servicios docentes,
   detecta los no docentes y advierte que podrían completar los requisitos por la vía del
   prorrateo `[DL 9650/80, art. 27]`, marcando la elegibilidad como no definitiva.
4. **Given** una docente que cumple el inc. b y el inc. d en fechas distintas, **When** se evalúa
   el cese, **Then** el motor informa ambos y señala cuál es más favorable y por qué.

---

### User Story 2 - Detectar los límites del motor antes de dar un número (Priority: P2)

La misma abogada carga un caso que el motor no puede resolver con certeza: la docente tiene
cargos simultáneos, o aportes en otra caja, o el cálculo depende de una regla que todavía no se
pudo verificar contra la norma. El motor no adivina: detecta la situación, se niega a dar un
resultado definitivo por ese camino, y explica exactamente qué encontró y por qué no puede
calcularlo.

**Why this priority**: Un número equivocado en un informe previsional es peor que la ausencia de
número: la abogada lo transmite a la docente y se toma una decisión de cese irreversible sobre
una base falsa. Esta historia es la que vuelve confiable a la US1 y a todo lo que venga después.

**Independent Test**: Se prueba con un conjunto de casos deliberadamente fuera de alcance o
afectados por reglas `NO_VERIFICADA`, verificando que ninguno recibe un resultado definitivo y
que todos reciben una advertencia que nombra la situación y su norma.

**Acceptance Scenarios**:

1. **Given** una historia con dos cargos que se superponen durante más de 3 años continuos,
   **When** se procesa el caso, **Then** el motor detecta la simultaneidad, advierte su posible
   impacto en el haber citando `[DL 9650/80, art. 47; Res. IPS 995/2021]`, y NO calcula el
   incremento.
2. **Given** una historia con períodos aportados a ANSES o a otra caja provincial, **When** se
   procesa el caso, **Then** el motor lo informa como fuera de alcance de la v1 citando
   `[DL 9650/80, arts. 66 y 67]` y no computa esos períodos ni emite un haber.
3. **Given** un caso cuyo haber depende de la escala de bonificación por antigüedad, **When** se
   calcula, **Then** el motor marca el resultado como no definitivo por la regla `NO_VERIFICADA`
   correspondiente y explica qué falta verificar.
4. **Given** un establecimiento de gestión privada en la historia de servicios, **When** se
   procesa el caso, **Then** el motor lo detecta y lo informa como fuera de alcance sin calcular.
5. **Given** una docente que con sus servicios docentes no alcanza ningún inciso del art. 24 pero
   tiene períodos no docentes aportados al IPS, **When** se evalúa la elegibilidad, **Then** el
   motor advierte explícitamente que esos servicios podrían completar los requisitos mediante el
   prorrateo `[DL 9650/80, art. 27]` y marca el resultado de elegibilidad como no definitivo.

---

### User Story 3 - Determinar el cargo base y el porcentaje aplicable (Priority: P3)

La abogada necesita saber sobre qué cargo se va a liquidar el haber y con qué porcentaje. El
motor recorre la historia de servicios, identifica el cargo de mayor jerarquía desempeñado
durante 36 meses consecutivos o 60 alternados, muestra exactamente qué períodos lo sustentan y
por qué descartó los otros candidatos, y determina el porcentaje aplicable según el inciso por el
que accede y su excedente de edad.

**Why this priority**: Es el corazón discutible del cálculo y lo que un abogado va a auditar
primero. Entregado solo, ya permite que un profesional complete el monto con su propia valuación
del cargo.

**Independent Test**: Se prueba con historias de servicios donde el cargo base correcto es
conocido, verificando que el motor lo elige, enumera los períodos que lo sustentan y descarta los
candidatos con su razón, sin depender de la grilla salarial.

**Acceptance Scenarios**:

1. **Given** una historia con un cargo de Director ejercido 40 meses consecutivos y un cargo de
   Maestro ejercido 25 años, **When** se determina el cargo base, **Then** el motor elige el de
   mayor jerarquía que cumple el requisito temporal, lista los meses que lo sustentan y cita
   `[DL 9650/80, art. 41 (texto Ley 13968); Res. IPS 14/10]`.
2. **Given** un cargo ejercido 60 meses alternados pero nunca 36 consecutivos, **When** se
   determina el cargo base, **Then** el motor lo acepta por la vía de los 60 alternados y lo
   explica.
3. **Given** un cargo de Director ejercido solo 20 meses y un cargo de Vicedirector ejercido 48
   meses consecutivos, **When** se determina el cargo base, **Then** el motor descarta el de
   Director por no alcanzar los 36/60 meses, considera a la persona comprendida en el inferior y
   regula el haber por Vicedirector, explicándolo `[DL 9650/80, art. 41]`.
4. **Given** una historia en la que ningún cargo alcanza los 36 consecutivos ni los 60
   alternados, **When** se determina el cargo base, **Then** el motor informa que correspondería
   el promedio de 36 meses del tercer párrafo del art. 41 y lo reporta como fuera de alcance v1,
   sin calcular.
5. **Given** una docente que accede por el inc. b y que alcanzó todas las condiciones del inciso
   5 años antes de la fecha de cese, **When** se determina el porcentaje, **Then** el motor
   aplica el 85 % contando el excedente desde que se cumplieron todas las condiciones, y cita
   `[DL 9650/80, art. 43; Res. IPS 995/2021, Anexo, punto 2.1.a]`.
6. **Given** una docente que completa sus 25 años de servicio a los 54 años de edad, **When** se
   determinan los porcentajes, **Then** el motor aplica el **75 %** al habilitarse el derecho
   (excedente 0, porque recién allí se cumplen todas las condiciones) y el **80 %** tres años
   después, y advierte que bajo la lectura literal de los arts. 42 y 43 —que mediría el excedente
   solo por la edad respecto de los 50 requeridos— el porcentaje inicial sería mayor.
7. **Given** una docente que accede por el inc. d sin excedente, **When** se determina el
   porcentaje, **Then** el motor aplica el 70 % y cita `[DL 9650/80, art. 41]`.
8. **Given** un período cuyo cargo el catálogo clasifica como al frente de alumnos por la
   Ley 13469 pero cuya extensión a ese cargo está discutida, **When** se determina el inciso y el
   porcentaje, **Then** el motor marca el resultado como provisional y advierte el impacto
   posible de 70 % vs 75 % `[Ley 13469 — NO_VERIFICADA; SCBA causa A 74801 (2020); Cuestión
   abierta #8]`.
9. **Given** cualquier combinación de entradas, **When** se determina el porcentaje, **Then** el
   resultado nunca supera el máximo legal del artículo aplicable.

---

### User Story 4 - Estimar el haber con la grilla aprobada (Priority: P4)

La abogada obtiene el monto estimado del haber: el motor valúa el cargo base con la grilla
salarial aprobada que corresponde a la fecha de cese, aplica el porcentaje y expone el monto
junto con la versión exacta de grilla utilizada y su norma de origen.

**Why this priority**: Es lo que la docente quiere saber, pero depende de las tres historias
anteriores y de que exista al menos una grilla aprobada cargada.

**Independent Test**: Se prueba con un cargo base y un porcentaje fijos y una grilla aprobada
conocida, verificando el monto resultante y que el informe declara la versión de grilla.

**Acceptance Scenarios**:

1. **Given** un cargo base determinado y una grilla aprobada vigente a la fecha de cese, **When**
   se calcula el haber, **Then** el motor devuelve el monto, la versión de grilla, su norma de
   origen y su fecha de vigencia.
2. **Given** que la grilla vigente a la fecha de cese no está cargada o no fue aprobada, **When**
   se calcula el haber, **Then** el motor advierte la situación, indica con qué grilla calculó y
   marca el monto como no definitivo.
3. **Given** dos corridas idénticas del mismo caso, **When** se comparan los montos, **Then** son
   exactamente iguales, sin diferencias por redondeo ni por orden de carga de los períodos.
4. **Given** un haber calculado, **When** se inspecciona el informe, **Then** el monto lleva
   visible el aviso de que es una estimación orientativa que no reemplaza el cálculo oficial del
   IPS.
5. **Given** un haber condicionado por reglas `NO_VERIFICADA`, **When** se exporta el informe en
   cualquier formato o se lee el monto por la interfaz de librería, **Then** el monto viaja
   siempre acompañado de su marca de provisional y de la lista de reglas que lo condicionan: no
   existe ninguna vía de salida que entregue el número sin ellas.
6. **Given** cualquier informe, **When** lo consume otra herramienta, **Then** encuentra un estado
   general legible por máquina cuyo valor es `definitivo` o `provisional`.

---

### User Story 5 - Comparar escenarios de cese (Priority: P5)

La abogada carga varias fechas de cese posibles —o deja que el motor las derive— y obtiene una
comparación: la fecha en que se habilita el derecho, la fecha en que alcanza el excedente de 3
años de edad y la de 5 años, cada una con su porcentaje y su monto estimado. Con eso puede
aconsejar a la docente cuándo le conviene cesar.

**Why this priority**: Es el valor diferencial del producto —responder "¿me conviene esperar?"—
pero requiere que el cálculo de una sola fecha ya funcione y sea confiable.

**Independent Test**: Se prueba con un caso cuyo escenario de habilitación y excedentes son
conocidos, verificando las tres fechas, sus porcentajes y el orden de la comparación.

**Acceptance Scenarios**:

1. **Given** una docente que se habilita en 2030 por el inc. b, **When** se generan los
   escenarios, **Then** el motor informa la fecha de habilitación (75 %), la fecha del excedente
   de 3 años (80 %) y la de 5 años (85 %) —contadas desde que se cumplieron todas las
   condiciones del inciso `[Res. IPS 995/2021, Anexo, punto 2.1.a]`— cada una con su monto
   estimado y con la advertencia de la lectura literal alternativa (FR-027b).
2. **Given** varias fechas de cese provistas por el usuario, **When** se generan los escenarios,
   **Then** el motor evalúa cada una y las presenta en orden cronológico con su resultado.
3. **Given** una fecha de cese anterior a la habilitación del derecho, **When** se evalúa,
   **Then** el motor informa que a esa fecha no hay derecho y cuánto falta, sin emitir monto.
4. **Given** escenarios de cese futuros, **When** se valúa el cargo base, **Then** el motor usa la
   última grilla aprobada, aplica la antigüedad que la docente tendría a esa fecha y aclara que
   los montos están expresados a valores de hoy.
5. **Given** una docente que a la fecha del escenario todavía no alcanzó el tope de la escala de
   antigüedad, **When** se valúa el cargo, **Then** la bonificación por antigüedad crece respecto
   del escenario de habilitación, y el motor lo muestra como un paso del desglose.
6. **Given** cualquier escenario con monto, **When** se lee el informe, **Then** incluye la
   aclaración de que el haber es móvil `[DL 9650/80, art. 50]` y que el motor no proyecta esa
   movilidad.

---

### User Story 6 - Ejecutar el motor desde la línea de comandos (Priority: P6)

Un gremio con decenas de consultas necesita correr el motor sobre un archivo de caso desde una
terminal, sin instalar una aplicación web ni depender de ningún servicio, y obtener el informe
estructurado en su salida para archivarlo junto al expediente.

**Why this priority**: Habilita el uso operativo y la auditoría reproducible por terceros, pero
el valor de cálculo ya está entregado por las historias anteriores usando el motor como librería.

**Independent Test**: Se prueba invocando el ejecutable con un archivo de caso de ejemplo y
verificando que emite el informe completo y el código de salida correcto, con la máquina
desconectada de la red.

**Acceptance Scenarios**:

1. **Given** un archivo de caso válido, **When** se invoca el motor desde la línea de comandos,
   **Then** emite el informe estructurado completo y termina con código de salida de éxito.
2. **Given** un archivo de caso con datos faltantes o inválidos, **When** se invoca el motor,
   **Then** emite un mensaje accionable que nombra el campo y el período con problema, y termina
   con un código de salida distinto de éxito.
3. **Given** la máquina sin conexión de red, **When** se invoca el motor, **Then** produce el
   mismo informe que produciría con red.
4. **Given** una corrida completa, **When** se inspecciona la salida de diagnóstico, **Then** no
   contiene ningún dato personal (nombre, CUIL, fecha de nacimiento, montos individuales).

---

### Edge Cases

- ¿Qué pasa cuando el caso cae **fuera del Alcance de la v1** (simultaneidad a calcular, otras
  cajas, establecimientos privados, invalidez, recibos escaneados)? El sistema lo **detecta y lo
  informa**; nunca lo aproxima (Principio X).
- ¿Qué pasa cuando falta un dato o un período no está cubierto por los recibos? El resultado
  parcial se explica con su advertencia (Principio IV).
- ¿Qué pasa si dos períodos de la historia de servicios se superponen en el tiempo? Se detecta
  como posible simultaneidad o como error de carga, y se pide al usuario que lo confirme.
- ¿Qué pasa si un período tiene fecha de fin anterior a la de inicio? Se rechaza con un mensaje
  que nombra el período y el campo (FR-003).
- ¿Qué pasa si un período se extiende más allá de la fecha de cese evaluada? No se rechaza: se
  **recorta** a esa fecha, y cada fecha de cese del mismo caso recorta de forma independiente
  (FR-018a).
- ¿Qué pasa si un período no declara fecha de fin? Es un período en curso: se proyecta hasta cada
  fecha de cese bajo supuesto de continuidad en el mismo cargo, el supuesto queda en la
  procedencia y como advertencia, y condiciona todo monto que dependa de él (FR-002e).
- ¿Qué pasa si dos períodos simultáneos cubren el mismo año? Aporta **un** año de servicio, no
  dos: el cómputo es sobre la unión de tramos temporales (FR-004a).
- ¿Qué pasa si el mismo cargo en el mismo establecimiento aparece dos veces solapado? Se clasifica
  como posible error de carga, no como simultaneidad, y se pide confirmación (FR-004).
- ¿Qué pasa si el caso no declara fecha de cálculo? La línea de comandos la completa con la fecha
  del sistema; el motor como librería la exige. El motor nunca lee el reloj (FR-001a).
- ¿Qué pasa con las licencias sin goce de haberes dentro del cómputo de los 36/60 meses y de los
  años de servicio? Depende de la Cuestión abierta #5; hasta resolverla la regla es
  `NO_VERIFICADA` y el motor advierte el impacto.
- ¿Qué pasa si la historia de servicios no alcanza el mínimo de 22 años con aportes? Se informa
  el faltante sin calcular haber `[DL 9650/80, art. 24]`.
- ¿Qué pasa si la fecha de cese es futura y la grilla de esa fecha todavía no existe? Se valúa
  con la última grilla aprobada, a valores de hoy, aplicando la antigüedad que la persona tendría
  a esa fecha, y el informe lo aclara junto con la movilidad del art. 50 (FR-030a a FR-030c).
- ¿Qué pasa si a la fecha del escenario futuro la persona ya alcanzó el tope de la escala de
  antigüedad? La bonificación deja de crecer; como el tope es una regla `NO_VERIFICADA`, el monto
  queda marcado como provisional.
- ¿Qué pasa si la docente no alcanza los requisitos con servicios docentes pero tiene no docentes
  aportados al IPS? Se advierte que el prorrateo del art. 27 podría completarlos y la elegibilidad
  se marca como no definitiva (FR-015a).
- ¿Qué pasa si alguien intenta exportar o leer el monto sin su marca de provisional? No es
  posible: la marca viaja con el monto por toda vía de salida (FR-046a).
- ¿Qué pasa si dos cargos empatan en jerarquía para el cargo base? El criterio de comparación es
  la Cuestión abierta #4; hasta resolverla el motor informa el empate como advertencia.
- ¿Qué pasa si el cargo de mayor jerarquía no llega a los 36 consecutivos ni a los 60 alternados?
  Se regula por el cargo inferior que sí los alcance, y el descenso se explica en el desglose
  (FR-020a).
- ¿Qué pasa si ningún cargo alcanza los 36/60 meses? Correspondería el promedio de 36 meses del
  tercer párrafo del art. 41: se detecta y se informa como fuera de alcance v1, sin calcular
  (FR-020b).
- ¿Qué pasa si el cargo de un período no figura en el catálogo de cargos? El motor no adivina su
  condición: la marca como indeterminada, lo advierte y el resultado queda provisional.
- ¿Qué pasa si el usuario corrige la condición de al frente de alumnos que derivó el catálogo?
  Se respeta, pero el dato queda marcado como manual y el informe señala que difiere del catálogo
  (FR-002b).
- ¿Qué pasa si la historia de servicios está vacía o tiene un solo período corto? Se informa que
  no hay derecho y qué falta, sin error técnico.

## Requirements *(mandatory)*

### Functional Requirements

#### Entrada del caso

- **FR-001**: El motor DEBE aceptar la fecha de nacimiento de la persona y una o más fechas de
  cese a evaluar.
- **FR-001a**: El caso DEBE declarar una **fecha de cálculo** explícita. El motor NUNCA consulta
  el reloj del sistema: toda validación o derivación relativa a "hoy" usa esa fecha. La interfaz
  de línea de comandos la completa con la fecha del sistema cuando el usuario no la provee, y el
  informe la declara `[Principio II]`.
- **FR-002**: El motor DEBE aceptar una historia de servicios como lista de períodos, donde cada
  período declara: cargo u horas cátedra/módulos, establecimiento estatal de la DGCyE, fecha de
  inicio, fecha de fin (**opcional**), caja de aportes, situación de revista y las licencias con
  su tipo y fechas. La condición de **al frente de alumnos** y la **naturaleza del servicio**
  (docente / no docente) NO son datos de entrada libres: se derivan del cargo (FR-002a, FR-002d).
- **FR-002d**: La **naturaleza del servicio** (docente o no docente) DEBE derivarse del cargo
  mediante el mismo catálogo versionado que resuelve la condición de al frente de alumnos. Es
  corregible por el usuario con el mismo tratamiento de dato manual que FR-002b. La **caja de
  aportes** sí es un dato de entrada del período, porque depende de la relación de empleo y no
  del cargo.
- **FR-002e**: Un período PUEDE no declarar fecha de fin, representando un **período en curso**.
  Para cada fecha de cese evaluada, el motor DEBE proyectar ese período hasta esa fecha bajo el
  **supuesto de continuidad en el mismo cargo**, registrar el supuesto en la procedencia (FR-039)
  y emitir una advertencia. El supuesto condiciona todo monto que dependa de él (FR-046a).
- **FR-002a**: El motor DEBE derivar la condición de al frente de alumnos **a partir del cargo**,
  usando un **catálogo de cargos versionado** que declara, por cada cargo, su condición y la
  norma que la sostiene. El catálogo DEBE incluir al menos: preceptores y bibliotecarios
  `[Ley 13469]`, técnico-docentes de Psicología y Educación Especial `[Ley 10745]` y visitadoras
  de higiene escolar `[Ley 11860]`.
- **FR-002b**: El usuario PUEDE corregir la condición derivada para un período. Cuando lo hace,
  el dato DEBE quedar registrado como **manual** en la procedencia (FR-039) y el informe DEBE
  señalar que difiere de lo que indica el catálogo.
- **FR-002c**: El alcance de la Ley 13469 respecto de **otros cargos del escalafón** no incluidos
  explícitamente DEBE marcarse como no definitivo: cuando la elegibilidad o el porcentaje de un
  caso dependen de esa extensión, el resultado se marca como provisional y la advertencia indica
  el impacto posible `[Ley 13469 — NO_VERIFICADA: interpretación discutida, SCBA causa A 74801
  (2020); Cuestión abierta #8 — impacto 70 % vs 75 %]`.
- **FR-003**: El motor DEBE validar la coherencia temporal de cada período (fin posterior o igual
  al inicio cuando el fin se declara, fechas dentro de rangos plausibles respecto de la fecha de
  cálculo) y rechazar la entrada inválida nombrando el período y el campo afectado. Que un
  período supere la fecha de cese evaluada NO es una entrada inválida: se recorta (FR-018a).
- **FR-004**: El motor DEBE detectar toda superposición temporal entre períodos y clasificarla
  en exactamente una de tres categorías, sin resolverla por su cuenta:
  1. **`simultaneidad_computable_art47`**: el solapamiento dura 3 años continuos o más **y**
     alcanza al cargo base. Es la que tendría incidencia en el haber por el art. 47, y la que el
     motor detecta y advierte sin calcular `[DL 9650/80, art. 47; Res. IPS 995/2021]`.
  2. **`simultaneidad_no_computable`**: solapamiento real de cargos distintos que no reúne las
     condiciones anteriores. Se informa, sin impacto en el haber.
  3. **`posible_error_carga`**: solapamiento del **mismo cargo en el mismo establecimiento**, que
     casi siempre indica una carga duplicada. Se informa para que el usuario lo confirme o lo
     corrija.
- **FR-004a**: Los años de servicio y los meses que sustentan el cargo base DEBEN computarse
  sobre la **unión de los tramos temporales** cubiertos por los períodos, nunca sumando las
  duraciones de períodos que se superponen. Dos cargos simultáneos durante un mismo año aportan
  un año de servicio, no dos.
- **FR-005**: El motor NO DEBE requerir ni aceptar archivos PDF ni ninguna forma de extracción
  automática de recibos en esta funcionalidad.

#### Reglas y grillas como datos versionados

- **FR-006**: Las reglas del régimen DEBEN estar expresadas como datos versionados que declaran,
  por cada regla: la norma de origen, su vigencia desde/hasta, su fecha de verificación y su
  estado (`Verificado` o `NO_VERIFICADA`) `[Principio I]`.
- **FR-007**: Ningún porcentaje, edad, plazo mínimo, tope ni escala normativa puede estar escrito
  dentro de la lógica de cálculo; todos provienen del conjunto de reglas versionado
  `[Principio I]`.
- **FR-008**: Las grillas salariales DEBEN estar expresadas como datos versionados que declaran
  norma de origen, enlace, vigencia, fecha de extracción y quién las aprobó `[Principio IX]`.
- **FR-009**: Todo informe DEBE declarar la versión del conjunto de reglas y la versión de grilla
  con las que fue producido `[Principio IV]`.
- **FR-010**: El motor NO DEBE usar nunca una grilla que no esté aprobada `[Principio IX]`.

#### Elegibilidad (art. 24)

- **FR-011**: El motor DEBE determinar si se cumple el inciso b (50 años de edad y 25 años de
  servicios al frente de alumnos o 20 horas cátedra), computando la condición de al frente de
  alumnos según la deriva el catálogo de cargos (FR-002a)
  `[DL 9650/80, art. 24 inc. b]`.
- **FR-012**: El motor DEBE determinar si se cumple el inciso c (50 años de edad y 25 años de
  servicios, de los cuales 10 al frente de alumnos), computando esa condición según la deriva el
  catálogo de cargos (FR-002a) `[DL 9650/80, art. 24 inc. c]`.
- **FR-013**: El motor DEBE determinar si se cumple el inciso d (55 años de edad y 30 años de
  servicios) `[DL 9650/80, art. 24 inc. d]`.
- **FR-014**: El motor DEBE verificar el mínimo general de 22 años con aportes y, si no se
  alcanza, informar el faltante sin emitir haber `[DL 9650/80, art. 24]`.
- **FR-015**: El motor DEBE detectar los períodos no docentes aportados al IPS, computar la
  elegibilidad únicamente con los servicios docentes, y advertir que los no docentes quedan sin
  computar. NO DEBE aplicar el prorrateo `[DL 9650/80, art. 27 — fuera de alcance v1]`.
- **FR-015a**: Cuando los servicios docentes NO alcanzan ningún inciso del art. 24 y existen
  períodos no docentes aportados al IPS, la advertencia DEBE indicar explícitamente que esos
  servicios podrían completar los requisitos mediante el prorrateo `[DL 9650/80, art. 27]`, y el
  resultado de elegibilidad DEBE marcarse como no definitivo.
- **FR-016**: Para cada inciso, el motor DEBE informar la fecha desde la cual queda habilitado el
  derecho, o cuánto falta en edad y en servicios para habilitarlo.
- **FR-017**: Cuando más de un inciso se cumple, el motor DEBE informar todos e indicar cuál
  resulta más favorable y por qué.
- **FR-018**: El motor DEBE cerrar los cómputos a la fecha de cese evaluada, sin computar
  servicios posteriores `[DL 9650/80, arts. 71 y 72]`.
- **FR-018a**: Un período que se extiende más allá de la fecha de cese evaluada NO DEBE
  rechazarse: se **recorta** a esa fecha. El mismo caso puede evaluarse contra varias fechas de
  cese, y cada una recorta de forma independiente.

#### Cargo base (art. 41)

- **FR-019**: El motor DEBE identificar el cargo de mayor jerarquía desempeñado durante 36 meses
  consecutivos o 60 meses alternados, anteriores al cese
  `[DL 9650/80, art. 41 (texto Ley 13968); Res. IPS 14/10]`.
- **FR-020**: El motor DEBE exponer, para el cargo base elegido, los períodos concretos que lo
  sustentan y la vía por la que califica (36 consecutivos o 60 alternados).
- **FR-020a**: Si el cargo de mayor jerarquía NO alcanza los 36 meses consecutivos ni los 60
  alternados, el motor DEBE considerar a la persona comprendida en el **cargo inferior** que sí
  los alcance y regular el haber por este, explicando el descenso en el desglose
  `[DL 9650/80, art. 41]`.
- **FR-020b**: Cuando no puede determinarse ningún cargo por la vía de los 36/60 meses y
  correspondería recurrir al **promedio de los 36 meses** previsto en el tercer párrafo del
  art. 41, el motor DEBE detectar la situación e informarla como **fuera de alcance v1**, sin
  calcular `[DL 9650/80, art. 41, tercer párrafo — fuera de alcance v1]`.
- **FR-021**: El motor DEBE exponer los cargos candidatos descartados y la razón del descarte,
  incluido el caso en que un cargo de mayor jerarquía se descarta por no alcanzar los 36/60 meses
  (FR-020a).
- **FR-022**: El criterio de comparación de jerarquía entre cargos DEBE provenir del conjunto de
  reglas versionado y, mientras siga sin verificarse, el motor DEBE marcar la elección como no
  definitiva `[Res. IPS 14/10 — NO_VERIFICADA: criterio puntaje/índice vs remuneración, Cuestión
  abierta #4]`.
- **FR-023**: El tratamiento de horas cátedra y módulos como carrera a los efectos del cargo base
  DEBE marcarse como no definitivo hasta verificar la norma
  `[Res. HD IPS 8/14 — NO_VERIFICADA, Cuestión abierta #3]`.
- **FR-024**: El cómputo de licencias, suplencias e interinatos dentro de los 36/60 meses DEBE
  marcarse como no definitivo hasta verificar el criterio
  `[NO_VERIFICADA, Cuestión abierta #5]`.
- **FR-024a**: Si la **situación de revista** (titular, provisional, suplente) condiciona o no la
  elección del cargo base DEBE marcarse como no definitivo, dado que el art. 41 se refiere al
  cargo "de que era titular" `[DL 9650/80, art. 41 — NO_VERIFICADA, Cuestión abierta #5]`.

#### Porcentaje aplicable (arts. 41, 42 y 43)

- **FR-025**: El motor DEBE aplicar el 70 % de la remuneración del cargo base como haber base
  general `[DL 9650/80, art. 41]`.
- **FR-026**: El motor DEBE elevar el porcentaje al 75 % y al 80 % por excedente de 3 y 5 años
  respectivamente `[DL 9650/80, art. 42]`.
- **FR-027**: Para el acceso por el inciso b, el motor DEBE aplicar el 75 % de base y elevarlo al
  80 % y 85 % por excedente de 3 y 5 años `[DL 9650/80, art. 43]`.
- **FR-027a**: Por defecto, el excedente DEBE contarse **desde la fecha en que se alcanzan todas
  las condiciones del inciso aplicable** (edad y servicios), no solo desde que se alcanza la edad
  requerida `[Res. IPS 995/2021, Anexo, punto 2.1.a — Interpretación]`.
- **FR-027b**: El informe DEBE advertir que existe una **lectura literal de los arts. 42 y 43**
  según la cual el excedente se mide únicamente por la edad respecto de la edad requerida por el
  inciso, y que esa lectura tendría impacto **al alza** sobre el porcentaje. La advertencia DEBE
  indicar el porcentaje que correspondería bajo esa lectura alternativa
  `[DL 9650/80, arts. 42 y 43 — lectura literal; Res. IPS 995/2021, Anexo, punto 2.1.a — criterio
  aplicado]`.
- **FR-028**: El porcentaje resultante NUNCA DEBE superar el máximo legal del artículo aplicable,
  cualquiera sea la combinación de entradas.
- **FR-029**: El motor DEBE informar la fecha exacta en que la persona alcanza cada excedente,
  contada según FR-027a, para que sea utilizable como escenario de cese.

#### Haber estimado

- **FR-030**: El motor DEBE valuar el cargo base con la grilla aprobada correspondiente a la
  fecha de cese evaluada y aplicar el porcentaje determinado.
- **FR-030a**: Para fechas de cese **futuras**, el motor DEBE valuar el cargo con la **última
  grilla aprobada** disponible, sin proyectar aumentos salariales, y DEBE declarar que los montos
  están expresados a valores de la fecha de esa grilla.
- **FR-030b**: En los escenarios futuros, el motor DEBE aplicar la **antigüedad que la persona
  tendría a la fecha del escenario**; si a esa fecha aún no alcanzó el tope de la escala, la
  bonificación DEBE crecer en consecuencia, y el crecimiento DEBE aparecer como un paso del
  desglose `[Ley 10579 art. 33; Decreto 818/13 — NO_VERIFICADA: tope, Cuestión abierta #1]`.
- **FR-030c**: Todo informe que emita montos DEBE aclarar que el haber es **móvil** y se actualiza
  por correlación con el cargo en actividad, y que el motor NO proyecta esa movilidad
  `[DL 9650/80, art. 50]`.
- **FR-031**: Qué conceptos del recibo integran la remuneración asignada al cargo DEBE provenir
  del conjunto de reglas y marcarse como no definitivo hasta verificarse
  `[DL 9650/80, art. 40 — NO_VERIFICADA, Cuestión abierta #2]`.
- **FR-031a**: El valor de un cargo en la grilla DEBE expresarse como un conjunto de
  **componentes**, cada uno con su código de concepto, su importe, si es **bonificable** (si
  sobre él se aplica la antigüedad) y si es **remunerativo**. El haber no se calcula sobre un
  importe único e indiviso.
- **FR-031b**: La bonificación por antigüedad DEBE aplicarse **únicamente sobre los componentes
  bonificables**, nunca sobre el total del cargo
  `[Ley 10579 art. 33 — NO_VERIFICADA: tope, Cuestión abierta #1]`.
- **FR-032**: La escala de bonificación por antigüedad DEBE marcarse como no definitiva hasta
  confirmar el tope vigente `[Ley 10579 art. 33; Decreto 818/13 — NO_VERIFICADA: tope 120 % vs
  125 %, Cuestión abierta #1]`.
- **FR-033**: Todo cálculo monetario y porcentual DEBE usar aritmética decimal exacta, y el
  redondeo DEBE aplicarse en un único punto con una política explícita; esa política DEBE
  marcarse como no definitiva hasta verificar la que aplica el IPS
  `[NO_VERIFICADA, Cuestión abierta #6]` `[Principio II]`.
- **FR-034**: Cuando la grilla vigente a la fecha de cese no está cargada o aprobada, el motor
  DEBE advertirlo, indicar con qué grilla calculó y marcar el monto como no definitivo.

#### Escenarios de cese

- **FR-035**: Para cada fecha de cese evaluada, el motor DEBE emitir un escenario con su
  porcentaje y su haber estimado, o la razón por la que no hay derecho a esa fecha.
- **FR-036**: El motor DEBE derivar y emitir, además de las fechas provistas, los escenarios de
  habilitación del derecho y de excedentes de 3 y 5 años de edad.
- **FR-036a**: Los escenarios DEBEN ser comparables entre sí: todos valuados con la misma grilla
  (la última aprobada), de modo que las diferencias de monto entre escenarios se expliquen solo
  por el porcentaje aplicable y por la antigüedad acumulada, nunca por cambios de grilla.
- **FR-037**: Los escenarios DEBEN presentarse en orden cronológico y ser comparables entre sí.

#### Transparencia del informe

- **FR-038**: El informe DEBE incluir un desglose paso a paso del cálculo, donde cada paso declara
  la regla aplicada y su norma de origen `[Principio IV]`.
- **FR-039**: El informe DEBE declarar la procedencia de cada dato utilizado: cargado a mano o
  inferido por el motor, y en este último caso de qué se infirió `[Principio IV]`.
- **FR-040**: El informe DEBE distinguir la letra de la ley de las interpretaciones (criterios del
  IPS, jurisprudencia, práctica administrativa) e identificar cada una como tal `[Principio I]`.
- **FR-041**: El informe DEBE listar todas las advertencias aplicables: datos faltantes, períodos
  sin cubrir, simultaneidad detectada, reglas `NO_VERIFICADA` y situaciones fuera de alcance
  `[Principio IV]`.
- **FR-042**: El informe DEBE decir de forma visible que es una estimación orientativa que no
  reemplaza el cálculo oficial del IPS ni el asesoramiento profesional `[Principio IV]`.

#### Límites, advertencias y negativa a calcular

- **FR-043**: El motor DEBE detectar cargos simultáneos con un mínimo de 3 años continuos,
  advertir su posible impacto en el haber y NO calcular el incremento
  `[DL 9650/80, art. 47; Res. IPS 995/2021 — fuera de alcance v1]`.
- **FR-044**: El motor DEBE detectar servicios aportados a otras cajas y reportarlos como fuera de
  alcance sin computarlos `[DL 9650/80, arts. 66 y 67 — fuera de alcance v1]`.
- **FR-045**: El motor DEBE detectar establecimientos de gestión privada, solicitudes de
  jubilación por invalidez o por edad avanzada, y pensiones, y reportarlos como fuera de alcance
  sin calcular.
- **FR-045a**: Un caso fuera de alcance NO DEBE abortar el cálculo. El motor DEBE devolver un
  informe con **todo lo que sí puede sostener** (elegibilidad parcial, detecciones, desglose de
  lo computado), **sin haber**, y con una advertencia marcada como **bloqueante** por cada
  situación detectada. El profesional necesita saber qué parte del caso sí se pudo analizar; una
  negativa total le quita información que el motor tenía `[Principio IV]`.
- **FR-045b**: La interfaz de línea de comandos DEBE devolver el código de salida de caso fuera
  de alcance cuando el informe contenga al menos una advertencia bloqueante (FR-056).
- **FR-046**: Cuando una regla `NO_VERIFICADA` interviene en un resultado, el motor DEBE emitir
  el resultado marcado como **provisional**, nunca como definitivo, y explicar qué falta verificar
  `[Principio I]`.
- **FR-046a**: La marca de provisional es **inseparable del monto**: ninguna vía de salida del
  motor —informe, exportación en cualquier formato, o lectura por la interfaz de librería— puede
  entregar el monto sin su marca y sin la lista de **condicionantes**. Una salida que omita la
  marca es un defecto bloqueante.
- **FR-046b**: El informe DEBE listar cada **condicionante** del monto indicando, para cada uno,
  **en qué sentido podría alterarlo**: al alza, a la baja o indeterminado, con la magnitud
  estimada cuando se la pueda acotar. Un condicionante es una regla `NO_VERIFICADA` **o** una
  **situación del caso** que introduce incertidumbre: grilla ausente (FR-034), cargo fuera del
  catálogo, corrección manual de un dato derivado (FR-002b, FR-002d) o supuesto de continuidad de
  un período en curso (FR-002e).
- **FR-046c**: El resultado DEBE exponer un **estado general legible por máquina** con valor
  `definitivo` o `provisional`, de modo que una herramienta que consuma el informe pueda bloquear
  automáticamente el uso de un monto provisional sin interpretar texto.
- **FR-047**: Cuando faltan datos para completar un cálculo, el motor DEBE entregar el resultado
  parcial que sí puede sostener, explicado, en lugar de un resultado completo pero dudoso
  `[Principio IV]`.

#### Determinismo, independencia y privacidad

- **FR-048**: Las mismas entradas con la misma versión de reglas y la misma versión de grilla
  DEBEN producir siempre el mismo resultado `[Principio II]`.
- **FR-049**: El orden en que se cargan los períodos de la historia de servicios NO DEBE alterar
  el resultado `[Principio II]`.
- **FR-050**: Ningún modelo de lenguaje ni componente probabilístico puede participar del cálculo
  `[Principio II]`.
- **FR-051**: El motor DEBE poder ejecutarse localmente, sin red, tanto como librería mediante una
  interfaz pública y documentada como desde la línea de comandos, con resultados idénticos por
  ambas vías `[Principio V]`.
- **FR-052**: El motor NO DEBE depender de la aplicación web, de la base de datos de
  organizaciones ni de la facturación `[Principio V]`.
- **FR-053**: El motor NO DEBE persistir ningún dato del caso ni escribirlo a disco, salvo el
  informe que el usuario solicita explícitamente `[Principio III]`.
- **FR-054**: Ningún dato personal (nombre, CUIL, fecha de nacimiento, montos individuales,
  cargos) puede aparecer en logs, métricas, trazas ni reportes de error `[Principio III]`.

#### Interfaz de línea de comandos

- **FR-055**: La línea de comandos DEBE aceptar un archivo de caso y emitir el informe
  estructurado completo en su salida.
- **FR-056**: La línea de comandos DEBE devolver códigos de salida distinguibles para éxito,
  entrada inválida, caso fuera de alcance y error interno.
- **FR-057**: Ante entrada inválida, el mensaje DEBE nombrar el campo y el período afectado y
  describir la corrección posible `[Principio VIII]`.

### Fundamento normativo *(obligatorio si la funcionalidad calcula algo)*

| Requisito | Norma (ley, art., inc. / resolución) | Tipo | Estado | Verificada el |
|---|---|---|---|---|
| FR-002a | Ley 13469 (preceptores y bibliotecarios) | Letra de la ley | Verificado para los cargos nombrados | 2026-10-30 |
| FR-002a | Ley 10745 (técnico-docentes de Psicología y Educación Especial) | Letra de la ley | Verificado | 2026-10-30 |
| FR-002a | Ley 11860 (visitadoras de higiene escolar) | Letra de la ley | Verificado | 2026-10-30 |
| FR-002c | Ley 13469 — extensión a otros cargos del escalafón | Interpretación (discutida; SCBA causa A 74801, 2020) | NO_VERIFICADA (impacto 70 % vs 75 %) | — |
| FR-011 | DL 9650/80, art. 24 inc. b | Letra de la ley | Verificado | 2026-10-30 |
| FR-012 | DL 9650/80, art. 24 inc. c | Letra de la ley | Verificado | 2026-10-30 |
| FR-013 | DL 9650/80, art. 24 inc. d | Letra de la ley | Verificado | 2026-10-30 |
| FR-014 | DL 9650/80, art. 24 (mínimo 22 años con aportes) | Letra de la ley | Verificado | 2026-10-30 |
| FR-004 | DL 9650/80, art. 47; Res. IPS 995/2021 (clasificación de la simultaneidad) | Letra de la ley + interpretación | Verificado — se clasifica y se advierte, no se computa | 2026-10-30 |
| FR-015, FR-015a | DL 9650/80, art. 27 (prorrateo) | Letra de la ley | Verificado — fuera de alcance v1 (se detecta y se advierte, no se computa) | 2026-10-30 |
| FR-018 | DL 9650/80, arts. 71 y 72 (cese y cierre de cómputos) | Letra de la ley | Verificado | 2026-10-30 |
| FR-019, FR-020 | DL 9650/80, art. 41 (texto Ley 13968) | Letra de la ley | Verificado (alcance de Ley 14025 a revisar) | 2026-10-30 |
| FR-020a | DL 9650/80, art. 41 (cargo inferior cuando el superior no alcanza 36/60) | Letra de la ley | Verificado | 2026-10-30 |
| FR-020b | DL 9650/80, art. 41, tercer párrafo (promedio de 36 meses) | Letra de la ley | Fuera de alcance v1 | 2026-10-30 |
| FR-022 | Res. IPS 14/10 (acreditación de mayor jerarquía) | Interpretación | NO_VERIFICADA | — |
| FR-023 | Res. HD IPS 8/14 (horas cátedra y módulos como carrera) | Interpretación | NO_VERIFICADA | — |
| FR-024 | Criterio de cómputo de licencias, suplencias e interinatos | Interpretación | NO_VERIFICADA | — |
| FR-024a | DL 9650/80, art. 41 (cargo "de que era titular" vs situación de revista) | Interpretación | NO_VERIFICADA | — |
| FR-025 | DL 9650/80, art. 41 (70 % del cargo) | Letra de la ley | Verificado | 2026-10-30 |
| FR-026 | DL 9650/80, art. 42 (75 % / 80 % por excedente 3 / 5) | Letra de la ley | Verificado | 2026-10-30 |
| FR-027 | DL 9650/80, art. 43 (75 / 80 / 85 % docente inc. b) | Letra de la ley | Verificado | 2026-10-30 |
| FR-027a | Res. IPS 995/2021, Anexo, punto 2.1.a (excedente contado desde que se cumplen todas las condiciones) | Interpretación | Verificado — criterio aplicado por defecto | 2026-10-30 |
| FR-027b | DL 9650/80, arts. 42 y 43 — lectura literal (excedente medido solo por edad) | Letra de la ley (lectura alternativa) | Se informa como advertencia, impacto al alza | 2026-10-30 |
| FR-031 | DL 9650/80, art. 40 (concepto de remuneración) | Letra de la ley + interpretación de conceptos | NO_VERIFICADA | — |
| FR-030b, FR-031b, FR-032 | Ley 10579 art. 33; Decreto 818/13 y posteriores (bonificación por antigüedad sobre componentes bonificables) | Letra de la ley | NO_VERIFICADA (tope 120 % vs 125 %) | — |
| FR-030c | DL 9650/80, art. 50 (movilidad por correlación de cargos) | Letra de la ley | Verificado — solo se informa, no se calcula | 2026-10-30 |
| FR-033 | Política de redondeo aplicada por el IPS | Práctica administrativa | NO_VERIFICADA | — |
| FR-043 | DL 9650/80, art. 47; Res. IPS 995/2021 | Letra de la ley + interpretación | Verificado (fórmula a detallar) — fuera de alcance v1 | 2026-10-30 |
| FR-044 | DL 9650/80, arts. 66 y 67 (caja otorgante y reciprocidad) | Letra de la ley | Fuera de alcance v1 | 2026-10-30 |

**Reglas `NO_VERIFICADA` en esta funcionalidad**: extensión de la Ley 13469 a otros cargos del
escalafón (FR-002c), criterio de mayor jerarquía (FR-022), horas cátedra y módulos (FR-023),
cómputo de licencias y suplencias (FR-024), incidencia de la situación de revista en el cargo
base (FR-024a), conceptos que integran la remuneración del cargo (FR-031), escala y tope de
antigüedad (FR-032) y política de redondeo (FR-033). En todos los casos el motor entrega el resultado parcial que sí puede sostener, lo marca
como no definitivo, nombra la regla afectada y explica qué falta verificar, en lugar de emitir un
número cerrado (FR-046, FR-047).

**Cuestiones abiertas del dominio que afectan a esta especificación**: #1 (escala de antigüedad),
#2 (remuneración del cargo), #3 (horas cátedra y módulos), #4 (criterio de mayor jerarquía),
#5 (conteo de períodos con licencias) y #6 (redondeo). La #7 (formatos de recibo) no aplica: esta
funcionalidad no lee recibos.

**Ampliación de la Cuestión abierta #5**: además del tratamiento de licencias, suplencias e
interinatos, la #5 DEBE resolver si la **situación de revista** (titular, provisional, suplente)
condiciona la elección del cargo base, dado que el art. 41 se refiere al cargo "de que era
titular" (FR-024a).

**Cuestión abierta #8 (nueva, planteada por esta especificación)**: alcance de la **Ley 13469**
respecto de los cargos del escalafón no nombrados explícitamente en ella, a los efectos de la
condición de al frente de alumnos. La interpretación está discutida (SCBA, causa A 74801, 2020) y
su impacto es de **70 % vs 75 %** sobre el haber base, porque determina si el acceso es por el
inciso b (art. 43) o por los incisos c/d (art. 41). Afecta FR-002a, FR-002c, FR-011 y FR-012.

> **Nota de gobernanza**: la Cuestión abierta #8 fue **incorporada a la constitución** en la
> enmienda **v1.1.0** (2026-10-30), junto con las dos filas del Marco normativo que la sostienen
> (cargos al frente de alumnos por Leyes 13469, 10745 y 11860; y el cómputo del excedente por
> Res. IPS 995/2021, Anexo 2.1.a). La constitución enumera ahora 8 cuestiones abiertas.
>
> **Pendiente**: la ampliación de la Cuestión abierta #5 (si la situación de revista condiciona
> la elección del cargo base, art. 41 "de que era titular", FR-024a) todavía NO está incorporada
> a la constitución. Vive en esta spec y el motor la trata como cualquier otra regla
> `NO_VERIFICADA`; formalizarla requiere otra enmienda MINOR vía `/speckit-constitution`.

### Key Entities

- **Persona**: la docente cuyo beneficio se estima. Atributos mínimos: fecha de nacimiento. No se
  persiste ni se identifica nominalmente en ninguna salida de diagnóstico.
- **Período de servicio**: un tramo de desempeño. Cargo u horas cátedra/módulos, establecimiento,
  caja de aportes, fecha de inicio, fecha de fin **opcional** (ausente = período en curso),
  situación de revista y licencias asociadas. Ni la condición de al frente de alumnos ni la
  naturaleza del servicio se cargan: se derivan del cargo vía el catálogo, y solo pueden
  sobrescribirse manualmente dejando rastro en la procedencia.
- **Fecha de cálculo**: la fecha respecto de la cual el motor evalúa todo lo relativo a "hoy".
  Es una entrada explícita del caso, no el reloj del sistema, y el informe la declara.
- **Superposición**: un solapamiento temporal entre dos períodos, clasificado como simultaneidad
  computable por el art. 47, simultaneidad no computable, o posible error de carga.
- **Componente salarial**: una línea del valor de un cargo en la grilla, con su código de
  concepto, importe, si es bonificable (si la antigüedad se aplica sobre él) y si es
  remunerativo.
- **Catálogo de cargos versionado**: la correspondencia entre cada cargo del escalafón y su
  condición de al frente de alumnos, con la norma que la sostiene y su estado de verificación.
  Incluye los cargos alcanzados por las Leyes 13469, 10745 y 11860.
- **Licencia**: interrupción dentro de un período de servicio, con tipo (con o sin goce de
  haberes) y fechas. Su efecto sobre el cómputo es una regla `NO_VERIFICADA`.
- **Historia de servicios**: el conjunto ordenado de períodos de una persona, con sus
  superposiciones detectadas.
- **Fecha de cese evaluada**: una fecha hipotética de baja sobre la que se corre el cálculo
  completo.
- **Regla**: una norma aplicable expresada como dato. Norma de origen, vigencia desde/hasta, fecha
  de verificación, estado (`Verificado` / `NO_VERIFICADA`), tipo (letra de la ley /
  interpretación).
- **Conjunto de reglas versionado**: la colección de reglas con una versión identificable que el
  informe declara.
- **Grilla salarial**: valores de los cargos con norma de origen, enlace, vigencia, fecha de
  extracción, aprobador y versión. Solo las aprobadas se usan.
- **Cargo base**: el cargo de mayor jerarquía que califica por 36 meses consecutivos o 60
  alternados, con los períodos que lo sustentan y los candidatos descartados con su razón.
- **Escenario de cese**: fecha, inciso por el que accede, porcentaje, haber estimado y
  advertencias propias de esa fecha.
- **Advertencia**: una situación que el usuario debe conocer. Tipo (dato faltante, cada clase de
  simultaneidad, servicios no docentes sin computar, fuera de alcance, regla no verificada,
  grilla ausente, cargo fuera de catálogo, supuesto de continuidad, dato corregido a mano), norma
  asociada si la tiene, su efecto sobre el resultado, si **bloquea el cálculo** del haber y,
  cuando condiciona un monto, el sentido del impacto posible.
- **Condicionante**: aquello que impide que un monto sea definitivo. Es una regla
  `NO_VERIFICADA` **o** una situación del caso (grilla ausente, cargo fuera de catálogo,
  corrección manual, supuesto de continuidad). Viaja siempre junto al monto.
- **Estado del resultado**: el veredicto general del informe, `definitivo` o `provisional`,
  legible por máquina, derivado de las reglas `NO_VERIFICADA` y las situaciones detectadas que
  intervinieron. Acompaña inseparablemente a todo monto emitido.
- **Paso del desglose**: una operación del cálculo con su entrada, su salida, la regla aplicada y
  su norma.
- **Informe**: el resultado completo. Estado del resultado, escenarios, cargo base, desglose,
  procedencia de los datos, versión de reglas, versión de grilla, advertencias, el aviso de
  estimación orientativa y la aclaración de movilidad del art. 50.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las reglas de cálculo aplicadas en cualquier informe cita su norma
  (ley, artículo, inciso o resolución); una auditoría de un informe cualquiera no encuentra ningún
  número sin fuente.
- **SC-002**: El motor reproduce exactamente, con diferencia cero, el haber de los casos reales
  del IPS ya otorgados que integran el conjunto de casos dorados. Cada caso dorado se valúa con
  la **grilla histórica vigente a la fecha del cese real de ese caso**, no con la última grilla
  aprobada: la comparación contra el haber efectivamente otorgado solo es válida a valores de su
  propia época.
- **SC-003**: Dos corridas del mismo caso con las mismas versiones de reglas y grilla producen
  informes idénticos, incluido el orden de los escenarios y las advertencias.
- **SC-004**: El 100 % de los casos fuera de alcance se detecta y se informa; ningún caso fuera de
  alcance recibe un haber calculado.
- **SC-005**: Un abogado previsional que no conoce el proyecto puede rastrear cualquier número del
  informe hasta su norma de origen y su dato de entrada sin consultar al equipo de desarrollo.
- **SC-006**: Un caso de 30 años de historia de servicios con 5 escenarios de cese produce su
  informe completo en menos de 5 segundos en una computadora de escritorio común.
- **SC-007**: El motor produce resultados idénticos con la máquina desconectada de la red.
- **SC-008**: Una corrida completa no deja ningún dato personal en su salida de diagnóstico,
  verificable inspeccionando la salida de un caso con datos conocidos.
- **SC-009**: Ningún informe presenta como definitivo un resultado que depende de una regla
  `NO_VERIFICADA`; todos ellos salen marcados como provisionales.
- **SC-010**: Cambiar el orden de carga de los períodos de la historia de servicios no altera
  ningún valor del informe.
- **SC-014**: Dos cargos simultáneos durante un mismo tramo aportan ese tramo una sola vez al
  cómputo de años de servicio y de meses del cargo base.
- **SC-015**: Un caso fuera de alcance recibe igualmente el análisis parcial que el motor sí
  puede sostener, con sus advertencias bloqueantes y sin haber.
- **SC-011**: Ninguna vía de salida del motor entrega un monto sin su marca de estado y sin la
  lista de reglas que lo condicionan, verificable recorriendo todas las salidas disponibles
  (informe, exportaciones e interfaz de librería).
- **SC-012**: Una herramienta que consume el informe determina si el resultado es definitivo o
  provisional leyendo un único campo, sin interpretar texto libre.
- **SC-013**: Para cada regla `NO_VERIFICADA` que condiciona un monto, el informe indica el
  sentido en que podría alterarlo (al alza, a la baja o indeterminado).

## Assumptions

- La historia de servicios se carga manualmente y ya viene depurada por el profesional; el motor
  valida coherencia pero no audita la veracidad de lo cargado contra el certificado de servicios.
- Todos los servicios declarados corresponden a establecimientos estatales de la DGCyE con aportes
  al IPS, salvo los que el usuario marque como de otra naturaleza, que el motor reportará como
  fuera de alcance.
- Los usuarios son profesionales (abogados previsionales y personal de gremios) con conocimiento
  del vocabulario previsional; aun así el informe explica cada término técnico la primera vez que
  aparece.
- El informe se entrega como dato estructurado apto para que otra herramienta lo consuma y lo
  presente; esta funcionalidad no define la presentación visual.
- Existe al menos una grilla salarial aprobada cargada antes de poder ejercer la User Story 4; las
  historias 1 a 3 no la requieren.
- La movilidad del haber por correlación de cargos `[DL 9650/80, arts. 50 y 51]` y el límite de
  reducción `[art. 52]` no se **calculan** en esta funcionalidad: se estima el haber inicial, no
  su evolución posterior. La existencia de la movilidad del art. 50 sí se **informa** en todo
  informe que emita montos (FR-030c), para que nadie lea el monto como un valor congelado.
- Los montos de escenarios futuros están expresados a valores de la última grilla aprobada, sin
  proyección salarial de ningún tipo: la comparación entre escenarios es válida en términos
  relativos (cuánto más cobra esperando), no como pronóstico del monto nominal futuro.
- La antigüedad sí se proyecta a la fecha de cada escenario, porque su progresión depende del
  tiempo transcurrido y no de una variable económica; esa progresión queda condicionada por el
  tope de la escala, que es una regla `NO_VERIFICADA`.
- El archivo de caso es un formato propio del proyecto, legible y versionable, apto para
  adjuntarse a un expediente.
- No hay requisitos de concurrencia: el motor procesa un caso por corrida.
- El motor no tiene noción propia del tiempo: la fecha de cálculo entra como dato. Esto es lo que
  hace que un caso archivado hoy produzca dentro de un año exactamente el mismo informe.
- La proyección de un período en curso asume continuidad en el **mismo cargo**, sin ascensos ni
  cambios de situación de revista. Es el supuesto más conservador disponible y queda explícito en
  el informe.
- **Validación contra el IPS y alcance del release** (decisión del mantenedor, 2026-10-30): el
  **MVP técnico** (historias US1 a US3) puede completarse y demostrarse **sin** validación contra
  un cálculo real del IPS; su mecánica se verifica con casos sintéticos y una grilla de prueba
  explícitamente ficticia. El **release comercial queda bloqueado** hasta que **SC-002** se cumpla
  con al menos **un caso real del IPS anonimizado**. Hasta entonces el motor se usa internamente
  y para demostración, y ningún informe producido por una versión que no reprodujo un cálculo
  real del IPS puede presentarse como estimación profesional a gremios o estudios.

## Clarifications

### Sesión 2026-10-30

**Q1 — ¿Con qué grilla se valúan los escenarios de cese futuros?**

Decisión: con la **última grilla aprobada**, a valores de hoy, sin proyección salarial. La
**antigüedad sí se proyecta** a la fecha del escenario: si a esa fecha la persona todavía no
alcanzó el tope de la escala, la bonificación crece y ese crecimiento aparece en el desglose.
Todo informe con montos aclara que están expresados a valores de hoy y que el haber es móvil
`[DL 9650/80, art. 50]`, movilidad que el motor no proyecta.

Razón: mantiene la comparación entre escenarios honesta y auditable —la diferencia de monto se
explica solo por el porcentaje y por la antigüedad acumulada, nunca por un supuesto económico sin
fuente normativa (Principio I)— sin perder el valor de la pregunta "¿me conviene esperar?".

Impacto: FR-030a, FR-030b, FR-030c, FR-036a; US5 escenarios 4 a 6; nuevas suposiciones sobre
valores de hoy y proyección de antigüedad.

**Q2 — ¿Se computan los servicios no docentes aportados al IPS?**

Decisión: **no se computan**. Se detectan y se advierte. Además, cuando los servicios docentes no
alcanzan ningún inciso del art. 24 y existen períodos no docentes, la advertencia indica
explícitamente que esos servicios **podrían completar los requisitos** mediante el prorrateo
`[DL 9650/80, art. 27]`, y la elegibilidad se marca como no definitiva.

Razón: mantiene acotado el alcance de la v1 (Principio X) sin dejar al profesional con un "no
cumple" engañoso, que es el peor resultado posible: una negativa que en realidad podría revertirse
por una vía que el motor conoce y no aplicó.

Impacto: FR-015, FR-015a; US1 escenario 3; US2 escenario 5; fila de art. 27 en Fundamento
normativo pasa a "fuera de alcance v1".

**Q3 — ¿Qué hace el motor cuando una regla `NO_VERIFICADA` afecta el monto?**

Decisión: **emite el monto marcado como provisional**, con tres resguardos obligatorios:

1. La marca es **inseparable del monto** en toda vía de salida —informe, exportación o lectura por
   la interfaz de librería—. Una salida que entregue el número sin ella es un defecto bloqueante.
2. El informe lista **cada regla `NO_VERIFICADA`** que condiciona el monto y **en qué sentido
   podría alterarlo** (al alza, a la baja o indeterminado), con magnitud estimada cuando se la
   pueda acotar.
3. El resultado expone un **estado general legible por máquina** (`definitivo` / `provisional`),
   para que una herramienta consumidora pueda bloquear el uso de un monto provisional sin
   interpretar texto.

Razón: la US4 queda viable en v1 sin violar el Principio I. Los resguardos atacan el riesgo real
de la opción —que el profesional copie el monto al expediente ignorando la marca— haciendo que la
marca no se pueda perder por el camino.

Impacto: FR-046, FR-046a, FR-046b, FR-046c; US4 escenarios 5 y 6; SC-009, SC-011, SC-012, SC-013;
nueva entidad *Estado del resultado*.
