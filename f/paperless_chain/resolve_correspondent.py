from f.paperless_chain.shared.llm_client import chat_json
from f.paperless_chain.shared.prompts import (
    CORRESPONDENT_SCHEMA,
    build_resolve_correspondent_prompt,
    build_resolve_correspondent_user_prompt,
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
        build_resolve_correspondent_prompt(lang_label),
        build_resolve_correspondent_user_prompt(doc_id, summary),
        format_schema=CORRESPONDENT_SCHEMA,
    )

    generated_corr = " ".join((result.get("correspondent") or "").split()).strip()
    if not generated_corr:
        warnings.append("LLM hat keinen Korrespondenten geliefert")
        return {
            "doc_id": doc_id,
            "generated_correspondent": None,
            "warnings": warnings,
        }

    return {
        "doc_id": doc_id,
        "generated_correspondent": generated_corr,
        "warnings": warnings,
    }
