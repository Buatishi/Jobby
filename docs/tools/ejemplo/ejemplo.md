# Ejemplo de humo de las herramientas de documentación

Este documento comprueba que Markdown, Mermaid y PlantUML llegan al PDF. **No es** la
documentación oficial del proyecto: sirve de plantilla para los diagramas de la Etapa 1.

## 1. Flujo de datos (Mermaid, flowchart)

```mermaid
flowchart LR
    U([Persona usuaria]) -->|CV y oferta| W[Aplicación web]
    W -->|HTTPS| API[API FastAPI]
    API -->|consulta y guarda| DB[(Supabase)]
    API -->|prompt| IA[Proveedor de IA]
    IA -->|respuesta| API
```

## 2. Secuencia (Mermaid, sequenceDiagram)

```mermaid
sequenceDiagram
    participant W as Web
    participant A as API
    participant T as Tarea local
    W->>A: POST /jobs/analyze
    A-->>W: 202 con task_id
    A->>T: ejecuta el análisis
    W->>A: GET /tasks/{id}/stream
    T-->>A: resultado
    A-->>W: evento SUCCESS
```

## 3. Modelo de datos (Mermaid, erDiagram)

```mermaid
erDiagram
    USERS ||--o{ UPLOADED_DOCUMENTS : sube
    USERS ||--o{ JOB_DESCRIPTIONS : crea
    JOB_DESCRIPTIONS ||--o{ JOB_MATCHES : genera
    USERS {
        uuid id PK
        text tier
    }
```

## 4. Casos de uso UML (PlantUML, SVG generado)

![Casos de uso](ejemplo-casos-de-uso.svg)

| Herramienta | Uso recomendado |
|---|---|
| Mermaid | DFD, secuencia, ER y flujos dentro de los `.md` |
| PlantUML | UML formal: casos de uso y despliegue |
