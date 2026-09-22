# Herramientas de documentación y diagramas

Todo lo necesario para producir la documentación de la Etapa 1 desde el repositorio, con
formatos que se versionan y se revisan en un pull request. Decisiones 16 y 18 de `DECISIONS.md`.

## 1. Qué hay

| Herramienta | Versión | Licencia | Para qué | Dónde queda |
|---|---|---|---|---|
| Markdown | — | — | Fuente de todos los documentos (`docs/`) | Repositorio |
| Mermaid | 12.0.0 | MIT | Borradores y documentos internos (no entregables) | `~/tools/mermaid/12.0.0/` |
| PlantUML | 1.2026.8 | LGPL-3.0 | Todos los diagramas entregables: DFD, casos de uso, DER, arquitectura y despliegue | `~/tools/plantuml.jar` |
| Temurin JRE | 21 | GPL-2.0 con excepción Classpath | Ejecuta PlantUML | `~/tools/jre21/` |
| Microsoft Edge | el instalado | — | Genera el PDF (modo headless) | Sistema |

Las versiones y los hashes verificados están en `tools.lock.json`. Las herramientas se
instalan fuera del repositorio, en `~/tools` (se cambia con la variable `JOBBY_TOOLS_HOME`).

## 2. Puesta en marcha (una sola vez)

```bash
python docs/tools/setup_tools.py --check            # estado de cada herramienta
python docs/tools/setup_tools.py --install-mermaid  # solo si falta Mermaid
```

`--install-mermaid` descarga el paquete del registro oficial de npm y **no instala nada** si
el hash SHA-512 del paquete o el SHA-256 del archivo extraído no coinciden con el lock.
Requisitos de Python: `pip install markdown` (para los PDF).

## 3. Uso diario

```bash
# 1) Diagramas PlantUML (.puml -> .svg junto al archivo); sin rutas procesa todo docs/
python docs/tools/render_diagrams.py

# 2) PDF de un documento (por defecto en docs/pdf/<nombre>.pdf)
python docs/tools/build_pdf.py docs/tools/ejemplo/ejemplo.md

# Con hojas apaisadas, útil para tablas o diagramas anchos
python docs/tools/build_pdf.py docs/tools/ejemplo/ejemplo.md --landscape

# Hoja A3, para que los diagramas grandes se impriman con el texto legible
python docs/tools/build_pdf.py docs/03-dfd-nivel-2.md --paper A3

# Un único diagrama .svg en su propia hoja, con título
python docs/tools/build_pdf.py docs/diagramas/modelo-entidad-relacion.svg --paper A3 --landscape --title "Modelo de datos"
```

Los PDF de la Etapa 1 (`docs/pdf/`) se generan así; las láminas A3 son para imprimir cada
diagrama con el texto legible (letra mínima de 5,8 pt):

```bash
python docs/tools/build_pdf.py docs/00-propuesta.md
python docs/tools/build_pdf.py docs/01-dfd.md
python docs/tools/build_pdf.py docs/02-casos-de-uso.md
python docs/tools/build_pdf.py docs/03-dfd-nivel-2.md
python docs/tools/build_pdf.py docs/04-modelo-de-datos.md
python docs/tools/build_pdf.py docs/06-arquitectura-y-despliegue.md
python docs/tools/build_pdf.py docs/07-decisiones-tecnicas.md

L=docs/pdf/laminas
python docs/tools/build_pdf.py docs/diagramas/dfd-nivel-0.svg --paper A3 -o $L/dfd-nivel-0.pdf --title "4.1 · DFD nivel 0: diagrama de contexto"
python docs/tools/build_pdf.py docs/diagramas/dfd-nivel-1-vista-a.svg --paper A3 -o $L/dfd-nivel-1-vista-a.pdf --title "4.2 · DFD nivel 1, vista 1A: procesos y personas"
python docs/tools/build_pdf.py docs/diagramas/dfd-nivel-1-vista-b.svg --paper A3 -o $L/dfd-nivel-1-vista-b.pdf --title "4.2 · DFD nivel 1, vista 1B: procesos y sistemas externos"
python docs/tools/build_pdf.py docs/diagramas/dfd-nivel-1-vista-c.svg --paper A3 --landscape -o $L/dfd-nivel-1-vista-c.pdf --title "4.2 · DFD nivel 1, vista 1C: procesos y almacenes de datos"
python docs/tools/build_pdf.py docs/diagramas/dfd-nivel-2-proceso-2.svg --paper A3 -o $L/dfd-nivel-2-proceso-2.pdf --title "4.3 · DFD nivel 2 del proceso 2: Procesar CV y perfil"
python docs/tools/build_pdf.py docs/diagramas/dfd-nivel-2-proceso-4.svg --paper A3 --landscape -o $L/dfd-nivel-2-proceso-4.pdf --title "4.3 · DFD nivel 2 del proceso 4: Evaluar compatibilidad"
python docs/tools/build_pdf.py docs/diagramas/casos-de-uso.svg --paper A3 -o $L/casos-de-uso.pdf --title "4.4 · Diagrama de casos de uso"
python docs/tools/build_pdf.py docs/diagramas/modelo-entidad-relacion.svg --paper A3 --landscape -o $L/modelo-entidad-relacion.pdf --title "4.5 · Modelo de datos (DER)"
python docs/tools/build_pdf.py docs/diagramas/arquitectura.svg --paper A3 --landscape -o $L/arquitectura.pdf --title "4.6 · Arquitectura: componentes y comunicaciones"
python docs/tools/build_pdf.py docs/diagramas/despliegue-y-secretos.svg --paper A3 --landscape -o $L/despliegue-y-secretos.pdf --title "4.6 · Despliegue en producción y secretos"
python docs/tools/build_pdf.py docs/diagramas/recorrido-del-codigo.svg --paper A3 --landscape -o $L/recorrido-del-codigo.pdf --title "4.6 · Recorrido del código hasta producción"
```

`docs/tools/ejemplo/` es un ejemplo de humo con los cuatro tipos de diagrama: sirve de
plantilla y para comprobar que la cadena funciona.

## 4. Qué lenguaje usar para cada diagrama

| Diagrama | Herramienta | Motivo |
|---|---|---|
| DFD nivel 0, 1 y 2 | PlantUML | Salida vectorial que se imprime nítida y acomodo controlable (Decisión 18) |
| Casos de uso UML | PlantUML | Notación UML completa; el de Mermaid es `usecase-beta` |
| DER | PlantUML, contrastado con el esquema real | Tipos, claves y patas de gallo, legible en A3 |
| Arquitectura, despliegue y recorrido del código | PlantUML | UML de despliegue maduro |
| Borradores y documentos internos | Mermaid (opcional) | GitHub lo dibuja dentro del `.md`, pero al pasar a PDF Edge lo convierte en imagen: no se usa en entregables |

Reglas:

- PlantUML lleva `!pragma layout smetana` (no requiere Graphviz). Se versionan el `.puml` y
  el `.svg` generado, porque GitHub **no** dibuja PlantUML.
- GitHub dibuja Mermaid de forma nativa
  ([doc](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)),
  pero su versión de Mermaid puede ir por detrás de la 12.0.0: antes de depender de una
  sintaxis nueva, probarla en un pull request borrador.
- Los entregables no usan Mermaid (Decisión 18); después de editar un `.puml`, regenerar su `.svg`
  y versionar ambos.
- Ningún diagrama incluye datos personales ni contenido de CV.

## 5. Pruebas

```bash
python -m unittest discover -s docs/tools -p "test_*.py" -v
```

## 6. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Falta Java o plantuml.jar` | Ejecutar `setup_tools.py --check`; definir `JAVA` o `PLANTUML_JAR` si están en otra ruta |
| El PDF sale sin diagramas Mermaid | Falta Mermaid (`--install-mermaid`) o hay un error de sintaxis en el bloque |
| `PlantUML generó una imagen de error de sintaxis` | Abrir el `.svg` para ver la línea del error |
| Edge no genera el PDF | Cerrar Edge o definir `EDGE_PATH`; el script usa un perfil temporal |

## 7. Fuentes

- Mermaid: <https://www.npmjs.com/package/mermaid/v/12.0.0> (publicado con procedencia).
- PlantUML: <https://github.com/plantuml/plantuml/releases/tag/v1.2026.8> (el hash del `.jar`
  coincide con el digest oficial del release).
