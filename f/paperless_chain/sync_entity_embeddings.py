import os

import httpx

from f.paperless_chain.shared.llm_client import embed_texts
from f.paperless_chain.shared.paperless_client import (
    get_all_correspondents,
    get_all_document_types,
    get_all_tags,
)

EMBED_DIM = 1024
COLLECTION = "entity_embeddings"


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
            "description": p.get("description"),
        }
    return entities


def _build_entity_id(entity_type: str, paperless_id: int) -> str:
    return f"{entity_type}_{paperless_id}"


def main() -> dict:
    base = os.environ["QDRANT_URL"].rstrip("/")

    all_tags = get_all_tags()
    all_correspondents = get_all_correspondents()
    all_types = get_all_document_types()

    paperless_entities = {}

    for tag in all_tags:
        key = _build_entity_id("tag", tag["id"])
        paperless_entities[key] = {
            "name": tag["name"],
            "type": "tag",
            "paperless_id": tag["id"],
        }

    for corr in all_correspondents:
        key = _build_entity_id("corr", corr["id"])
        paperless_entities[key] = {
            "name": corr["name"],
            "type": "correspondent",
            "paperless_id": corr["id"],
        }

    for dt in all_types:
        key = _build_entity_id("doctype", dt["id"])
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
    to_add = paperless_keys - qdrant_keys

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

    added_count = 0
    if to_add:
        new_entities = []
        for key in to_add:
            entity = paperless_entities[key]
            entity["description"] = ""
            entity["id"] = key
            new_entities.append(entity)

        descriptions = [e["description"] for e in new_entities]
        vectors = embed_texts(descriptions)

        points = []
        for i, entity in enumerate(new_entities):
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

        if points:
            with httpx.Client(timeout=300.0) as client:
                r = client.put(
                    f"{base}/collections/{COLLECTION}/points",
                    json={"points": points},
                )
                r.raise_for_status()
            added_count = len(points)

    return {
        "paperless_total": len(paperless_entities),
        "qdrant_before": len(qdrant_entities),
        "added": added_count,
        "deleted": deleted_count,
        "qdrant_after": len(qdrant_entities) - deleted_count + added_count,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=2))
