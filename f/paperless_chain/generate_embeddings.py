from f.paperless_chain.shared.llm_client import embed_texts


def main(chunks: list) -> dict:
    texts = [chunk["text"] for chunk in chunks]
    if not texts:
        return {"doc_id": None, "embedded_chunks": [], "count": 0}

    vectors = embed_texts(texts)

    embedded = []
    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        embedded.append({
            "vector": vector,
            "payload": {
                "doc_id": chunk["doc_id"],
                "chunk_index": index,
                "chunk_kind": chunk["chunk_kind"],
                "label": chunk.get("label", ""),
                "text": chunk["text"],
            },
        })

    return {
        "doc_id": chunks[0]["doc_id"] if chunks else None,
        "embedded_chunks": embedded,
        "count": len(embedded),
    }
