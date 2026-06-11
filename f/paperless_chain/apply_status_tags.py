from f.paperless_chain.shared.paperless_client import add_document_tags

STATUS_TAG_WARNING = "AI-Warning"


def _dedupe_warnings(*warning_lists: list | None) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()
    for warning_list in warning_lists:
        for warning in warning_list or []:
            text = str(warning).strip()
            if text and text not in seen:
                seen.add(text)
                warnings.append(text)
    return warnings


def main(
    doc_id: int,
    summarize_warnings: list | None = None,
    analyze_warnings: list | None = None,
    update_warnings: list | None = None,
    chunk_warnings: list | None = None,
) -> dict:
    warnings = _dedupe_warnings(
        summarize_warnings,
        analyze_warnings,
        update_warnings,
        chunk_warnings,
    )

    tag_result = None
    applied_status_tag = None
    if warnings:
        tag_result = add_document_tags(doc_id, [STATUS_TAG_WARNING])
        applied_status_tag = STATUS_TAG_WARNING

    return {
        "doc_id": doc_id,
        "warnings": warnings,
        "applied_status_tag": applied_status_tag,
        "tag_result": tag_result,
    }
