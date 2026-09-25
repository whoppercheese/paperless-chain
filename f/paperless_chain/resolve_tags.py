from f.paperless_chain.shared.llm_client import chat_json
from f.paperless_chain.shared.prompts import (
    TAGS_SCHEMA,
    build_resolve_tags_prompt,
    build_resolve_tags_user_prompt,
)


def main(
    doc_id: int,
    summary: str,
    document_language: str = "de",
) -> dict:
    warnings: list[str] = []
    result = chat_json(
        build_resolve_tags_prompt(document_language),
        build_resolve_tags_user_prompt(doc_id, summary),
        format_schema=TAGS_SCHEMA,
    )

    generated_tags = result.get("tags") or []
    generated_tags = [" ".join(t.split()).strip() for t in generated_tags if t]

    if not generated_tags:
        warnings.append("LLM hat keine Tags geliefert")
        return {
            "doc_id": doc_id,
            "generated_tags": None,
            "warnings": warnings,
        }

    return {
        "doc_id": doc_id,
        "generated_tags": generated_tags,
        "warnings": warnings,
    }
