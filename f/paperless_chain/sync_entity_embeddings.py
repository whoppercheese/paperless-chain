import json
import os
import uuid

import httpx

from f.paperless_chain.shared.llm_client import embed_texts
from f.paperless_chain.shared.notify_client import notify
from f.paperless_chain.shared.paperless_client import (
    get_all_correspondents,
    get_all_document_types,
    get_all_tags,
)

EMBED_DIM = 1024
COLLECTION = "entity_embeddings"
ENTITY_NAMESPACE = uuid.NAMESPACE_DNS

TYPE_LABELS = {
    "tag": "Tag",
    "correspondent": "Korrespondent",
    "document_type": "Dokumenttyp",
}


def _format_message(added_entities: list[dict]) -> str:
    by_type: dict[str, list[str]] = {"tag": [], "correspondent": [], "document_type": []}
    for e in added_entities:
        by_type.setdefault(e["type"], []).append(e["name"])

    lines = [
        f"Paperless-chAIn: {len(added_entities)} neue Entity(s) synchronisiert",
    ]
    for entity_type, names in by_type.items():
        if names:
            lines.append(f"{TYPE_LABELS[entity_type]}: {', '.join(names)}")
    return "\n".join(lines)


def _entity_key(entity_type: str, paperless_id: int) -> str:
    if entity_type == "correspondent":
        prefix = "corr"
    elif entity_type == "document_type":
        prefix = "doctype"
    else:
        prefix = entity_type
    return f"{prefix}_{paperless_id}"


def _qdrant_point_id(entity_key: str) -> str:
    return str(uuid.uuid5(ENTITY_NAMESPACE, entity_key))


def _ensure_collection(client: httpx.Client, base: str) -> None:
    r = client.get(f"{base}/collections/{COLLECTION}")
    if r.status_code == 200:
        return

    create = client.put(
        f"{base}/collections/{COLLECTION}",
        json={"vectors": {"size": EMBED_DIM, "distance": "Cosine"}},
    )
    create.raise_for_status()


def _get_qdrant_entities(client: httpx.Client, base: str) -> dict:
    _ensure_collection(client, base)

    r = client.post(
        f"{base}/collections/{COLLECTION}/points/scroll",
        json={"limit": 10000, "with_payload": True},
    )
    r.raise_for_status()
    results = r.json().get("result", {}).get("points", [])

    entities = {}
    for point in results:
        p = point["payload"]
        entities[f"{p['type']}_{p['paperless_id']}"] = {
            "id": point["id"],
            "name": p["name"],
            "type": p["type"],
            "paperless_id": p["paperless_id"],
            "description": (p.get("description") or "").strip(),
        }
    return entities


def main() -> dict:
    base = os.environ["QDRANT_URL"].rstrip("/")

    all_tags = get_all_tags()
    all_correspondents = get_all_correspondents()
    all_types = get_all_document_types()

    paperless_entities = {}

    for tag in all_tags:
        key = _entity_key("tag", tag["id"])
        paperless_entities[key] = {
            "name": tag["name"],
            "type": "tag",
            "paperless_id": tag["id"],
        }

    for corr in all_correspondents:
        key = _entity_key("corr", corr["id"])
        paperless_entities[key] = {
            "name": corr["name"],
            "type": "correspondent",
            "paperless_id": corr["id"],
        }

    for dt in all_types:
        key = _entity_key("doctype", dt["id"])
        paperless_entities[key] = {
            "name": dt["name"],
            "type": "document_type",
            "paperless_id": dt["id"],
        }

    with httpx.Client(timeout=120.0) as client:
        qdrant_entities = _get_qdrant_entities(client, base)

    paperless_keys = set(paperless_entities.keys())
    qdrant_keys = set(qdrant_entities.keys())

    to_delete = qdrant_keys - paperless_keys
    to_upsert: list[dict] = []
    added_entities_for_notify: list[dict] = []

    for key in sorted(paperless_keys - qdrant_keys):
        entity = paperless_entities[key]
        entity["id"] = _qdrant_point_id(key)
        entity["description"] = ""
        to_upsert.append(entity)
        added_entities_for_notify.append({"type": entity["type"], "name": entity["name"]})

    for key in sorted(paperless_keys & qdrant_keys):
        existing = qdrant_entities[key]
        description = existing.get("description", "")
        if not description:
            continue
        entity = paperless_entities[key]
        entity["id"] = existing["id"]
        entity["description"] = description
        to_upsert.append(entity)

    deleted_count = 0
    if to_delete:
        point_ids = [qdrant_entities[k]["id"] for k in to_delete]
        with httpx.Client(timeout=120.0) as client:
            r = client.post(
                f"{base}/collections/{COLLECTION}/points/delete",
                json={"points": point_ids},
            )
            r.raise_for_status()
        deleted_count = len(point_ids)

    embeddable = [e for e in to_upsert if e.get("description")]
    skipped_no_description = [e for e in to_upsert if not e.get("description")]

    if skipped_no_description:
        names = [e["name"] for e in skipped_no_description]
        print(f"[sync_entity_embeddings] Skip (no description): {names}")

    if embeddable:
        texts = [f"{e['name']}: {e['description']}" for e in embeddable]
        vectors = embed_texts(texts)

        points = []
        for i, entity in enumerate(embeddable):
            points.append({
                "id": entity["id"],
                "vector": vectors[i],
                "payload": {
                    "name": entity["name"],
                    "type": entity["type"],
                    "paperless_id": entity["paperless_id"],
                    "description": entity["description"],
                },
            })

        with httpx.Client(timeout=300.0) as client:
            r = client.put(
                f"{base}/collections/{COLLECTION}/points",
                json={"points": points},
            )
            if r.status_code >= 400:
                raise RuntimeError(f"Qdrant PUT failed: {r.status_code} {r.text}")
            r.raise_for_status()

    notified = False
    if added_entities_for_notify:
        try:
            mode = notify(
                _format_message(added_entities_for_notify),
                event="paperless_chain.entities_added",
            )
            notified = mode != "log"
        except Exception as e:
            print(f"Notify failed: {e}")
            notified = False

    return {
        "paperless_total": len(paperless_entities),
        "qdrant_before": len(qdrant_entities),
        "added": len([e for e in to_upsert if e["id"] not in {qe["id"] for qe in qdrant_entities.values()}]),
        "re_embedded": len([e for e in to_upsert if e["id"] in {qe["id"] for qe in qdrant_entities.values()}]),
        "deleted": deleted_count,
        "skipped_no_description": len(skipped_no_description),
        "qdrant_after": len(qdrant_entities) - deleted_count + len(added_entities_for_notify),
        "notified": notified,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=2, ensure_ascii=False))
