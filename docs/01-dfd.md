# Diagramas de flujo de datos (DFD)

Estado: Etapa 1, niveles 0 y 1. El nivel 2 se agrega en el siguiente documento de la serie.

## Convenciones

| Símbolo | Significa |
|---|---|
| Rectángulo | Entidad externa (persona o sistema de terceros) |
| Círculo numerado | Proceso |
| Cilindro `D#` | Almacén de datos |
| Flecha | Flujo de datos, rotulado con **el dato que viaja** y no con la acción |

Todo lo descrito se verificó contra el código: los endpoints de `services/api/app/api/v1/`,
las tareas de `services/api/app/tasks/` y las pantallas de `apps/web`. Lo que aún no existe
está marcado como **planificado**.

## 1. Nivel 0: diagrama de contexto

El sistema completo es un único proceso, rodeado de sus entidades externas.

```mermaid
flowchart LR
    U[Persona usuaria]
    A["Administrador<br/>(planificado)"]
    ID["Proveedor de identidad<br/>Supabase Auth con Google"]
    IA["Proveedores de IA<br/>DeepSeek, Anthropic y OpenAI"]
    LS[LemonSqueezy]
    W["Sitios de ofertas laborales<br/>y LinkedIn"]
    EM["Servicio de email<br/>Resend"]
    SE[Sentry]
    P(("0<br/>Sistema<br/>Jobby"))

    U -->|"F1 Credenciales y datos de registro"| P
    U -->|"F2 CV en PDF"| P
    U -->|"F3 Datos del perfil"| P
    U -->|"F4 Oferta laboral"| P
    U -->|"F5 Valoración de resultados"| P
    U -->|"F6 Solicitud de plan premium"| P
    U -->|"F7 Solicitud de baja de cuenta"| P
    U -->|"F8 Solicitud de CV optimizado"| P
    U -->|"F9 Solicitud de kit de entrevista"| P
    P -->|"F11 Perfil estructurado del CV"| U
    P -->|"F12 Resultados de compatibilidad"| U
    P -->|"F13 CV optimizado"| U
    P -->|"F14 Kit de entrevista"| U
    P -->|"F15 Estado de las tareas"| U
    P -->|"F16 Enlace de pago"| U
    P -->|"F17 Resumen del panel"| U
    P -->|"F18 Confirmación de baja"| U

    A -->|"F19 Solicitud de métricas"| P
    P -->|"F20 Métricas agregadas de uso"| A

    P -->|"F21 Credenciales a verificar"| ID
    ID -->|"F22 Sesión e identidad verificada"| P
    P -->|"F23 Orden de eliminar identidad"| ID

    P -->|"F24 Instrucciones con texto del CV o de la oferta"| IA
    P -->|"F25 Textos a vectorizar"| IA
    IA -->|"F26 Datos estructurados o texto generado"| P
    IA -->|"F27 Vectores de significado"| P

    P -->|"F28 Solicitud de checkout"| LS
    LS -->|"F29 Enlace de pago del checkout"| P
    LS -->|"F30 Eventos de suscripción firmados"| P

    P -->|"F31 Solicitud de una página web"| W
    W -->|"F32 Contenido de la página web"| P

    P -->|"F33 Mensaje de aviso de suscripción"| EM
    P -->|"F34 Eventos de error"| SE
```

### Entidades externas

| Entidad | Quién es |
|---|---|
| Persona usuaria | Quien busca empleo; usa el plan gratuito o el premium |
| Administrador | Consulta métricas agregadas, sin acceso a CV ni a datos personales (**planificado**, Decisión 2) |
| Proveedor de identidad | Supabase Auth, con inicio de sesión federado con Google |
| Proveedores de IA | DeepSeek (principal), Anthropic (premium) y OpenAI (solo vectores) |
| LemonSqueezy | Cobra la suscripción premium |
| Sitios de ofertas laborales y LinkedIn | Páginas públicas que se leen para obtener el texto de un puesto |
| Servicio de email | Resend, para avisos de suscripción |
| Sentry | Recibe los eventos de error |

### Flujos del nivel 0

| ID | Dato | Origen | Destino |
|---|---|---|---|
| F1 | Credenciales y datos de registro | Persona usuaria | Sistema |
| F2 | CV en PDF | Persona usuaria | Sistema |
| F3 | Datos del perfil (experiencia, educación, idiomas, habilidades) | Persona usuaria | Sistema |
| F4 | Oferta laboral (URL o texto) | Persona usuaria | Sistema |
| F5 | Valoración de resultados (del match y del kit) | Persona usuaria | Sistema |
| F6 | Solicitud de plan premium | Persona usuaria | Sistema |
| F7 | Solicitud de baja de cuenta | Persona usuaria | Sistema |
| F8 | Solicitud de CV optimizado | Persona usuaria | Sistema |
| F9 | Solicitud de kit de entrevista | Persona usuaria | Sistema |
| F11 | Perfil estructurado del CV | Sistema | Persona usuaria |
| F12 | Resultados de compatibilidad (Match Score, reporte ATS y Reality Gap) | Sistema | Persona usuaria |
| F13 | CV optimizado | Sistema | Persona usuaria |
| F14 | Kit de entrevista | Sistema | Persona usuaria |
| F15 | Estado de las tareas | Sistema | Persona usuaria |
| F16 | Enlace de pago | Sistema | Persona usuaria |
| F17 | Resumen del panel | Sistema | Persona usuaria |
| F18 | Confirmación de baja | Sistema | Persona usuaria |
| F19 | Solicitud de métricas | Administrador | Sistema |
| F20 | Métricas agregadas de uso | Sistema | Administrador |
| F21 | Credenciales a verificar | Sistema | Proveedor de identidad |
| F22 | Sesión e identidad verificada | Proveedor de identidad | Sistema |
| F23 | Orden de eliminar identidad | Sistema | Proveedor de identidad |
| F24 | Instrucciones con texto del CV o de la oferta | Sistema | Proveedores de IA |
| F25 | Textos a vectorizar | Sistema | Proveedores de IA |
| F26 | Datos estructurados o texto generado | Proveedores de IA | Sistema |
| F27 | Vectores de significado | Proveedores de IA | Sistema |
| F28 | Solicitud de checkout | Sistema | LemonSqueezy |
| F29 | Enlace de pago del checkout | LemonSqueezy | Sistema |
| F30 | Eventos de suscripción firmados | LemonSqueezy | Sistema |
| F31 | Solicitud de una página web (del puesto o de un perfil de LinkedIn) | Sistema | Sitios de ofertas |
| F32 | Contenido de la página web | Sitios de ofertas | Sistema |
| F33 | Mensaje de aviso de suscripción | Sistema | Servicio de email |
| F34 | Eventos de error | Sistema | Sentry |

`F10` no se usa: la numeración se conserva para que los identificadores no cambien entre
niveles.

## 2. Nivel 1: procesos principales

El proceso 0 se descompone en siete procesos y ocho almacenes de datos.

Para que se lea al imprimirlo, el nivel 1 se dibuja en tres vistas del mismo diagrama, todas
con los mismos procesos y la misma numeración: la **vista 1A** muestra las personas y sus flujos,
la **vista 1B** los sistemas externos y sus flujos, y la **vista 1C** los ocho almacenes de datos.

### Vista 1A: procesos y personas

```mermaid
%%{init: {"layout": "dagre", "flowchart": {"curve": "basis", "nodeSpacing": 30, "rankSpacing": 70}}}%%
flowchart LR
    U[Persona usuaria]
    A["Administrador<br/>(planificado)"]

    subgraph SIS["Sistema Jobby"]
        P1(("1<br/>Gestionar cuenta<br/>y acceso"))
        P2(("2<br/>Procesar CV<br/>y perfil"))
        P3(("3<br/>Analizar<br/>puesto"))
        P4(("4<br/>Evaluar<br/>compatibilidad"))
        P5(("5<br/>Generar kit<br/>de entrevista"))
        P6(("6<br/>Gestionar<br/>suscripción"))
        P7(("7<br/>Consultar métricas<br/>(planificado)"))
    end

    U -->|"F1 Credenciales y datos de registro<br/>F7 Solicitud de baja de cuenta"| P1
    P1 -->|"F18 Confirmación de baja"| U
    U -->|"F2 CV en PDF<br/>F3 Datos del perfil"| P2
    P2 -->|"F11 Perfil estructurado del CV<br/>F15.2 Estado de la tarea"| U
    U -->|"F4 Oferta laboral"| P3
    P3 -->|"F15.3 Estado de la tarea"| U
    P3 -->|"Identificadores de puesto y perfil"| P4
    U -->|"F5.1 Valoración del match<br/>F8 Solicitud de CV optimizado"| P4
    P4 -->|"F12 Resultados de compatibilidad<br/>F13 CV optimizado<br/>F17 Resumen del panel<br/>F15.4 Estado de la tarea"| U
    U -->|"F9 Solicitud de kit de entrevista<br/>F5.2 Valoración del kit"| P5
    P5 -->|"F14 Kit de entrevista<br/>F15.5 Estado de la tarea"| U
    U -->|"F6 Solicitud de plan premium"| P6
    P6 -->|"F16 Enlace de pago"| U
    A -->|"F19 Solicitud de métricas"| P7
    P7 -->|"F20 Métricas agregadas de uso"| A
```

### Vista 1B: procesos y sistemas externos

```mermaid
%%{init: {"layout": "dagre", "flowchart": {"curve": "basis", "nodeSpacing": 30, "rankSpacing": 70}}}%%
flowchart LR
    subgraph SIS["Sistema Jobby"]
        P1(("1<br/>Gestionar cuenta<br/>y acceso"))
        P2(("2<br/>Procesar CV<br/>y perfil"))
        P3(("3<br/>Analizar<br/>puesto"))
        P4(("4<br/>Evaluar<br/>compatibilidad"))
        P5(("5<br/>Generar kit<br/>de entrevista"))
        P6(("6<br/>Gestionar<br/>suscripción"))
    end

    ID["Proveedor de identidad"]
    IA["Proveedores de IA"]
    LS[LemonSqueezy]
    W["Sitios de ofertas<br/>y LinkedIn"]
    EM["Servicio de email"]
    SE[Sentry]

    P1 -->|"F21 Credenciales a verificar<br/>F23 Orden de eliminar identidad"| ID
    ID -->|"F22 Sesión e identidad verificada"| P1
    P2 -->|"F24.2 Instrucciones con texto del CV<br/>F25.2 Textos a vectorizar"| IA
    IA -->|"F26.2 Datos estructurados<br/>F27.2 Vectores de significado"| P2
    P3 -->|"F24.3 Instrucciones con texto de la oferta<br/>F25.3 Textos a vectorizar"| IA
    IA -->|"F26.3 Datos estructurados<br/>F27.3 Vectores de significado"| P3
    P3 -->|"F31.3 Solicitud de la página"| W
    W -->|"F32.3 Contenido de la página"| P3
    P4 -->|"F24.4 Instrucciones con texto del CV"| IA
    IA -->|"F26.4 Texto generado"| P4
    P5 -->|"F24.5 Instrucciones con perfil, puesto y LinkedIn"| IA
    IA -->|"F26.5 Texto generado"| P5
    P5 -->|"F31.5 Solicitud de perfil de LinkedIn"| W
    W -->|"F32.5 Contenido del perfil de LinkedIn"| P5
    P6 -->|"F28 Solicitud de checkout"| LS
    LS -->|"F29 Enlace de pago del checkout<br/>F30 Eventos de suscripción firmados"| P6
    P6 -->|"F33 Mensaje de aviso de suscripción"| EM
    SIS -->|"F34 Eventos de error"| SE
```

El proceso 7 no aparece en esta vista porque no intercambia datos con sistemas externos.

### Vista 1C: procesos y almacenes de datos

```mermaid
%%{init: {"layout": "dagre", "flowchart": {"curve": "basis", "nodeSpacing": 30, "rankSpacing": 70}}}%%
flowchart LR
    P1(("1<br/>Gestionar cuenta<br/>y acceso"))
    P2(("2<br/>Procesar CV<br/>y perfil"))
    P3(("3<br/>Analizar<br/>puesto"))
    P4(("4<br/>Evaluar<br/>compatibilidad"))
    P5(("5<br/>Generar kit<br/>de entrevista"))
    P6(("6<br/>Gestionar<br/>suscripción"))
    P7(("7<br/>Consultar métricas<br/>(planificado)"))
    D1[("D1 Usuarios y planes")]
    D2[("D2 Perfil maestro")]
    D3[("D3 Documentos de CV")]
    D4[("D4 Puestos")]
    D5[("D5 Resultados de compatibilidad")]
    D6[("D6 Kits de entrevista")]
    D7[("D7 Caché de LinkedIn")]
    D8[("D8 Estado de tareas y límites")]

    P1 -->|"Datos de cuenta y plan"| D1
    P1 -->|"Orden de borrado de archivos"| D3
    P1 -->|"Orden de borrado de caché"| D7
    P1 -->|"Orden de invalidar claves"| D8
    P2 -->|"CV y estado de procesamiento"| D3
    P2 -->|"Perfil estructurado"| D2
    P3 -->|"Puesto estructurado con vector"| D4
    D1 -->|"Plan de la persona"| P4
    D2 -->|"Perfil y habilidades"| P4
    D4 -->|"Puesto estructurado"| P4
    P4 <-->|"Resultados de compatibilidad"| D5
    D1 -->|"Plan de la persona"| P5
    D2 -->|"Perfil y habilidades"| P5
    D4 -->|"Puesto estructurado"| P5
    P5 -->|"Kit de entrevista"| D6
    P5 <-->|"Perfiles de LinkedIn en caché"| D7
    P6 <-->|"Suscripción y plan"| D1
    P2 <-->|"Estado de la tarea"| D8
    P3 <-->|"Estado de la tarea"| D8
    P4 <-->|"Estado de la tarea"| D8
    P5 <-->|"Estado de la tarea"| D8
    P6 <-->|"Eventos ya procesados"| D8
    D1 -->|"Conteos agregados"| P7
    D4 -->|"Conteos agregados"| P7
    D5 -->|"Conteos agregados"| P7
    D6 -->|"Conteos agregados"| P7
```

### Procesos

| N.º | Proceso | Qué hace | Se apoya en |
|---|---|---|---|
| 1 | Gestionar cuenta y acceso | Registro e inicio de sesión (con Supabase Auth) y baja de cuenta: borra archivos, caché, claves, el usuario (los datos personales se eliminan en cascada) y la identidad | `DELETE /users/me` |
| 2 | Procesar CV y perfil | Recibe el PDF, extrae su texto, lo estructura con IA, genera vectores y arma el perfil maestro; permite confirmar o rechazar habilidades y completar experiencia, educación e idiomas | `POST /profiles/documents`, `/profiles/*` |
| 3 | Analizar puesto | Valida la URL o el texto, obtiene el contenido de la página, lo estructura con IA, genera vectores y guarda el puesto | `POST /jobs/analyze` |
| 4 | Evaluar compatibilidad | Calcula el Match Score, el reporte ATS y el Reality Gap, arma el resumen del panel y, en el plan premium, optimiza el CV con IA | `/matches`, `/ats`, `/dashboard`, `/profiles/reality-gap` |
| 5 | Generar kit de entrevista | Solo plan premium: arma el kit con IA a partir del perfil, el puesto y, si se indican, perfiles de LinkedIn | `/interview-kits` |
| 6 | Gestionar suscripción | Crea el checkout, recibe los eventos firmados de LemonSqueezy, actualiza el plan y avisa por email | `POST /billing/checkout`, `POST /webhooks/lemonsqueezy` |
| 7 | Consultar métricas agregadas | Devuelve conteos sin datos personales al administrador (**planificado**) | (no existe todavía) |

### Almacenes de datos

| N.º | Almacén | Contenido | Tablas o servicio |
|---|---|---|---|
| D1 | Usuarios y planes | Cuenta, plan free o premium y estado de la suscripción | `users` |
| D2 | Perfil maestro | Perfil, habilidades, experiencia, educación, idiomas y certificaciones | `master_profiles`, `skills`, `experiences`, `educations`, `languages`, `certifications`, `rejected_skills` |
| D3 | Documentos de CV | Archivos PDF y su estado de procesamiento | `uploaded_documents` y el bucket privado `cv-documents` de Storage |
| D4 | Puestos | Ofertas estructuradas con su vector | `job_descriptions` |
| D5 | Resultados de compatibilidad | Match Score y detalle por puesto | `job_matches` |
| D6 | Kits de entrevista | Kits generados y su valoración | `interview_kits` |
| D7 | Caché de LinkedIn | Perfiles ya leídos, para no repetir la lectura | `linkedin_scrape_cache` |
| D8 | Estado de tareas y límites | Estado de las tareas, límites de uso y eventos de pago ya procesados | Redis (Upstash) |

## 3. Correspondencia entre el nivel 0 y el nivel 1

Cada flujo del nivel 0 aparece en el nivel 1, entero o partido en sub-flujos (`F15` en `F15.2` a
`F15.5`, por ejemplo), y **no aparece ningún flujo externo nuevo**. Los únicos flujos que no
figuran en el nivel 0 son internos: los que van hacia y desde los almacenes y el que encadena
el proceso 3 con el 4.

| Flujo del nivel 0 | Nivel 1 | Proceso |
|---|---|---|
| F1, F7, F18 | F1, F7, F18 | 1 |
| F21, F22, F23 | F21, F22, F23 | 1 |
| F2, F3, F11 | F2, F3, F11 | 2 |
| F4 | F4 | 3 |
| F5 | F5.1 (match) y F5.2 (kit) | 4 y 5 |
| F8, F12, F13, F17 | F8, F12, F13, F17 | 4 |
| F9, F14 | F9, F14 | 5 |
| F6, F16, F28, F29, F30, F33 | F6, F16, F28, F29, F30, F33 | 6 |
| F19, F20 | F19, F20 | 7 |
| F15 | F15.2, F15.3, F15.4 y F15.5 | 2, 3, 4 y 5 |
| F24 | F24.2, F24.3, F24.4 y F24.5 | 2, 3, 4 y 5 |
| F25 | F25.2 y F25.3 | 2 y 3 |
| F26 | F26.2, F26.3, F26.4 y F26.5 | 2, 3, 4 y 5 |
| F27 | F27.2 y F27.3 | 2 y 3 |
| F31 | F31.3 y F31.5 | 3 y 5 |
| F32 | F32.3 y F32.5 | 3 y 5 |
| F34 | F34 (desde el conjunto de procesos) | 1 a 6 |

Comprobación de equilibrio: de los 33 flujos del nivel 0 (F1 a F34 sin F10), los 33 tienen su
correspondiente en el nivel 1, con el mismo origen y destino externos.
