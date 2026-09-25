from f.paperless_chain.shared.paperless_client import patch
from f.paperless_chain.shared.text_utils import (
    FLOW_PROCESSED_TAG,
    content_tag_names,
    limit_words,
)


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


def _content_tag_names_from_ids(tag_ids: list[int], tag_id_to_name: dict[int, str]) -> list[str]:
    return content_tag_names(
        tag_id_to_name[tag_id]
        for tag_id in tag_ids
        if tag_id in tag_id_to_name
    )


def _collect_metadata_warnings(
    *,
    final_title: str,
    final_document_type_name: str | None,
    final_correspondent_name: str | None,
    final_content_tag_names: list[str],
    created_document_type: dict | None,
    created_correspondent: dict | None,
    created_tags: list[dict] | None,
) -> list[str]:
    warnings: list[str] = []
    if not final_title:
        warnings.append("Kein Titel verfügbar")
    if not final_document_type_name:
        warnings.append("Kein Dokumenttyp ermittelt")
    if not final_correspondent_name:
        warnings.append("Kein Korrespondent ermittelt")
    if not final_content_tag_names:
        warnings.append("Keine Tags gesetzt")
    if created_document_type and created_document_type.get("created"):
        warnings.append(f"Neuer Dokumenttyp angelegt: {created_document_type['name']}")
    if created_correspondent and created_correspondent.get("created"):
        warnings.append(f"Neuer Korrespondent angelegt: {created_correspondent['name']}")
    if created_tags:
        for tag in created_tags:
            warnings.append(f"Neuer Tag angelegt: {tag['name']}")
    return warnings


def _merge_created_entity(
    entity: dict | None,
    name_to_id: dict[str, int],
    id_to_name: dict[int, str],
) -> None:
    if not entity:
        return
    name = (entity.get("name") or "").strip()
    entity_id = entity.get("id")
    if not name or entity_id is None:
        return
    name_to_id[name.lower()] = entity_id
    id_to_name[entity_id] = name


def _merge_created_tags(
    created_tags: list[dict] | None,
    tag_name_to_id: dict[str, int],
    tag_id_to_name: dict[int, str],
) -> None:
    if not created_tags:
        return
    for tag in created_tags:
        name = (tag.get("name") or "").strip()
        tag_id = tag.get("id")
        if not name or tag_id is None:
            continue
        tag_name_to_id[name.lower()] = tag_id
        tag_id_to_name[tag_id] = name


def main(
    doc_id: int,
    title: str,
    selected_correspondent: str | None,
    existing_tags: list,
    existing_correspondents: list,
    existing_document_types: list,
    current_tag_ids: list | None = None,
    selected_document_type: str | None = None,
    document_date: str | None = None,
    current_title: str | None = None,
    current_correspondent_id: int | None = None,
    current_document_type_id: int | None = None,
    summarize_warnings: list | None = None,
    title_warnings: list | None = None,
    created_document_type: dict | None = None,
    created_correspondent: dict | None = None,
    selected_tags: list[str] | None = None,
    created_tags: list[dict] | None = None,
) -> dict:
    tag_name_to_id = {t["name"].lower(): t["id"] for t in existing_tags}
    tag_id_to_name = {t["id"]: t["name"] for t in existing_tags}
    corr_name_to_id = {c["name"].lower(): c["id"] for c in existing_correspondents}
    corr_id_to_name = {c["id"]: c["name"] for c in existing_correspondents}
    dtype_name_to_id = {d["name"].lower(): d["id"] for d in existing_document_types}
    dtype_id_to_name = {d["id"]: d["name"] for d in existing_document_types}
    _merge_created_entity(created_document_type, dtype_name_to_id, dtype_id_to_name)
    _merge_created_entity(created_correspondent, corr_name_to_id, corr_id_to_name)
    _merge_created_tags(created_tags, tag_name_to_id, tag_id_to_name)
    collected_warnings = list(summarize_warnings or [])
    collected_warnings.extend(title_warnings or [])
    current_ids = list(current_tag_ids or [])
    tag_ids = list(dict.fromkeys(current_ids))
    known_tag_ids = set(tag_ids)

    if not _append_tag(FLOW_PROCESSED_TAG, tag_name_to_id, tag_ids, known_tag_ids):
        collected_warnings.append(
            f"System-Tag {FLOW_PROCESSED_TAG} existiert nicht in Paperless"
        )

    if selected_tags:
        for tag_name in selected_tags:
            _append_tag(tag_name, tag_name_to_id, tag_ids, known_tag_ids)

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

    final_title = cleaned_title or (current_title or "").strip()
    final_document_type_name = document_type_name
    if not final_document_type_name and current_document_type_id:
        final_document_type_name = dtype_id_to_name.get(current_document_type_id)
    final_correspondent_name = correspondent_name
    if not final_correspondent_name and current_correspondent_id:
        final_correspondent_name = corr_id_to_name.get(current_correspondent_id)
    final_content_tag_names = _content_tag_names_from_ids(tag_ids, tag_id_to_name)

    collected_warnings.extend(
        _collect_metadata_warnings(
            final_title=final_title,
            final_document_type_name=final_document_type_name,
            final_correspondent_name=final_correspondent_name,
            final_content_tag_names=final_content_tag_names,
            created_document_type=created_document_type,
            created_correspondent=created_correspondent,
            created_tags=created_tags,
        )
    )

    if not update_payload:
        collected_warnings.append("Keine Metadaten-Änderungen, Paperless-Update übersprungen")
        print("=== Paperless-chAIn Paperless Update (skipped) ===")
        print(f"doc_id: {doc_id}")
        print("reason: Keine Metadaten-Änderungen")
        return {
            "doc_id": doc_id,
            "title": final_title,
            "tag_names": final_content_tag_names,
            "correspondent_name": final_correspondent_name,
            "document_type_name": final_document_type_name,
            "warnings": collected_warnings,
            "paperless_document": None,
            "skipped": True,
        }

    updated = patch(f"/api/documents/{doc_id}/", update_payload)

    return {
        "doc_id": doc_id,
        "title": final_title,
        "tag_names": final_content_tag_names,
        "correspondent_name": final_correspondent_name,
        "document_type_name": final_document_type_name,
        "warnings": collected_warnings,
        "paperless_document": updated,
    }
