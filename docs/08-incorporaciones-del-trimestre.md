# Incorporaciones del trimestre

Estado: borrador del 2026-09-25 para la Etapa 2. Se actualiza al congelar el código, en la semana
11.

Jobby es un proyecto preexistente. La consigna (sección 1) evalúa las incorporaciones y
adaptaciones hechas durante el trimestre, que deben poder acreditarse en el historial de commits.
Este documento separa lo previo de lo nuevo y enlaza cada incorporación con su pull request.

## 1. El corte

| | Base preexistente | Trimestre |
|---|---|---|
| Período | 2026-06-27 al 2026-07-15 | Desde el 2026-09-20 |
| Commits propios (sin contar merges) | 60 | 74 |
| Pull requests integrados | — | 30 (del #1 al #31; el #15 se cerró sin integrar a propósito) |
| Primer y último commit | `52a0ad8` … `bb97750` | `41cdfde` … en curso |

- **Por mes:** junio 30 commits, julio 30, agosto 0 y septiembre 107 (74 propios, 30 merges de
  pull requests y 3 merges de `main` hacia una rama). Al 2026-09-25 `main` tiene 167 commits, todos
  del mismo autor.
- **Cómo se trabaja desde el corte:** cada cambio va en una rama corta, entra por pull request con
  los tres controles del pipeline en verde y queda como un merge en `main`
  ([00-flujo-de-ramas.md](00-flujo-de-ramas.md)). Las etiquetas `milestone/00` a `milestone/10`
  marcan los hitos de la base preexistente; `milestone/11` ya es el primer pull request del trimestre.
- **Uso de herramientas de IA:** declarado en [07-decisiones-tecnicas.md](07-decisiones-tecnicas.md).

Tamaño de lo incorporado, medido desde el último commit previo (`bb97750`) hasta `main`:

| Área | Archivos | Líneas agregadas | Líneas quitadas |
|---|---|---|---|
| API (`services/api/app`) | 43 | 1213 | 272 |
| Pruebas de la API (`services/api/tests`) | 35 | 3223 | 253 |
| Migraciones de la base (023 a 027) | 5 | 243 | 0 |
| Web (`apps/web`: `src`, `lib` y `components`) | 41 | 2670 | 158 |
| Documentación (`docs`) | 63 | 3192 | 0 |
| Pipeline (`.github`) | 2 | 44 | 75 |
| `README.md` y `DECISIONS.md` | 2 | 913 | 113 |

## 2. Lo previsto en la propuesta y lo hecho

La propuesta de la semana 1 ([00-propuesta.md](00-propuesta.md)) listó seis incorporaciones.

| Incorporación prevista | Estado | Pull requests | Decisión |
|---|---|---|---|
| Documentación de análisis y diseño: DFD, casos de uso, DER, arquitectura y decisiones | Hecha y entregada en E1; se mantiene al día | #2, #7, #11, #12, #16 y las actualizaciones de #22 a #28 | 16 y 18 |
| Pipeline de CI/CD que ejecuta los tests, exige el 65 % de cobertura y corta el despliegue ante una falla | Hecho. La corrida fallida y su arreglo están en la rama `ci/verificacion-del-corte` | #14, #16, #18 y los deploy hooks del 2026-09-24 | 3 y 6 |
| Dos roles con permisos diferenciados y respuesta 403 | Hecho: usuario y administrador, con permisos guardados como datos | #22 | 2 y 21 |
| Tests de integración contra una base de pruebas separada | Hecho: 12 pruebas contra el proyecto `jobby-test`, en cada ejecución del pipeline | #28 | 4 |
| CRUD completo de la entidad principal (puestos) | Hecho: editar y eliminar, con 409 si el puesto tiene resultados | #26 | 1 |
| Tecnología avanzada: integración con servicios de IA de terceros, con manejo de fallas y demoras | Hecha: errores públicos sin detalles internos, tiempo límite y reintentos solo ante fallas temporales | #3, #29 y #31 | 17 |

## 3. Incorporado además de lo previsto

- **Seguridad:** tareas en segundo plano con autenticación y control de dueño, guarda anti-SSRF y
  límites de entrada (#3); 63 alertas de dependencias resueltas y redirección abierta del login
  cerrada (#17); solo se registran documentos y perfiles propios (#19); la clave pública ya no lee
  ni escribe ninguna tabla (#21, Decisión 20); cerrar sesión invalida el token al instante (#25,
  Decisión 22).
- **Errores y validación:** 404 para lo que no existe y 400 para los datos inválidos (#13), también
  cuando la base rechaza un id mal formado (#27, Decisión 8).
- **Pruebas:** orden aleatorio en cada corrida y una prueba de errores deliberados que hoy detecta
  las 11 alteraciones de reglas de negocio (eran 5) (#28). Las pruebas unitarias de la API pasaron de
  unos 63 s a 3 s (#29). Hoy son 261 pruebas de la API (249 unitarias y 12 de integración, cobertura del 82 %) y 85
  de la web.
- **Rendimiento y operación:** arranque en frío mitigado con precalentamiento y reintentos de lectura
  (#5, Decisión 14); tareas en proceso mientras no haya un worker pago (#6, Decisión 15); reporte ATS
  con los vectores en lote e índices para las claves foráneas (#20, Decisión 19); código muerto
  eliminado (#18).
- **Experiencia de uso:** ver la contraseña y aviso de Bloq Mayús (#24); inicio con Google cuando ya
  hay una sesión abierta (#30); aviso claro cuando la cuenta de OpenAI se queda sin saldo (#31).

## 4. Diferencias respecto de la Etapa 1

La documentación de E1 se integró en el #12 (2026-09-22). Desde entonces cambió así:

- **DFD** ([01-dfd.md](01-dfd.md) y [03-dfd-nivel-2.md](03-dfd-nivel-2.md)): flujos F35 y F36 por el
  cierre de sesión (#25) y F37 a F40 por la edición y el borrado de puestos; el proceso 3 pasó a
  llamarse «Analizar y gestionar puestos» (#26).
- **Casos de uso** ([02-casos-de-uso.md](02-casos-de-uso.md)): CU23 (métricas del administrador)
  implementado (#22), y CU24 (cerrar sesión), CU25 y CU26 (editar y eliminar puesto) nuevos (#25 y
  #26).
- **Modelo de datos** ([04-modelo-de-datos.md](04-modelo-de-datos.md)): migraciones 023 a 027, con las
  tablas `roles` y `role_permissions`, la columna `users.role`, índices para las claves foráneas y
  las funciones `admin_metrics` y `session_is_active` (#14, #20, #21, #22 y #25).
- **Arquitectura y despliegue** ([06-arquitectura-y-despliegue.md](06-arquitectura-y-despliegue.md)):
  el despliegue sale solo del pipeline, con deploy hooks, y el CI usa los secretos del proyecto de
  pruebas (#28).
- **Decisiones** ([../DECISIONS.md](../DECISIONS.md)): 19 a 22 nuevas y actualizaciones de las
  decisiones 1, 4, 8 y 17.

## 5. Cómo verificarlo

```bash
git log --oneline --no-merges --until=2026-08-31 main | wc -l   # base preexistente: 60
git log --oneline --no-merges --since=2026-09-01 main | wc -l   # trimestre: 74 al 2026-09-25
git diff --shortstat bb97750 main                               # tamaño de lo incorporado
gh pr list --state merged --limit 100                           # los pull requests del trimestre
```

El historial del pipeline está en la pestaña Actions del repositorio
(<https://github.com/Buatishi/Jobby/actions>), con la corrida fallida de la rama
`ci/verificacion-del-corte` como evidencia del corte del despliegue.
