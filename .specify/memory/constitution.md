<!--
Sync Impact Report
==================
Versión: 1.1.1 → 1.1.2
Tipo de cambio: Enmienda PATCH. Se marca la Cuestión abierta #1 como resuelta, con su evidencia y
su fecha, y se documenta el criterio con que una cuestión se da por resuelta. No se agregan ni
amplían secciones. **Los diez principios no se modificaron** (ni su texto, ni su numeración, ni
su orden), y se verificó por hash del bloque completo.

Secciones modificadas:
  • Cuestiones abiertas del dominio — #1 resuelta el 2026-11-04 con la evidencia de una
    liquidación DGCyE 09/2026; se agrega el criterio de resolución (evidencia verificable, no
    plausibilidad) y la convención de tachar en lugar de borrar.

Propagación a los artefactos del proyecto:
  • rules/v1/haber.yaml → `antiguedad.escala_y_tope` verificada, con `evidencia` y tope 125 %;
    nueva `antiguedad.base_bonificable`; `antiguedad.escala_ley_10579` marcada no vigente.
  • rules/v1/no_verificadas.yaml → la #1 sale del archivo; su encabezado ya no dice "#1 a #6".
  • src/ultimo_timbre/engine/condicionantes.py → la escala sale de `REGLAS_DEL_MONTO`.
  • specs/001-motor-calculo-jubilacion/spec.md → FR-030b, FR-031b y FR-032 pasan a verificado;
    tabla de fundamento normativo y lista de cuestiones que afectan a la spec.
  • tests/golden/test_provisional_antiguedad.py → reescrito con la afirmación invertida.

Nota de gobernanza: esta enmienda **no cierra** las Cuestiones #2 a #6 ni la #9. La #2 mejoró su
criterio por defecto —pasó a los componentes con aporte al IPS, con evidencia— y sigue abierta,
porque que un concepto tribute no prueba que integre el haber: eso lo tiene que decir una
resolución del IPS.

--- Sync Impact Report de la enmienda anterior (v1.1.0 → v1.1.1) ---
Versión: 1.1.0 → 1.1.1
Tipo de cambio: Enmienda PATCH. Se agrega la Cuestión abierta #9 a la lista existente. No se
agregan ni amplían secciones: la lista de Cuestiones abiertas ya existía y ya preveía su propio
crecimiento ("Estas cuestiones DEBEN resolverse con fuente verificable…"). **Los diez principios
no se modificaron** (ni su texto, ni su orden, ni su numeración), como tampoco el Marco normativo,
el Alcance de la v1, las Restricciones técnicas, el Flujo de trabajo, el Licenciamiento ni la
Gobernanza.

Principios modificados: ninguno.
Secciones agregadas: ninguna.
Secciones removidas: ninguna.

Cuestiones abiertas del dominio — nueva #9: porcentaje aplicable cuando la docente cumple el
art. 24 inc. b por sus años al frente de alumnos pero su cargo base del art. 41 es un cargo que
no cuenta al frente (un directivo). No está verificado si corresponde el 75 % del art. 43 sobre
ese cargo base o el 70 % del art. 41. Impacto **indeterminado** —las dos lecturas son
defendibles— con magnitud 70 % vs 75 % sobre el cargo base. El motor aplica el 70 % por ser el
criterio más conservador y lo declara como valor por defecto aplicado.

Por qué es PATCH y no MINOR: la #8 trata de **qué cargos** cuentan al frente de alumnos; la #9
supone esa pregunta ya resuelta y trata de **sobre qué cargo** se calcula el porcentaje. Son
distintas, pero la #9 no amplía la guía de la constitución: precisa un caso que la lista de
Cuestiones abiertas ya estaba destinada a recibir.

Origen de la enmienda: implementación de la US3 (cargo base y porcentaje), que expuso el caso al
poder determinar por primera vez el cargo base y el porcentaje en el mismo informe.

Registro de la enmienda anterior (v1.0.0 → v1.1.0, MINOR), que se conserva:
Tipo de cambio: Enmienda MINOR. Se amplía materialmente el Marco normativo de referencia y la
lista de Cuestiones abiertas del dominio. **Los diez principios no se modificaron** (ni su texto,
ni su orden, ni su numeración), como tampoco el Alcance de la v1, las Restricciones técnicas, el
Flujo de trabajo, el Licenciamiento ni la Gobernanza.

Principios modificados: ninguno.
Secciones agregadas: ninguna.
Secciones removidas: ninguna.

Secciones ampliadas:
  • Marco normativo de referencia — dos filas nuevas:
      1. Cargos considerados al frente de alumnos (Ley 13469 preceptores y bibliotecarios;
         Ley 10745 técnico-docentes de Psicología y Educación Especial; Ley 11860 visitadoras de
         higiene escolar). Verificado para los cargos nombrados; el alcance de la Ley 13469 a
         otros cargos del escalafón queda NO_VERIFICADA (SCBA, causa A 74801, 2020).
      2. Cómputo del excedente de 3 / 5 años contado desde que se alcanzan todas las condiciones
         del inciso (Res. IPS 995/2021, Anexo, punto 2.1.a). Registrado como Interpretación IPS:
         es el criterio aplicado por defecto, y la lectura literal de los arts. 42 y 43 se informa
         como advertencia con impacto al alza.
  • Cuestiones abiertas del dominio — nueva #8: alcance de la Ley 13469 a cargos no nombrados,
    con impacto 70 % vs 75 % sobre elegibilidad y porcentaje.

Origen de la enmienda: especificación 001-motor-calculo-jubilacion, que detectó ambas cuestiones
al desarrollar los requisitos de elegibilidad (FR-002a a FR-002c, FR-027a, FR-027b).

Plantillas sincronizadas el 2026-10-30 (sin cambios requeridos por esta enmienda):
  ✅ .specify/templates/plan-template.md   → "Constitution Check" con tabla de gates I–X
     (estado PASA/NO APLICA/VIOLACIÓN por principio), chequeo de Alcance v1 y de Cuestiones
     abiertas del dominio; "Complexity Tracking" exige nombrar el principio violado.
     Sin cambios: referencia las cuestiones abiertas de forma genérica, no por número.
  ✅ .specify/templates/spec-template.md   → cita normativa obligatoria (ley, art., inc. /
     resolución) en todo requisito de cálculo, con ejemplos; sección "Fundamento normativo"
     (norma, tipo letra-de-la-ley vs interpretación, estado Verificado/NO_VERIFICADA, fecha de
     verificación) y listado de reglas NO_VERIFICADA y cuestiones abiertas que la afectan.
     Sin cambios: ya contempla el tipo "Interpretación" que usan las dos filas nuevas.
  ✅ .specify/templates/tasks-template.md  → tests OBLIGATORIOS y antes de la implementación
     (Principio VI), tareas de caso dorado con cita normativa, property-based testing y gates de
     cobertura (≥95 % motor/parser, ≥80 % resto) y de seguridad (Principio VII).
     Sin cambios.
  ○ .specify/templates/checklist-template.md → sin cambios requeridos (genérica).

Artefactos aguas abajo a revisar tras esta enmienda:
  ⚠ specs/001-motor-calculo-jubilacion/spec.md → la "Nota de gobernanza" bajo la Cuestión
    abierta #8 dice que la #8 todavía no está en la constitución y que requiere una enmienda
    MINOR. Esta enmienda la incorporó: la nota quedó obsoleta y conviene actualizarla.
  ⚠ specs/001-motor-calculo-jubilacion/checklists/requirements.md → el ítem "Pendiente de
    gobernanza" quedó cumplido en lo relativo a la #8.

TODOs diferidos:
  • La ampliación de la Cuestión abierta #5 propuesta por la spec 001 (si la situación de revista
    —titular, provisional, suplente— condiciona la elección del cargo base, dado que el art. 41
    habla del cargo "de que era titular") NO fue incluida en esta enmienda: el pedido del usuario
    abarcó solo las dos filas del Marco normativo y la Cuestión abierta #8. Queda disponible para
    una próxima enmienda.
-->

# Último Timbre — Constitución

**Último Timbre** calcula una estimación del haber jubilatorio de docentes de la Provincia de
Buenos Aires bajo el régimen del Instituto de Previsión Social (IPS), a partir de sus recibos de
sueldo y de su historia de servicios. Muestra los escenarios posibles según la fecha de cese,
explica cada paso del cálculo con su fundamento normativo y advierte sobre todo lo que pueda
afectar el resultado.

Esta constitución define reglas no negociables. Toda especificación, plan, tarea y cambio de
código DEBE cumplirla. Ante un conflicto entre un documento del proyecto y esta constitución,
prevalece la constitución.

---

## Principios fundamentales

### I. Toda regla tiene fuente normativa

- Cada regla de cálculo (requisitos, porcentajes, plazos mínimos, topes, escalas) DEBE citar la
  norma exacta que la origina: ley, artículo, inciso y, si corresponde, resolución del IPS o
  decreto.
- Las reglas del régimen DEBEN vivir como **datos versionados** (con norma, vigencia desde/hasta
  y fecha de verificación), separadas del código que las aplica. Ningún porcentaje, edad ni plazo
  normativo puede estar escrito "a mano" dentro de la lógica.
- Si la norma es ambigua o no se pudo verificar, la regla se marca `NO_VERIFICADA` y el motor
  DEBE negarse a dar un resultado definitivo por ese camino: informa la situación como
  advertencia en lugar de adivinar.
- Las interpretaciones (criterios del IPS, jurisprudencia, práctica administrativa) se registran
  aparte de la letra de la ley y se identifican como tales en el informe.

**Por qué:** el valor del producto es que un abogado o un gremio pueda auditar cada número. Una
regla sin fuente es una opinión.

### II. Cálculo determinístico y exacto

- Mismas entradas + misma versión de reglas + misma versión de grilla ⇒ mismo resultado,
  siempre.
- Todo cálculo monetario y porcentual DEBE usar aritmética decimal exacta (nunca punto flotante
  binario). El redondeo se aplica en un único lugar, con una política explícita y documentada.
- Fechas y períodos (meses consecutivos o alternados, años de servicio, edad al cese) se calculan
  con una librería de fechas probada y reglas de conteo documentadas. No se aceptan
  aproximaciones del tipo "un mes = 30 días" salvo que una norma lo establezca.
- **Ningún modelo de lenguaje ni componente probabilístico** participa en la extracción de datos
  de los recibos ni en el cálculo. La extracción de PDF es por parser determinístico.

### III. Privacidad por diseño: no guardamos casos

- Los PDF subidos se procesan **en memoria, en una única corrida**, y se descartan al terminar.
  Nunca se escriben a disco, almacenamiento de objetos, colas persistentes ni cachés.
- **No se persiste ningún dato de casos:** ni recibos, ni líneas de tiempo, ni resultados en el
  servidor. El informe se entrega al usuario para descarga. Si el usuario quiere retomar un caso,
  vuelve a cargar su archivo de caso exportado.
- La única información persistida es la **mínima necesaria de las organizaciones clientes**
  (gremios y estudios): identificación de la organización, usuarios profesionales, licencia y
  facturación. Esa base de datos NUNCA contiene datos de docentes.
- Prohibido registrar datos personales en logs, métricas, trazas, reportes de errores o
  analítica: CUIL, nombres, montos, cargos, fechas de nacimiento ni contenido de archivos. Los
  errores se reportan con identificadores técnicos anónimos.
- Se aplica la Ley 25.326 de Protección de Datos Personales y la regulación que la reemplace. La
  arquitectura sin almacenamiento de casos es la estrategia principal de cumplimiento.

### IV. Transparencia total del resultado

- Todo informe DEBE mostrar:
  1. el resultado de cada escenario (por ejemplo cese hoy, +3 años de edad excedente,
     +5 años) con fecha estimada en que se habilita;
  2. el **desglose paso a paso**: requisitos verificados, cargo base elegido y por qué, período de
     36/60 meses que lo sustenta, porcentaje aplicado y su artículo;
  3. la **procedencia de cada dato**: extraído de un recibo (cuál), cargado a mano o inferido;
  4. la versión de reglas y la versión de grilla salarial usadas;
  5. todas las advertencias (datos faltantes, períodos sin cubrir, simultaneidad detectada, reglas
     no verificadas, situaciones fuera de alcance).
- Todo informe DEBE decir de forma visible que es una **estimación orientativa**, que no
  reemplaza el cálculo oficial del IPS ni el asesoramiento profesional.
- Cuando el sistema no puede calcular algo con certeza, lo dice. Un resultado parcial explicado es
  mejor que un número completo pero dudoso.

### V. Motor abierto, separado e independiente

- El **motor de cálculo** y el **conjunto de reglas** son un paquete independiente, publicado
  bajo licencia **AGPL-3.0-or-later**.
- El motor NO DEBE depender de la aplicación web, de la base de datos de organizaciones, de la
  facturación ni de ningún componente propietario. Se comunica solo por una interfaz pública,
  tipada y documentada.
- El motor DEBE poder ejecutarse localmente, sin red, desde la línea de comandos o como
  librería, con los mismos resultados que la versión hosteada.
- Las funcionalidades comerciales (gestión de organizaciones, procesamiento por lotes, informes
  con membrete, soporte) viven fuera del motor.

### VI. Test-first con casos reales

- Desarrollo guiado por pruebas en el motor y el parser: la prueba se escribe, se revisa, falla, y
  recién después se implementa.
- **Casos dorados:** cada regla tiene al menos un caso de prueba con su fundamento normativo. Los
  casos reales de jubilaciones ya otorgadas por el IPS (anonimizados) son la prueba de
  aceptación máxima. Una discrepancia con un caso real bloquea la publicación hasta explicarla.
- **Fixtures de recibos:** el parser se prueba con recibos reales **anonimizados**, uno por cada
  variante de formato conocida. Nunca se suben al repositorio recibos con datos reales.
- Pruebas basadas en propiedades para invariantes: el porcentaje nunca supera el máximo legal, más
  servicios nunca reduce el resultado, el orden de carga de los recibos no cambia el resultado,
  etc.
- Cobertura mínima de ramas: 95 % en motor y parser; 80 % en el resto.

### VII. Seguridad como requisito, no como agregado

- Objetivo de verificación: OWASP ASVS nivel 2 para la aplicación web.
- **Los archivos subidos son hostiles por defecto.** Se valida tipo real (no la extensión), tamaño
  y cantidad de páginas; se rechazan PDF cifrados, con JavaScript, formularios activos o archivos
  embebidos; el parseo corre con límites de tiempo y memoria y aislado del resto del proceso.
- El pipeline de CI DEBE incluir análisis estático (SAST), escaneo de dependencias, detección de
  secretos y generación de SBOM. Una vulnerabilidad alta o crítica sin mitigar bloquea el
  despliegue.
- HTTPS obligatorio, HSTS, Content-Security-Policy estricta, cookies seguras, sin recursos de
  terceros que puedan leer los datos del usuario.
- Secretos fuera del repositorio y del código. Principio de mínimo privilegio en la
  infraestructura.
- Política de divulgación responsable (`SECURITY.md`) publicada desde el primer release.

### VIII. Pensado para docentes: claro, accesible y propio

- Diseño visual **propio y actual**, con identidad de Último Timbre. No se aceptan plantillas
  genéricas ni estilos por defecto de frameworks sin adaptar.
- Mobile-first: el flujo completo DEBE poder hacerse desde un celular.
- Accesibilidad WCAG 2.2 nivel AA como mínimo: contraste, tamaño de letra cómodo, navegación por
  teclado, compatibilidad con lectores de pantalla.
- Lenguaje claro en español rioplatense. Todo término técnico o previsional (cese, cargo base,
  simultaneidad, carrera pura) se explica en contexto la primera vez que aparece.
- El usuario siempre sabe en qué paso está, qué falta y qué puede corregir. Ningún error deja al
  usuario sin una acción posible.
- Los profesionales (abogados, gremios) tienen una vista técnica con el detalle normativo
  completo; la docente que lee el informe tiene una versión comprensible sin perder exactitud.

### IX. Las grillas salariales se publican solo con revisión humana

- El sistema detecta automáticamente las normas salariales nuevas publicadas y extrae sus
  valores, pero esos valores quedan **pendientes** hasta que una persona los revisa y aprueba.
- Cada versión de grilla registra: norma de origen, enlace, vigencia, fecha de extracción, quién
  la aprobó y diferencias con la versión anterior.
- El flujo de aprobación usa el control de versiones: la extracción automática abre un pull
  request con los datos; aprobarlo es fusionar el PR.
- Un informe nunca usa una grilla no aprobada. Si la grilla vigente al momento del cálculo no está
  cargada, el informe lo advierte y muestra con qué grilla calculó.

### X. Simplicidad y alcance acotado

- Se construye lo que la v1 necesita (ver *Alcance de la v1*) y nada más. Toda funcionalidad fuera
  de alcance requiere una especificación propia y una enmienda o decisión registrada.
- Ante dos diseños que cumplen los principios, se elige el más simple de entender, probar y
  operar.
- Las situaciones fuera de alcance no se "resuelven aproximadamente": se **detectan y se
  informan** como tales.

---

## Marco normativo de referencia

Fuente primaria: **Decreto-Ley 9650/80** (texto ordenado Decreto 600/94 y modificatorias),
régimen previsional de la Provincia de Buenos Aires, administrado por el IPS.

| Tema | Norma | Estado |
|---|---|---|
| Requisitos de jubilación ordinaria docente (50/25 al frente de alumnos o 20 hs cátedra; 50/25 con 10 al frente; 55/30) y mínimo general de 22 años con aportes | DL 9650/80, art. 24 incs. b, c, d | Verificado |
| Cargos considerados al frente de alumnos: preceptores y bibliotecarios (Ley 13469), técnico-docentes de Psicología y Educación Especial (Ley 10745), visitadoras de higiene escolar (Ley 11860) | Ley 13469; Ley 10745; Ley 11860 | Verificado para los cargos nombrados; alcance de la Ley 13469 a otros cargos del escalafón NO_VERIFICADA (SCBA, causa A 74801, 2020) |
| Prorrateo con servicios de distinta naturaleza | DL 9650/80, art. 27 | Verificado |
| Concepto de remuneración | DL 9650/80, art. 40 | Verificado |
| Haber base 70 % del cargo; cargo de mayor jerarquía con 36 meses consecutivos o 60 alternados | DL 9650/80, art. 41 (texto Ley 13968; ver Ley 14025 y Res. IPS 14/10) | Verificado (alcance de Ley 14025 a revisar) |
| 75 % / 80 % por excedente de edad de 3 / 5 años | DL 9650/80, art. 42 | Verificado |
| Docente inc. b): 75 % base, +5 % y +10 % por excedente de 3 / 5 años (75 / 80 / 85 %) | DL 9650/80, art. 43 | Verificado |
| Cómputo del excedente de 3 / 5 años: se cuenta desde que se alcanzan **todas** las condiciones del inciso (edad y servicios), no solo la edad requerida | Res. IPS 995/2021, Anexo, punto 2.1.a | Interpretación IPS (criterio aplicado por defecto; la lectura literal de los arts. 42 y 43 se informa como advertencia, impacto al alza) |
| Cargos simultáneos (mínimo 3 años continuos, proporcional) | DL 9650/80, art. 47; Res. IPS 995/2021 | Verificado, fórmula a detallar |
| Horas cátedra y módulos como "carrera" | Res. HD IPS 8/14 | NO_VERIFICADA |
| Movilidad del haber por correlación de cargos | DL 9650/80, arts. 50 y 51 | Verificado |
| Límite de reducción del haber respecto del cargo | DL 9650/80, art. 52 | Verificado |
| Caja otorgante y reciprocidad | DL 9650/80, arts. 66 y 67 | Fuera de alcance v1 |
| Cese definitivo y cierre de cómputos | DL 9650/80, arts. 71 y 72 | Verificado |
| Escala de bonificación por antigüedad docente | Ley 10579 art. 33; Decreto 818/13 y posteriores | NO_VERIFICADA (tope 120 % vs 125 %) |
| Composición del sueldo: índice escalafonario × básico del preceptor, sumas fijas y bonificaciones por código | Nomenclador de cargos docentes y decretos paritarios vigentes | A relevar |

Esta tabla es la semilla del conjunto de reglas versionado; el repositorio de reglas es la fuente
de verdad operativa.

---

## Alcance de la v1

**Dentro de alcance:**

- Docentes de establecimientos **estatales** dependientes de la Dirección General de Cultura y
  Educación (DGCyE).
- Servicios con aportes **exclusivamente al IPS**.
- Jubilación ordinaria docente, art. 24 incisos b, c y d, con los porcentajes de los arts. 41, 42 y
  43.
- Determinación del **cargo base** (36 meses consecutivos o 60 alternados) y valuación con la
  grilla aprobada vigente.
- Escenarios por fecha de cese (habilitación del derecho y excedentes de 3 y 5 años de edad).
- Carga de recibos en PDF digitales del portal ABC ("Mis Haberes"), más carga y corrección
  **manual** de la historia de servicios a partir del certificado de servicios.
- **Detección** de simultaneidad de cargos con aviso de impacto potencial, sin calcular el
  incremento.
- Informe descargable (PDF y archivo de caso reimportable).
- Acceso para organizaciones licenciadas (gremios y estudios profesionales).

**Fuera de alcance (se detecta y se informa, no se calcula):**

- Cálculo del incremento por simultaneidad (art. 47 y Res. 995/2021).
- Servicios en otras cajas, reciprocidad, ANSES, docentes de otras jurisdicciones.
- Establecimientos privados (subvencionados o no).
- Jubilación por invalidez, por edad avanzada, pensiones y reajustes de beneficios otorgados.
- Recibos escaneados o fotografiados (requieren OCR).
- Acceso para docentes individuales.

---

## Cuestiones abiertas del dominio

Estas cuestiones DEBEN resolverse con fuente verificable antes de implementar las reglas que
dependen de ellas. Hasta entonces, las reglas afectadas quedan como `NO_VERIFICADA`.

Una cuestión se da por resuelta cuando hay **evidencia verificable**, no cuando parece razonable.
La regla correspondiente pasa a `verificado` declarando en `evidencia` contra qué documento se
comprobó, y la cuestión queda acá tachada con su fecha en lugar de borrarse: el registro de por
qué estuvo abierta es parte de la auditoría.

1. ~~**Escala de antigüedad vigente**~~ — **RESUELTA el 2026-11-04.** Rige la escala del
   `Decreto 818/13, Anexo Único`, con **tope 125 %** en el tramo de 24 años.

   Los once tramos estaban transcriptos del Anexo Único desde el principio; lo que faltaba era la
   certeza de que ninguna norma posterior los había modificado, y eso ninguna relectura de la
   norma podía darla. La dio una **liquidación DGCyE 09/2026**: con 26 años de antigüedad, el
   código 0220 es exactamente 1,25 veces el código 0110. El 120 % que mencionaban otras fuentes
   es la escala original de la `Ley 10579, art. 33`, anterior al decreto, que queda como
   referencia histórica y no se informa como lectura alternativa.

   Verificado además **sobre qué** se aplica: solo el sueldo básico. Las bonificaciones
   remunerativa docente (0455) y no jerárquica (0667) no integran la base aunque sean
   remunerativas y lleven aporte.
2. **Remuneración del cargo:** qué conceptos del recibo integran la "remuneración asignada al
   cargo" que toma el IPS (básico, antigüedad, sumas fijas remunerativas no bonificables, códigos
   específicos) y cuáles no.
3. **Horas cátedra y módulos:** contenido de la Res. HD IPS 8/14 y su aplicación al cargo base.
4. **Mayor jerarquía:** criterio para comparar cargos (puntaje/índice o remuneración) y
   acreditación según Res. IPS 14/10.
5. **Conteo de períodos:** tratamiento de licencias con y sin goce, suplencias e interinatos en el
   cómputo de los 36/60 meses y de los años de servicio.
6. **Redondeo:** política de redondeo que aplica el IPS en la liquidación del haber.
7. **Formato de recibos:** variantes históricas del recibo digital de la DGCyE y su
   correspondencia de códigos de concepto.
8. **Alcance de la Ley 13469:** si la condición de "al frente de alumnos" alcanza a cargos del
   escalafón no nombrados explícitamente en la norma. La interpretación está discutida (SCBA,
   causa A 74801, 2020). Decide si el acceso es por el inciso b (art. 43, 75 % de base) o por los
   incisos c y d (art. 41, 70 % de base), de modo que su impacto es de **70 % vs 75 %** y alcanza
   tanto a la elegibilidad como al porcentaje.
9. **Porcentaje con cargo base que no cuenta al frente de alumnos:** si la docente cumple el
   art. 24 inciso b **por sus años al frente de alumnos** pero su cargo base del art. 41 es un
   cargo que **no** cuenta al frente —típicamente un directivo—, no está verificado si corresponde
   el 75 % del art. 43 sobre ese cargo base o el 70 % del art. 41. Las dos lecturas son
   defendibles: el art. 43 rige "el personal del art. 24 inc. b", y ella lo es; pero su 75 % se
   pensó para el cargo al frente de alumnos, que no es el cargo base. El impacto es
   **indeterminado**, con magnitud de **70 % vs 75 % sobre el cargo base**. Hasta verificarlo el
   motor aplica el 70 %, que es el criterio más conservador, y lo declara como valor por defecto
   aplicado. Se distingue de la #8: esa pregunta cuáles cargos cuentan al frente; esta supone la
   respuesta y pregunta sobre qué cargo se calcula el porcentaje.

---

## Restricciones técnicas

- **Motor y parser:** Python (versión estable con soporte vigente), tipado estático estricto,
  aritmética `Decimal`, modelos de datos validados. Parser de PDF determinístico.
- **Reglas y grillas:** archivos de datos versionados en el repositorio del motor, con esquema
  validado en CI.
- **Aplicación web:** frontend web moderno con diseño propio; API sin estado para el
  procesamiento de casos.
- **Persistencia:** solo para organizaciones, usuarios profesionales, licencias y facturación.
  Prohibido almacenar datos de casos (Principio III).
- **Despliegue:** contenedores reproducibles, infraestructura como código, entornos separados de
  desarrollo, staging y producción.
- **Observabilidad:** métricas y logs técnicos sin datos personales.
- Las decisiones concretas de frameworks, librerías e infraestructura se toman en
  `/speckit.plan` y se registran como ADR (Architecture Decision Record), siempre dentro de estas
  restricciones.

---

## Flujo de trabajo

1. Cada funcionalidad sigue el ciclo de Spec Kit: `/speckit.specify` → `/speckit.clarify` →
   `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze` → `/speckit.implement`.
2. Toda especificación que involucre cálculo DEBE citar las normas que aplica (Principio I).
3. Todo plan DEBE incluir un "Constitution Check" que verifique los principios I a X; las
   desviaciones se justifican por escrito o se rechazan.
4. Rama por funcionalidad, pull request con revisión obligatoria y CI en verde para fusionar.
5. **Definición de terminado:** pruebas escritas antes y pasando, cobertura cumplida, casos
   dorados en verde, escaneos de seguridad sin hallazgos altos/críticos, documentación de
   usuario actualizada, reglas con fuente citada.
6. Commits convencionales y versionado semántico, independiente para el motor, las reglas y la
   aplicación.

---

## Licenciamiento y aspectos legales

- **Motor y reglas:** AGPL-3.0-or-later. Toda contribución externa requiere aceptar un acuerdo de
  licencia de contribución (CLA) que preserve la posibilidad de licenciamiento dual.
- **Aplicación web y servicios comerciales:** propietarios.
- Antes del lanzamiento DEBEN publicarse: términos y condiciones, política de privacidad y aviso
  de responsabilidad (la herramienta es orientativa, no constituye asesoramiento legal ni
  previsional y no reemplaza el cálculo oficial del IPS).
- La marca "Último Timbre" se gestiona ante el INPI y el software se registra ante la DNDA.

---

## Gobernanza

- Esta constitución prevalece sobre cualquier otra práctica, plantilla o documento del proyecto.
- **Enmiendas:** se proponen por pull request con la justificación, el impacto en
  especificaciones y código existentes y un plan de migración. Requieren aprobación del
  responsable del proyecto.
- **Versionado de la constitución:**
  - MAJOR: se elimina o redefine un principio de forma incompatible.
  - MINOR: se agrega un principio o sección, o se amplía materialmente una regla.
  - PATCH: aclaraciones y correcciones de redacción sin cambio de significado.
- Al ampliar el alcance (por ejemplo, calcular simultaneidad o abrir a docentes individuales), se
  actualiza la sección *Alcance de la v1* mediante enmienda.
- Cada pull request y cada `/speckit.analyze` verifica el cumplimiento. Toda complejidad agregada
  se justifica contra el Principio X.
- Las cuestiones abiertas del dominio se revisan antes de cada release del motor.

**Versión**: 1.1.2 | **Ratificada**: 2026-10-30 | **Última enmienda**: 2026-11-04
