import json


def build_summary_prompt(document_language: str) -> str:
    lang = document_language
    return f"""\
Du erstellst eine Zusammenfassung eines Dokuments für eine Dokumentenverwaltung (Paperless-ngx).
Die Dokumentsprache laut Paperless ist: {lang}.
Antworte als JSON.

SPRACHE (PFLICHT):
- summary MUSS vollständig in der Dokumentsprache ({lang}) verfasst sein.
- NIEMALS in einer anderen Sprache antworten — auch nicht teilweise.
- Eigennamen, Firmennamen und Beträge unverändert übernehmen.

INHALT:
Lies den gesamten Text und fasse ihn zusammen.
- summary: ausführliche Zusammenfassung auf {lang}, typischerweise 6-12 Sätze
- Enthalte zwingend: Zweck, Absender/Absendername, Dokumentart, alle genannten Daten (Rechnungs-, Brief-, Vertragsdatum etc.), Beträge, Fristen, Vertragsparteien, wichtige Konditionen
- Keine Floskeln, keine Einleitung wie "Dieses Dokument..."
- Die Summary muss alle Fakten enthalten, die später für Titel, Dokumenttyp, Korrespondent und Tags benötigt werden

DATUM:
Extrahiere das relevante Dokumentdatum direkt aus dem Volltext (nicht aus heutigem Datum raten).
- document_date: YYYY-MM-DD oder null
- Priorität: Rechnungsdatum > Briefdatum > Vertragsdatum > Auszugsdatum > andere im Dokument genannte Daten
- Nur setzen wenn ein konkretes Datum im Text steht; bei mehreren Kandidaten das relevanteste nach Priorität wählen

Antworte ausschließlich als JSON mit Feldern "summary" und "document_date". Keine Erklärungen außerhalb des JSON."""


def build_analyze_prompt(
    document_language: str,
    document_types: list[str],
    tags: list[str],
    correspondents: list[str],
    current_tags: list[str] | None = None,
) -> str:
    lang = document_language
    types_json = json.dumps(document_types, ensure_ascii=False)
    tags_json = json.dumps(tags, ensure_ascii=False)
    correspondents_json = json.dumps(correspondents, ensure_ascii=False)
    current = list(current_tags or [])
    current_tags_block = (
        f"AKTUELLE TAGS (bereits am Dokument — prüfen und bereinigen):\n"
        f"{json.dumps(current, ensure_ascii=False)}\n"
        f"- Prüfe jeden aktuellen Tag anhand der Summary\n"
        f"- Behalte passende Tags in selected_tags\n"
        f"- Entferne unpassende oder falsch zugewiesene Tags (nicht in selected_tags aufnehmen)\n"
        f"- Ergänze bei Bedarf weitere passende Tags aus VORHANDENE TAGS\n"
        f"- Bewerte nur Tags aus dieser Liste; erfinde keine neuen Namen\n\n"
        if current
        else ""
    )
    return f"""\
Du extrahierst Metadaten aus einer Dokumenten-Zusammenfassung für Paperless-ngx.
Die Dokumentsprache laut Paperless ist: {lang}.
Im User-Prompt erhältst du die Summary — nicht den Volltext.
Arbeite die folgenden Schritte der Reihe nach ab und antworte als ein einziges JSON-Objekt.

SPRACHE (PFLICHT):
- title MUSS vollständig in der Dokumentsprache ({lang}) verfasst sein.
- NIEMALS in einer anderen Sprache antworten — auch nicht teilweise.
- Eigennamen, Firmennamen und Beträge unverändert übernehmen.

VORHANDENE DOKUMENTTYPEN (NUR diese exakten Namen verwenden):
{types_json}

VORHANDENE KORRESPONDENTEN (NUR diese exakten Namen verwenden):
{correspondents_json}

VORHANDENE TAGS (NUR diese exakten Namen verwenden):
{tags_json}

{current_tags_block}SCHRITT 1: TITEL
Leite aus der Summary einen Titel ab.
- title: kurzer Titel auf {lang}, 3-12 Wörter (Wortgrenzen einhalten, niemals mitten im Wort abbrechen).
  Enthalte Absender (Kurzname), Dokumentart und Datum/Zeitraum.
  Keine Rechnungsnummern, vollständigen Firmennamen oder Adressen.

SCHRITT 2: DOKUMENTTYP
Ordne das Dokument einem Typ aus der obigen Liste zu.
- selected_document_type: exakter Name aus VORHANDENE DOKUMENTTYPEN, oder null wenn keiner passt
Regeln:
- NUR Namen aus VORHANDENE DOKUMENTTYPEN verwenden, NIEMALS neue Typen erfinden oder vorschlagen
- Bevorzuge vorhandene Typen auch bei ungefährer Übereinstimmung
- Rechtsformen, Groß-/Kleinschreibung und Umlaute sind beim Vergleich irrelevant

SCHRITT 3: KORRESPONDENT
Bestimme den Absender aus der obigen Korrespondenten-Liste.
- selected_correspondent: exakter Name aus VORHANDENE KORRESPONDENTEN, oder null wenn keiner passt
Regeln:
- NUR Namen aus VORHANDENE KORRESPONDENTEN verwenden, NIEMALS neue Korrespondenten erfinden oder vorschlagen
- Bevorzuge vorhandene Korrespondenten auch bei ungefährer Übereinstimmung
- Rechtsformen (GmbH, AG etc.), Titel (Dr., Prof.), Groß-/Kleinschreibung und Umlaute sind beim Vergleich irrelevant

SCHRITT 4: TAGS
Lege die finale Tag-Liste für das Dokument fest.
- selected_tags: Liste, NUR exakte Namen aus VORHANDENE TAGS — das ist die vollständige Ziel-Liste
Regeln:
- NUR Namen aus VORHANDENE TAGS verwenden, NIEMALS neue Tags erfinden oder vorschlagen
- Wenn AKTUELLE TAGS existieren: jeden einzeln prüfen; unpassende Tags weglassen, passende behalten
- Entferne Tags die thematisch nicht zum Dokument passen (z.B. falscher Absender, falsches Thema, veraltete Zuordnung)
- Ergänze bei Bedarf weitere passende Tags aus VORHANDENE TAGS (typisch 1-5)
- Ohne AKTUELLE TAGS: 1-5 passende Tags wählen; leere Liste nur wenn wirklich kein vorhandener Tag passt
- NIEMALS System-Tags vergeben oder in selected_tags aufnehmen: AI-Warning, AI-Error, AI-Processed
- Keine redundanten Tags (nicht mehrere für dasselbe Konzept)
- Vorhandene Personen-Tags wählen wenn Person im Dokument vorkommt
- Keine zu generischen ("Dokument") oder zu spezifischen ("Rechnung-2024-März") Tags

SCHRITT 5: WARNINGS
Sammle alle Warnings in einer einzigen Liste.
- warnings: Liste von Warn-Strings, leer wenn keine nötig
Erzeuge eine Warning für JEDE der folgenden Situationen:
- selected_document_type ist null: "Kein passender Dokumenttyp gefunden"
- selected_correspondent ist null: "Kein passender Korrespondent gefunden"
- selected_tags ist leer UND es gibt keine passenden AKTUELLE TAGS: "Keine passenden Tags gefunden"

JSON-AUSGABEFORMAT - verwende exakt diese Top-Level-Feldnamen (keine verschachtelten Schritte):
title, selected_document_type, selected_correspondent, selected_tags, warnings

Antworte ausschließlich als JSON mit diesen Feldern. Keine Erklärungen außerhalb des JSON."""


def build_chunk_prompt(document_language: str) -> str:
    lang = document_language
    return f"""\
Du teilst den Volltext eines Dokuments in semantische Such-Chunks auf.
Die Dokumentsprache laut Paperless ist: {lang}.
Antworte als JSON.

Regeln:
- chunks: Liste von Abschnitten mit "text" und "label"
- text: vollständiger Abschnittstext aus dem Dokument (keine Kürzung, keine Auslassungen mit "...")
- label: kurze Beschreibung auf {lang} (2-6 Wörter), z.B. Rechnungspositionen, Kündigungsfrist
- Bevorzuge wenige, größere Chunks statt vieler kleiner — zusammengehörige Inhalte in einem Chunk belassen
- Teile nur bei klar getrennten Themen (z.B. Vertragskern vs. Anlagen, Rechnungskopf vs. AGB)
- Kleine Absätze, Einleitungen oder Detailblöcke nicht einzeln abtrennen, wenn sie zum gleichen Thema gehören
- Tabellen und zugehörige Erläuterungen zusammen in einem Chunk belassen
- Teile nach inhaltlicher Logik, nicht nach Zeichen-, Token- oder Seitengrenzen
- Jeder Chunk soll für sich in einer Vektorsuche sinnvoll und ausreichend substanziell sein
- Keine Überschneidungen zwischen Chunks
- Zusammen sollen die Chunks den relevanten Dokumentinhalt abdecken
- Boilerplate (AGB, Datenschutz, Impressum) in einen Chunk bündeln
- Erzeuge KEINE Zusammenfassung — die wird separat gespeichert
- Mindestens 1 Chunk; kurze Dokumente oft in 1 Chunk, längere typischerweise in 2-5 Chunks (nur mehr wenn klar getrennte Hauptthemen)

Antworte ausschließlich als JSON mit Feld "chunks"."""


SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "document_date": {"type": ["string", "null"]},
    },
    "required": ["summary"],
}

ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "selected_document_type": {"type": ["string", "null"]},
        "selected_correspondent": {"type": ["string", "null"]},
        "selected_tags": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "title",
        "selected_tags",
        "warnings",
    ],
}

CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "chunks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["text", "label"],
            },
        },
    },
    "required": ["chunks"],
}
