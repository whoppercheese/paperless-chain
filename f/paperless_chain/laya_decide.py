import json
import os

import httpx


def main(
    summary: str,
    entity_type: str,
    candidates: list[dict],
    doc_id: int,
) -> dict:
    url = os.environ["LAYA_URL"].rstrip("/")

    if not candidates:
        return {
            "doc_id": doc_id,
            "entity_type": entity_type,
            "decision": None,
            "reasoning": "No candidates provided",
        }

    criteria = {}
    for c in candidates:
        criteria[c["name"]] = c["description"]

    if entity_type == "tag":
        instructions = "Welche Tags passen zum Dokument? Bewerte jeden Tag."
        question_type = "score"
    elif entity_type == "correspondent":
        instructions = "Welcher Korrespondent passt zum Dokument?"
        question_type = "score"
    elif entity_type == "document_type":
        instructions = "Welcher Dokumenttyp passt zum Dokument?"
        question_type = "score"
    else:
        return {"error": f"Unknown entity_type: {entity_type}"}

    questions = {
        "decision": {
            "type": question_type,
            "instructions": instructions,
            "criteria": criteria,
        }
    }

    payload = {
        "context": summary,
        "questions": questions,
    }

    print("=== Laya Request ===")
    print(f"url: {url}/decide")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{url}/decide", json=payload)
        r.raise_for_status()
        response = r.json()

    print("=== Laya Response ===")
    print(json.dumps(response, ensure_ascii=False, indent=2))

    decision_raw = response.get("decision")

    if entity_type == "tag":
        if isinstance(decision_raw, dict):
            selected = []
            for name, conf in decision_raw.items():
                if conf and conf > 0:
                    selected.append({"name": name, "confidence": conf})
        elif isinstance(decision_raw, list):
            selected = [{"name": s, "confidence": 1.0} for s in decision_raw if s]
        elif isinstance(decision_raw, str):
            selected = [{"name": s.strip(), "confidence": 1.0} for s in decision_raw.split(",") if s.strip()]
        else:
            selected = []
    else:
        if isinstance(decision_raw, dict):
            selected = []
            for name, conf in decision_raw.items():
                if conf and conf > 0:
                    selected.append({"name": name, "confidence": conf})
        elif isinstance(decision_raw, str) and decision_raw.strip():
            selected = [{"name": decision_raw.strip(), "confidence": 1.0}]
        else:
            selected = []

    result = {
        "doc_id": doc_id,
        "entity_type": entity_type,
        "selected": selected,
        "raw_response": decision_raw,
        "candidates": candidates,
    }

    return result


if __name__ == "__main__":
    print(main(
        summary="Rechnung von Amazon über 99,99 EUR für电子产品",
        entity_type="tag",
        doc_id=1,
        candidates=[
            {"name": "Rechnung", "description": "Für Rechnungen und Mahnungen"},
            {"name": "Versicherung", "description": "Für Versicherungsdokumente"},
            {"name": "Vertrag", "description": "Für Verträge und Vereinbarungen"},
            {"name": "Wichtig", "description": "Für wichtige Dokumente"},
            {"name": "Bezahlt", "description": "Für bezahlte Dokumente"},
        ],
    ))
