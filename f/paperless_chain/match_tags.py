from f.paperless_chain.shared.llm_client import chat_json
from f.paperless_chain.shared.paperless_client import (
    create_or_get_tag,
    get_all_tags,
)
from f.paperless_chain.shared.text_utils import language_name, normalize_language

MATCH_TAGS_SCHEMA = {
    "type": "object",
    "properties": {
        "matched_tags": {"type": "array", "items": {"type": "string"}},
        "is_new": {"type": "array", "items": {"type": "boolean"}},
        "reasoning": {"type": "string"},
    },
    "required": ["matched_tags", "is_new", "reasoning"],
}


def main(
    doc_id: int,
    generated_tags: list[str] | None,
    paperless_tags: list[str] | None,
    existing_tags: list[dict] | None,
    document_language: str = "de",
    model: str | None = None,
) -> dict:
    lang_code = normalize_language(document_language)
    lang_label = language_name(lang_code)

    warnings: list[str] = []

    if not generated_tags:
        warnings.append("Keine Tags von LLM generiert")
        return {
            "doc_id": doc_id,
            "selected_tags": [],
            "created_tags": [],
            "warnings": warnings,
        }

    if not existing_tags:
        existing_tags = []

    existing_tag_names = [t["name"] for t in existing_tags]
    existing_tags_str = "\n".join(f"- {name}" for name in existing_tag_names)

    system_prompt = f"""\
Du findest die besten Tags für ein Dokument in Paperless-ngx.
Die Dokumentsprache ist: {lang_label}.

AUFGABE:
1. Du erhältst LLM-generierte Tags und bereits in Paperless gesetzte Tags
2. Du erhältst die Liste aller existierenden Tags in Paperless
3. Finde die besten Matches für die LLM-generierten Tags in der Liste
4. Wenn KEIN guter Match existiert, schlage einen NEUEN Tag vor — aber nur wenn WIRKLICH nötig

REGELN:
- Priorität: Verwende NUR existierende Tags — NIEMALS neue Tags erstellen, wenn ein existierender auch nur annähernd passt
- Nur SEHR保守 wenn KEIN existierender Tag auch nur entfernt passt, einen neuen vorschlagen
- Wenn ein guter Match existiert (exact oder sehr nah), verwende diesen
- Neue Tags nur im Stil der existierenden: kurze, generische Namen auf {lang_label}
- Maximal 5 Tags

Antworte als JSON mit:
- matched_tags: Array der gewählten Tags
- is_new: Array von booleans — true nur für wirklich neue Tags
- reasoning: kurze Begründung
"""

    user_prompt = f"""\
Dokument-ID: {doc_id}

LLM-generierte Tags: {", ".join(generated_tags)}

Bereits in Paperless gesetzte Tags: {", ".join(paperless_tags) if paperless_tags else "keine"}

Existierende Tags in Paperless:
{existing_tags_str}

Priorisiere existierende Tags — neue Tags nur als letzte Option."""

    result = chat_json(
        system_prompt,
        user_prompt,
        format_schema=MATCH_TAGS_SCHEMA,
        model=model,
    )

    matched_tags = result.get("matched_tags") or []
    is_new_list = result.get("is_new") or []
    matched_tags = [" ".join(t.split()).strip() for t in matched_tags if t]

    if not matched_tags:
        warnings.append("Matching LLM hat keine Tags geliefert")
        return {
            "doc_id": doc_id,
            "selected_tags": [],
            "created_tags": [],
            "warnings": warnings,
        }

    created_tags = []
    selected_tags = []

    for i, tag_name in enumerate(matched_tags):
        if not tag_name:
            continue
        try:
            entity, was_created = create_or_get_tag(tag_name)
            selected_tags.append(entity["name"])
            if was_created:
                created_tags.append({"id": entity["id"], "name": entity["name"]})
        except Exception as exc:
            warnings.append(f"Tag konnte nicht angelegt werden: {exc}")

    return {
        "doc_id": doc_id,
        "selected_tags": selected_tags,
        "created_tags": created_tags,
        "warnings": warnings,
    }
