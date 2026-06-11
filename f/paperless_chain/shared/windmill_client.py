import json
import os

import httpx

PROCESS_DOCUMENT_FLOW = "f/paperless_chain/process_document"


def _resolve_windmill_credentials() -> tuple[str | None, str | None, str | None]:
    base = (
        os.environ.get("WMILL_BASE_URL")
        or os.environ.get("WINDMILL_BASE_URL")
        or os.environ.get("BASE_INTERNAL_URL")
        or os.environ.get("WM_BASE_URL")
    )
    workspace = os.environ.get("WMILL_WORKSPACE") or os.environ.get("WM_WORKSPACE")
    token = os.environ.get("WMILL_TOKEN") or os.environ.get("WM_TOKEN")
    return base, workspace, token


def run_process_document_async(doc_id: int) -> str:
    """Queue process_document flow for a Paperless doc_id. Returns Windmill job id."""
    try:
        import wmill

        return wmill.run_flow_async(
            PROCESS_DOCUMENT_FLOW,
            args={"doc_id": doc_id},
        )
    except ImportError:
        return _run_process_document_http(doc_id)


def _run_process_document_http(doc_id: int) -> str:
    base, workspace, token = _resolve_windmill_credentials()
    missing = [
        name
        for name, value in [
            (
                "WMILL_BASE_URL, WINDMILL_BASE_URL, BASE_INTERNAL_URL, or WM_BASE_URL",
                base,
            ),
            ("WMILL_WORKSPACE or WM_WORKSPACE", workspace),
            ("WMILL_TOKEN or WM_TOKEN", token),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            "wmill module not available and missing env for HTTP fallback: "
            + ", ".join(missing)
        )

    # wmill client uses /jobs/run/f/{path}; path already includes the f/ prefix.
    url = f"{base.rstrip('/')}/api/w/{workspace}/jobs/run/f/{PROCESS_DOCUMENT_FLOW}"
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"doc_id": doc_id},
        )
        response.raise_for_status()
        body = response.text.strip()
    if not body:
        raise RuntimeError("Windmill returned empty job id")
    if body.startswith("{"):
        data = json.loads(body)
        if isinstance(data, str):
            return data
        return str(data.get("id") or data.get("job_id") or data)
    return body
