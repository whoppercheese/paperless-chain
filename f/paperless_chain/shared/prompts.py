import json


SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "document_date": {"type": ["string", "null"]},
    },
    "required": ["summary"],
}

TITLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
    },
    "required": ["title"],
}

DOCUMENT_TYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string"},
    },
    "required": ["document_type"],
}

CORRESPONDENT_SCHEMA = {
    "type": "object",
    "properties": {
        "correspondent": {"type": "string"},
    },
    "required": ["correspondent"],
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


def _json_schema_instruction(schema: dict) -> str:
    schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
    return f"""\
JSON-SCHEMA (PFLICHT — exakt dieses Format einhalten):
{schema_json}

- Alle required-Felder müssen vorhanden sein
- Keine zusätzlichen Top-Level-Felder
- Feldtypen und verschachtelte Struktur exakt wie im Schema
- Antworte ausschließlich als JSON gemäß Schema. Keine Erklärungen außerhalb des JSON."""


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
- Die Summary muss alle Fakten enthalten, die später für Titel, Dokumenttyp und Korrespondent benötigt werden

DATUM:
Extrahiere das relevante Dokumentdatum direkt aus dem Volltext (nicht aus heutigem Datum raten).
- document_date: YYYY-MM-DD oder null
- Priorität: Rechnungsdatum > Briefdatum > Vertragsdatum > Auszugsdatum > andere im Dokument genannte Daten
- Nur setzen wenn ein konkretes Datum im Text steht; bei mehreren Kandidaten das relevanteste nach Priorität wählen

{_json_schema_instruction(SUMMARY_SCHEMA)}"""


def build_derive_title_prompt(document_language: str) -> str:
    lang = document_language
    return f"""\
Du leitest einen Titel aus einer Dokumenten-Zusammenfassung für Paperless-ngx ab.
Die Dokumentsprache laut Paperless ist: {lang}.
Im User-Prompt erhältst du nur die Summary — nicht den Volltext.
Antworte als JSON.

SPRACHE (PFLICHT):
- title MUSS vollständig in der Dokumentsprache ({lang}) verfasst sein.
- NIEMALS in einer anderen Sprache antworten — auch nicht teilweise.
- Eigennamen, Firmennamen und Beträge unverändert übernehmen.

TITEL:
- title: kurzer Titel auf {lang}, 3-12 Wörter (Wortgrenzen einhalten, niemals mitten im Wort abbrechen)
- Enthalte Absender (Kurzname) und Dokumentart
- Keine Rechnungsnummern, vollständigen Firmennamen oder Adressen

{_json_schema_instruction(TITLE_SCHEMA)}"""


def build_resolve_document_type_prompt(document_language: str) -> str:
    lang = document_language
    return f"""\
Du bestimmst den Dokumenttyp für ein Dokument in Paperless-ngx.
Die Dokumentsprache laut Paperless ist: {lang}.
Im User-Prompt erhältst du nur die Summary — nicht den Volltext.
Der Typ wird als neuer Eintrag in Paperless angelegt.
Antworte als JSON.

SPRACHE (PFLICHT):
- document_type MUSS vollständig in der Dokumentsprache ({lang}) verfasst sein.
- NIEMALS in einer anderen Sprache antworten — auch nicht teilweise.

DOKUMENTTYP:
- document_type: passender Dokumenttyp auf {lang}
- Kurzer generischer Typ (z.B. Rechnung, Vertrag, Kontoauszug, Brief)
- Synonyme und Abkürzungen in die Dokumentsprache überführen (z.B. Invoice → Rechnung, KTO-Auszug → Kontoauszug)
- Nicht zu spezifisch: keine Rechnungsnummern, keine Datumsangaben, keine Beträge im Namen
- Der Typ muss klar zum Inhalt der Summary passen

{_json_schema_instruction(DOCUMENT_TYPE_SCHEMA)}"""


def build_resolve_correspondent_prompt(document_language: str) -> str:
    lang = document_language
    return f"""\
Du bestimmst den Korrespondenten (Absender) für ein Dokument in Paperless-ngx.
Die Dokumentsprache laut Paperless ist: {lang}.
Im User-Prompt erhältst du nur die Summary — nicht den Volltext.
Der Korrespondent wird als neuer Eintrag in Paperless angelegt.
Antworte als JSON.

SPRACHE (PFLICHT):
- correspondent MUSS vollständig in der Dokumentsprache ({lang}) verfasst sein.
- NIEMALS in einer anderen Sprache antworten — auch nicht teilweise.
- Eigennamen und Firmennamen unverändert übernehmen.

KORRESPONDENT:
- correspondent: Absender aus der Summary
- Möglichst kurzer Kernname
- Nur der Kernname: keine Rechtsformen (GmbH, AG, Inc., Ltd. etc.), keine Domains (.com), keine Zusätze
- Beispiel: "Amazon.com, Inc." → "Amazon"; "Deutsche Telekom AG" → "Deutsche Telekom"
- Bei Personen: Vor- und Nachname, ohne Anrede oder Titel
- Keine Adressen, keine E-Mail-Adressen

{_json_schema_instruction(CORRESPONDENT_SCHEMA)}"""


def build_derive_title_user_prompt(doc_id: int, summary: str) -> str:
    return f"""\
Leite aus der folgenden Summary einen Titel ab.

Dokument-ID: {doc_id}

Summary:
{summary.strip()}"""


def build_resolve_document_type_user_prompt(doc_id: int, summary: str) -> str:
    return f"""\
Bestimme den Dokumenttyp aus der folgenden Summary.

Dokument-ID: {doc_id}

Summary:
{summary.strip()}"""


def build_resolve_correspondent_user_prompt(doc_id: int, summary: str) -> str:
    return f"""\
Bestimme den Korrespondenten aus der folgenden Summary.

Dokument-ID: {doc_id}

Summary:
{summary.strip()}"""


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

{_json_schema_instruction(CHUNK_SCHEMA)}"""
