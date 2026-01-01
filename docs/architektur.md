# Architektur

## Hintergrund

Die Kernbank (`core/`) entstand ab 2011 als Eigenentwicklung und wurde über die Jahre erweitert. 2019 übernahm die Musterbank AG das Zahlungs-Start-up Pfennigflug GmbH. Dessen Überweisungsdienst läuft seitdem als eigener Prozess (`payments/`) vor der Kernbank. Deshalb gibt es zwei Stile im Code: gewachsene Klassen in `core/` und typisierte Dataclasses in `payments/`.

## Überblick

```text
Browser ──> web/ ──HTTP──> payments/ ──Import──> core/ ──> SQLite
             │                                    ▲
             └──────Import──> statements/ ────────┘
tools/ ───────────────────────────────────────────┘
```

| Modul | Aufgabe |
|---|---|
| `core/` | Kunden, Konten, Buchungen, Zinsen, Tagesende, Mahnwesen, Berichte, Postfach, Altformat-Import |
| `payments/` | Überweisungen über eine HTTP-API, bucht über `core` |
| `statements/` | Kontoauszüge und Umsatzabfragen als Bibliothek und CLI |
| `web/` | Serverseitig gerendertes Online-Banking |
| `tools/` | Datengenerator, Lastgenerator, Sachbearbeitung, Abgleich |

Web und Payments sind eigene Prozesse und teilen sich eine SQLite-Datei. Jede Anfrage öffnet eine eigene Verbindung. Die Datenbank läuft im WAL-Modus.

## Öffentliche Schnittstellen

Auf diese Schnittstellen verlassen sich andere Module. Sie bleiben stabil, auch wenn sich die Interna ändern.

**Kernbank**, `core.bank.BankCore(db_path)`:

| Methode | Bedeutung |
|---|---|
| `createCustomer(first_name, last_name, ...)` | legt einen Kunden an, gibt die ID zurück |
| `open_account(customer_id, product_code, opened_on=None, overdraft_limit_cents=0, maturity_date=None)` | eröffnet ein Konto, gibt die IBAN zurück |
| `get_balance(iban)` | Saldo in Cent |
| `post_booking(iban, amount_cents, kind, at=None, value_date=None, ...)` | bucht einen vorzeichenbehafteten Betrag ohne Limitprüfung |
| `credit(iban, amount_cents, ...)` / `debit(iban, amount_cents, ...)` | Gutschrift und Belastung, `debit` prüft den Überziehungsrahmen |
| `calculate_interest(iban, from_date, to_date)` | Zinsen in Cent für alle Kalendertage von `from_date` bis `to_date` einschließlich |
| `run_end_of_day(business_date)` | Tagesendverarbeitung, gibt unter anderem die Prüfsumme zurück |

**Helfer:** `core.money` (`to_cents`, `parse_eur`, `format_eur`), `core.iban` (`validate_iban`, `build_de_iban`, `format_iban`, `mask_iban`), `core.dates` (`berlin_date`, `is_business_day`, `next_business_day`).

**Überweisungs-API:**

| Aufruf | Bedeutung |
|---|---|
| `POST /transfers` | Überweisung ausführen, JSON mit `debtor_iban`, `creditor_iban`, `creditor_name`, `amount` (Euro), `purpose`; Antwort `201` |
| `GET /transfers/{id}` | eine Überweisung |
| `GET /transfers?debtor_iban=...&limit=...` | Überweisungen eines Kontos |
| `GET /accounts/{iban}/balance` | Saldo |
| `GET /health` | Lebenszeichen |

Fehlercodes: `400` ungültige Anfrage, `404` unbekanntes Konto, `409` von der Bank abgelehnt, zum Beispiel mangels Deckung.

**Prozesse:** `python -m payments --db PFAD --port N` und `python -m web --db PFAD --port N --payments-url URL`.

## Datenmodell

Alle Beträge sind ganzzahlige Cent. Datumswerte stehen als ISO-Text in der Datenbank.

| Tabelle | Inhalt |
|---|---|
| `customers` | Stammdaten |
| `products` | Konditionen je Produkt |
| `accounts` | Konten mit aktuellem Saldo |
| `bookings` | Buchungsjournal |
| `transfers` | Überweisungsaufträge |
| `eod_runs`, `eod_results` | Tagesendläufe und ihre Ergebnisse je Konto |
| `dunning_notices` | Mahnungen |
| `mailbox_messages` | Postfach im Online-Banking |
| `web_sessions` | Anmeldungen |
| `schema_version` | angewendete Migrationen |

Schemaänderungen liegen als nummerierte SQL-Dateien in `core/migrations/` und werden beim Öffnen der Datenbank automatisch angewendet.

## Grundregeln der Buchhaltung

- Der Saldo eines Kontos entspricht zu jeder Zeit der Summe seiner Buchungen. `tools/reconcile.py` prüft das.
- Eine Überweisung bucht immer zwei Seiten in einer Transaktion. Empfänger bei anderen Banken laufen über das interne Verrechnungskonto. Die Summe aller Salden ändert sich durch Überweisungen deshalb nicht.

## Tagesende

`run_end_of_day` verarbeitet alle aktiven Konten:

1. Zinsabschluss, wenn das Produkt an diesem Tag abschließt
2. Kontoführungsgebühr am Monatsletzten
3. Ergebnis je Konto in `eod_results`
4. SHA-256-Prüfsumme über alle Ergebniszeilen

Die Prüfsumme hängt nur von den fachlichen Ergebnissen ab. Sie eignet sich deshalb, um Umbauten zu vergleichen: Bleibt sie gleich, hat sich fachlich nichts geändert.
