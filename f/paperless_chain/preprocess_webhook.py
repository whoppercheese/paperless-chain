def preprocessor(event):
    if event.get("kind") != "webhook":
        raise ValueError(f"Unsupported trigger kind: {event.get('kind')}")

    body = event.get("body") or {}
    doc_url = body.get("doc_url", "")
    if not doc_url:
        raise ValueError("Missing doc_url in webhook payload")

    parts = [part for part in doc_url.strip("/").split("/") if part]
    if "documents" not in parts:
        raise ValueError(f"Could not parse doc_id from doc_url: {doc_url}")

    doc_index = parts.index("documents")
    doc_id = int(parts[doc_index + 1])
    return {"doc_id": doc_id}
