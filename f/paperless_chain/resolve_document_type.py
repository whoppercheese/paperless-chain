from f.paperless_chain.shared.llm_client import chat_json
from f.paperless_chain.shared.prompts import (
    DOCUMENT_TYPE_SCHEMA,
    build_resolve_document_type_prompt,
    build_resolve_document_type_user_prompt,
)
from f.paperless_chain.shared.text_utils import language_name, normalize_language


def main(
    doc_id: int,
    summary: str,
    document_language: str = "de",
) -> dict:
    lang_code = normalize_language(document_language)
    lang_label = language_name(lang_code)

    warnings: list[str] = []
    result = chat_json(
        build_resolve_document_type_prompt(lang_label),
        build_resolve_document_type_user_prompt(doc_id, summary),
        format_schema=DOCUMENT_TYPE_SCHEMA,
    )

    generated_type = " ".join((result.get("document_type") or "").split()).strip()
    if not generated_type:
        warnings.append("LLM hat keinen Dokumenttyp geliefert")
        return {
            "doc_id": doc_id,
            "generated_document_type": None,
            "warnings": warnings,
        }

    return {
        "doc_id": doc_id,
        "generated_document_type": generated_type,
        "warnings": warnings,
    }
