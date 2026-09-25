from f.paperless_chain.shared.llm_client import chat_json
from f.paperless_chain.shared.prompts import (
    TITLE_SCHEMA,
    build_derive_title_prompt,
    build_derive_title_user_prompt,
)
from f.paperless_chain.shared.text_utils import (
    language_name,
    limit_words,
    normalize_language,
)


def main(
    doc_id: int,
    summary: str,
    added_date: str = "",
    document_language: str = "de",
) -> dict:
    lang_code = normalize_language(document_language)
    lang_label = language_name(lang_code)

    result = chat_json(
        build_derive_title_prompt(lang_label),
        build_derive_title_user_prompt(doc_id, summary),
        format_schema=TITLE_SCHEMA,
    )

    title = limit_words((result.get("title") or "").strip())

    return {
        "doc_id": doc_id,
        "title": title,
        "warnings": [],
    }
