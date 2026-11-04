# Política de seguridad

## Cómo reportar una vulnerabilidad

Escribí a **valentinventos@gmail.com** con el asunto `[seguridad] ultimo-timbre-motor`.

Si preferís el canal de GitHub, usá
[Security Advisories](https://github.com/valenventos/ultimo-timbre-motor/security/advisories/new),
que mantiene el reporte privado hasta que haya corrección.

**No abras un issue público.** Un issue es visible desde el instante en que se
crea, y eso convierte el reporte en una guía de explotación antes de que exista
el parche.

Incluí, en lo posible: qué versión probaste, qué hiciste, qué pasó, qué
esperabas, y el impacto que le ves. Un caso mínimo que reproduzca el problema
vale más que una descripción larga.

**No incluyas datos personales reales de ninguna docente.** Si el problema
aparece con un caso concreto, anonimizalo antes de mandarlo: cambiá fechas y
cargos hasta que el caso siga reproduciendo el problema sin identificar a
nadie. Si no se puede reproducir sin datos reales, decilo y lo coordinamos por
privado.

## Qué esperar

| Momento | Compromiso |
|---|---|
| Hasta 72 h | acuse de recibo |
| Hasta 10 días | primera evaluación: si se reproduce, qué severidad tiene y qué plan hay |
| Hasta 90 días | corrección publicada, o explicación de por qué no la hay |

Este proyecto lo mantiene **una sola persona**, sin equipo de guardia. Los
plazos de arriba son compromisos reales, no un acuerdo de nivel de servicio
empresarial: si algo se va a demorar, lo vas a saber dentro de los plazos y no
después.

No hay programa de recompensas. Sí hay crédito en el aviso de seguridad y en el
changelog, con tu nombre o de forma anónima, como preferís.

## Divulgación coordinada

Pedimos **90 días** desde el acuse de recibo antes de publicar. Si el problema
ya está siendo explotado o ya es público, ese plazo no aplica: publicá lo que
haga falta para que la gente se proteja y avisanos.

Cuando haya corrección, se publica un aviso de seguridad con la versión
afectada, la versión corregida y el crédito correspondiente.

## Alcance

Este repositorio es el **motor de cálculo**: una librería de Python y una CLI.
No tiene servidor, ni base de datos, ni red. Eso acota mucho qué es una
vulnerabilidad acá.

**Dentro del alcance:**

- ejecución de código a partir de un archivo de caso (`.yaml` / `.json`), que
  es la única entrada no confiable que el motor acepta;
- consumo desmedido de memoria o de CPU provocado por un archivo de caso
  construido a mala fe (un YAML con anclas recursivas, una historia de
  servicios absurdamente grande);
- **filtración de datos personales por un canal que no debería tenerlos**: un
  log, un mensaje de error, un volcado de excepción o la salida estándar
  mostrando el nombre, el cargo o las fechas de una docente donde el contrato
  dice que no pueden aparecer (Principio III, FR-054). Para este proyecto esto
  es una vulnerabilidad de pleno derecho, no un defecto cosmético;
- dependencias con vulnerabilidades conocidas que el motor alcance de verdad;
- cualquier forma de hacer que el motor escriba fuera de donde se le pidió, o
  lea archivos que no se le pasaron.

**Fuera del alcance:**

- **que un cálculo dé un resultado equivocado**. Eso es un error de dominio y se
  reporta como issue normal: es grave, pero no es un problema de seguridad y
  tratarlo en privado sería peor, porque la discusión normativa tiene que ser
  pública (Principio IV);
- que una regla esté marcada `NO_VERIFICADA` o que un informe salga
  `provisional`. Es el comportamiento buscado: el motor declarando lo que no
  tiene verificado;
- que `grids/` esté vacío y no haya montos reales. Está documentado en el README,
  bajo «Pendientes de datos»;
- el andamiaje de desarrollo (`.specify/`, `.claude/`), que no se ejecuta en
  producción;
- vulnerabilidades en GitHub Actions o en dependencias de CI que no afecten a
  quien instala el paquete, salvo que permitan inyectar código en un release.

Los puntos del Principio VII sobre HTTPS, CSP, cookies y PDF subidos aplican a
la **aplicación web** del producto, que no es este repositorio. Acá no hay
superficie web que endurecer.

## Lo que el motor ya hace por diseño

No es una lista de promesas: son restricciones verificadas por la suite de
tests y por CI, y cada una se puede auditar.

- **Sin red.** El motor no abre sockets. No hay telemetría, no hay analítica,
  no hay actualización automática de reglas: los datos normativos son archivos
  del repositorio.
- **Sin persistencia.** Ningún caso se guarda. Lo que el proceso recibe muere
  con el proceso, salvo que el usuario redirija la salida a un archivo él mismo.
- **Sin datos personales en diagnósticos.** El invariante I8 lo exige y los
  tests lo verifican: los mensajes de error llevan índice anónimo del período,
  campo y corrección. El enriquecimiento con cargo y fechas ocurre **solo** en
  la pantalla de la CLI, a partir del caso que el usuario ya tiene en la mano, y
  nunca en lo que viaja a logging (FR-054 y FR-057). Hay un test canario que
  observa la salida de logging para confirmarlo.
- **YAML cargado en modo seguro.** El único cargador del proyecto
  (`CargadorSinFloat`) deriva de `yaml.SafeLoader`, así que un archivo de caso
  no puede construir objetos de Python arbitrarios. Lo único que ese cargador
  le cambia a `SafeLoader` es entregar los decimales como `str` en lugar de
  `float`, para que el binario nunca toque un importe.
- **Aritmética exacta.** Todo con `Decimal`. No es seguridad en sentido
  estricto, pero es la razón por la que un importe no puede desviarse por
  redondeo binario.
- **CI con SAST, escaneo de dependencias, detección de secretos y SBOM.**
  `bandit`, `pip-audit`, `gitleaks` y `cyclonedx-py` corren en cada push. Un
  hallazgo alto o crítico sin mitigar bloquea el merge.

## Versiones con soporte

| Versión | Soporte |
|---|---|
| `0.1.x` | sí, es la línea en desarrollo |

El proyecto está **antes de su primer release estable**. Hasta el `1.0.0` solo
se mantiene la última versión publicada, y el gate de release comercial sigue
cerrado por los motivos que explica el README en «Pendientes de datos».
