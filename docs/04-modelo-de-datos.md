# Modelo de datos (DER)

Estado: Etapa 1. Verificado el 2026-09-21 contra las 22 migraciones de
`services/api/migrations` y contra los catálogos de la base real de Supabase (solo metadatos:
tablas, columnas, tipos, claves, índices y políticas; no se leyó ningún dato de personas). Las
columnas del diagrama se compararon una a una con `information_schema` y coinciden.

![Modelo entidad-relación de Jobby](diagramas/modelo-entidad-relacion.svg)

Fuente editable: `docs/diagramas/modelo-entidad-relacion.puml` (PlantUML). Para imprimir: lámina
A3 en [pdf/laminas/modelo-entidad-relacion.pdf](pdf/laminas/modelo-entidad-relacion.pdf).

## 1. Cómo leerlo

- Cada rectángulo es una tabla del esquema `public` con sus columnas y tipos de PostgreSQL.
  `auth.users` pertenece al servicio de identidad de Supabase y se dibuja solo como referencia.
- `<<PK>>` marca la clave primaria y `<<FK>>` la clave foránea; el asterisco (`*`), las
  columnas obligatorias (`NOT NULL`).
- Cardinalidad con patas de gallo: `||` uno y solo uno, `|o` cero o uno, `o{` cero o muchos.
- Colores: verde, cuenta y plan; azul, perfil maestro y sus datos; amarillo, archivos y caché;
  violeta, puestos y resultados.

## 2. Tablas

| Tabla | Para qué sirve | ¿Datos de personas? |
|---|---|---|
| `users` | Cuenta, plan (`tier`: free o premium) y datos de la suscripción de LemonSqueezy. | Sí: correo y nombre |
| `master_profiles` | Perfil profesional único de cada persona: titular, resumen, rol y seniority buscados, modalidad, industrias y porcentaje de perfil completo. | Sí |
| `uploaded_documents` | CV subidos: ruta en el almacén privado, estado del análisis y CV estructurado (`parsed_data`). | Sí: el contenido del CV |
| `skills` | Habilidades (confirmadas o no, si figuran en el CV o en LinkedIn) con su vector de 1536 números. | Sí |
| `experiences` | Experiencia laboral: empresa, cargo, fechas, descripción y logros. | Sí |
| `educations` | Estudios: institución, campo, nivel y fechas, con vector. | Sí |
| `languages` | Idiomas y nivel. | Sí |
| `certifications` | Certificaciones: emisor, fechas y enlace. | Sí |
| `rejected_skills` | Habilidades que la persona rechazó al revisar el resultado del CV. | Sí (bajo) |
| `job_descriptions` | Puestos analizados: texto original, datos estructurados y vector. | Texto pegado por la persona |
| `job_matches` | Resultado de comparar perfil y puesto: MatchScore, potencial, representación, origen de la brecha, desglose, recomendaciones y valoración de 1 a 5. | Derivado del perfil |
| `interview_kits` | Kits de entrevista del plan premium: preguntas, notas, estado y valoración. | Sí |
| `linkedin_scrape_cache` | Caché de siete días de las páginas de LinkedIn leídas para un kit. | Puede incluir datos de terceros |

## 3. Relaciones y cardinalidades

| Relación | Cardinalidad | Clave foránea | Al borrar el padre |
|---|---|---|---|
| `auth.users` – `users` | 1 a 0..1 | `users.supabase_uid` (única) | NO ACTION |
| `users` – `master_profiles` | 1 a 0..1 | `master_profiles.user_id` (única) | CASCADE |
| `users` – `uploaded_documents` | 1 a 0..N | `uploaded_documents.user_id` | CASCADE |
| `master_profiles` – `uploaded_documents` | 1 a 0..N | `uploaded_documents.profile_id` | CASCADE |
| `master_profiles` – `skills`, `experiences`, `educations`, `languages`, `certifications`, `rejected_skills` | 1 a 0..N cada una | `profile_id` en cada tabla | CASCADE |
| `users` – `job_descriptions` | 1 a 0..N | `job_descriptions.user_id` | CASCADE |
| `users`, `master_profiles` y `job_descriptions` – `job_matches` | 1 a 0..N cada una | `user_id`, `profile_id` y `job_id` | CASCADE |
| `users`, `master_profiles` y `job_descriptions` – `interview_kits` | 1 a 0..N cada una | `user_id`, `profile_id` y `job_id` | CASCADE |
| `job_matches` – `interview_kits` | 0..1 a 0..N | `interview_kits.match_id` (opcional) | SET NULL |
| `users` – `linkedin_scrape_cache` | 1 a 0..N | `linkedin_scrape_cache.user_id` | CASCADE |

De las 18 claves foráneas entre tablas de la aplicación, 17 borran en cascada y
`interview_kits.match_id` queda vacía (el kit se conserva). La clave hacia `auth.users` no borra
en cascada: por eso el borrado de cuenta elimina primero la fila de `users` y después la identidad.

## 4. Reglas que impone la base

- **Unicidad:** `users.supabase_uid`, un perfil por persona, un solo CV principal por persona
  (índice parcial), una ranura por CV y una lectura de LinkedIn por persona y enlace.
- **Acceso por dueño (RLS):** las 13 tablas tienen seguridad por fila; cada política deja ver y
  modificar solo las filas propias (`auth.uid()`). La API usa la clave de servicio, que no pasa
  por RLS, así que en sus consultas el aislamiento entre personas depende de filtrar por el
  usuario que sale del token.
- **Vectores:** las columnas `embedding` usan pgvector (`vector(1536)`) con índices HNSW de
  coseno en `skills`, `educations` y `job_descriptions`.

El esquema no declara restricciones `CHECK`: los valores permitidos de `tier`, `status`, `type`,
`cv_slot`, `user_rating` y similares los valida la API con modelos Pydantic.

## 5. Diferencias entre las migraciones y la base real

- La función `set_primary_uploaded_document` de la migración 018 no existe en la base de
  producción, aunque `PATCH /profiles/documents/{id}/set-primary` la invoca. La interfaz no usa
  ese endpoint; su corrección va en una migración nueva.
- Supabase no registra migraciones aplicadas (se aplicaron desde el editor SQL).
- La base real corre PostgreSQL 17.6; parte de la documentación y el `docker-compose.yml` local
  mencionan la versión 16.
