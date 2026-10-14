"""Heurísticas para distinguir un texto con información de uno de relleno.

Son reglas deterministas y sin IA (no suman costo por llamada): no entienden el
significado, descartan lo que claramente no sirve para comparar un perfil con un
puesto: «asdf», «N/A», «profesional responsable», una bio que repite tres palabras.
Se usan para que el porcentaje del perfil no premie texto de relleno y para decidir
si un puesto menciona algo de lo que la persona sabe hacer.
"""

import re
import unicodedata
from urllib.parse import urlparse

# Conectores sin contenido, en español y en inglés.
STOPWORDS = frozenset(
    {
        "a", "al", "ante", "con", "como", "de", "del", "e", "el", "en", "entre",
        "es", "ha", "han", "hay", "la", "las", "le", "lo", "los", "me", "mi",
        "mis", "muy", "o", "para", "por", "que", "se", "sin", "sobre", "soy",
        "su", "sus", "un", "una", "uno", "y", "ya",
        "an", "and", "are", "as", "at", "by", "for", "from", "i", "in", "is",
        "my", "of", "on", "or", "the", "to", "with",
    }
)  # fmt: skip

# Palabras que no dicen qué hace la persona: adjetivos genéricos, búsqueda de
# trabajo y textos de prueba. Una bio hecha solo de esto no sirve para comparar.
FILLER_WORDS = frozenset(
    {
        "profesional", "trabajador", "trabajadora", "persona", "empleado",
        "empleada", "responsable", "proactivo", "proactiva", "dinamico",
        "dinamica", "comprometido", "comprometida", "motivado", "motivada",
        "apasionado", "apasionada", "buscando", "busco", "trabajo", "empleo",
        "laburo", "oportunidad", "oportunidades", "crecer", "crecimiento",
        "aprender", "ganas", "hola", "chau", "test", "testing", "prueba",
        "probando", "nada", "ninguno", "ninguna", "algo", "cosas", "cosa",
        "varios", "varias", "etc", "lorem", "ipsum", "dolor", "amet",
        "consectetur", "asd", "asdf", "qwe", "qwerty", "zxc", "xxx", "hello",
        "world", "sample", "example", "ejemplo", "none", "null", "undefined",
        "unknown", "default", "nn",
    }
)  # fmt: skip

# Valores de relleno que se escriben enteros: se comparan contra el texto completo.
PLACEHOLDERS = frozenset(
    {
        "n/a", "na", "n.a", "s/d", "sd", "ninguno", "ninguna", "ningun",
        "no aplica", "no tengo", "sin dato", "sin datos", "sin experiencia",
        "none", "null", "test", "prueba", "xxx", "asdf", "asd", "todo", "otro",
        "otros", "varios", "varias",
    }
)  # fmt: skip

_KEYBOARD_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm", "qazwsxedc")
_WORD = re.compile(r"[a-z]+")
_REPEATED_CHAR = re.compile(r"(.)\1{3,}")
_REPEATED_CHUNK = re.compile(r"(.{2,3})\1{2,}")
_VOWELS = re.compile(r"[aeiouy]")


def fold(text: str) -> str:
    """Minúsculas y sin acentos: «Ingeniería» y «ingenieria» son la misma palabra."""
    decomposed = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def words(text: str | None) -> list[str]:
    """Las palabras de letras del texto, sin acentos y en minúscula."""
    return _WORD.findall(fold(text or ""))


def is_gibberish_word(word: str) -> bool:
    """«aaaa», «jajaja», «asdfg» o una palabra larga sin una sola vocal."""
    if _REPEATED_CHAR.search(word) or _REPEATED_CHUNK.fullmatch(word):
        return True
    if len(word) >= 4 and any(
        word in row or word[::-1] in row for row in _KEYBOARD_ROWS
    ):
        return True
    # Con 6 letras o más ninguna palabra real carece de vocales; las siglas técnicas
    # sin vocales (sql, html, https, rdbms) tienen cinco o menos.
    return len(word) >= 6 and _VOWELS.search(word) is None


def content_words(text: str | None) -> list[str]:
    """Las palabras que aportan información: ni conectores, ni relleno, ni ruido."""
    return [
        word
        for word in words(text)
        if len(word) >= 2
        and word not in STOPWORDS
        and word not in FILLER_WORDS
        and not is_gibberish_word(word)
    ]


def is_meaningful_name(text: str | None) -> bool:
    """Un nombre corto (empresa, institución, skill, idioma) que no es relleno.

    No exige largo mínimo ni palabras «de contenido»: «C», «R», «Go» y «3M» son
    nombres válidos.
    """
    if not text or not text.strip():
        return False
    if fold(text) in PLACEHOLDERS:
        return False
    found = words(text)
    if not found:
        return False
    return not all(
        word in FILLER_WORDS or is_gibberish_word(word) or word in STOPWORDS
        for word in found
    )


def is_meaningful_text(
    text: str | None,
    min_words: int = 1,
    min_diversity: float = 0.5,
) -> bool:
    """Un texto libre (cargo, headline, bio) con al menos `min_words` palabras útiles.

    Descarta el texto en el que más de un tercio de las palabras es ruido y el que
    repite lo mismo: «chef chef chef» no es una bio. `min_diversity` es la fracción
    mínima de palabras distintas entre las útiles.
    """
    if not text or not text.strip() or fold(text) in PLACEHOLDERS:
        return False
    found = words(text)
    if not found:
        return False
    if sum(is_gibberish_word(word) for word in found) / len(found) > 0.34:
        return False
    useful = content_words(text)
    if len(useful) < min_words:
        return False
    return len(set(useful)) / len(useful) >= min_diversity


def is_linkedin_profile_url(value: str | None) -> bool:
    """Una URL de perfil de LinkedIn: `linkedin.com/in/<usuario>` con usuario real."""
    if not value or not value.strip():
        return False
    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"}:
        return False
    if host != "linkedin.com" and not host.endswith(".linkedin.com"):
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 2 and parts[0].lower() == "in" and len(parts[1]) >= 3
