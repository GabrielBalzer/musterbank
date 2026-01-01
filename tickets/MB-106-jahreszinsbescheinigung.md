# MB-106: Jahreszinsbescheinigung

**Art:** Feature, **Schwierigkeit:** mittel

## Beschreibung

Für die Steuererklärung brauchen Kundinnen und Kunden eine Übersicht der im Jahr gebuchten Zinsen über alle ihre Konten.

## Akzeptanzkriterien

- Die Bescheinigung nennt Name und Anschrift, das Jahr und je Konto IBAN, Produkt, Habenzinsen und Sollzinsen.
- Maßgeblich sind die Zinsbuchungen mit Buchungstag im Jahr.
- Sie enthält eine Summenzeile und umfasst auch inzwischen geschlossene Konten.
- Konten ohne Zinsbuchung erscheinen mit 0,00 €.
- Es gibt eine Textausgabe auf der Konsole und eine Seite im Online-Banking.

## Schnittstelle

- `statements.service.StatementService.interest_certificate(customer_id, year)` liefert ein Dict mit `customer_no`, `name`, `year`, `accounts` (Liste mit `iban`, `product`, `credit_cents`, `debit_cents`) und `total_cents`.
- `python -m statements --certificate K00000001 --year 2025`
