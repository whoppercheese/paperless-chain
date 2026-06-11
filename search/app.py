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
) -> list[dict]:
    body: dict = {"query": vector, "limit": limit, "with_payload": True}
    if filters:
        must = []
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
    """Fetch distinct correspondents and tags from the collection via scroll."""
    correspondents: set[str] = set()
    tags: set[str] = set()

    offset = None
    while True:
        body: dict = {
            "limit": 100,
            "with_payload": {"include": ["correspondent", "tags"]},
            "with_vector": False,
        }
        if offset is not None:
            body["offset"] = offset

        r = await http.post(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/scroll",
            json=body,
        )
        if r.status_code != 200:
            break
        data = r.json().get("result", {})
        points = data.get("points", [])
        if not points:
            break
        for pt in points:
            p = pt.get("payload", {})
            if p.get("correspondent"):
                correspondents.add(p["correspondent"])
            for t in p.get("tags", []):
                tags.add(t)
        offset = data.get("next_page_offset")
        if offset is None:
            break

    return {
        "correspondents": sorted(correspondents),
        "tags": sorted(tags),
    }


async def _fetch_doc_titles(doc_ids: list[int]) -> dict[int, str]:
    if not doc_ids or not PAPERLESS_URL or not PAPERLESS_API_TOKEN:
        return {}
    headers = {"Authorization": f"Token {PAPERLESS_API_TOKEN}"}
    titles: dict[int, str] = {}
    for doc_id in doc_ids:
        try:
            r = await http.get(
                f"{PAPERLESS_URL}/api/documents/{doc_id}/",
                headers=headers,
            )
            if r.status_code == 200:
                titles[doc_id] = r.json().get("title", "")
        except httpx.HTTPError:
            continue
    return titles


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
    if correspondent:
        filters["correspondent"] = correspondent
    if tag:
        filters["tags"] = tag
    if chunk_kind:
        filters["chunk_kind"] = chunk_kind

    points = await _search_qdrant(vector, limit=limit, filters=filters)

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
                "correspondent": payload.get("correspondent", ""),
                "tags": payload.get("tags", []),
                "document_type": payload.get("document_type", ""),
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

    doc_titles = await _fetch_doc_titles([d for d in docs if d is not None])

    for doc in docs.values():
        doc["relevance"] = round(doc["best_score"] * 0.6 + (doc["score_sum"] / doc["count"]) * 0.4, 4)
        doc["chunks"].sort(key=lambda c: c["score"], reverse=True)
        doc["title"] = doc_titles.get(doc["doc_id"], "")

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
