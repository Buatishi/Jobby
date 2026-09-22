# Propuesta de proyecto — Jobby (JobMatch AI)

Trabajo Práctico Integrador · Programación sobre Redes · 6.° 1.ª · E.T. N.° 21 · Semana 1

## Denominación del producto

**Jobby** (nombre técnico del repositorio: JobMatch AI).

## Problema que resuelve y destinatarios

Quien busca empleo se postula sin saber cuánto encaja con cada oferta ni por qué los sistemas de
filtrado automático (ATS) descartan su CV. Jobby está pensado para personas que buscan trabajo y
quieren saber, antes de postularse, qué tan compatibles son con un puesto y qué mejorar.

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

## Integrantes y rol previsto

| Integrante | Rol previsto |
|---|---|
| Bautista Giraud | Análisis y diseño, backend (API), frontend, base de datos, despliegue y documentación |

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

<small>Versión preparada el 2026-09-22.</small>
