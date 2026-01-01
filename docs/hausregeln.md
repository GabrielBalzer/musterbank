# Hausregeln für Code-Reviews

Diese Regeln gelten seit der Pfennigflug-Übernahme für allen neuen und geänderten Code. Der Altbestand hält sie nicht überall ein. Wer dort arbeitet, zieht die berührten Stellen nach.

## Pflichtregeln

Ein Verstoß führt zur Ablehnung des Pull Requests.

### R1: Kein Float für Geld

Geldbeträge werden nicht als `float` berechnet oder gespeichert. Intern zählen ganzzahlige Cent, an Schnittstellen `Decimal` oder eine Umrechnung über `core.money`.

Prozentwerte für die Anzeige und Messwerte dürfen `float` sein.

### R2: Zahlungsauslösende Endpunkte brauchen einen Idempotency-Key

Jeder neue HTTP-Endpunkt, der Geld bewegt, verlangt den Header `Idempotency-Key` und bucht bei Wiederholung nicht erneut. Rein lesende Endpunkte brauchen ihn nicht.

### R3: Keine personenbezogenen Daten im Log

Namen, vollständige IBANs, Adressen, E-Mail-Adressen und Geburtsdaten gehören nicht ins Log. IBANs dürfen maskiert erscheinen, siehe `core.iban.mask_iban`. Technische IDs sind erlaubt.

### R4: SQL nur parametrisiert

Werte kommen nie per Verkettung oder Formatierung in SQL, sondern als Parameter (`?`). Feste Bezeichner aus dem Code, etwa ein Tabellenname aus einer Konstante, sind keine Werte und dürfen eingesetzt werden.

## Weitere Erwartungen

- Neue Logik bringt Tests mit.
- Pull Requests bleiben klein und haben eine kurze Beschreibung.
- Schemaänderungen laufen über eine neue Datei in `core/migrations/`, vorhandene Migrationen werden nicht geändert.
- Code und Bezeichner sind Englisch, Doku und Tickets Deutsch.
