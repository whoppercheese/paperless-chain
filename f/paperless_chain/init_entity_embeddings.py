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


def _ensure_collection(client: httpx.Client, base: str) -> None:
    r = client.get(f"{base}/collections/{COLLECTION}")
    if r.status_code == 200:
        return
    create = client.put(f"{base}/collections/{COLLECTION}", json={
        "vectors": {"size": EMBED_DIM, "distance": "Cosine"},
    })
    create.raise_for_status()


def _build_entity_id(entity_type: str, paperless_id: int) -> str:
    return f"{entity_type}_{paperless_id}"


def main() -> dict:
    base = os.environ["QDRANT_URL"].rstrip("/")

    all_tags = get_all_tags()
    all_correspondents = get_all_correspondents()
    all_types = get_all_document_types()

    entities = []

    for tag in all_tags:
        entities.append({
            "id": _build_entity_id("tag", tag["id"]),
            "name": tag["name"],
            "type": "tag",
            "paperless_id": tag["id"],
        })

    for corr in all_correspondents:
        entities.append({
            "id": _build_entity_id("corr", corr["id"]),
            "name": corr["name"],
            "type": "correspondent",
            "paperless_id": corr["id"],
        })

    for dt in all_types:
        entities.append({
            "id": _build_entity_id("doctype", dt["id"]),
            "name": dt["name"],
            "type": "document_type",
            "paperless_id": dt["id"],
        })

    if not entities:
        return {"initialized": 0, "message": "No entities found in Paperless"}

    descriptions = [""] * len(entities)
    ids = [entity["id"] for entity in entities]

    vectors = embed_texts(descriptions)

    points = []
    for i, entity in enumerate(entities):
        points.append({
            "id": ids[i],
            "vector": vectors[i],
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
        r.raise_for_status()

    return {
        "initialized": len(points),
        "tags": len(all_tags),
        "correspondents": len(all_correspondents),
        "document_types": len(all_types),
    }


if __name__ == "__main__":
    print(main())
