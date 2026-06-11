def preprocessor(event):
    if event.get("kind") != "webhook":
        raise ValueError(f"Unsupported trigger kind: {event.get('kind')}")

    body = event.get("body") or {}

    doc_id = body.get("doc_id")
    if doc_id is not None and str(doc_id).strip() != "":
        return {"doc_id": int(doc_id)}

    doc_url = body.get("doc_url", "")
    if not doc_url:
        raise ValueError("Missing doc_url or doc_id in webhook payload")

    parts = [part for part in doc_url.strip("/").split("/") if part]
    if "documents" not in parts:
        raise ValueError(f"Could not parse doc_id from doc_url: {doc_url}")

    doc_index = parts.index("documents")
    return {"doc_id": int(parts[doc_index + 1])}
