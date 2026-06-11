from f.paperless_chain.shared.paperless_client import get, paginate


def main(doc_id: int) -> dict:
    document = get(f"/api/documents/{doc_id}/")
    metadata = get(f"/api/documents/{doc_id}/metadata/")
    text = document.get("content") or ""
    document_language = (metadata.get("lang") or "de").strip().lower()[:2]
    tags = paginate("/api/tags/")
    correspondents = paginate("/api/correspondents/")
    document_types = paginate("/api/document_types/")

    existing_tags = [{"id": t["id"], "name": t["name"]} for t in tags]
    tag_id_to_name = {t["id"]: t["name"] for t in existing_tags}
    current_tag_names = [
        tag_id_to_name[tid]
        for tid in document.get("tags", [])
        if tid in tag_id_to_name
    ]

    return {
        "doc_id": doc_id,
        "text": text,
        "document_language": document_language,
        "existing_tags": existing_tags,
        "existing_correspondents": [{"id": c["id"], "name": c["name"]} for c in correspondents],
        "existing_document_types": [{"id": d["id"], "name": d["name"]} for d in document_types],
        "added_date": (document.get("added") or "")[:10],
        "current_tag_names": current_tag_names,
        "current_metadata": {
            "title": document.get("title"),
            "correspondent": document.get("correspondent"),
            "tag_ids": document.get("tags", []),
            "document_type": document.get("document_type"),
        },
    }
