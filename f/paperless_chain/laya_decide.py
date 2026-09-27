import json
import os

import httpx

from f.paperless_chain.shared.prompts import build_laya_choice_instructions


def main(
    summary: str,
    entity_type: str,
    candidates: list[dict],
    doc_id: int,
) -> dict:
    url = os.environ["LAYA_URL"].rstrip("/")

    if entity_type == "tag":
        return {
            "error": "Tag-Decision wird über laya_decide_tags.py (noul-Loop) entschieden.",
        }

    if not candidates:
        return {
            "doc_id": doc_id,
            "entity_type": entity_type,
            "decision": None,
            "reasoning": "No candidates provided",
        }

    criteria = {c["name"]: c["description"] for c in candidates}
    criteria_list = "\n".join(f"- {n}: {d}" for n, d in criteria.items())

    try:
        instructions = build_laya_choice_instructions(entity_type, criteria_list)
    except ValueError as e:
        return {"error": str(e)}

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
        entity_type="document_type",
        doc_id=1,
        candidates=[
            {"name": "Rechnung", "description": "Rechnungen und Mahnungen"},
            {"name": "Vertrag", "description": "Verträge und Vereinbarungen"},
            {"name": "Sonstiges", "description": "Alles andere"},
        ],
    ))
