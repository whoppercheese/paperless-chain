import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

QDRANT_URL = ""
QDRANT_COLLECTION = ""
OLLAMA_URL = ""
OLLAMA_EMBED_MODEL = ""
PAPERLESS_URL = ""
PAPERLESS_API_TOKEN = ""

http: httpx.AsyncClient

SYSTEM_TAG_NAMES = frozenset({
    "ai-warning",
    "ai-error",
    "ai-processed",
    "ai-embedded",
})


def _content_tag_names(names: list[str]) -> list[str]:
    return [name for name in names if name.strip().lower() not in SYSTEM_TAG_NAMES]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global QDRANT_URL, QDRANT_COLLECTION, OLLAMA_URL, OLLAMA_EMBED_MODEL, PAPERLESS_URL, PAPERLESS_API_TOKEN, http
    QDRANT_URL = os.environ["QDRANT_URL"].rstrip("/")
    QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "paperless_chain_documents")
    OLLAMA_URL = os.environ["OLLAMA_URL"].rstrip("/")
    OLLAMA_EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3")
    PAPERLESS_URL = os.environ.get("PAPERLESS_URL", "").rstrip("/")
    PAPERLESS_API_TOKEN = os.environ.get("PAPERLESS_API_TOKEN", "")
    http = httpx.AsyncClient(timeout=120.0)
    yield
    await http.aclose()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def _paperless_headers() -> dict:
    return {"Authorization": f"Token {PAPERLESS_API_TOKEN}"}


async def _paperless_paginate(path: str, params: dict | None = None) -> list[dict]:
    if not PAPERLESS_URL or not PAPERLESS_API_TOKEN:
        return []

    results: list[dict] = []
    page = 1
    while True:
        query = {"page": page, "page_size": 100, **(params or {})}
        r = await http.get(
            f"{PAPERLESS_URL}{path}",
            headers=_paperless_headers(),
            params=query,
        )
        if r.status_code != 200:
            break
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("next"):
            break
        page += 1
    return results


async def _embed(text: str) -> list[float]:
    r = await http.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": OLLAMA_EMBED_MODEL, "input": [text]},
    )
    r.raise_for_status()
    data = r.json()
    vecs = data.get("embeddings") or [data["embedding"]]
    return vecs[0]


async def _search_qdrant(
    vector: list[float],
    limit: int = 20,
    filters: dict | None = None,
    doc_ids: list[int] | None = None,
) -> list[dict]:
    body: dict = {"query": vector, "limit": limit, "with_payload": True}
    must = []
    if doc_ids is not None:
        if not doc_ids:
            return []
        must.append({"key": "doc_id", "match": {"any": doc_ids}})
    if filters:
        for key, value in filters.items():
            if value:
                must.append({"key": key, "match": {"value": value}})
    if must:
        body["filter"] = {"must": must}

    r = await http.post(
        f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/query",
        json=body,
    )
    r.raise_for_status()
    return r.json().get("result", {}).get("points", [])


async def _get_filter_values() -> dict:
    correspondents = await _paperless_paginate("/api/correspondents/")
    tags = await _paperless_paginate("/api/tags/")
    return {
        "correspondents": sorted(c["name"] for c in correspondents),
        "tags": sorted(t["name"] for t in tags),
    }


async def _filter_doc_ids(correspondent: str, tag: str) -> list[int] | None:
    if not correspondent and not tag:
        return None
    if not PAPERLESS_URL or not PAPERLESS_API_TOKEN:
        return []

    params: dict = {}
    if correspondent:
        correspondents = await _paperless_paginate("/api/correspondents/")
        corr_id = next((c["id"] for c in correspondents if c["name"] == correspondent), None)
        if corr_id is None:
            return []
        params["correspondent__id"] = corr_id
    if tag:
        tags = await _paperless_paginate("/api/tags/")
        tag_id = next((t["id"] for t in tags if t["name"] == tag), None)
        if tag_id is None:
            return []
        params["tags__id__all"] = tag_id

    documents = await _paperless_paginate("/api/documents/", params)
    return [doc["id"] for doc in documents]


async def _fetch_doc_metadata(doc_ids: list[int]) -> dict[int, dict]:
    if not doc_ids or not PAPERLESS_URL or not PAPERLESS_API_TOKEN:
        return {}

    tags = await _paperless_paginate("/api/tags/")
    correspondents = await _paperless_paginate("/api/correspondents/")
    document_types = await _paperless_paginate("/api/document_types/")

    tag_id_to_name = {t["id"]: t["name"] for t in tags}
    corr_id_to_name = {c["id"]: c["name"] for c in correspondents}
    dtype_id_to_name = {d["id"]: d["name"] for d in document_types}

    metadata: dict[int, dict] = {}
    headers = _paperless_headers()
    for doc_id in doc_ids:
        try:
            r = await http.get(
                f"{PAPERLESS_URL}/api/documents/{doc_id}/",
                headers=headers,
            )
            if r.status_code != 200:
                continue
            doc = r.json()
            metadata[doc_id] = {
                "title": doc.get("title", ""),
                "tags": _content_tag_names([
                    tag_id_to_name[tag_id]
                    for tag_id in doc.get("tags", [])
                    if tag_id in tag_id_to_name
                ]),
                "correspondent": corr_id_to_name.get(doc.get("correspondent"), ""),
                "document_type": dtype_id_to_name.get(doc.get("document_type"), ""),
            }
        except httpx.HTTPError:
            continue
    return metadata


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    filter_values = await _get_filter_values()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "paperless_url": PAPERLESS_URL,
            **filter_values,
        },
    )


@app.post("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    query: str = Form(""),
    correspondent: str = Form(""),
    tag: str = Form(""),
    chunk_kind: str = Form(""),
    limit: int = Form(20),
):
    query = query.strip()
    if not query:
        return HTMLResponse("")

    vector = await _embed(query)

    filters: dict = {}
    if chunk_kind:
        filters["chunk_kind"] = chunk_kind

    doc_ids = await _filter_doc_ids(correspondent, tag)
    points = await _search_qdrant(vector, limit=limit, filters=filters, doc_ids=doc_ids)

    docs: dict[int, dict] = {}
    for pt in points:
        payload = pt.get("payload", {})
        score = pt.get("score", 0.0)
        doc_id = payload.get("doc_id")

        chunk = {
            "score": score,
            "text": payload.get("text", ""),
            "chunk_kind": payload.get("chunk_kind", ""),
            "label": payload.get("label", ""),
        }

        if doc_id not in docs:
            docs[doc_id] = {
                "doc_id": doc_id,
                "chunks": [],
                "best_score": score,
                "score_sum": score,
                "count": 0,
            }

        doc = docs[doc_id]
        doc["chunks"].append(chunk)
        doc["count"] += 1
        doc["score_sum"] += score
        if score > doc["best_score"]:
            doc["best_score"] = score

    doc_metadata = await _fetch_doc_metadata([d for d in docs if d is not None])

    for doc in docs.values():
        doc["relevance"] = round(doc["best_score"] * 0.6 + (doc["score_sum"] / doc["count"]) * 0.4, 4)
        doc["chunks"].sort(key=lambda c: c["score"], reverse=True)
        meta = doc_metadata.get(doc["doc_id"], {})
        doc["title"] = meta.get("title", "")
        doc["correspondent"] = meta.get("correspondent", "")
        doc["tags"] = meta.get("tags", [])
        doc["document_type"] = meta.get("document_type", "")

    grouped = sorted(docs.values(), key=lambda d: d["relevance"], reverse=True)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "documents": grouped,
            "query": query,
            "paperless_url": PAPERLESS_URL,
        },
    )
