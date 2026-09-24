# Visión del sistema objetivo: Jobby (JobMatch AI)

> Estado: **aprobada el 2026-09-20**. Es la fuente única para la documentación de
> análisis y diseño (E1) y para el cierre hacia E2. Cualquier cambio se registra en
> [`DECISIONS.md`](../DECISIONS.md) y se actualiza este archivo con la fecha.

## 1. Producto

Jobby es una plataforma de empleabilidad. El candidato sube su CV; la IA lo estructura
en un perfil maestro que el candidato confirma; carga puestos (texto o URL) y obtiene un
MatchScore explicable (fórmula ponderada de skills, seniority, educación, idiomas,
habilidades blandas y empresa), un reporte ATS y la brecha de realidad. El plan premium
suma optimización de CV para ATS y Interview Kit. El administrador ve solo métricas
agregadas, nunca datos personales ni CVs.

## 2. Arquitectura objetivo

| Componente | Dónde corre | Se comunica con | Protocolo / puerto | ¿Cruza Internet? |
|---|---|---|---|---|
| Cliente | Navegador | Vercel; Supabase Auth y Storage (login, OAuth y subida de CV) | HTTPS 443 | Sí |
| Frontend Next.js 15 | Vercel (`jobbyweb.vercel.app`) | API, mediante el rewrite `/api/backend/*` | HTTPS 443 | Sí |
| API FastAPI | Render, Docker (servicio `jobmatch-api`) | Supabase (PostgREST), Redis, proveedores de IA, Resend | HTTPS 443; rediss 6379 | Sí |
| Workers Celery | Render (a confirmar, ver sección 10) | Redis, Supabase, proveedores de IA | rediss 6379; HTTPS 443 | Sí |
| Datos | Supabase: Postgres 17 + pgvector, Auth y Storage (`cv-documents`) | — | 443 | Sí |
| Cola y límites de uso | Upstash Redis | — | 6379 (TLS) | Sí |
| Pagos | LemonSqueezy, webhook firmado con HMAC hacia la API | API | HTTPS 443 | Sí |
| IA | DeepSeek (principal), OpenAI (solo embeddings), Anthropic (premium) | — | HTTPS 443 | Sí |
| CI/CD | GitHub Actions hacia Render y Vercel | — | HTTPS 443 | Sí |

Recorrido objetivo del código a producción:

```
push o PR a main -> Actions: ruff + mypy -> tests unitarios y de integración
(Supabase de TEST) con cobertura >= 65 % -> build -> [gate] -> deploy Render + Vercel
```

Ambiente local: frontend en `localhost:3000`, API en `localhost:8000` y Redis por
`docker compose`. La diferencia con producción se resuelve solo por variables de entorno.

## 3. Acceso: dos ejes independientes

| Eje | Valores | Dónde vive | Qué controla |
|---|---|---|---|
| Plan | `free` / `premium` | `users.tier` (existente) | Límites de uso y funciones premium (403 `PREMIUM_REQUIRED`) |
| Rol | `user` / `admin` | `users.role` y `role_permissions` (migración 026) | Métricas agregadas en `/admin/metrics` (403 sin el permiso `metrics:read`) |

El control de acceso vive en el servidor, en cada endpoint. La identidad sale del token,
nunca de un parámetro del cliente. La autenticación (registro, login, hash de contraseñas
y emisión del JWT) está delegada en Supabase Auth.

## 4. Qué cambia respecto del estado actual

1. `/api/v1/tasks/{id}` y `/stream` con autenticación y control de dueño.
2. El borrado de cuenta usa el bucket real `cv-documents` (Decisión 5).
3. `PATCH` y `DELETE` de `jobs`, con 409 `JOB_HAS_DEPENDENT_RESULTS` (Decisión 1).
4. `users.role`, `GET /admin/metrics` y `GET /users/me` (hecho el 2026-09-24, Decisión 21).
5. Datos inválidos responden 400 `VALIDATION_ERROR`, con límites de entrada.
6. Tests unitarios separados de los de integración; estos contra un Supabase de prueba.
7. Pipeline con gate de deploy y `main` como única rama de producción (hecho el 2026-09-24).
8. Frontend: logout, manejo de 403, plan real en la interfaz y sin fallback a la URL de
   producción en `next.config.ts`.
9. `docker-compose` con solo Redis (el Postgres local no se usa).
10. Mitigación del cold start de la API.

## 5. Tecnología avanzada declarada

Cola de tareas (Celery + Redis) como única capacidad declarada. Problema que resuelve:
parsear un CV y analizar un puesto con IA tarda entre 10 y 60 s y no puede bloquear la
petición HTTP; la API responde 202 con un `task_id`, un consumidor independiente procesa
la tarea y el frontend sigue el estado por SSE. Condición: confirmar en producción que el
worker corre (Decisión 7). Las integraciones con IA, Storage y pagos son parte del
producto y no se reclaman como capacidades adicionales.

Nota (2026-09-21, Decisión 15): en producción las tareas corren en modo local, sin
consumidor independiente, así que la cola no puede declararse hoy como capacidad
avanzada. La capacidad se confirma cuando se resuelva el modo de USD 7 (worker o Render
Starter) o se elija otra.

Actualización (2026-09-22, Decisión 17): la capacidad declarada pasa a ser la integración con
servicios de terceros (pasarela de IA con ruteo por plan, tiempo límite, reintentos y errores
sanitizados). La cola queda como ampliación posible si se paga un worker.

## 6. Estrategia de tests

- `tests/unit/`: lógica pura de negocio (motor de match, ATS, reglas de límites, merge de
  skills), sin I/O, en milisegundos.
- `tests/integration/`: peticiones HTTP contra un proyecto Supabase de pruebas
  (Decisión 4); deben fallar cerrados si faltan `TEST_SUPABASE_*`.
- Casos obligatorios: 201, 200, PATCH, DELETE, 400, 404 y una regla de negocio de
  extremo a extremo.
- Cobertura de líneas del backend >= 65 %, medida y exigida en el pipeline.

## 7. Ramas y CI/CD

`main` es el tronco y la rama de producción. El trabajo va en ramas temáticas con
prefijo, integradas por pull request. Detalle en
[`00-flujo-de-ramas.md`](00-flujo-de-ramas.md).

## 8. Documentación de E1 (carpeta `docs/`, en PDF y fuentes)

DFD nivel 0, casos de uso (UML, con tres narrativas), DFD nivel 1, DFD nivel 2, DER,
arquitectura y despliegue, y decisiones técnicas (2 páginas, con la declaración de uso de
IA). Diagramas como código con PlantUML (Decisión 10).

## 9. Decisiones aprobadas

Ver [`DECISIONS.md`](../DECISIONS.md): decisiones 1 a 12.

## 10. Pendientes conocidos

- **CI/CD:** activar GitHub Actions con cobertura mínima y un job de despliegue que
  dependa de los tests (Decisión 6).
- **Protección de `main`:** pull request obligatorio (Decisión 12).
- **Cola de tareas:** producción usa el modo local por ahora (Decisión 15); el worker de
  Celery (USD 7/mes) o Render Starter quedan para evaluar más adelante.
- **Frontend:** el dominio público pasó al despliegue actual el 2026-09-21. Pendientes
  de producto y frontend en `docs/05-pendientes-producto.md`.
- **Disponibilidad:** el plan gratuito de Render duerme el servicio tras un rato sin
  tráfico. Mitigado con el pre-calentamiento al abrir la web y el reintento de los GET
  (Decisión 14); una primera petición en frío sin visita previa sigue tardando unos 42 s.
- **Tests de integración** contra una base de pruebas separada (Decisión 4).
