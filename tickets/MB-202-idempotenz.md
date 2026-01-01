# MB-202: Überweisungs-API idempotent machen

**Art:** Challenge

## Beschreibung

Clients wiederholen `POST /transfers`, wenn eine Antwort ausbleibt, zum Beispiel nach einem Verbindungsabbruch. Heute kann das doppelt buchen. Hausregel R2 verlangt einen Idempotency-Key.

## Akzeptanzkriterien

- `POST /transfers` verlangt den Header `Idempotency-Key`. Fehlt er, antwortet die API mit `400`.
- Dieselbe Anfrage mit demselben Key bucht genau einmal und liefert dieselbe Statuscode-Antwort samt Inhalt.
- Derselbe Key mit anderem Inhalt ergibt `422` und bucht nicht.
- Parallele Anfragen mit demselben Key buchen genau einmal, auch über mehrere Prozesse hinweg.
- Bricht die Verbindung nach dem Senden ab, liefert die Wiederholung das Ergebnis der ersten Ausführung.
- Bricht die Verbindung mitten im Body ab, wird nichts gebucht.
- Auch eine Ablehnung, etwa `409` mangels Deckung, wird für den Key gemerkt und wiederholt.
- `web/` und `tools/loadgen.py` senden den Header.
- Die Summe aller Salden bleibt unverändert, `tools/reconcile.py` meldet keine Differenzen.

## Schnittstelle

`POST /transfers` mit Header `Idempotency-Key: <beliebiger Text bis 128 Zeichen>`, sonst wie in `docs/architektur.md`.
