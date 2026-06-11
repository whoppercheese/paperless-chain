#requirements:
#httpx==0.27.2

import json
import os

import httpx


def _headers() -> dict:
    return {"Authorization": f"Token {os.environ['PAPERLESS_API_TOKEN']}"}


def _base_url() -> str:
    return os.environ["PAPERLESS_URL"].rstrip("/")


def get(path: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=120.0) as client:
        r = client.get(f"{_base_url()}{path}", headers=_headers(), params=params)
        r.raise_for_status()
        return r.json()


def post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{_base_url()}{path}", headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()


def _log_patch_request(path: str, payload: dict) -> None:
    print("=== Paperless-chAIn Paperless PATCH ===")
    print(f"url: {_base_url()}{path}")
    print("--- payload ---")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _log_patch_response(response: dict) -> None:
    print("=== Paperless-chAIn Paperless PATCH Response ===")
    print(json.dumps(response, ensure_ascii=False, indent=2))


def patch(path: str, payload: dict) -> dict:
    _log_patch_request(path, payload)
    with httpx.Client(timeout=120.0) as client:
        r = client.patch(f"{_base_url()}{path}", headers=_headers(), json=payload)
        r.raise_for_status()
        response = r.json()
    _log_patch_response(response)
    return response


def paginate(path: str) -> list[dict]:
    results: list[dict] = []
    page = 1
    while True:
        data = get(path, params={"page": page, "page_size": 100})
        results.extend(data.get("results", []))
        if not data.get("next"):
            break
        page += 1
    return results


def get_document_tag_names(doc_id: int) -> list[str]:
    document = get(f"/api/documents/{doc_id}/")
    tag_id_to_name = {t["id"]: t["name"] for t in paginate("/api/tags/")}
    return [
        tag_id_to_name[tag_id]
        for tag_id in document.get("tags", [])
        if tag_id in tag_id_to_name
    ]


def add_document_tags(doc_id: int, tag_names: list[str]) -> dict:
    if not tag_names:
        return {
            "doc_id": doc_id,
            "added_tag_names": [],
            "missing_tag_names": [],
            "skipped": True,
        }

    all_tags = paginate("/api/tags/")
    tag_name_to_id = {t["name"].lower(): t["id"] for t in all_tags}
    tag_id_to_name = {t["id"]: t["name"] for t in all_tags}
    document = get(f"/api/documents/{doc_id}/")
    tag_ids = list(document.get("tags") or [])
    known_ids = set(tag_ids)
    added_names: list[str] = []
    missing_names: list[str] = []
    changed = False

    for name in tag_names:
        tag_id = tag_name_to_id.get(name.lower())
        if tag_id is None:
            missing_names.append(name)
            continue
        if tag_id not in known_ids:
            tag_ids.append(tag_id)
            known_ids.add(tag_id)
            added_names.append(tag_id_to_name.get(tag_id, name))
            changed = True

    updated = None
    if changed:
        updated = patch(f"/api/documents/{doc_id}/", {"tags": tag_ids})

    if missing_names:
        print(f"=== Paperless-chAIn Paperless Tags (missing) ===")
        print(f"doc_id: {doc_id}")
        print(f"missing tag names: {missing_names}")

    return {
        "doc_id": doc_id,
        "added_tag_names": added_names,
        "missing_tag_names": missing_names,
        "tag_ids": tag_ids,
        "paperless_document": updated,
        "skipped": not changed,
    }
