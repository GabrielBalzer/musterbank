# Aufgabenmenü

Sucht euch aus, was euch reizt. Es gibt keine Reihenfolge, keine Punkte und keine Abgabe. Probiert aus, was mit KI geht, in eurem Tempo.

Das Setup steht in [docs/README.md](docs/README.md). Jedes Ticket in [tickets/](tickets/) beschreibt das Ziel, die Akzeptanzkriterien und die Schnittstelle.

## Neue Funktionen

| Ticket | Thema | Schwierigkeit |
|---|---|---|
| [MB-101](tickets/MB-101-dispo-limit.md) | Dispo-Limit pro Konto | leicht |
| [MB-102](tickets/MB-102-benachrichtigung.md) | Benachrichtigung bei großen Abbuchungen | leicht |
| [MB-103](tickets/MB-103-umsatzsuche.md) | Umsatzsuche mit Filtern | leicht |
| [MB-104](tickets/MB-104-dauerauftraege.md) | Daueraufträge | mittel |
| [MB-105](tickets/MB-105-empfaengerueberpruefung.md) | Empfängerüberprüfung | mittel |
| [MB-106](tickets/MB-106-jahreszinsbescheinigung.md) | Jahreszinsbescheinigung | mittel |
| [MB-107](tickets/MB-107-camt053.md) | Kontoauszug im camt.053-Format | schwer |
| [MB-108](tickets/MB-108-sammelueberweisung.md) | Sammelüberweisung per pain.001 | schwer |

## Der Bestandscode

| Ticket | Thema | Worum es geht |
|---|---|---|
| [MB-201](tickets/MB-201-fehler-in-der-kernbank.md) | Fehler in der Kernbank | Findet Fehler und belegt sie mit Tests |
| [MB-202](tickets/MB-202-idempotenz.md) | Idempotenz | Macht die Überweisungs-API robust gegen Wiederholungen |
| [MB-203](tickets/MB-203-zinsberechnung-herausloesen.md) | Strangler Fig | Löst die Zinsberechnung aus der Kernbank heraus |
| [MB-204](tickets/MB-204-tagesende-beschleunigen.md) | Performance | Beschleunigt das Tagesende bei gleichem Ergebnis |
| [MB-205](tickets/MB-205-barrierefreiheit.md) | Barrierefreiheit | Macht das Online-Banking für alle bedienbar |
| [MB-206](tickets/MB-206-review-agent.md) | Review-Agent | Lasst einen Agenten Pull Requests prüfen |
| [MB-207](tickets/MB-207-testsuite-schaerfen.md) | Testqualität | Bringt die Tests dazu, echte Fehler zu finden |

## Tipps

- **Prüfsumme notieren:** `python3 run.py eod` gibt eine Prüfsumme über alle Ergebnisse aus. Notiert sie vor einem Umbau. Bleibt sie gleich, hat sich fachlich nichts geändert. Fachliche Korrekturen ändern sie, also haltet Umbauten und Korrekturen in getrennten Schritten.
- **Regeln kennen:** Die Fachregeln stehen in `docs/glossar.md` und `docs/produkte.md`, die Hausregeln in `docs/hausregeln.md`.
- **Eigene Werkzeuge:** Legt euch gern eigene Anweisungen, Skills und Tests für eure KI an. Das gehört ausdrücklich dazu.

## Umgebung

Es gibt keinen Zugriff nach außen. Alles Nötige liegt im Repo. Datenbank ist SQLite, die Dienste laufen lokal auf `127.0.0.1`.
