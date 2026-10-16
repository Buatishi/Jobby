"""Cuándo dos nombres de skill son la misma skill.

«React» y «React.js», «API REST» y «REST APIs», «Integración de APIs» y «API
Integrations» nombran lo mismo; «Java» y «JavaScript», «React» y «React Native»,
«SQL» y «PostgreSQL» no. Comparar el texto tal cual fallaba en los primeros y no hay
forma de acertar los segundos con una distancia de edición, que igualaría «Java» con
«Javas» y también con «Lava».

Por eso la regla es explícita y conservadora. Dos nombres coinciden solo si, después de
llevarlos a una forma común, quedan iguales:

1. Se quitan acentos y mayúsculas y se ignora la puntuación (salvo `.`, `+` y `#`, que
   son parte de «Node.js», «C++» y «C#»).
2. Un producto escrito de varias maneras se lleva a una sola palabra («Power BI»,
   «Microsoft Power BI» y «PowerBI» son `powerbi`) y «React.js», «ReactJS» y «react js»
   son `react`. Solo los frameworks de la lista: «AngularJS» no es «Angular».
3. Las palabras genéricas se llevan a una forma inglesa única, en singular y sin
   traducción pendiente («integración», «integraciones» e «integrations» son
   `integration`). Las palabras que no están en la tabla se dejan como están: un nombre
   desconocido solo coincide con el mismo nombre.
4. Se descartan los conectores («de», «y», «of») y las palabras que no cambian de qué
   skill se habla («skills», «habilidades», «metodologías»).
5. El orden no importa: «API REST» y «REST API» son lo mismo.

Cada alias de la tabla tiene que ser la misma skill, no una parecida o relacionada.
Ante la duda no se agrega: `tests/unit/test_skill_names.py` fija los pares que no deben
igualarse. Quien dude de una equivalencia nueva debe empezar por ese archivo.
"""

import re
import unicodedata
from typing import Any

# Productos que se escriben partidos o con el nombre del fabricante delante: pasan a una
# sola palabra antes de separar en palabras.
_BRAND_PHRASES: dict[str, str] = {
    "power bi": "powerbi",
    "microsoft power bi": "powerbi",
    "microsoft excel": "excel",
    "ms excel": "excel",
    "mongo db": "mongodb",
    "postgre sql": "postgresql",
    "my sql": "mysql",
    "java script": "javascript",
    "type script": "typescript",
    "git hub": "github",
    "git lab": "gitlab",
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "google cloud": "gcp",
    "microsoft azure": "azure",
    "ruby on rails": "rails",
    "e commerce": "ecommerce",
    "machine learning": "machinelearning",
    "aprendizaje automatico": "machinelearning",
    "deep learning": "deeplearning",
    "aprendizaje profundo": "deeplearning",
}

# Frameworks que se escriben con o sin «.js»: «React», «React.js», «ReactJS».
# Angular queda afuera a propósito: AngularJS (1.x) y Angular (2+) son distintos.
_JS_FRAMEWORKS = re.compile(
    r"(?<![a-z0-9])(react|vue|node|next|express|nest|nuxt|d3)[ .]?js(?![a-z0-9])"
)

# (forma común, variantes). La forma común puede ser varias palabras: el nombre se parte
# en palabras antes de comparar.
_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # --- tecnologías: solo variantes de escritura del mismo producto ---
    ("javascript", ("js",)),
    ("typescript", ("ts",)),
    ("go", ("golang",)),
    ("postgresql", ("postgres",)),
    ("mongodb", ("mongo",)),
    ("kubernetes", ("k8s",)),
    ("ci cd", ("cicd",)),
    ("rest", ("restful",)),
    ("artificial intelligence", ("ai", "ia")),
    ("object oriented programming", ("oop", "poo")),
    ("front end", ("frontend",)),
    ("back end", ("backend",)),
    ("full stack", ("fullstack",)),
    ("team work", ("teamwork",)),
    ("base data", ("database", "databases")),
    # --- palabras genéricas: plural y traducción al inglés ---
    ("api", ("apis",)),
    ("integration", ("integracion", "integraciones", "integrations")),
    ("system", ("sistema", "sistemas", "systems")),
    (
        "application",
        ("aplicacion", "aplicaciones", "applications", "app", "apps"),
    ),
    ("mobile", ("movil", "moviles")),
    ("development", ("desarrollo", "desarrollos")),
    (
        "developer",
        (
            "developers",
            "desarrollador",
            "desarrolladora",
            "desarrolladores",
            "desarrolladoras",
        ),
    ),
    ("engineer", ("engineers", "ingeniero", "ingeniera", "ingenieros")),
    ("engineering", ("ingenieria",)),
    ("management", ("gestion", "gestiones")),
    ("manager", ("managers", "gerente", "gerentes")),
    ("project", ("proyecto", "proyectos", "projects")),
    ("team", ("equipo", "equipos", "teams")),
    ("work", ("trabajo",)),
    ("data", ("datos", "dato")),
    ("base", ("bases",)),
    ("science", ("ciencia", "ciencias")),
    ("analysis", ("analisis", "analyses")),
    ("analytics", ("analitica", "analiticas")),
    ("analyst", ("analista", "analistas", "analysts")),
    ("automation", ("automatizacion", "automatizaciones")),
    ("testing", ("test", "tests", "prueba", "pruebas", "testeo")),
    ("unit", ("unitaria", "unitarias", "unitario", "unitarios")),
    ("security", ("seguridad",)),
    ("cybersecurity", ("ciberseguridad",)),
    ("cloud", ("nube",)),
    ("design", ("diseno", "disenos")),
    ("service", ("servicio", "servicios", "services")),
    ("architecture", ("arquitectura",)),
    ("microservice", ("microservicio", "microservicios", "microservices")),
    ("container", ("contenedor", "contenedores", "containers")),
    ("pipeline", ("pipelines",)),
    ("framework", ("frameworks",)),
    ("script", ("scripts", "scripting")),
    ("version", ("versiones", "versionado", "versioning")),
    ("documentation", ("documentacion",)),
    ("optimization", ("optimizacion",)),
    ("scalability", ("escalabilidad",)),
    ("visualization", ("visualizacion",)),
    ("report", ("reporte", "reportes", "reports")),
    ("dashboard", ("tablero", "tableros", "dashboards")),
    ("programming", ("programacion",)),
    ("object", ("objeto", "objetos", "objects")),
    ("oriented", ("orientada", "orientado", "orientadas", "orientados")),
    ("agile", ("agil", "agiles")),
    ("support", ("soporte",)),
    ("technical", ("tecnico", "tecnica", "tecnicos")),
    ("sales", ("ventas",)),
    ("accounting", ("contabilidad",)),
    ("finance", ("finanzas",)),
    ("resource", ("recurso", "recursos", "resources")),
    ("human", ("humano", "humanos")),
    ("intelligence", ("inteligencia",)),
    ("learning", ("aprendizaje",)),
    # --- habilidades blandas ---
    ("leadership", ("liderazgo",)),
    ("communication", ("comunicacion", "comunicaciones", "communications")),
    ("creativity", ("creatividad",)),
    ("adaptability", ("adaptabilidad",)),
    ("negotiation", ("negociacion", "negociaciones")),
    ("solving", ("resolucion",)),
    ("problem", ("problema", "problemas", "problems")),
    ("thinking", ("pensamiento",)),
    ("critical", ("critico", "critica")),
    ("time", ("tiempo",)),
    ("decision", ("decisiones", "decisions")),
    ("making", ("toma",)),
    ("attention", ("atencion",)),
    ("detail", ("detalle", "detalles", "details")),
)

# Conectores que no dicen de qué skill se habla.
_CONNECTORS = frozenset(
    {
        "a", "al", "an", "and", "at", "con", "de", "del", "e", "el", "en", "for",
        "in", "la", "las", "lo", "los", "o", "of", "on", "or", "para", "por", "the",
        "to", "u", "un", "una", "with", "y",
    }
)  # fmt: skip

# Palabras que acompañan al nombre sin cambiar de qué skill se habla: «Communication
# Skills», «Habilidades de comunicación» y «Comunicación» son lo mismo.
_FILLER = frozenset(
    {
        "skill", "skills", "habilidad", "habilidades", "competencia", "competencias",
        "conocimiento", "conocimientos", "knowledge", "methodology", "methodologies",
        "metodologia", "metodologias", "tool", "tools", "herramienta", "herramientas",
    }
)  # fmt: skip


def _build_token_map(
    groups: tuple[tuple[str, tuple[str, ...]], ...],
) -> dict[str, str]:
    """Variante → forma común. Falla al importar si la tabla se contradice."""
    mapping: dict[str, str] = {}
    for common, variants in groups:
        for variant in variants:
            if variant != _fold(variant) or " " in variant:
                raise ValueError(
                    f"La variante «{variant}» debe ser una palabra normalizada."
                )
            if variant in mapping:
                raise ValueError(f"La variante «{variant}» está en dos grupos.")
            mapping[variant] = common
    for common, _variants in groups:
        for word in common.split():
            if word in mapping:
                raise ValueError(
                    f"«{word}» es la forma común de un grupo y variante de otro."
                )
    return mapping


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).lower()


_TOKEN_MAP = _build_token_map(_GROUPS)
_BRAND_PATTERN = re.compile(
    r"(?<![a-z0-9])("
    + "|".join(re.escape(p) for p in sorted(_BRAND_PHRASES, key=len, reverse=True))
    + r")(?![a-z0-9])"
)
_NOT_PART_OF_A_NAME = re.compile(r"[^a-z0-9.+# ]+")
_WORD = re.compile(r"\.?[a-z0-9][a-z0-9.+#]*")


def canonical_skill_key(name: Any) -> str:
    """Forma común del nombre de una skill; vacía si no queda nada con contenido.

    Dos nombres son la misma skill si tienen la misma forma común.
    """
    if not isinstance(name, str):
        return ""

    text = _NOT_PART_OF_A_NAME.sub(" ", _fold(name))
    text = _BRAND_PATTERN.sub(lambda match: _BRAND_PHRASES[match.group(1)], text)
    text = _JS_FRAMEWORKS.sub(r"\1", text)

    words: set[str] = set()
    for raw in _WORD.findall(text):
        for word in _TOKEN_MAP.get(raw.rstrip("."), raw.rstrip(".")).split():
            if word and word not in _CONNECTORS and word not in _FILLER:
                words.add(word)
    return " ".join(sorted(words))


def same_skill(left: Any, right: Any) -> bool:
    """Verdadero si los dos nombres son la misma skill (nunca con un nombre vacío)."""
    key = canonical_skill_key(left)
    return bool(key) and key == canonical_skill_key(right)
