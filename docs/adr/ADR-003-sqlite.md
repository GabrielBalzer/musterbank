# ADR-003: SQLite als Datenbank

**Status:** angenommen, 2016

## Kontext

Die Bank betreibt eine überschaubare Zahl an Konten auf wenigen Rechnern. Ein eigener Datenbankserver hätte Betrieb und Tests deutlich aufwendiger gemacht.

## Entscheidung

Alle Module nutzen eine gemeinsame SQLite-Datei im WAL-Modus. Mehrere Leser und ein Schreiber können gleichzeitig arbeiten. Schreibende Abläufe öffnen ihre Transaktion mit `BEGIN IMMEDIATE`.

## Folgen

- Tests brauchen nur eine temporäre Datei.
- Schreiboperationen laufen nacheinander. Lange Transaktionen blockieren andere Schreiber.
- Schemaänderungen laufen über nummerierte Migrationen.
