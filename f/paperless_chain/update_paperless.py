from f.paperless_chain.shared.paperless_client import patch
from f.paperless_chain.shared.text_utils import FLOW_PROCESSED_TAG, is_system_tag, limit_words


def _append_tag(
    name: str,
    tag_name_to_id: dict[str, int],
    tag_ids: list[int],
    known_tag_ids: set[int],
) -> bool:
    tag_id = tag_name_to_id.get(name.lower())
    if tag_id is None:
        return False
    if tag_id not in known_tag_ids:
        tag_ids.append(tag_id)
        known_tag_ids.add(tag_id)
    return True


def main(
    doc_id: int,
    title: str,
    selected_tags: list,
    selected_correspondent: str | None,
    existing_tags: list,
    existing_correspondents: list,
    existing_document_types: list,
    current_tag_ids: list | None = None,
    selected_document_type: str | None = None,
    document_date: str | None = None,
    warnings: list | None = None,
) -> dict:
    tag_name_to_id = {t["name"].lower(): t["id"] for t in existing_tags}
    tag_id_to_name = {t["id"]: t["name"] for t in existing_tags}
    corr_name_to_id = {c["name"].lower(): c["id"] for c in existing_correspondents}
    dtype_name_to_id = {d["name"].lower(): d["id"] for d in existing_document_types}
    collected_warnings = list(warnings or [])
    current_ids = list(current_tag_ids or [])

    tag_ids: list[int] = []
    known_tag_ids: set[int] = set()
    applied_tag_names: list[str] = []
    for name in selected_tags:
        if is_system_tag(name):
            continue
        key = name.lower()
        if key in tag_name_to_id:
            tag_id = tag_name_to_id[key]
            applied_tag_names.append(tag_id_to_name[tag_id])
            if tag_id not in known_tag_ids:
                tag_ids.append(tag_id)
                known_tag_ids.add(tag_id)

    if not _append_tag(FLOW_PROCESSED_TAG, tag_name_to_id, tag_ids, known_tag_ids):
        collected_warnings.append(
            f"System-Tag {FLOW_PROCESSED_TAG} existiert nicht in Paperless"
        )

    correspondent_id = None
    correspondent_name = selected_correspondent
    if correspondent_name:
        key = correspondent_name.lower()
        if key in corr_name_to_id:
            correspondent_id = corr_name_to_id[key]
        else:
            correspondent_name = None

    document_type_id = None
    document_type_name = selected_document_type
    if document_type_name:
        key = document_type_name.lower()
        if key in dtype_name_to_id:
            document_type_id = dtype_name_to_id[key]
        else:
            document_type_name = None

    update_payload: dict = {}
    cleaned_title = limit_words(title.strip())
    if cleaned_title:
        update_payload["title"] = cleaned_title
    if set(tag_ids) != set(current_ids):
        update_payload["tags"] = list(dict.fromkeys(tag_ids))
    if correspondent_id is not None:
        update_payload["correspondent"] = correspondent_id
    if document_type_id is not None:
        update_payload["document_type"] = document_type_id
    if document_date:
        update_payload["created_date"] = document_date

    if not update_payload:
        collected_warnings.append("Keine Metadaten-Änderungen, Paperless-Update übersprungen")
        print("=== Paperless-chAIn Paperless Update (skipped) ===")
        print(f"doc_id: {doc_id}")
        print("reason: Keine Metadaten-Änderungen")
        return {
            "doc_id": doc_id,
            "title": cleaned_title,
            "tag_names": applied_tag_names,
            "correspondent_name": correspondent_name,
            "document_type_name": document_type_name,
            "warnings": collected_warnings,
            "paperless_document": None,
            "skipped": True,
        }

    updated = patch(f"/api/documents/{doc_id}/", update_payload)

    return {
        "doc_id": doc_id,
        "title": title,
        "tag_names": applied_tag_names,
        "correspondent_name": correspondent_name,
        "document_type_name": document_type_name,
        "warnings": collected_warnings,
        "paperless_document": updated,
    }
