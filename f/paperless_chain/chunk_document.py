from f.paperless_chain.shared.ollama_client import chat_json
from f.paperless_chain.shared.prompts import CHUNK_SCHEMA, build_chunk_prompt
from f.paperless_chain.shared.text_utils import language_name, normalize_language, section_label, summary_label


def main(
    doc_id: int,
    text: str,
    summary: str = "",
    document_type_name: str | None = None,
    correspondent_name: str | None = None,
    tag_names: list | None = None,
    document_language: str = "de",
) -> dict:
    lang_code = normalize_language(document_language)
    lang_label = language_name(lang_code)
    doc_type = document_type_name or "Unbekannt"
    user = (
        f"Dokumentsprache (Paperless): {lang_code} ({lang_label})\n"
        f"Dokumenttyp: {doc_type}\n\nText:\n{text}"
    )
    result = chat_json(build_chunk_prompt(lang_label), user, format_schema=CHUNK_SCHEMA)

    warnings: list[str] = []
    chunks: list[dict] = []

    if summary.strip():
        chunks.append({
            "text": summary.strip(),
            "chunk_kind": "summary",
            "label": summary_label(lang_code),
        })
    else:
        warnings.append("Keine Zusammenfassung vorhanden, Summary-Embedding entfällt")

    for index, item in enumerate(result.get("chunks") or []):
        chunk_text = (item.get("text") or "").strip()
        if not chunk_text:
            continue
        label = (item.get("label") or section_label(lang_code, index)).strip()
        chunks.append({
            "text": chunk_text,
            "chunk_kind": "chunk",
            "label": label,
        })

    if not any(c["chunk_kind"] == "chunk" for c in chunks):
        warnings.append("LLM hat keine Teil-Chunks geliefert")

    for chunk in chunks:
        chunk["doc_id"] = doc_id
        chunk["correspondent"] = correspondent_name
        chunk["tags"] = tag_names or []
        chunk["document_type"] = doc_type

    return {
        "doc_id": doc_id,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "warnings": warnings,
    }
