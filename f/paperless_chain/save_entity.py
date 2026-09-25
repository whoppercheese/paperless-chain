from f.paperless_chain.shared.paperless_client import (
    add_document_tags,
    create_or_get_correspondent,
    create_or_get_document_type,
    create_or_get_tag,
)


def main(
    doc_id: int,
    entity_type: str,
    accepted: list[dict],
) -> dict:
    warnings = []
    created = []
    saved_names = []

    if not accepted:
        return {
            "doc_id": doc_id,
            "entity_type": entity_type,
            "saved": [],
            "created": [],
            "warnings": ["Keine akzeptierten Entities"],
        }

    if entity_type == "correspondent":
        if len(accepted) > 1:
            warnings.append("Mehrere Korrespondenten ausgewählt, nur erster wird verwendet")

        item = accepted[0]
        if item.get("paperless_id"):
            entity = {"id": item["paperless_id"], "name": item["name"]}
            saved_names.append(item["name"])
        else:
            entity, was_created = create_or_get_correspondent(item["name"])
            saved_names.append(entity["name"])
            if was_created:
                created.append({"id": entity["id"], "name": entity["name"]})

        return {
            "doc_id": doc_id,
            "entity_type": entity_type,
            "saved": saved_names,
            "created": created,
            "warnings": warnings,
        }

    elif entity_type == "document_type":
        if len(accepted) > 1:
            warnings.append("Mehrere Dokumenttypen ausgewählt, nur erster wird verwendet")

        item = accepted[0]
        if item.get("paperless_id"):
            entity = {"id": item["paperless_id"], "name": item["name"]}
            saved_names.append(item["name"])
        else:
            entity, was_created = create_or_get_document_type(item["name"])
            saved_names.append(entity["name"])
            if was_created:
                created.append({"id": entity["id"], "name": entity["name"]})

        return {
            "doc_id": doc_id,
            "entity_type": entity_type,
            "saved": saved_names,
            "created": created,
            "warnings": warnings,
        }

    elif entity_type == "tag":
        tag_names = [item["name"] for item in accepted]
        result = add_document_tags(doc_id, tag_names)

        for name in result.get("added_tag_names", []):
            saved_names.append(name)

        for name in result.get("missing_tag_names", []):
            warnings.append(f"Tag nicht gefunden: {name}")

        return {
            "doc_id": doc_id,
            "entity_type": entity_type,
            "saved": saved_names,
            "created": created,
            "warnings": warnings,
            "paperless_result": result,
        }

    return {"error": f"Unknown entity_type: {entity_type}"}


if __name__ == "__main__":
    import json
    print(json.dumps(main(
        doc_id=1,
        entity_type="tag",
        accepted=[
            {"name": "Rechnung", "paperless_id": 1},
            {"name": "Wichtig", "paperless_id": 2},
        ],
    ), indent=2))
