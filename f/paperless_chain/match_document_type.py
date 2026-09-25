from f.paperless_chain.shared.llm_client import chat_json
from f.paperless_chain.shared.paperless_client import (
    create_or_get_document_type,
    get_all_document_types,
)
from f.paperless_chain.shared.text_utils import language_name, normalize_language

MATCH_DOCUMENT_TYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "matched_document_type": {"type": "string"},
        "is_new": {"type": "boolean"},
        "reasoning": {"type": "string"},
    },
    "required": ["matched_document_type", "is_new", "reasoning"],
}


def main(
    doc_id: int,
    generated_document_type: str | None,
    paperless_document_type: str | None,
    document_language: str = "de",
    model: str | None = None,
) -> dict:
    lang_code = normalize_language(document_language)
    lang_label = language_name(lang_code)

    warnings: list[str] = []

    if not generated_document_type:
        warnings.append("Kein Dokumenttyp von LLM generiert")
        return {
            "doc_id": doc_id,
            "selected_document_type": paperless_document_type,
            "created_document_type": None,
            "warnings": warnings,
        }

    all_types = get_all_document_types()
    existing_type_names = [t["name"] for t in all_types]
    existing_types_str = "\n".join(f"- {name}" for name in existing_type_names)

    system_prompt = f"""\
Du findest den besten Dokumenttyp für ein Dokument in Paperless-ngx.
Die Dokumentsprache ist: {lang_label}.

AUFGABE:
1. Du erhältst einen LLM-generierten Dokumenttyp und einen bereits in Paperless gesetzten Dokumenttyp (falls vorhanden)
2. Du erhältst die Liste aller existierenden Dokumenttypen in Paperless
3. Finde den besten Match für den LLM-generierten Dokumenttyp in der Liste
4. Wenn kein guter Match existiert, schlage einen NEUEN Dokumenttyp vor, der zum Stil der existierenden Typen passt

REGELN:
- Wenn ein guter Match existiert (exact oder sehr nah), verwende diesen
- Wenn KEIN Match existiert, schlage einen neuen Typ vor im Stil der existierenden: kurze, generische Namen
- Verwende existierende Typen als Priorität, nur neue vorschlagen wenn wirklich nötig
- Der vorgeschlagene Name muss in der Dokumentsprache ({lang_label}) sein

Antworte als JSON mit:
- matched_document_type: der gewählte/neue Dokumenttyp
- is_new: true wenn neuer Typ, false wenn existierender Match
- reasoning: kurze Begründung warum dieser Typ gewählt wurde
"""

    user_prompt = f"""\
Dokument-ID: {doc_id}

LLM-generierter Dokumenttyp: {generated_document_type}

Bereits in Paperless gesetzter Dokumenttyp: {paperless_document_type or "keiner"}

Existierende Dokumenttypen in Paperless:
{existing_types_str}

Wenn kein guter Match existiert, schlage einen neuen Typ vor."""

    result = chat_json(
        system_prompt,
        user_prompt,
        format_schema=MATCH_DOCUMENT_TYPE_SCHEMA,
        model=model,
    )

    matched_type = " ".join((result.get("matched_document_type") or "").split()).strip()
    is_new = result.get("is_new", False)

    if not matched_type:
        warnings.append("Matching LLM hat keinen Dokumenttyp geliefert")
        return {
            "doc_id": doc_id,
            "selected_document_type": paperless_document_type,
            "created_document_type": None,
            "warnings": warnings,
        }

    try:
        entity, was_created = create_or_get_document_type(matched_type)
        return {
            "doc_id": doc_id,
            "selected_document_type": entity["name"],
            "created_document_type": {"id": entity["id"], "name": entity["name"], "created": was_created},
            "warnings": warnings,
        }
    except Exception as exc:
        warnings.append(f"Dokumenttyp konnte nicht angelegt werden: {exc}")
        return {
            "doc_id": doc_id,
            "selected_document_type": paperless_document_type,
            "created_document_type": None,
            "warnings": warnings,
        }
