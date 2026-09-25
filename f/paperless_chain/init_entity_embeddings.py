import os
import uuid

import httpx

from f.paperless_chain.shared.paperless_client import (
    get_all_correspondents,
    get_all_document_types,
    get_all_tags,
)

EMBED_DIM = 1024
COLLECTION = "entity_embeddings"
ENTITY_NAMESPACE = uuid.NAMESPACE_DNS


def _entity_key(entity_type: str, paperless_id: int) -> str:
    return f"{entity_type}_{paperless_id}"


def _qdrant_point_id(entity_key: str) -> str:
    return str(uuid.uuid5(ENTITY_NAMESPACE, entity_key))


def _ensure_collection(client: httpx.Client, base: str) -> None:
    r = client.get(f"{base}/collections/{COLLECTION}")
    if r.status_code == 200:
        return
    create = client.put(f"{base}/collections/{COLLECTION}", json={
        "vectors": {"size": EMBED_DIM, "distance": "Cosine"},
    })
    create.raise_for_status()


def main() -> dict:
    base = os.environ["QDRANT_URL"].rstrip("/")

    all_tags = get_all_tags()
    all_correspondents = get_all_correspondents()
    all_types = get_all_document_types()

    entities = []

    for tag in all_tags:
        key = _entity_key("tag", tag["id"])
        entities.append({
            "id": _qdrant_point_id(key),
            "name": tag["name"],
            "type": "tag",
            "paperless_id": tag["id"],
        })

    for corr in all_correspondents:
        key = _entity_key("corr", corr["id"])
        entities.append({
            "id": _qdrant_point_id(key),
            "name": corr["name"],
            "type": "correspondent",
            "paperless_id": corr["id"],
        })

    for dt in all_types:
        key = _entity_key("doctype", dt["id"])
        entities.append({
            "id": _qdrant_point_id(key),
            "name": dt["name"],
            "type": "document_type",
            "paperless_id": dt["id"],
        })

    if not entities:
        return {"initialized": 0, "message": "No entities found in Paperless"}

    points = []
    for entity in entities:
        points.append({
            "id": entity["id"],
            "vector": [0.0] * EMBED_DIM,
            "payload": {
                "name": entity["name"],
                "type": entity["type"],
                "paperless_id": entity["paperless_id"],
                "description": "",
            },
        })

    with httpx.Client(timeout=300.0) as client:
        _ensure_collection(client, base)
        r = client.put(f"{base}/collections/{COLLECTION}/points", json={"points": points})
        if r.status_code >= 400:
            raise RuntimeError(f"Qdrant PUT failed: {r.status_code} {r.text}")
        r.raise_for_status()

    return {
        "initialized": len(points),
        "tags": len(all_tags),
        "correspondents": len(all_correspondents),
        "document_types": len(all_types),
    }


if __name__ == "__main__":
    print(main())
