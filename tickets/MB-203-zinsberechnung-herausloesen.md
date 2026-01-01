# MB-203: Zinsberechnung aus der Kernbank herauslösen

**Art:** Challenge

## Beschreibung

Die Zinsberechnung steckt mitten in `BankCore`. Sie soll schrittweise in ein eigenes Modul mit klarer Schnittstelle umziehen (Strangler Fig). Die Altaufrufer funktionieren währenddessen weiter.

## Akzeptanzkriterien

- Es gibt ein Paket `interest/`, das `core` nicht importiert.
- Die Berechnung arbeitet auf einfachen Daten: Konditionen und Liste von Buchungen rein, Betrag raus.
- `BankCore.calculate_interest` bleibt erhalten und delegiert an das neue Modul.
- Das Tagesende nutzt ebenfalls das neue Modul.
- Das neue Modul hat eigene Tests, die ohne Datenbank laufen.
- Die Prüfsumme von `run.py eod` bleibt durch den Umbau gleich.

## Schnittstelle

`interest.calculate(terms, bookings, from_date, to_date)` liefert Cent als Ganzzahl.

- `terms`: `interest.Terms(day_count, credit_rate_bp, debit_rate_bp)`
- `bookings`: Liste von `(day, amount_cents)`, sortiert nach Tag

## Tipp

Notiert die Prüfsumme, bevor ihr anfangt. Fachliche Änderungen ändern sie, Umbauten nicht. Haltet beides in getrennten Schritten.
