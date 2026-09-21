# Herramientas de documentación y diagramas

Todo lo necesario para producir la documentación de la Etapa 1 desde el repositorio, con
formatos que se versionan y se revisan en un pull request. Decisión 16 de `DECISIONS.md`.

## 1. Qué hay

| Herramienta | Versión | Licencia | Para qué | Dónde queda |
|---|---|---|---|---|
| Markdown | — | — | Fuente de todos los documentos (`docs/`) | Repositorio |
| Mermaid | 12.0.0 | MIT | DFD, secuencia, ER y flujos dentro de los `.md` | `~/tools/mermaid/12.0.0/` |
| PlantUML | 1.2026.8 | LGPL-3.0 | UML formal: casos de uso y despliegue | `~/tools/plantuml.jar` |
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

# Con hojas apaisadas, útil para diagramas anchos como los DFD
python docs/tools/build_pdf.py docs/01-dfd.md --landscape
```

`docs/tools/ejemplo/` es un ejemplo de humo con los cuatro tipos de diagrama: sirve de
plantilla y para comprobar que la cadena funciona.

## 4. Qué lenguaje usar para cada diagrama

| Entregable | Herramienta | Motivo |
|---|---|---|
| DFD nivel 0, 1 y 2 | Mermaid `flowchart` | GitHub lo dibuja dentro del `.md` y el cambio se revisa en el PR |
| Diagramas de secuencia | Mermaid `sequenceDiagram` | Ídem |
| DER | Mermaid `erDiagram`, generado desde el esquema real | Ídem; se contrasta con las migraciones |
| Casos de uso UML | PlantUML | Notación UML completa; el de Mermaid es `usecase-beta` |
| Despliegue y arquitectura | PlantUML | UML de despliegue maduro |

Reglas:

- PlantUML lleva `!pragma layout smetana` (no requiere Graphviz). Se versionan el `.puml` y
  el `.svg` generado, porque GitHub **no** dibuja PlantUML.
- GitHub dibuja Mermaid de forma nativa
  ([doc](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)),
  pero su versión de Mermaid puede ir por detrás de la 12.0.0: antes de depender de una
  sintaxis nueva, probarla en un pull request borrador.
- No usar `usecase-beta` ni `architecture-beta` de Mermaid en entregables.
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
