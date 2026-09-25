import os

from f.paperless_chain.shared.paperless_client import (
    add_document_tags,
    get_all_correspondents,
    get_all_document_types,
)


def main(
    doc_id: int,
    entity_type: str,
    selected: list[dict],
    candidates: list[dict],
) -> dict:
    min_confidence = float(os.environ.get("LAYA_MIN_CONFIDENCE", 0.8))

    if not selected:
        return {
            "doc_id": doc_id,
            "entity_type": entity_type,
            "accepted": [],
            "rejected": [],
            "warnings": ["Keine Auswahl von Laya"],
        }

    candidate_map = {c["name"]: c for c in candidates}

    accepted = []
    rejected = []

    for item in selected:
        name = item["name"]
        confidence = item.get("confidence", 1.0)

        candidate = candidate_map.get(name)
        if not candidate:
            rejected.append({
                "name": name,
                "reason": "nicht in Kandidatenliste",
            })
            continue

        if confidence < min_confidence:
            rejected.append({
                "name": name,
                "confidence": confidence,
                "reason": f"confidence {confidence} < min {min_confidence}",
            })
            continue

        accepted.append({
            "name": name,
            "confidence": confidence,
            "paperless_id": candidate.get("paperless_id"),
        })

    warnings = []
    if rejected:
        warnings.append(f"{len(rejected)} {entity_type}(s) abgelehnt")

    return {
        "doc_id": doc_id,
        "entity_type": entity_type,
        "accepted": accepted,
        "rejected": rejected,
        "warnings": warnings,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(main(
        doc_id=1,
        entity_type="tag",
        selected=[
            {"name": "Rechnung", "confidence": 0.9},
            {"name": "Wichtig", "confidence": 0.85},
            {"name": "Unbekannt", "confidence": 0.3},
        ],
        candidates=[
            {"name": "Rechnung", "paperless_id": 1},
            {"name": "Wichtig", "paperless_id": 2},
            {"name": "Bezahlt", "paperless_id": 3},
        ],
    ), indent=2))
