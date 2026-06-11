LANGUAGE_NAMES: dict[str, str] = {
    "de": "Deutsch",
    "en": "Englisch",
    "fr": "Französisch",
    "es": "Spanisch",
    "it": "Italienisch",
    "nl": "Niederländisch",
    "pl": "Polnisch",
    "pt": "Portugiesisch",
    "ru": "Russisch",
    "da": "Dänisch",
    "sv": "Schwedisch",
    "no": "Norwegisch",
    "cs": "Tschechisch",
    "hu": "Ungarisch",
    "tr": "Türkisch",
}

SUMMARY_LABELS: dict[str, str] = {
    "de": "Zusammenfassung",
    "en": "Summary",
    "fr": "Résumé",
    "es": "Resumen",
    "it": "Riassunto",
    "nl": "Samenvatting",
    "pl": "Podsumowanie",
    "pt": "Resumo",
}

SECTION_LABELS: dict[str, str] = {
    "de": "Abschnitt {n}",
    "en": "Section {n}",
    "fr": "Section {n}",
    "es": "Sección {n}",
    "it": "Sezione {n}",
    "nl": "Sectie {n}",
    "pl": "Sekcja {n}",
    "pt": "Secção {n}",
}

DEFAULT_TITLE_MAX_WORDS = 12

SYSTEM_TAG_NAMES: frozenset[str] = frozenset({"ai-warning", "ai-error", "ai-processed"})
FLOW_PROCESSED_TAG = "AI-Processed"


def is_system_tag(name: str | None) -> bool:
    if not name:
        return False
    return name.strip().lower() in SYSTEM_TAG_NAMES


def content_tag_names(names: list[str] | None) -> list[str]:
    return [name for name in (names or []) if not is_system_tag(name)]


def normalize_language(code: str | None) -> str:
    if not code or not str(code).strip():
        return "de"
    return str(code).strip().lower()[:2]


def language_name(code: str | None) -> str:
    normalized = normalize_language(code)
    return LANGUAGE_NAMES.get(normalized, normalized)


def summary_label(code: str | None) -> str:
    return SUMMARY_LABELS.get(normalize_language(code), "Summary")


def section_label(code: str | None, index: int) -> str:
    template = SECTION_LABELS.get(normalize_language(code), "Section {n}")
    return template.format(n=index + 1)


def limit_words(text: str, max_words: int = DEFAULT_TITLE_MAX_WORDS) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    words = cleaned.split(" ")
    if len(words) <= max_words:
        return cleaned
    return " ".join(words[:max_words])
