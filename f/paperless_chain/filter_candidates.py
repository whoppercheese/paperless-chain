import json
import os
import sys

import httpx

from f.paperless_chain.shared.llm_client import embed_texts

COLLECTION = "entity_embeddings"


def main(
    summary: str,
    entity_type: str,
    top_k: int | None = None,
    min_score: float | None = None,
) -> dict:
    top_k = top_k or int(os.environ.get("ENTITY_TOP_K", 5))
    min_score = min_score or float(os.environ.get("ENTITY_MIN_SCORE", 0.7))

    base = os.environ["QDRANT_URL"].rstrip("/")

    vectors = embed_texts([summary])
    query_vector = vectors[0]

    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            f"{base}/collections/{COLLECTION}/points/search",
            json={
                "vector": query_vector,
                "filter": {"must": [{"key": "type", "match": {"value": entity_type}}]},
                "limit": top_k,
                "score_threshold": min_score,
            },
        )
        r.raise_for_status()
        results = r.json().get("result", [])

    candidates = []
    for item in results:
        payload = item.get("payload") or {}
        if not payload:
            continue
        candidates.append({
            "id": item["id"],
            "name": payload.get("name", ""),
            "type": payload.get("type", ""),
            "paperless_id": payload.get("paperless_id"),
            "description": payload.get("description", ""),
            "score": item.get("score", 0.0),
        })

    print(
        f"[filter_candidates] entity_type={entity_type} count={len(candidates)} top_k={top_k} min_score={min_score}",
        file=sys.stderr,
        flush=True,
    )
    for c in candidates:
        print(
            f"[filter_candidates]   - name={c['name']!r} score={c['score']:.4f} description={c['description']!r}",
            file=sys.stderr,
            flush=True,
        )

    return {
        "entity_type": entity_type,
        "candidates": candidates,
        "count": len(candidates),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(main(
        summary="Rechnung von Amazon über 99,99 EUR für电子产品",
        entity_type="tag",
    ), indent=2))
