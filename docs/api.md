# Interfaz pública de librería

Esta página documenta lo que `ultimo_timbre` exporta y, sobre todo, **lo que
garantiza**. El contrato formal —firmas, excepciones, política de estabilidad—
vive en
[`specs/001-motor-calculo-jubilacion/contracts/library-api.md`](../specs/001-motor-calculo-jubilacion/contracts/library-api.md);
acá están los ejemplos.

Todos los bloques de código de esta página se ejecutan en la suite
(`tests/contract/test_docs_api.py`). Si un ejemplo se desactualiza, falla un
test: la documentación no puede quedar mintiendo en silencio.

## La regla de oro: el motor no hace I/O

`calcular()` no lee archivos, no abre sockets y **no consulta el reloj**. Recibe
un caso y un conjunto de reglas ya cargados, y devuelve un informe. Esa
restricción es lo que vuelve el cálculo reproducible: el mismo caso con las
mismas reglas da el mismo informe byte a byte, hoy y en dos años (invariante I3,
[ADR-0005](adr/0005-superficie-publica-sin-io.md) y
[ADR-0007](adr/0007-el-reloj-como-entrada.md)).

La consecuencia práctica es que la fecha de cálculo **entra en el caso**
(`Caso.fecha_de_calculo`, FR-001a). No hay un `date.today()` escondido que haga
que un informe archivado deje de reproducirse.

## Un cálculo completo, sin tocar el disco

```python
import datetime as dt

from ultimo_timbre import (
    CajaAportes,
    Caso,
    Establecimiento,
    HistoriaDeServicios,
    PeriodoDeServicio,
    SituacionRevista,
    TipoEstablecimiento,
    calcular,
    cargar_reglas,
)

caso = Caso(
    # La fecha desde la que se razona. Es dato de entrada, no el reloj.
    fecha_de_calculo=dt.date(2030, 4, 1),
    fecha_nacimiento=dt.date(1980, 3, 15),
    historia=HistoriaDeServicios(
        periodos=(
            PeriodoDeServicio(
                cargo="maestro_de_grado",
                establecimiento=Establecimiento(tipo=TipoEstablecimiento.ESTATAL_DGCYE),
                desde=dt.date(2004, 3, 1),
                hasta=dt.date(2030, 3, 31),
                caja_aportes=CajaAportes.IPS,
                situacion_revista=SituacionRevista.TITULAR,
            ),
        )
    ),
    fechas_cese=(dt.date(2030, 3, 31),),
)

# Las reglas son datos versionados, no código. Esta llamada sí lee el disco:
# es el único I/O, y queda fuera del cálculo a propósito.
reglas = cargar_reglas("v1")

informe = calcular(caso, reglas=reglas)

assert informe.elegibilidad.inciso_mas_favorable == "b"
assert informe.estado_general.value == "definitivo"
```

Este informe sale **definitivo** porque todo lo que afirma descansa en reglas
verificadas: el art. 24 inc. b y el cómputo de los años al frente de alumnos.
No trae monto —no se le pasó grilla— y por lo tanto no arrastra ninguna de las
*Cuestiones abiertas* del haber.

Un caso con monto, o uno cuyo cargo base active una Cuestión abierta, sale
**provisional**. El estado se **deriva** del contenido del informe y no se
puede pasar como entrada: si hay condicionantes, es provisional, y si no, no
(invariante I6). No existe la combinación «provisional pero sin motivo
declarado».

## Los tipos estrictos no convierten por vos

Los modelos son Pydantic v2 con `strict=True`, `frozen=True` y
`extra="forbid"`. Eso significa que **no** aceptan `"2030-03-31"` donde va una
`date`, ni `"ips"` donde va un `CajaAportes`, ni una `list` donde va una
`tuple`:

```python
import datetime as dt

import pydantic

from ultimo_timbre import Caso, HistoriaDeServicios

try:
    Caso(
        fecha_de_calculo="2030-04-01",  # str donde va date
        fecha_nacimiento=dt.date(1980, 3, 15),
        historia=HistoriaDeServicios(periodos=()),
        fechas_cese=(),
    )
except pydantic.ValidationError as error:
    assert error.error_count() >= 1
else:
    raise AssertionError("strict=True tendría que haber rechazado el str")
```

Es deliberado. Una conversión automática de texto a fecha o de texto a
enumeración es el lugar donde entra un dato mal interpretado sin que nadie se
entere. La conversión existe, pero **explícita y en un solo lugar**: el borde de
entrada (`cargar_caso`), que traduce el error al lenguaje del usuario y dice
qué período y qué campo lo causaron.

## Leer un caso de un archivo

Cuando el caso viene de un `.yaml` o `.json` del usuario, el borde de entrada es
`cargar_caso`. Es lo único que convierte texto a tipos:

```python
from pathlib import Path

from ultimo_timbre import CasoInvalido, cargar_caso

try:
    caso_leido = cargar_caso(Path("examples/caso-inc-b.yaml"))
except CasoInvalido as error:
    # El error nombra el campo y la corrección, con índice anónimo del período:
    # nunca el cargo ni las fechas (FR-054).
    raise AssertionError(f"{error.campo}: {error.correccion}") from error

assert caso_leido.fecha_de_calculo.isoformat() == "2030-04-01"
```

`cargar_caso_desde_texto(texto, formato=...)` hace lo mismo sin tocar el disco,
para cuando el contenido ya está en memoria.

## Valuar con una grilla

Sin grilla el motor responde elegibilidad, cargo base y porcentaje, pero no
emite monto: no tiene con qué. Con grilla, cada monto viaja con sus
condicionantes.

```python
from ultimo_timbre import versiones_disponibles

# `grids/` está vacío a propósito: todavía no hay ninguna grilla real aprobada
# (ver «Pendientes de datos» en el README). De ahí que la lista salga vacía.
disponibles = versiones_disponibles()
assert disponibles.grillas == ()
assert "v1" in disponibles.reglas
```

Un monto **nunca** es un escalar suelto. `Monto` lleva el valor, la fecha a la
que están expresados esos valores, su estado y sus condicionantes, y los
renderizadores no saben imprimir el número sin ellos
([ADR-0004](adr/0004-un-modelo-dos-salidas.md)):

```python
from ultimo_timbre import Monto

campos = set(Monto.model_fields)
assert {"valor", "estado", "condicionantes", "a_valores_de"} <= campos
```

El invariante I5 lo ata: `estado == provisional` si y solo si hay
condicionantes. No hay forma de producir un monto provisional que se vea
definitivo.

## Las dos salidas del mismo informe

```python
from ultimo_timbre import informe_a_dict, informe_a_json, informe_a_texto

# `informe` viene del primer ejemplo.
datos = informe_a_dict(informe)
texto = informe_a_texto(informe)
json_str = informe_a_json(informe, indent=2)

assert datos["version_reglas"] == "v1"
assert texto.splitlines()[0].strip() != ""
assert json_str.startswith("{")
```

Las dos salen del mismo modelo `Informe` y ninguna puede mostrar algo que la
otra no tenga ([ADR-0004](adr/0004-un-modelo-dos-salidas.md)).
`informe_a_texto` no importa el motor ni las reglas, y un test lo verifica
sobre el AST: si alguna vez calculara algo propio, las dos
salidas podrían discrepar.

## Qué se puede capturar

Todo lo que el paquete levanta hereda de `UltimoTimbreError`:

```python
from ultimo_timbre import (
    CasoInvalido,
    FueraDeAlcance,
    GrillaInvalida,
    ReglasNoDisponibles,
    UltimoTimbreError,
)

for excepcion in (CasoInvalido, FueraDeAlcance, GrillaInvalida, ReglasNoDisponibles):
    assert issubclass(excepcion, UltimoTimbreError)
```

| Excepción | Cuándo |
|---|---|
| `CasoInvalido` | el caso no se puede interpretar: campo faltante, fecha imposible, período incoherente |
| `FueraDeAlcance` | el caso se entiende pero el motor no lo cubre (otra caja, privado, invalidez) y no se calcula |
| `GrillaInvalida` | la grilla no se puede cargar, o es ficticia y se la pidió para valuar en serio |
| `ReglasNoDisponibles` | no hay un conjunto de reglas con esa versión |

`FueraDeAlcance` **no** es un error del usuario: es el motor negándose a
calcular lo que no sabe, que es el comportamiento correcto. La CLI le da su
propio código de salida (3) justamente para no confundirlo con entrada
inválida (2).

## Qué versión de qué se usó

Cualquier informe se puede auditar años después porque dice con qué datos se
produjo:

```python
assert informe.version_reglas == "v1"
assert informe.version_grilla is None  # no hubo grilla en este cálculo
assert len(informe.procedencias) > 0
assert len(informe.desglose) > 0
```

`versiones_disponibles()` lista lo que el repositorio tiene a mano, sin calcular
nada.

## Estabilidad

Lo que está en `ultimo_timbre.__all__` es público: cambiarlo de forma
incompatible exige un MAJOR. Todo lo demás —`ultimo_timbre.engine.*`,
`ultimo_timbre.rules.*`, los módulos privados— es interno y puede cambiar en un
MINOR. Si necesitás algo de ahí, pedilo como exportación antes de depender de
él.

Los **datos** normativos tienen su propio versionado, independiente del código:
`rules/v1/` y `grids/<vigencia>.yaml`. Una corrección de una regla es un cambio
de datos, no de librería, y el informe lo deja registrado.
