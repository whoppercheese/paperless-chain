from f.paperless_chain.shared.paperless_client import get
from f.paperless_chain.shared.windmill_client import run_process_document_async

DEFAULT_LIMIT = 10


def _resolve_tag_id(tag_name: str, tag_name_to_id: dict[str, int]) -> int | None:
    return tag_name_to_id.get(tag_name.strip().lower())


def _list_tags() -> tuple[dict[str, int], dict[int, str]]:
    from f.paperless_chain.shared.paperless_client import paginate

    tags = paginate("/api/tags/")
    name_to_id = {t["name"].lower(): t["id"] for t in tags}
    id_to_name = {t["id"]: t["name"] for t in tags}
    return name_to_id, id_to_name


def _list_documents_with_tag(tag_id: int) -> list[dict]:
    documents: list[dict] = []
    page = 1
    while True:
        data = get(
            "/api/documents/",
            params={
                "page": page,
                "page_size": 100,
                "tags__id__all": tag_id,
                "ordering": "created",
            },
        )
        documents.extend(data.get("results", []))
        if not data.get("next"):
            break
        page += 1
    return documents


def _should_skip_document(
    document: dict,
    skip_tag_ids: set[int],
    id_to_name: dict[int, str],
) -> str | None:
    doc_tag_ids = set(document.get("tags") or [])
    overlap = doc_tag_ids & skip_tag_ids
    if not overlap:
        return None
    skipped_names = sorted(id_to_name.get(tag_id, str(tag_id)) for tag_id in overlap)
    return ", ".join(skipped_names)


def main(
    tag_name: str,
    limit: int = DEFAULT_LIMIT,
    skip_tag_names: list[str] | None = None,
) -> dict:
    if not tag_name or not tag_name.strip():
        raise ValueError("tag_name is required")

    if limit < 1:
        raise ValueError("limit must be at least 1")

    tag_name_to_id, tag_id_to_name = _list_tags()
    queue_tag_id = _resolve_tag_id(tag_name, tag_name_to_id)
    if queue_tag_id is None:
        raise ValueError(f"Tag not found in Paperless: {tag_name}")

    skip_names = list(skip_tag_names or [])
    skip_tag_ids: set[int] = set()
    unknown_skip_tags: list[str] = []
    for name in skip_names:
        tag_id = _resolve_tag_id(name, tag_name_to_id)
        if tag_id is None:
            unknown_skip_tags.append(name)
        else:
            skip_tag_ids.add(tag_id)

    documents = _list_documents_with_tag(queue_tag_id)
    matched_count = len(documents)

    queued: list[dict] = []
    skipped: list[dict] = []

    for document in documents:
        if len(queued) >= limit:
            break

        doc_id = document["id"]
        skip_reason = _should_skip_document(document, skip_tag_ids, tag_id_to_name)
        if skip_reason:
            skipped.append({
                "doc_id": doc_id,
                "title": document.get("title") or "",
                "reason": f"has skip tag(s): {skip_reason}",
            })
            continue

        job_id = run_process_document_async(doc_id)
        queued.append({
            "doc_id": doc_id,
            "title": document.get("title") or "",
            "job_id": job_id,
        })

    result = {
        "tag_name": tag_id_to_name.get(queue_tag_id, tag_name),
        "limit": limit,
        "matched_count": matched_count,
        "queued_count": len(queued),
        "skipped_count": len(skipped),
        "not_queued_count": max(0, matched_count - len(queued)),
        "queued": queued,
        "skipped": skipped,
        "unknown_skip_tags": unknown_skip_tags,
    }

    print("=== Paperless-chAIn Queue by Tag ===")
    print(f"tag: {result['tag_name']}")
    print(f"matched: {matched_count}, queued: {len(queued)}, skipped: {len(skipped)}")
    for item in queued:
        print(f"  queued doc_id={item['doc_id']} job_id={item['job_id']}")

    return result
