# MB-105: Empfängerüberprüfung

**Art:** Feature, **Schwierigkeit:** mittel

## Beschreibung

Vor einer Überweisung soll geprüft werden können, ob der angegebene Name zum Empfängerkonto passt. Siehe Glossar unter „Empfängerüberprüfung".

## Akzeptanzkriterien

- Groß- und Kleinschreibung, mehrfache Leerzeichen und Umlaut-Schreibweisen (`ü` und `ue`) spielen keine Rolle.
- Die Reihenfolge von Vor- und Nachname spielt keine Rolle, auch `Nachname, Vorname` ergibt `MATCH`.
- Tippfehler in einem ansonsten passenden Namen ergeben `CLOSE_MATCH`. Die Antwort nennt dann den Namen des Kontoinhabers.
- Andere Namen ergeben `NO_MATCH`. Die Antwort nennt keinen Namen.
- Konten anderer Banken ergeben `NOT_AVAILABLE`.
- Ungültige IBANs ergeben `400`.
- Firmenkonten werden gegen den Firmennamen geprüft, Rechtsformen wie `GmbH` dürfen fehlen.
- Das Online-Banking zeigt das Ergebnis vor der Ausführung an.

## Schnittstelle

`POST /verification-of-payee` mit `{"iban": ..., "name": ...}` antwortet mit `200` und `{"result": "MATCH" | "CLOSE_MATCH" | "NO_MATCH" | "NOT_AVAILABLE", "suggested_name": ... oder null}`.
