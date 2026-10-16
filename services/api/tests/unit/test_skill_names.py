"""Cuándo dos nombres de skill son la misma skill.

El PDF de LinkedIn nombra «React.js» y la persona tiene «React»; LinkedIn dice «API
Integrations» y el perfil «Integración de APIs». Comparar el texto literal no las
marcaba. Pero igualar de más es peor que no igualar: «Java» no es «JavaScript» ni
«React» es «React Native». Estas pruebas fijan las dos cosas: lo que sí coincide y,
sobre todo, lo parecido que no.
"""

import pytest

from app.services.cv_parser import skills_named_in_linkedin
from app.services.cv_parser.ai_structurer import CVStructuredData, ParsedSkill
from app.services.skill_names import (
    _BRAND_PHRASES,
    _FILLER,
    _GROUPS,
    _TOKEN_MAP,
    _build_token_map,
    canonical_skill_key,
    same_skill,
)

# --- lo que es la misma skill ---------------------------------------------------

SAME = [
    # El mismo producto escrito de otra manera.
    ("React", "React.js"),
    ("React", "ReactJS"),
    ("React", "react js"),
    ("React.js", "React-JS"),
    ("Node", "Node.js"),
    ("NodeJS", "node.js"),
    ("Vue", "Vue.js"),
    ("Next.js", "NextJS"),
    ("Express", "Express.js"),
    ("JavaScript", "JS"),
    ("JavaScript", "Java Script"),
    ("TypeScript", "TS"),
    ("Go", "Golang"),
    ("PostgreSQL", "Postgres"),
    ("PostgreSQL", "Postgre SQL"),
    ("MongoDB", "Mongo"),
    ("MongoDB", "Mongo DB"),
    ("MySQL", "My SQL"),
    ("Power BI", "PowerBI"),
    ("Power BI", "Microsoft Power BI"),
    ("Excel", "Microsoft Excel"),
    ("Excel", "MS Excel"),
    ("AWS", "Amazon Web Services"),
    ("GCP", "Google Cloud"),
    ("GCP", "Google Cloud Platform"),
    ("Azure", "Microsoft Azure"),
    ("Kubernetes", "K8s"),
    ("CI/CD", "CI CD"),
    ("CI/CD", "CICD"),
    ("GitHub", "Git Hub"),
    ("Rails", "Ruby on Rails"),
    ("E-commerce", "Ecommerce"),
    # Singular, plural y orden.
    ("API", "APIs"),
    ("REST API", "REST APIs"),
    ("REST API", "API REST"),
    ("REST APIs", "RESTful API"),
    ("Unit Test", "Unit Tests"),
    ("Dashboard", "Dashboards"),
    ("Microservice", "Microservices"),
    # Traducción de palabras genéricas.
    ("API Integrations", "Integración de APIs"),
    ("API Integration", "Integracion de API"),
    ("Systems Integration", "Integración de sistemas"),
    ("Automation", "Automatización"),
    ("Full Stack Development", "Desarrollo Full Stack"),
    ("Fullstack Developer", "Desarrollador Full Stack"),
    ("Frontend", "Front-end"),
    ("Frontend Developer", "Desarrollador Front End"),
    ("Backend", "Back End"),
    ("Mobile App Development", "Desarrollo de aplicaciones móviles"),
    ("Database", "Bases de datos"),
    ("Database Design", "Diseño de bases de datos"),
    ("Data Analysis", "Análisis de datos"),
    ("Data Science", "Ciencia de datos"),
    ("Data Visualization", "Visualización de datos"),
    ("Unit Testing", "Pruebas unitarias"),
    ("Software Testing", "Software Testing"),
    ("Cloud Computing", "Cloud Computing"),
    ("Cybersecurity", "Ciberseguridad"),
    ("Security", "Seguridad"),
    ("Version Control", "Control de versiones"),
    ("Web Services", "Servicios web"),
    ("Technical Support", "Soporte técnico"),
    ("Human Resources", "Recursos Humanos"),
    ("Object Oriented Programming", "Programación orientada a objetos"),
    ("Object-Oriented Programming", "Programación Orientada a Objetos"),
    ("OOP", "POO"),
    ("OOP", "Object Oriented Programming"),
    ("Agile", "Metodologías ágiles"),
    ("Agile Methodologies", "Agile"),
    ("Artificial Intelligence", "Inteligencia Artificial"),
    ("Artificial Intelligence", "IA"),
    ("AI", "IA"),
    ("Machine Learning", "Aprendizaje automático"),
    ("Deep Learning", "Aprendizaje profundo"),
    # Habilidades blandas.
    ("Teamwork", "Trabajo en equipo"),
    ("Team Work", "Teamwork"),
    ("Leadership", "Liderazgo"),
    ("Communication", "Comunicación"),
    ("Communication Skills", "Comunicación"),
    ("Habilidades de comunicación", "Communication"),
    ("Project Management", "Gestión de proyectos"),
    ("Project Manager", "Gerente de proyectos"),
    ("Time Management", "Gestión del tiempo"),
    ("Problem Solving", "Resolución de problemas"),
    ("Critical Thinking", "Pensamiento crítico"),
    ("Decision Making", "Toma de decisiones"),
    ("Attention to Detail", "Atención al detalle"),
    ("Negotiation", "Negociación"),
    ("Creativity", "Creatividad"),
    ("Adaptability", "Adaptabilidad"),
    # Nombres que la tabla no conoce: solo coinciden con ellos mismos.
    ("Salesforce", "salesforce"),
    ("Salesforce", "  SALESFORCE  "),
    ("Zapier", "Zapier"),
    ("n8n", "N8N"),
]


@pytest.mark.parametrize(("left", "right"), SAME)
def test_these_names_are_the_same_skill(left: str, right: str) -> None:
    assert same_skill(left, right), (
        canonical_skill_key(left),
        canonical_skill_key(right),
    )
    # Y en el otro sentido: la comparación no depende de quién es quién.
    assert same_skill(right, left)


# --- lo parecido que NO es la misma skill ---------------------------------------

DIFFERENT = [
    # Nombres que se parecen pero son tecnologías distintas.
    ("Java", "JavaScript"),
    ("JavaScript", "TypeScript"),
    ("C", "C++"),
    ("C++", "C#"),
    ("C", "Rust"),
    ("R", "Ruby"),
    ("Go", "Google"),
    ("React", "React Native"),
    ("React", "Preact"),
    ("Angular", "AngularJS"),
    ("Angular", "React"),
    ("Node.js", "Node-RED"),
    ("Node.js", "Next.js"),
    ("Express", "Expression"),
    ("Vue", "Vite"),
    ("SQL", "PostgreSQL"),
    ("SQL", "MySQL"),
    ("MySQL", "PostgreSQL"),
    ("SQL", "NoSQL"),
    ("MongoDB", "PostgreSQL"),
    ("Git", "GitHub"),
    ("GitHub", "GitLab"),
    ("Docker", "Kubernetes"),
    ("AWS", "Azure"),
    ("AWS", "GCP"),
    ("REST API", "GraphQL"),
    ("REST API", "SOAP"),
    ("Python", "Pandas"),
    ("Python", "Python 3"),
    ("Excel", "Power BI"),
    ("Power BI", "Power Automate"),
    ("Salesforce", "Salesforce Apex"),
    ("Linux", "Unix"),
    ("HTML", "CSS"),
    (".NET", "NET"),
    (".NET", "ASP.NET"),
    # Conceptos parecidos pero distintos.
    ("Project Management", "Product Management"),
    ("Project Management", "Project"),
    ("Team Management", "Teamwork"),
    ("Leadership", "Team Leadership"),
    ("Data Science", "Data Analysis"),
    ("Data Analysis", "Data Analytics"),
    ("Machine Learning", "Deep Learning"),
    ("Machine Learning", "Learning"),
    ("Artificial Intelligence", "Machine Learning"),
    ("Testing", "Test Automation"),
    ("Unit Testing", "Integration Testing"),
    ("Security", "Cybersecurity"),
    ("Frontend", "Backend"),
    ("Frontend Developer", "Full Stack Developer"),
    ("Mobile Development", "Web Development"),
    ("Data", "Database"),
    ("API Integration", "API"),
    ("API Integration", "System Integration"),
    ("Agile", "Scrum"),
    ("Communication", "Negotiation"),
    ("Problem Solving", "Problem"),
    ("Critical Thinking", "Thinking"),
    ("Developer", "Engineer"),
    ("Manager", "Management"),
    ("Technical Support", "Support"),
    ("Human Resources", "Resources"),
    ("Version Control", "Version"),
    ("Object Oriented Programming", "Programming"),
]


@pytest.mark.parametrize(("left", "right"), DIFFERENT)
def test_these_names_are_not_the_same_skill(left: str, right: str) -> None:
    assert not same_skill(left, right), canonical_skill_key(left)
    assert not same_skill(right, left)


# --- la forma común no depende de cómo se escribe --------------------------------


@pytest.mark.parametrize(
    "variant",
    ["react", "REACT", "  React  ", "React.", "Réact", "react.js", "React JS"],
)
def test_case_accents_spaces_and_a_trailing_dot_do_not_matter(variant: str) -> None:
    assert canonical_skill_key(variant) == canonical_skill_key("React")


def test_accents_and_punctuation_do_not_matter_in_a_spanish_name() -> None:
    assert (
        canonical_skill_key("Gestión de proyectos")
        == canonical_skill_key("GESTION DE PROYECTOS!")
        == canonical_skill_key("gestion-de-proyectos")
    )


def test_the_key_is_stable_for_every_name_in_the_tables() -> None:
    # Si no, comparar dos veces el mismo nombre podría dar distinto.
    names = [name for pair in SAME + DIFFERENT for name in pair]
    for name in names:
        assert canonical_skill_key(name) == canonical_skill_key(name)
    for common, variants in _GROUPS:
        for variant in variants:
            assert canonical_skill_key(variant) == canonical_skill_key(common)


@pytest.mark.parametrize("name", [None, "", "   ", "...", 42, ["React"], {}])
def test_a_name_with_no_content_has_no_key_and_matches_nothing(name: object) -> None:
    assert canonical_skill_key(name) == ""
    assert not same_skill(name, name)
    assert not same_skill(name, "React")
    assert not same_skill("React", name)


def test_a_name_made_only_of_connectors_and_filler_has_no_key() -> None:
    assert canonical_skill_key("Skills de la") == ""
    assert not same_skill("Habilidades", "Skills")


def test_c_plus_plus_and_c_sharp_keep_their_symbols() -> None:
    assert canonical_skill_key("C++") == "c++"
    assert canonical_skill_key("C#") == "c#"
    assert canonical_skill_key(".NET") == ".net"


# --- las tablas no se contradicen ----------------------------------------------


def test_no_variant_is_in_two_groups() -> None:
    variants = [variant for _common, group in _GROUPS for variant in group]
    assert len(variants) == len(set(variants))


def test_a_variant_cannot_also_be_the_common_form_of_another_group() -> None:
    commons = {word for common, _group in _GROUPS for word in common.split()}
    assert not commons & set(_TOKEN_MAP)


def test_every_variant_is_one_normalized_word() -> None:
    for variant in _TOKEN_MAP:
        assert variant == variant.lower()
        assert " " not in variant
        assert variant.isascii()


def test_a_contradictory_table_fails_when_it_is_built() -> None:
    with pytest.raises(ValueError, match="dos grupos"):
        _build_token_map((("a", ("x",)), ("b", ("x",))))
    with pytest.raises(ValueError, match="forma común"):
        _build_token_map((("a", ("x",)), ("x", ("y",))))
    with pytest.raises(ValueError, match="normalizada"):
        _build_token_map((("a", ("Éx",)),))


def test_brand_phrases_are_normalized_and_do_not_collide_with_filler() -> None:
    for phrase, brand in _BRAND_PHRASES.items():
        assert phrase == phrase.lower() and phrase.isascii()
        assert " " not in brand
        assert brand not in _FILLER


# --- el marcado de LinkedIn ----------------------------------------------------


def _parsed(*names: str) -> CVStructuredData:
    return CVStructuredData(
        skills=[
            ParsedSkill(name=name, category="other", level="intermediate")
            for name in names
        ]
    )


def _saved(skill_id: str, name: str, **overrides: object) -> dict[str, object]:
    return {"id": skill_id, "name": name, "category": "technical", **overrides}


def test_linkedin_marks_the_skills_the_person_has_under_another_name() -> None:
    # El caso medido en producción: LinkedIn nombra «React.js» y «API Integrations».
    saved = [
        _saved("s-react", "React"),
        _saved("s-apis", "Integración de APIs"),
        _saved("s-rest", "REST APIs"),
        _saved("s-sql", "SQL"),
    ]

    ids = skills_named_in_linkedin(
        _parsed("React.js", "API Integrations", "REST API"), saved
    )

    assert ids == ["s-react", "s-apis", "s-rest"]


def test_linkedin_does_not_mark_a_related_but_different_skill() -> None:
    saved = [
        _saved("s-js", "JavaScript"),
        _saved("s-native", "React Native"),
        _saved("s-sql", "SQL"),
        _saved("s-git", "Git"),
    ]

    ids = skills_named_in_linkedin(
        _parsed("Java", "React", "PostgreSQL", "GitHub"), saved
    )

    assert ids == []


def test_linkedin_ignores_a_name_with_no_content() -> None:
    saved = [_saved("s-1", "Python"), _saved("s-2", "...")]

    assert skills_named_in_linkedin(_parsed("...", "Skills"), saved) == []
