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
| API FastAPI | Render, Docker (`jobby-fp0r.onrender.com`) | Supabase (PostgREST), Redis, proveedores de IA, Resend | HTTPS 443; rediss 6379 | Sí |
| Workers Celery | Render (a confirmar, ver sección 10) | Redis, Supabase, proveedores de IA | rediss 6379; HTTPS 443 | Sí |
| Datos | Supabase: Postgres 16 + pgvector, Auth y Storage (`cv-documents`) | — | 443 | Sí |
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
| Rol | `user` / `admin` | `users.role` (migración 023, nueva) | Métricas agregadas en `/admin/metrics` (403 si no es admin) |

El control de acceso vive en el servidor, en cada endpoint. La identidad sale del token,
nunca de un parámetro del cliente. La autenticación (registro, login, hash de contraseñas
y emisión del JWT) está delegada en Supabase Auth.

## 4. Qué cambia respecto del estado actual

1. `/api/v1/tasks/{id}` y `/stream` con autenticación y control de dueño.
2. El borrado de cuenta usa el bucket real `cv-documents` (Decisión 5).
3. `PATCH` y `DELETE` de `jobs`, con 409 `JOB_HAS_DEPENDENT_RESULTS` (Decisión 1).
4. `users.role`, `GET /admin/metrics` y `GET /users/me`.
5. Datos inválidos responden 400 `VALIDATION_ERROR`, con límites de entrada.
6. Tests unitarios separados de los de integración; estos contra un Supabase de prueba.
7. Pipeline con gate de deploy y `main` como única rama de producción.
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

## 10. Hallazgos y riesgos abiertos (relevados el 2026-09-20)

- **GitHub Actions no arranca.** Cada ejecución termina en `startup_failure` con el
  mensaje "recent account payments have failed or your spending limit needs to be
  increased". Hasta resolver la facturación de la cuenta el pipeline no puede correr.
- **Sin protección de rama.** En el plan Free de un repo privado GitHub la rechaza
  (403). Ver Decisión 12.
- **Render sigue la rama `feat/jobmatch-phase-1-2`.** Hay que apuntarlo a `main`.
- **Worker de Celery sin ubicación confirmada.** En los Deployments de GitHub solo
  aparece `jobmatch-api` de Render; existe además un proyecto de Railway
  (`elegant-energy`) con 6 deploys entre 2026-06-30 y 2026-07-15.
- **`ENVIRONMENT=production` no está seteada en Render**: `/docs` sigue público y faltan
  HSTS y CSP.
- **Frontend fijado.** `jobbyweb.vercel.app` apunta al deployment del commit `0abca0b`
  (2026-07-14); los deployments de producción posteriores no se asignan al dominio. No
  promover hasta mitigar el cold start: el proxy de Next corta a los 30 s y Render Free
  tarda ~40 s en despertar, lo que produce un 500 en la primera petición.
- **Endpoints y datos:** `/api/v1/tasks/{id}` sin autenticación y borrado de cuenta sobre
  el bucket equivocado (`cv-docs`).
- **Higiene local:** 3 refs ocultas `refs/codex/*` con binarios y ~155 MiB de temporales
  huérfanos en `.git`. No usar `git push --mirror`.
