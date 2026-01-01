# MB-104: Daueraufträge

**Art:** Feature, **Schwierigkeit:** mittel

## Beschreibung

Kundinnen und Kunden sollen wiederkehrende Überweisungen einrichten können. Das Tagesende führt fällige Aufträge aus.

## Akzeptanzkriterien

- Ein Dauerauftrag hat Auftraggeber-IBAN, Empfänger, Betrag, Verwendungszweck, Ausführungstag (1 bis 31), Rhythmus (monatlich oder quartalsweise), Startdatum und optional ein Enddatum.
- Fällt der Ausführungstag auf einen Tag, den der Monat nicht hat, wird am Monatsletzten ausgeführt.
- Fällt er auf einen Nicht-Bankarbeitstag, wird am nächsten Bankarbeitstag ausgeführt.
- Das Tagesende führt jeden fälligen Auftrag genau einmal aus, auch wenn das Datum mehrfach geprüft wird.
- Reicht die Deckung nicht, wird die Ausführung ausgelassen und eine Nachricht ins Postfach gelegt. Der nächste reguläre Termin gilt weiter.
- Gelöschte oder abgelaufene Aufträge werden nicht mehr ausgeführt.
- Ohne Daueraufträge bleibt die Prüfsumme von `run.py eod` unverändert.

## Schnittstelle

- `POST /standing-orders`, Felder: `debtor_iban`, `creditor_iban`, `creditor_name`, `amount_cents`, `purpose`, `day_of_month`, `cycle` (`MONTHLY` oder `QUARTERLY`), `start_date`, `end_date`
- `GET /standing-orders?debtor_iban=...`
- `DELETE /standing-orders/{id}`
- Ausführung über `BankCore.run_end_of_day(date)`
