#requirements:
#httpx==0.27.2

import hashlib
import hmac
import json
import os
import uuid

import httpx


def send_hermes(message: str, event: str = "paperless_chain.document_processed", doc_id: int | None = None) -> None:
    webhook_url = os.environ.get("HERMES_WEBHOOK_URL", "")
    secret = os.environ.get("HERMES_WEBHOOK_SECRET", "")
    if not webhook_url or not secret:
        raise ValueError("HERMES_WEBHOOK_URL and HERMES_WEBHOOK_SECRET must be set")

    payload = {"event": event, "message": message}
    if doc_id is not None:
        payload["doc_id"] = doc_id
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    with httpx.Client(timeout=30.0) as client:
        r = client.post(webhook_url, content=body, headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        })
        r.raise_for_status()


def send_matrix(message: str) -> None:
    homeserver = os.environ.get("MATRIX_HOMESERVER", "").rstrip("/")
    token = os.environ.get("MATRIX_ACCESS_TOKEN", "")
    room_id = os.environ.get("MATRIX_ROOM_ID", "")
    if not (homeserver and token and room_id):
        raise ValueError("MATRIX_HOMESERVER, MATRIX_ACCESS_TOKEN and MATRIX_ROOM_ID must be set")

    txn = str(uuid.uuid4())
    url = f"{homeserver}/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn}"
    with httpx.Client(timeout=30.0) as client:
        r = client.put(url, json={"msgtype": "m.text", "body": message},
                       headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()


def notify(message: str, event: str = "paperless_chain.document_processed", doc_id: int | None = None) -> str:
    mode = os.environ.get("NOTIFY_MODE", "log").lower()
    if mode == "hermes":
        send_hermes(message, event=event, doc_id=doc_id)
    elif mode == "matrix":
        send_matrix(message)
    else:
        print(message)
    return mode
