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

    criteria = {c["name"]: c["description"] for c in candidates}
    criteria_list = "\n".join(f"- {n}: {d}" for n, d in criteria.items())

    if entity_type == "tag":
        instructions = (
            "Welche Tags passen zum Dokument? Wähle den am besten passenden "
            "Tag aus den Kandidaten. Es kann nur EIN Tag gewählt werden.\n"
            f"Kandidaten:\n{criteria_list}"
        )
    elif entity_type == "correspondent":
        instructions = (
            "Welcher Korrespondent passt zum Dokument? Wähle einen aus den "
            f"Kandidaten.\nKandidaten:\n{criteria_list}"
        )
    elif entity_type == "document_type":
        instructions = (
            "Welcher Dokumenttyp passt zum Dokument? Wähle einen aus den "
            f"Kandidaten.\nKandidaten:\n{criteria_list}"
        )
    else:
        return {"error": f"Unknown entity_type: {entity_type}"}

    questions = {
        "decision": {
            "type": "choice",
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

    answers = response.get("answers", {})
    decision = answers.get("decision", {})
    probabilities = decision.get("probabilities", {}) or {}

    if entity_type == "tag":
        selected = sorted(
            ({"name": n, "confidence": c} for n, c in probabilities.items() if c and c > 0),
            key=lambda x: x["confidence"],
            reverse=True,
        )
    else:
        choice_name = decision.get("choice")
        confidence = probabilities.get(choice_name, 0.0) if choice_name else 0.0
        if choice_name and confidence > 0:
            selected = [{"name": choice_name, "confidence": confidence}]
        else:
            selected = []

    result = {
        "doc_id": doc_id,
        "entity_type": entity_type,
        "selected": selected,
        "raw_response": probabilities,
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
