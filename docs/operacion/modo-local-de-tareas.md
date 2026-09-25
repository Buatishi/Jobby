# Modo local de tareas en segundo plano

Estado: código disponible desde 2026-09-21 (Decisión 15 de `DECISIONS.md`). Se activa con
una variable de entorno; por defecto la API sigue usando Celery.

## 1. Qué es

Cuando una persona sube un CV o pide un análisis, la API no hace el trabajo lento dentro de
la petición HTTP: crea una tarea, responde de inmediato con un `task_id` y el frontend
consulta el avance por SSE (`/tasks/{task_id}/stream`). Hay dos formas de ejecutar la tarea:

| | Modo `celery` (por defecto) | Modo `local` |
|---|---|---|
| Quién ejecuta | Un worker independiente que consume la cola de Redis (Upstash) | Un hilo del propio proceso de la API |
| Requiere | Un servicio worker desplegado (en Render cuesta desde USD 7/mes; no hay plan gratis) | Nada adicional |
| Estado de la tarea | En Redis (sobrevive a reinicios) | En memoria del proceso (se pierde al reiniciar o dormirse) |
| Concurrencia | La del worker (`--concurrency`) | `LOCAL_TASK_MAX_CONCURRENCY` (2 por defecto) |

Tareas cubiertas en modo local: parseo de CV, análisis de puesto, match y kit de entrevista
(las tres últimas desde este cambio; el parseo ya lo tenía).

## 2. Configuración

| Variable | Valor | Efecto |
|---|---|---|
| `TASK_EXECUTION_MODE` | `celery` (defecto) o `local` (sin distinguir mayúsculas) | Elige cómo se ejecutan las tareas |
| `LOCAL_TASK_MAX_CONCURRENCY` | entero, 2 por defecto | Tareas locales simultáneas |

El `.env.example` de la raíz ya usa `TASK_EXECUTION_MODE=local` para desarrollo.

## 3. Comportamiento en modo local

- El identificador es `<user_id>.local-<tipo>-<uuid>` (`local-parse-cv`, `local-job`,
  `local-match`, `local-kit`). La comprobación de propiedad de `/tasks` es la misma que en
  Celery: nadie ve tareas ajenas.
- Un pedido directo con la capacidad llena falla enseguida con un mensaje genérico.
- El **match** que se encadena al terminar un análisis espera su cupo hasta 300 s en lugar
  de fallar, porque el análisis todavía ocupa uno cuando lo encadena.
- Las excepciones se reportan a Sentry igual que en los workers de Celery, y al usuario le
  llega el mensaje público de `app/core/public_errors.py`, sin detalles internos.

## 4. Límites

- El estado vive en la memoria del proceso: si el servicio se reinicia o se duerme mientras
  corre una tarea, esa tarea se pierde y hay que repetirla. Desde el 2026-09-23, consultar
  una tarea que ya no está en memoria responde enseguida `failed` con un mensaje que pide
  repetirla; antes el cliente esperaba los 15 minutos del tiempo límite del stream.
- Una tarea terminada se conserva una hora para que el cliente lea el resultado y después
  se descarta (`FINISHED_TASK_RETENTION_SECONDS`): así la memoria no crece con cada tarea.
- Es una sola instancia (Render Free no permite más) y comparte los 512 MB con la API.
- El análisis por URL usa Playwright, y la imagen de la API no instala Chromium
  (`services/api/Dockerfile`): es un pendiente aparte, ver `docs/05-pendientes-producto.md`.

## 5. Cómo activarlo en producción

Es un cambio de variable de entorno en producción, así que requiere aprobación explícita.

1. En el servicio `jobmatch-api` de Render, agregar `TASK_EXECUTION_MODE=local`. Render
   redespliega solo.
2. Validar: subir un CV de prueba propio y comprobar que el estado pasa de `PENDING` a
   `SUCCESS` en pocos segundos (el parseo además necesita saldo de OpenAI para los
   embeddings).
3. Reversión: quitar la variable o poner `celery`. No hay migraciones ni cambios de datos.

## 6. Cuándo revisar esta decisión

- Si se aprueba el worker (USD 7/mes): volver a `celery`; el código de Celery no se tocó.
- Si se aprueba Render Starter para la API (USD 7/mes, siempre despierta): conviene
  mantener el modo local, porque el proceso no se duerme y no se pierden tareas por eso.

## 7. Pruebas

`services/api/tests/unit/test_local_tasks.py` (7 casos): ejecución en proceso de análisis, match
y kit, sin distinguir mayúsculas; reporte de fallas; Celery sin cambios; solo el match
encadenado espera cupo; espera frente a falla inmediata con la capacidad llena.
