import json
import os

import httpx

from f.paperless_chain.shared.prompts import (
    build_laya_tag_noul_instructions,
)

YES_THRESHOLD = 0.5


def _ask_laya_tag_choice(
    client: httpx.Client,
    url: str,
    summary: str,
    tag_name: str,
    tag_description: str,
) -> tuple[str, float]:
    payload = {
        "context": summary,
        "questions": {
            "decision": {
                "type": "noul",
                "instructions": build_laya_tag_noul_instructions(tag_name, tag_description),
            }
        },
    }

    print(f"=== Laya tag-noul Request: tag='{tag_name}' ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    r = client.post(f"{url}/decide", json=payload)
    r.raise_for_status()
    response = r.json()

    print(f"=== Laya tag-noul Response: tag='{tag_name}' ===")
    print(json.dumps(response, ensure_ascii=False, indent=2))

    decision = response.get("answers", {}).get("decision", {}) or {}
    noul = decision.get("noul")
    answer_confidence = float(decision.get("answer_confidence", 0.0) or 0.0)
    if noul is None:
        return "", answer_confidence
    return ("yes" if noul >= 0.5 else "no"), answer_confidence


def main(
    summary: str,
    candidates: list[dict],
    doc_id: int,
) -> dict:
    url = os.environ["LAYA_URL"].rstrip("/")

    if not candidates:
        return {
            "doc_id": doc_id,
            "entity_type": "tag",
            "selected": [],
            "raw_response": {},
            "candidates": [],
            "warnings": ["Keine Tag-Kandidaten vorhanden"],
        }

    raw_response: dict[str, dict] = {}
    warnings: list[str] = []

    with httpx.Client(timeout=120.0) as client:
        for candidate in candidates:
            name = candidate.get("name")
            if not name:
                continue
            description = candidate.get("description", "")
            try:
                choice, confidence = _ask_laya_tag_choice(
                    client=client,
                    url=url,
                    summary=summary,
                    tag_name=name,
                    tag_description=description,
                )
            except Exception as e:
                warnings.append(f"Laya-Aufruf für Tag '{name}' fehlgeschlagen: {e}")
                choice, confidence = "", 0.0
            raw_response[name] = {"choice": choice, "answer_confidence": confidence}

    selected = sorted(
        (
            {"name": n, "confidence": raw_response[n]["answer_confidence"]}
            for n in raw_response
            if raw_response[n]["choice"] == "yes"
            and raw_response[n]["answer_confidence"] >= YES_THRESHOLD
        ),
        key=lambda x: x["confidence"],
        reverse=True,
    )

    return {
        "doc_id": doc_id,
        "entity_type": "tag",
        "selected": selected,
        "raw_response": raw_response,
        "candidates": candidates,
        "warnings": warnings,
    }


if __name__ == "__main__":
    import sys

    laya_url = os.environ.get("LAYA_URL", "http://localhost:8000")
    os.environ["LAYA_URL"] = laya_url

    print(json.dumps(main(
        summary="Rechnung von Amazon über 99,99 EUR für einen Bluetooth-Lautsprecher.",
        doc_id=1,
        candidates=[
            {"name": "Rechnung", "description": "Rechnungen und Mahnungen", "paperless_id": 1},
            {"name": "Versicherung", "description": "Versicherungsdokumente", "paperless_id": 2},
            {"name": "Vertrag", "description": "Verträge und Vereinbarungen", "paperless_id": 3},
            {"name": "Wichtig", "description": "Wichtige Dokumente", "paperless_id": 4},
            {"name": "Bezahlt", "description": "Bezahlte Dokumente", "paperless_id": 5},
        ],
    ), indent=2, ensure_ascii=False))