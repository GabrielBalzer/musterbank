# ADR-002: Payments bleibt ein eigener Prozess

**Status:** angenommen, 2019

## Kontext

Mit der Übernahme der Pfennigflug GmbH kam ein fertiger Überweisungsdienst ins Haus, mit eigenem Stil und eigener API. Die Integration in die Kernbank hätte beide Teile über Monate blockiert.

## Entscheidung

`payments/` läuft als eigener Prozess und bietet eine HTTP-API. Buchungen laufen per Import über `core.bank.BankCore`. Das Online-Banking ruft die API über HTTP auf und nicht den Code direkt.

## Folgen

- Die API ist die Schnittstelle für alle Überweisungen, auch für künftige Kanäle.
- Beide Prozesse teilen sich die Datenbank. Konsistenz hängt damit an Transaktionen und nicht an Sperren im Prozess.
- Es gibt weiter zwei Stile im Code. Neuer Code orientiert sich an `payments/`.
