#requirements:
#httpx==0.27.2

import os
import uuid

import httpx

EMBED_DIM = 1024


def _ensure_collection(client: httpx.Client, base: str, collection: str) -> None:
    r = client.get(f"{base}/collections/{collection}")
    if r.status_code == 200:
        return
    create = client.put(f"{base}/collections/{collection}", json={
        "vectors": {"size": EMBED_DIM, "distance": "Cosine"},
    })
    create.raise_for_status()


def _delete_doc_points(client: httpx.Client, base: str, collection: str, doc_id: int) -> None:
    r = client.post(f"{base}/collections/{collection}/points/delete", json={
        "filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}
    })
    if r.status_code not in (200, 202):
        r.raise_for_status()


def main(embedded_chunks: list) -> dict:
    if not embedded_chunks:
        return {"stored": 0, "doc_id": None}

    base = os.environ["QDRANT_URL"].rstrip("/")
    collection = os.environ.get("QDRANT_COLLECTION", "paperless_chain_documents")
    doc_id = embedded_chunks[0]["payload"]["doc_id"]

    points = []
    for item in embedded_chunks:
        p = item["payload"]
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"paperless_chain:{p['doc_id']}:{p['chunk_index']}"))
        points.append({
            "id": point_id,
            "vector": item["vector"],
            "payload": p,
        })

    with httpx.Client(timeout=120.0) as client:
        _ensure_collection(client, base, collection)
        _delete_doc_points(client, base, collection, doc_id)
        r = client.put(f"{base}/collections/{collection}/points", json={"points": points})
        r.raise_for_status()

    return {"doc_id": doc_id, "stored": len(points), "collection": collection}
