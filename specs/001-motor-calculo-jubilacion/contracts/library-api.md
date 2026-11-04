# Contrato de librería

**Feature**: `001-motor-calculo-jubilacion` · Implementa FR-051, FR-052, Principio V

Paquete `ultimo_timbre`, tipado (PEP 561, `py.typed`), publicado bajo AGPL-3.0-or-later.

## Superficie pública

Todo lo exportado está en `ultimo_timbre.__all__`. Nada fuera de esa lista es contrato: los
submódulos internos pueden cambiar sin MAJOR.

### Cálculo

```python
def calcular(
    caso: Caso,
    *,
    reglas: ConjuntoDeReglas,
    grilla: GrillaSalarial | None = None,
) -> Informe: ...
```

**`calcular` no hace I/O ni consulta el reloj**: no lee archivos, no abre sockets, no escribe
logs y no llama a `date.today()`. Recibe datos ya cargados —incluida `caso.fecha_de_calculo`
(FR-001a)— y devuelve un `Informe`. Es lo que hace que la equivalencia entre CLI y librería
(FR-051) sea estructural y no una coincidencia: la CLI es un cargador más un renderizador
alrededor de esta misma función.

**`calcular` siempre devuelve un `Informe`**, incluso cuando el caso está fuera de alcance: en ese
caso el informe trae el análisis parcial que sí puede sostenerse, sin haber, con advertencias
marcadas `bloquea_calculo` (FR-045a). No lanza excepción por casos de usuario.

`grilla=None` es válido: produce un informe sin montos, que es exactamente lo que necesitan las
historias US1 a US3 (elegibilidad, cargo base y porcentaje sin grilla).

### Carga de datos

```python
def cargar_caso(ruta: Path) -> Caso: ...
def cargar_caso_desde_texto(texto: str, formato: Formato) -> Caso: ...
def cargar_reglas(version: str | None = None) -> ConjuntoDeReglas: ...
def cargar_grilla(version: str | None = None) -> GrillaSalarial: ...
def grilla_vigente_a(fecha: date) -> GrillaSalarial | None: ...
def versiones_disponibles() -> Versiones: ...
```

Separadas de `calcular` a propósito (research R7). Un consumidor que ya tiene los datos en memoria
—la futura app web, que no puede tocar disco por caso— usa solo `calcular`.

`grilla_vigente_a` devuelve `None` cuando no hay grilla aprobada para esa fecha; el llamador
decide, y `calcular` emite la advertencia `grilla_ausente` con el monto marcado provisional
(FR-034).

### Procedencia de una grilla: dos campos distintos

`GrillaSalarial.norma` es la **fuente de los valores** y es obligatoria.
`GrillaSalarial.acto_aprobatorio` es el decreto o acta paritaria que les dio fuerza, y **puede ser
`None`**.

No es un descuido del modelo: la escala salarial de la Ley 10.579 que publica el Ministerio de
Economía de la Provincia no cita, en ninguna de sus publicaciones mensuales, el acto que la
aprueba. Rechazar la grilla dejaría al motor sin poder valuar nada con la única fuente oficial
disponible; darla por firme le prestaría al monto una certeza que no tiene. La salida intermedia
es admitirla y marcarla: todo monto calculado con una grilla sin acto aprobatorio lleva el
condicionante `grilla_sin_acto_aprobatorio`, con `sentido_impacto: indeterminado`, y el informe
sale provisional.

### Índice escalafonario del catálogo

`EntradaCatalogo.indice_escalafonario` es un `Decimal | None`, cargado desde un string numérico
(research R1). Es el multiplicador del sueldo básico del cargo testigo, y por eso sirve a la vez
como criterio de «mejor remunerado» de la `Res. IPS 995/2021` y como desempate verificable del
art. 41.

Está en `None` en todas las entradas de la v1 y eso es deliberado: el Anexo del art. 9º del
Decreto 2397/2005, que aprueba el texto ordenado del nomenclador, no está publicado. Cada entrada
apunta con `regla_indice` a `jerarquia.indices_escalafonarios`, que lo declara como Cuestión
abierta #4.

Las entradas del catálogo llevan la **categoría** del nomenclador —`director_primera`,
`director_segunda`, `bibliotecario_ensenanza_superior`— y no un nombre genérico, porque el
nomenclador les asigna índices distintos.

### Unidad de carga

`EntradaCatalogo.unidad_de_carga` es un `UnidadDeCarga`: `cargo`, `hora_catedra` o `modulo`.
Reemplazó al booleano `indice_es_por_hora`, que no alcanzaba.

Decide si el `indice_escalafonario` de una entrada es comparable con el de otra. Son tres
magnitudes distintas y mezclarlas da un resultado que parece válido: 1,15 por hora cátedra no es
«menos jerarquía» que 1,70 de un Director, y 1,15 por **módulo** tampoco equivale a 1,15 por hora,
porque el módulo dura 60 minutos y la hora cátedra 40. Con un solo booleano las horas y los
módulos quedaban marcados igual y el comparador podía enfrentarlos.

La propiedad derivada `indice_por_unidad` es `True` para todo lo que no sea `cargo`.

El período de servicio declara su carga en el campo que corresponda: `horas_catedra` o `modulos`,
nunca convertida. Convertir en la entrada perdería el dato original del recibo y haría imposible
mostrar el umbral del art. 24 inc. b bajo las dos lecturas de la equivalencia, que es lo que
decide si el inciso sale definitivo o provisional (Cuestión abierta #3).

### Componentes de la grilla: remunerativo y con aporte son dos cosas

`ComponenteSalarial` declara `bonificable`, `remunerativo` y `aporte_ips`, y los tres responden
preguntas distintas:

| Campo | Pregunta | Para qué lo usa el motor |
|---|---|---|
| `bonificable` | ¿la antigüedad se aplica sobre él? | la base del adicional por antigüedad (FR-031b) |
| `remunerativo` | ¿el concepto es remunerativo? | la lectura restrictiva de la remuneración |
| `aporte_ips` | ¿tributa al IPS? | **el criterio aplicado** de la remuneración del cargo |

`aporte_ips` es `bool | None`, y `None` **no** equivale a `False`: significa que la grilla no lo
declara. El motor deja el componente afuera e informa la laguna, en lugar de suponer que no
tributa. Un `bool()` en el borde habría borrado esa diferencia justo donde decide la base del
haber.

Cuál de las tres preguntas define la remuneración del cargo es la Cuestión abierta #2. El criterio
aplicado desde el 2026-11-04 es el aporte, por la evidencia de una liquidación donde el aporte
personal es el 16 % exacto de la suma de los conceptos que tributan.

`porcentaje_del_basico` es metadato de procedencia, no de cálculo: el motor **no** recalcula el
importe, que la grilla trae resuelto. Sirve para auditar una grilla contra la escala publicada.

### Evidencia de una regla

`Regla.evidencia` es un `str | None` y es distinto de `norma`:

* `norma` dice **qué dice el derecho**;
* `evidencia` dice **qué se miró para convencerse de que es lo que efectivamente se aplica**.

La distinción no es académica. La escala de antigüedad del Decreto 818/13 estaba transcripta de su
Anexo Único desde el principio, y lo que faltaba no eran los valores sino la certeza de que
ninguna norma posterior los había cambiado. Eso no lo resuelve otra lectura de la norma: lo
resolvió una liquidación real con el porcentaje aplicado.

La evidencia **nunca** identifica a una persona: nombra el tipo de documento y su período, no su
titular (Principio III).

### Serialización

```python
def informe_a_json(informe: Informe) -> str: ...  # determinista, sort_keys
def informe_a_texto(informe: Informe) -> str: ...  # legible en terminal
```

Ambas renderizan el **mismo** modelo `Informe`. Ninguna recalcula nada.

### Modelos exportados

`Caso`, `HistoriaDeServicios`, `PeriodoDeServicio`, `Licencia`, `Establecimiento`,
`ConjuntoDeReglas`, `Regla`, `Norma`, `CatalogoDeCargos`,
`GrillaSalarial`, `ValorCargo`, `ComponenteSalarial`,
`Informe`, `Elegibilidad`, `CargoBase`, `Escenario`, `Monto`, `Condicionante`,
`PasoDelDesglose`, `Procedencia`, `Advertencia`, `Superposicion`, `Versiones`.

Enums: `SituacionRevista`, `TipoLicencia`, `TipoEstablecimiento`, `CajaAportes`,
`NaturalezaServicio`, `ClasificacionSuperposicion`, `EstadoResultado`, `SentidoImpacto`,
`ClaseCondicionante`, `CodigoAdvertencia`, `TipoFuente`, `ViaCargoBase`, `TipoEscenario`,
`Formato`.

Ver [`data-model.md`](../data-model.md) para los campos de cada uno.

## Excepciones

| Excepción | Cuándo | Exit code CLI |
|---|---|---|
| `CasoInvalido` | Schema o coherencia temporal (FR-003) | 2 |
| `ReglasNoDisponibles` | Versión de reglas inexistente | 2 |
| `FueraDeAlcance` | **Solo error de programación** (ver abajo) | 4 |

Todas derivan de `UltimoTimbreError`. Llevan el `periodo_idx` y el campo afectado, nunca valores
de dominio (FR-054).

**Un caso fuera de alcance NO es una excepción.** El motor devuelve un `Informe` con lo que sí
puede sostener y advertencias bloqueantes (FR-045a); la CLI traduce eso a exit 3 (FR-045b).
Abortar con excepción le quitaría al profesional el análisis parcial que el motor ya tenía
calculado —qué dicen los 25 años que sí son del IPS—, y el Principio IV prefiere un resultado
parcial explicado a ninguno.

`FueraDeAlcance` queda reservada para **errores de programación**: que una ruta interna llegue a
valuar un tramo marcado fuera de alcance es un bug del motor, no un caso de usuario. Si se
dispara en producción, es un 4.

## Garantías

| Garantía | Verificación |
|---|---|
| `calcular` es pura: mismas entradas ⇒ mismo `Informe` | property test (I3) |
| El orden de los períodos no afecta el resultado | property test (I1) |
| Sin red en ninguna ruta | test con sockets bloqueados |
| Sin logging propio (solo `NullHandler`) | test de canarios (I8) |
| Sin escritura a disco desde `calcular` | test con filesystem de solo lectura |
| Sin reloj: no hay `date.today()` en `engine/` ni `rules/` | inspección de AST + doble corrida con fechas de cálculo distintas |
| `Monto` nunca existe sin su estado y sus condicionantes | invariante de tipo (I5) |
| Los cómputos usan la unión de tramos, nunca la suma de duraciones | property test (I9) |

## Estabilidad

`schema_version` del informe y del caso siguen semver propio, independiente del paquete. Un cambio
incompatible en cualquiera de los dos exige MAJOR del paquete y un ADR en `docs/adr/`.
