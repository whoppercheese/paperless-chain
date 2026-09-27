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

CHUNK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "chunks": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string", "minLength": 1},
                    "label": {"type": "string", "minLength": 1},
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
- Keine zusätzlichen Felder
- Antworte ausschließlich als JSON — kein Markdown, keine Erklärungen
"""



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

TITEL:
- title: kurzer Titel auf {lang}, 3-12 Wörter (Wortgrenzen einhalten, niemals mitten im Wort abbrechen)
- Beschreibe Dokumentart und inhaltlichen Kern (Thema, Zweck, Gegenstand)
- KEINE Namen: weder Empfänger, Korrespondent/Absender, Firmen, Personen noch andere Eigennamen
- KEINE Daten: keine Tages-, Monats- oder vollständigen Datumsangaben (Ausnahme: Jahreszahlen, z.B. „Steuerbescheid 2023“)
- Keine Rechnungsnummern, Vertragsnummern, Beträge oder Adressen

{_json_schema_instruction(TITLE_SCHEMA)}"""


def build_derive_title_user_prompt(doc_id: int, summary: str) -> str:
    return f"""\
Leite aus der folgenden Summary einen Titel ab.

Dokument-ID: {doc_id}

Summary:
{summary.strip()}"""


def build_chunk_prompt(document_language: str) -> str:
    lang = document_language
    return f"""\
Teile den Volltext in semantische Such-Chunks auf. Dokumentsprache: {lang}.

AUFGABE:
Jeder Chunk hat "text" (wörtlicher Abschnitt aus dem Dokument) und "label" (kurze Beschreibung, 2-6 Wörter auf {lang}).

REGELN:
1. Wenige, große Chunks — nur bei klaren Themenwechseln trennen.
2. "text" ist immer der vollständige, unveränderte Originaltext des Abschnitts. Nichts kürzen oder weglassen.
3. Zusammengehöriges zusammenlassen: Tabellen mit Erläuterungen, Einleitungen mit Hauptteil, Detailblöcke mit Kontext.
4. Boilerplate (AGB, Datenschutz, Impressum) in einen einzigen Chunk bündeln.
5. Keine Überschneidungen. Zusammen decken die Chunks den gesamten relevanten Inhalt ab.
6. Keine Zusammenfassung erzeugen — die wird separat gespeichert.
7. Kurze Dokumente: 1 Chunk. Längere: typisch 2-5 Chunks."""
