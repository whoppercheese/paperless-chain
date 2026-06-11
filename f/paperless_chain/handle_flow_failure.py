from f.paperless_chain.shared.notify_client import notify
from f.paperless_chain.shared.paperless_client import add_document_tags

STATUS_TAG_ERROR = "AI-Error"


def main(error: dict | None = None, doc_id: int | None = None) -> dict:
    if not error:
        error = {}
    if isinstance(error, str):
        error = {"message": error}

    step_id = error.get("step_id", "unknown")
    name = error.get("name", "Error")
    message_text = error.get("message", str(error) if error else "Unbekannter Fehler")
    stack = error.get("stack", "")

    lines = [
        "Paperless-chAIn: Flow fehlgeschlagen!",
        f"Step: {step_id}",
        f"Fehler: {name}",
        f"Details: {message_text}",
    ]
    if doc_id is not None:
        lines.insert(1, f"Dokument-ID: {doc_id}")
    if stack:
        lines.append(f"Stack: {stack[:500]}")
    notification = "\n".join(lines)

    tag_result = None
    if doc_id is not None:
        try:
            tag_result = add_document_tags(doc_id, [STATUS_TAG_ERROR])
        except Exception as exc:
            print(f"=== Paperless-chAIn Paperless Tags (error) ===")
            print(f"doc_id: {doc_id}")
            print(f"failed to apply {STATUS_TAG_ERROR}: {exc}")

    mode = notify(notification, event="paperless_chain.flow_error", doc_id=doc_id)

    return {
        "doc_id": doc_id,
        "error": error,
        "applied_status_tag": STATUS_TAG_ERROR if doc_id is not None else None,
        "tag_result": tag_result,
        "notified": mode != "log",
        "mode": mode,
    }
