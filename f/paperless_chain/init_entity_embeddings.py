import json
import os
import uuid

import httpx

from f.paperless_chain.shared.llm_client import embed_texts
from f.paperless_chain.shared.paperless_client import (
    get_all_correspondents,
    get_all_document_types,
    get_all_tags,
)

EMBED_DIM = 1024
COLLECTION = "entity_embeddings"


def _entity_key(entity_type: str, paperless_id: int) -> str:
    if entity_type == "correspondent":
        prefix = "corr"
    elif entity_type == "document_type":
        prefix = "doctype"
    else:
        prefix = entity_type
    return f"{prefix}_{paperless_id}"


def _qdrant_point_id(entity_key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, entity_key))


def _ensure_collection(client: httpx.Client, base: str) -> None:
    r = client.get(f"{base}/collections/{COLLECTION}")
    if r.status_code == 200:
        return
    create = client.put(f"{base}/collections/{COLLECTION}", json={
        "vectors": {"size": EMBED_DIM, "distance": "Cosine"},
    })
    create.raise_for_status()


def _get_qdrant_entities(client: httpx.Client, base: str) -> dict:
    _ensure_collection(client, base)
    r = client.post(
        f"{base}/collections/{COLLECTION}/points/scroll",
        json={"limit": 10000, "with_payload": True},
    )
    r.raise_for_status()
    entities = {}
    for point in r.json().get("result", {}).get("points", []):
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

    paperless_entities = {}

    for tag in get_all_tags():
        key = _entity_key("tag", tag["id"])
        paperless_entities[key] = {
            "name": tag["name"],
            "type": "tag",
            "paperless_id": tag["id"],
        }

    for corr in get_all_correspondents():
        key = _entity_key("corr", corr["id"])
        paperless_entities[key] = {
            "name": corr["name"],
            "type": "correspondent",
            "paperless_id": corr["id"],
        }

    for dt in get_all_document_types():
        key = _entity_key("doctype", dt["id"])
        paperless_entities[key] = {
            "name": dt["name"],
            "type": "document_type",
            "paperless_id": dt["id"],
        }

    with httpx.Client(timeout=120.0) as client:
        qdrant_entities = _get_qdrant_entities(client, base)

    with_description = []
    skipped_no_description = []

    for key, entity in paperless_entities.items():
        existing = qdrant_entities.get(key)
        if existing is None:
            skipped_no_description.append(entity)
            continue
        description = existing.get("description", "")
        if not description:
            skipped_no_description.append(entity)
            continue
        entity["id"] = existing["id"]
        entity["description"] = description
        with_description.append(entity)

    if not with_description:
        return {
            "initialized": 0,
            "skipped_no_description": len(skipped_no_description),
            "paperless_total": len(paperless_entities),
            "message": "Keine Entities mit Description in Qdrant gefunden",
        }

    texts = [f"{e['name']}: {e['description']}" for e in with_description]
    vectors = embed_texts(texts)

    points = []
    for i, entity in enumerate(with_description):
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
        _ensure_collection(client, base)
        r = client.put(f"{base}/collections/{COLLECTION}/points", json={"points": points})
        if r.status_code >= 400:
            raise RuntimeError(f"Qdrant PUT failed: {r.status_code} {r.text}")
        r.raise_for_status()

    return {
        "initialized": len(points),
        "skipped_no_description": len(skipped_no_description),
        "paperless_total": len(paperless_entities),
        "tags": len([e for e in paperless_entities.values() if e["type"] == "tag"]),
        "correspondents": len([e for e in paperless_entities.values() if e["type"] == "correspondent"]),
        "document_types": len([e for e in paperless_entities.values() if e["type"] == "document_type"]),
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False))
