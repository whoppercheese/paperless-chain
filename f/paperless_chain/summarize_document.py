from f.paperless_chain.shared.ollama_client import chat_json
from f.paperless_chain.shared.prompts import SUMMARY_SCHEMA, build_summary_prompt
from f.paperless_chain.shared.text_utils import language_name, normalize_language


def main(
    doc_id: int,
    text: str,
    document_language: str = "de",
    added_date: str = "",
) -> dict:
    lang_code = normalize_language(document_language)
    lang_label = language_name(lang_code)

    user = (
        f"Dokumentsprache (Paperless): {lang_code} ({lang_label})\n"
        f"Die Zusammenfassung MUSS vollständig auf {lang_label} verfasst sein.\n\n"
        f"Dokument-ID: {doc_id}\n\nText:\n{text}"
    )
    result = chat_json(build_summary_prompt(lang_label), user, format_schema=SUMMARY_SCHEMA)

    summary = (result.get("summary") or "").strip()
    document_date = (result.get("document_date") or "").strip() or None
    fallback_date = (added_date or "").strip()[:10] or None
    if not document_date:
        document_date = fallback_date
    warnings: list[str] = []
    if not summary:
        warnings.append("LLM hat keine Zusammenfassung geliefert")
    if not document_date:
        warnings.append("Kein Dokumentdatum verfügbar (weder im Text noch als Hinzufügedatum)")

    return {
        "doc_id": doc_id,
        "summary": summary,
        "document_date": document_date,
        "warnings": warnings,
    }
