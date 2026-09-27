import json
import os
import sys
import uuid

import httpx

from f.paperless_chain.shared.paperless_client import (
    get_all_correspondents,
    get_all_document_types,
    get_all_tags,
)

COLLECTION = "entity_embeddings"
EMBED_DIM = 1024
ZERO_VECTOR = [0.0] * EMBED_DIM


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
    r = client.put(
        f"{base}/collections/{COLLECTION}",
        json={"vectors": {"size": EMBED_DIM, "distance": "Cosine"}},
    )
    r.raise_for_status()


def _get_qdrant_keys(client: httpx.Client, base: str) -> set[str]:
    _ensure_collection(client, base)
    r = client.post(
        f"{base}/collections/{COLLECTION}/points/scroll",
        json={"limit": 10000, "with_payload": True},
    )
    r.raise_for_status()
    keys: set[str] = set()
    for point in r.json().get("result", {}).get("points", []):
        p = point["payload"]
        keys.add(f"{p['type']}_{p['paperless_id']}")
    return keys


def _fetch_paperless_entities() -> dict[str, dict]:
    entities: dict[str, dict] = {}
    for tag in get_all_tags():
        key = _entity_key("tag", tag["id"])
        entities[key] = {"name": tag["name"], "type": "tag", "paperless_id": tag["id"]}
    for corr in get_all_correspondents():
        key = _entity_key("corr", corr["id"])
        entities[key] = {
            "name": corr["name"],
            "type": "correspondent",
            "paperless_id": corr["id"],
        }
    for dt in get_all_document_types():
        key = _entity_key("doctype", dt["id"])
        entities[key] = {
            "name": dt["name"],
            "type": "document_type",
            "paperless_id": dt["id"],
        }
    return entities


def main() -> dict:
    base = os.environ["QDRANT_URL"].rstrip("/")

    with httpx.Client(timeout=120.0) as client:
        qdrant_keys = _get_qdrant_keys(client, base)

    paperless_entities = _fetch_paperless_entities()
    missing_keys = set(paperless_entities.keys()) - qdrant_keys

    if not missing_keys:
        return {
            "missing_count": 0,
            "restored_count": 0,
            "message": "Keine fehlenden Entities — Qdrant ist synchron mit Paperless.",
        }

    points = []
    for key in sorted(missing_keys):
        entity = paperless_entities[key]
        points.append({
            "id": _qdrant_point_id(key),
            "vector": ZERO_VECTOR,
            "payload": {
                "name": entity["name"],
                "type": entity["type"],
                "paperless_id": entity["paperless_id"],
                "description": "",
            },
        })

    print(f"[restore_missing] {len(points)} Entities fehlen in Qdrant — schreibe mit Nullvektor:")
    for p in points[:20]:
        print(f"  - {p['payload']['type']:15s} id={p['payload']['paperless_id']:3d}  {p['payload']['name']}")
    if len(points) > 20:
        print(f"  ... und {len(points) - 20} weitere")

    with httpx.Client(timeout=300.0) as client:
        r = client.put(
            f"{base}/collections/{COLLECTION}/points",
            json={"points": points},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Qdrant PUT failed: {r.status_code} {r.text}")
        r.raise_for_status()

    return {
        "missing_count": len(missing_keys),
        "restored_count": len(points),
        "vector_type": "zero (1024-dim)",
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False))
