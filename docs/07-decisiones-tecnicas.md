# Decisiones técnicas — Jobby (JobMatch AI)

**Autor:** Bautista Giraud · **Materia:** Programación sobre Redes, 6.° 1.ª, E.T. N.° 21 ·
**Etapa 1** · 2026-09-22

### 1. Framework de frontend

- **Opción adoptada:** Next.js 15 con React 19 y TypeScript estricto.
- **Alternativas evaluadas:** (a) React con Vite, como aplicación de una sola página; (b) Astro.
- **Fundamento:** costo cero en Vercel, con despliegue por Git y HTTPS incluido. El App Router
  permite proteger rutas en el servidor, que es donde vale: sin sesión, `/dashboard` responde 307
  antes de enviar nada al navegador. Documentación oficial extensa y ecosistema (Tailwind,
  shadcn/ui) que acelera la interfaz. Con Vite habría que montar el enrutado y la protección de
  rutas a mano; Astro está pensado para sitios de contenido, no para una aplicación con sesión.
- **Prestación resignada:** no es un sitio estático: hay render en servidor, así que hay que
  distinguir componentes de servidor y de cliente. El máximo rendimiento queda atado a Vercel.

### 2. Lenguaje del backend

- **Opción adoptada:** Python 3.13 con FastAPI y Pydantic v2.
- **Alternativas evaluadas:** (a) Node.js con Express o NestJS; (b) Django REST Framework.
- **Fundamento:** el núcleo del producto es procesamiento de texto e IA, y en Python están las
  bibliotecas que se usan (pdfplumber para el PDF, clientes HTTP asíncronos, similitud de
  vectores). FastAPI es asíncrono de punta a punta, valida con Pydantic y genera la documentación
  OpenAPI sola. Node habría unificado el lenguaje con el frontend, pero con menos herramientas
  para el PDF y los vectores; Django traía un ORM y un panel que el proyecto no necesita.
- **Prestación resignada:** dos lenguajes y dos cadenas de herramientas en el mismo repositorio;
  los tipos compartidos se mantienen a mano en `packages/shared-types`.

### 3. Base de datos

- **Opción adoptada:** PostgreSQL 17 gestionado por Supabase, con la extensión pgvector.
- **Alternativas evaluadas:** (a) MongoDB Atlas; (b) MySQL gestionado (PlanetScale);
  (c) Firebase Firestore.
- **Fundamento:** los datos son relacionales: una persona tiene un perfil, el perfil tiene
  habilidades, experiencia y estudios, y cada puesto produce un resultado. Trece tablas con claves
  foráneas y borrado en cascada lo modelan sin esfuerzo. Los vectores de significado se guardan
  con pgvector en el mismo motor, sin sumar otra base. Supabase agrega autenticación y
  almacenamiento de archivos con seguridad por fila, todo en el plan gratuito. Mongo no encaja con
  datos tan relacionales, MySQL no tiene un equivalente maduro a pgvector y Firestore ataría el
  modelo a consultas muy limitadas.
- **Prestación resignada:** el plan gratuito pausa el proyecto tras 7 días sin actividad. Base,
  identidad y archivos dependen del mismo proveedor. La base está en São Paulo y la API en
  Oregón, así que cada consulta cruza el continente.

### 4. Plataforma de despliegue y CI/CD

- **Opción adoptada:** Vercel para la web, Render (Docker) para la API y GitHub Actions para la
  integración continua.
- **Alternativas evaluadas:** (a) Railway para todo; (b) Fly.io; (c) servidores de la escuela.
- **Fundamento:** las dos plataformas tienen plan gratuito, despliegan con cada push a `main` y
  dan HTTPS y dominio sin configuración. Render corre la misma imagen Docker que se usa en local.
  Railway ya no ofrece un plan gratuito sostenido y Fly.io exige tarjeta y más administración; los
  servidores de la escuela obligaban a gestionar accesos y no quedaban accesibles desde cualquier
  conexión.
- **Prestación resignada:** Render gratuito duerme el servicio a los 15 minutos (la primera
  petición tarda entre 40 y 53 s; la web lo despierta y avisa) y no ofrece procesos de trabajo
  gratuitos. El dominio público de Vercel se asigna a mano.

### 5. Tecnología avanzada

- **Opción adoptada:** integración con servicios de terceros: pasarela de IA propia con ruteo
  por plan (DeepSeek en el gratuito, Claude en premium, OpenAI para vectores).
- **Alternativas evaluadas:** (a) cola de tareas con consumidor independiente (Celery y Redis);
  (b) almacenamiento de archivos con control de acceso, como segunda capacidad; (c) caché.
- **Fundamento:** analizar un CV o un puesto demanda entre 10 y 60 s y depende de servicios que
  fallan o demoran. La pasarela lo aísla con tiempo límite de 60 s, reintentos con espera
  creciente, proveedor según el plan y traducción de cualquier error a un mensaje comprensible,
  dejando el detalle en los registros; tiene tests propios. La cola exige un proceso de trabajo
  permanente que Render no ofrece gratis, y sin él no se puede mostrar el mensaje entrando y
  saliendo. El almacenamiento existe (bucket privado con políticas por persona) pero no se
  declara: la consigna recomienda una sola capacidad y descuenta si una adicional queda
  incompleta. La caché no se implementó: el módulo que había nunca se conectó y se quitó.
- **Prestación resignada:** las tareas largas corren dentro de la API (hasta dos a la vez) y su
  estado vive en memoria: si el servicio se reinicia, se pierde el seguimiento de una tarea en
  curso.

## Autoría

El proyecto fue desarrollado íntegramente por Bautista Giraud hasta la fecha de esta entrega:
análisis, diseño, backend, frontend, base de datos, despliegue y documentación. Al 2026-09-21
el repositorio tenía 102 commits desde el 2026-06-27, todos de ese único autor: los 42 de
septiembre corresponden a este trimestre y los anteriores, a la base preexistente del proyecto.

## Uso de herramientas de inteligencia artificial

Se utilizó **Codex** (OpenAI) durante el desarrollo, para generación y revisión de código,
interpretación de errores y redacción de documentación técnica. La documentación de esta entrega
(diagramas, matriz de requisitos y documentos técnicos) se elaboró con **Claude** (Anthropic) a
partir del repositorio y de la consigna, verificando cada afirmación contra el código, las
migraciones, las pruebas y comprobaciones de solo lectura sobre producción. Las decisiones de
diseño, la arquitectura y el alcance son propias; el resultado de las herramientas se revisó
antes de incorporarse. Se comprende la totalidad del código entregado y no se usarán
asistentes durante la defensa individual.

*El registro completo de decisiones operativas (Decisiones 1 a 22) está en `DECISIONS.md`; este
documento resume las cinco decisiones estructurales que pide la consigna.*
