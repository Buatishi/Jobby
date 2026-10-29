# Propuesta de proyecto — Jobby (JobMatch AI)

Trabajo Práctico Integrador · Programación sobre Redes · 6.° 1.ª · E.T. N.° 21 · Semana 1

## Denominación del producto

**Jobby** (nombre técnico del repositorio: JobMatch AI).

## Problema que resuelve y destinatarios

Quien busca empleo se postula sin saber cuánto encaja con cada oferta ni por qué los sistemas de
filtrado automático (ATS) descartan su CV. Jobby está pensado para personas que buscan trabajo y
quieren saber, antes de postularse, qué tan compatibles son con un puesto y qué mejorar.

## Dimensión del problema

- **Cuántas personas buscan empleo.** En el segundo trimestre de 2026, en los 31 aglomerados
  urbanos de la EPH, la desocupación fue del 7,9 %: 1,2 millones de personas sin trabajo, más 2,5
  millones con empleo que buscan otro, unos 3,7 millones en total. Entre los 14 y los 29 años la
  desocupación sube al 17,1 % en las mujeres y al 14,1 % en los varones (INDEC, cuadro 1.3).
- **Qué filtra las postulaciones.** El 97,4 % de las empresas Fortune 500 (487 de 500) usa un ATS
  (Jobscan, 2026). Es un dato de Estados Unidos: muestra que el filtrado está extendido, no mide el
  mercado argentino.
- **Qué sustentan y qué no.** Dimensionan la audiencia y justifican priorizar la compatibilidad y el
  reporte ATS antes de postularse. No miden cuántos CV descarta un ATS ni cuánto ayuda Jobby, y no
  se promete ese resultado. Jobby no busca ofertas ni contacta a las empresas.

**Fuentes** (consultadas el 2026-10-28): INDEC, *Mercado de trabajo. Tasas e indicadores
socioeconómicos (EPH)*, 2.º trimestre de 2026,
<https://www.indec.gob.ar/uploads/informesdeprensa/mercado_trabajo_eph_2trim26433FCBC5A8.pdf>;
Jobscan, *Fortune 500 ATS usage report*, 6.ª edición, 2026,
<https://www.jobscan.co/blog/fortune-500-use-applicant-tracking-systems/>.

## Funcionalidades principales

1. **Perfil a partir del CV.** La persona sube su CV en PDF; el sistema extrae el texto, lo ordena
   con IA en habilidades, experiencia, estudios e idiomas, y la persona lo revisa y confirma.
2. **Análisis de un puesto.** Se carga una oferta laboral (texto o enlace) y el sistema la
   estructura: cargo, seniority, tecnologías, idiomas y requisitos.
3. **MatchScore explicable.** Compara perfil y puesto en seis criterios ponderados, calcula un
   puntaje de 0 a 100 con el origen de la brecha y da recomendaciones concretas.
4. **Reporte ATS.** Indica qué palabras clave del puesto aparecen en el CV (de forma exacta o por
   significado), cuáles faltan y qué problemas de formato tiene el documento.

Todas las operaciones son sobre datos propios de cada persona (crear, consultar, modificar y
eliminar perfil, documentos, puestos y resultados), con un plan gratuito con límites y uno premium.

## De la necesidad a la solución técnica

La última columna remite a los casos de uso ([02-casos-de-uso.md](02-casos-de-uso.md)) y a los
procesos del DFD ([01-dfd.md](01-dfd.md)).

| Necesidad | Funcionalidad | Solución técnica | Se comprueba en |
|---|---|---|---|
| Mi CV es un PDF suelto | 1. Perfil a partir del CV | Storage privado de Supabase; tarea `parse_cv` (texto e IA); la persona confirma | CU05 a CU07; proceso 2 |
| No sé cuánto encajo con una oferta | 2. Análisis de puesto y 3. MatchScore | `POST /jobs/analyze`; tareas `job_analysis` y `match` (IA, pgvector); seis criterios ponderados | CU08 a CU11; procesos 3 y 4 |
| No sé por qué un ATS me descarta | 4. Reporte ATS | `GET /ats/{job_id}`: palabras clave (exactas o por significado) y formato | CU12; proceso 4 |
| No sé qué mejorar | Recomendaciones y optimizador de CV | `GET /profiles/reality-gap`; `POST /ats/optimize`; `GET /profiles/cv` | CU13, CU14 y CU27; procesos 4 y 2.9 |
| Quiero que mis datos sean solo míos | Operaciones sobre datos propios | Identidad por token y filtro por dueño; `DELETE /users/me`; admin: solo métricas agregadas | CU22, CU23, CU25 y CU26; procesos 1, 3 y 7 |
| Probar gratis y pagar solo si lo necesito | Plan gratuito y premium | `POST /billing/checkout`; webhook firmado de LemonSqueezy | CU19 a CU21; proceso 6 |

## Integrantes y rol previsto

| Integrante | Rol previsto |
|---|---|
| Bautista Giraud | Análisis y diseño, backend (API), frontend, base de datos, despliegue y documentación |
| Natalia Blanco | Parte de la documentación, aporte de ideas y solución de problemas |

## Proyecto preexistente

- **Repositorio:** <https://github.com/Buatishi/Jobby> (público).
- **Base existente al inicio del trimestre:** el flujo CV → perfil → puesto → MatchScore → reporte
  ATS, desplegado en Vercel (web) y Render (API) con Supabase como base de datos.
- **Incorporaciones previstas para este trimestre:** documentación de análisis y diseño (DFD, casos
  de uso, DER, arquitectura y decisiones); pipeline de CI/CD que ejecute los tests, exija el 65 % de
  cobertura y corte el despliegue ante una falla; dos roles con permisos diferenciados (usuario y
  administrador) con respuesta 403; tests de integración contra una base de pruebas separada;
  CRUD completo de la entidad principal (puestos); y la tecnología avanzada declarada (integración
  con servicios de IA de terceros) con su manejo de fallas y demoras.

<small>Versión preparada el 2026-09-22; actualizada el 2026-10-28 con la devolución del docente del
2026-10-06.</small>
