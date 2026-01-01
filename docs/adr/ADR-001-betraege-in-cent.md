# ADR-001: Beträge als ganzzahlige Cent

**Status:** angenommen, 2014

## Kontext

Die ersten Batch-Skripte rechneten mit Dezimalzahlen im Gleitkommaformat. Beim Monatsabschluss fehlten dadurch immer wieder einzelne Cent, die von Hand ausgebucht werden mussten.

## Entscheidung

Beträge werden in der Datenbank und in der Kernbank als ganzzahlige Cent geführt. Wo ein Betrag in Euro hereinkommt, wandelt `core.money.to_cents` ihn centgenau um. Zinsen werden exakt gerechnet und erst am Ende gerundet.

## Folgen

- Summen stimmen immer, der Abgleich gegen das Journal ist exakt.
- Die Überweisungs-API nimmt aus historischen Gründen Euro-Beträge als JSON-Zahl an. Die Umrechnung passiert an der Grenze zur Kernbank.
