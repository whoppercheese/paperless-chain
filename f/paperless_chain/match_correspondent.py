from f.paperless_chain.shared.llm_client import chat_json
from f.paperless_chain.shared.paperless_client import (
    create_or_get_correspondent,
    get_all_correspondents,
)
from f.paperless_chain.shared.text_utils import language_name, normalize_language

MATCH_CORRESPONDENT_SCHEMA = {
    "type": "object",
    "properties": {
        "matched_correspondent": {"type": "string"},
        "is_new": {"type": "boolean"},
        "reasoning": {"type": "string"},
    },
    "required": ["matched_correspondent", "is_new", "reasoning"],
}


def main(
    doc_id: int,
    generated_correspondent: str | None,
    paperless_correspondent: str | None,
    document_language: str = "de",
    model: str | None = None,
) -> dict:
    lang_code = normalize_language(document_language)
    lang_label = language_name(lang_code)

    warnings: list[str] = []

    if not generated_correspondent:
        warnings.append("Kein Korrespondent von LLM generiert")
        return {
            "doc_id": doc_id,
            "selected_correspondent": paperless_correspondent,
            "created_correspondent": None,
            "warnings": warnings,
        }

    all_correspondents = get_all_correspondents()
    existing_corr_names = [c["name"] for c in all_correspondents]
    existing_correspondents_str = "\n".join(f"- {name}" for name in existing_corr_names)

    system_prompt = f"""\
Du findest den besten Korrespondenten für ein Dokument in Paperless-ngx.
Die Dokumentsprache ist: {lang_label}.

AUFGABE:
1. Du erhältst einen LLM-generierten Korrespondenten und einen bereits in Paperless gesetzten Korrespondenten (falls vorhanden)
2. Du erhältst die Liste aller existierenden Korrespondenten in Paperless
3. Finde den besten Match für den LLM-generierten Korrespondenten in der Liste
4. Wenn kein guter Match existiert, schlage einen NEUEN Korrespondenten vor, der zum Stil der existierenden passt

REGELN:
- Wenn ein guter Match existiert (exact oder sehr nah), verwende diesen
- Wenn KEIN Match existiert, schlage einen neuen Korrespondenten vor im Stil der existierenden: kurze, generische Namen
- Eigennamen und Firmennamen unverändert übernehmen
- Keine Rechtsformen (GmbH, AG, Inc., Ltd. etc.), keine Domains (.com), keine Zusätze
- Beispiel: "Amazon.com, Inc." → "Amazon"; "Deutsche Telekom AG" → "Deutsche Telekom"
- Verwende existierende Korrespondenten als Priorität, nur neue vorschlagen wenn wirklich nötig

Antworte als JSON mit:
- matched_correspondent: der gewählte/neue Korrespondent
- is_new: true wenn neuer Typ, false wenn existierender Match
- reasoning: kurze Begründung warum dieser Korrespondent gewählt wurde
"""

    user_prompt = f"""\
Dokument-ID: {doc_id}

LLM-generierter Korrespondent: {generated_correspondent}

Bereits in Paperless gesetzter Korrespondent: {paperless_correspondent or "keiner"}

Existierende Korrespondenten in Paperless:
{existing_correspondents_str}

Wenn kein guter Match existiert, schlage einen neuen Korrespondenten vor."""

    result = chat_json(
        system_prompt,
        user_prompt,
        format_schema=MATCH_CORRESPONDENT_SCHEMA,
        model=model,
    )

    matched_corr = " ".join((result.get("matched_correspondent") or "").split()).strip()
    is_new = result.get("is_new", False)

    if not matched_corr:
        warnings.append("Matching LLM hat keinen Korrespondenten geliefert")
        return {
            "doc_id": doc_id,
            "selected_correspondent": paperless_correspondent,
            "created_correspondent": None,
            "warnings": warnings,
        }

    try:
        entity, was_created = create_or_get_correspondent(matched_corr)
        return {
            "doc_id": doc_id,
            "selected_correspondent": entity["name"],
            "created_correspondent": {"id": entity["id"], "name": entity["name"], "created": was_created},
            "warnings": warnings,
        }
    except Exception as exc:
        warnings.append(f"Korrespondent konnte nicht angelegt werden: {exc}")
        return {
            "doc_id": doc_id,
            "selected_correspondent": paperless_correspondent,
            "created_correspondent": None,
            "warnings": warnings,
        }
