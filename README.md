# Musterbank AG

Eine fiktive Bank als Spielwiese für KI-gestützte Softwareentwicklung. Das Repo ist für einen KI-Hackathon entstanden und fühlt sich an wie echter Bestandscode: ein gewachsener Monolith, ein übernommener Zahlungsdienst, Tests, ein Backlog und Pull Requests, die auf ein Review warten.

Sucht euch eine Aufgabe aus und probiert, wie weit ihr mit KI-Werkzeugen wie Claude Code kommt. Es gibt keine Punkte, keine Abgabe und keine Reihenfolge.

> Die Bank, ihre Kunden und alle Daten sind erfunden. Das Online-Banking ist eine Demo für den lokalen Rechner und nicht für den echten Betrieb gedacht.

## Schnellstart

Ihr braucht nur Python 3.10 oder neuer. Datenbank und Testwerkzeuge liegen bei, nach dem Herunterladen ist kein Netzwerk mehr nötig.

Repo klonen oder als ZIP herunterladen, dann im Repo-Ordner:

```bash
python3 run.py setup     # Testwerkzeuge aus vendor/ einrichten
python3 run.py data      # Demodaten erzeugen, dauert wenige Sekunden
python3 run.py test      # Tests ausführen
python3 run.py start     # Online-Banking und Überweisungs-API starten
```

Danach läuft:

- **Online-Banking:** <http://127.0.0.1:8080>, Anmeldung mit Kundennummer `K00000001` und PIN `1234`
- **Überweisungs-API:** <http://127.0.0.1:8081>, zum Beispiel `curl http://127.0.0.1:8081/health`

Mit `python3 run.py stop` beendet ihr die Dienste. Alle weiteren Befehle stehen in [docs/README.md](docs/README.md).

## Was drin ist

| Ordner | Inhalt |
|---|---|
| `core/` | Kernbank seit 2011: Kunden, Konten, Buchungen, Zinsen, Tagesende, Mahnwesen |
| `payments/` | Überweisungs-API, 2019 mit einem Start-up übernommen, läuft als eigener Prozess |
| `statements/` | Kontoauszüge und Umsatzabfragen |
| `web/` | Serverseitig gerendertes Online-Banking |
| `tools/` | Daten- und Lastgenerator, Sachbearbeitung, Abgleich |
| `tests/` | Testsuite mit pytest |
| `tickets/` | Backlog mit 15 Tickets |
| `reviews/` | 16 Pull Requests als Diff-Dateien |
| `docs/` | Architektur, Fachglossar, Produkte, Hausregeln, Architekturentscheidungen |
| `vendor/` | pytest und coverage als reine Wheels, damit alles offline läuft |

## Was ihr machen könnt

Alle Aufgaben stehen mit Schwierigkeit im [Aufgabenmenü](CHALLENGES.md):

- **Neue Funktionen:** vom Dispo-Limit bis zum Kontoauszug im camt.053-Format
- **Bestandscode:** Fehler in der Kernbank finden, die API idempotent machen, die Zinsberechnung herauslösen, das Tagesende beschleunigen, das Online-Banking barrierefrei machen
- **Agenten und Tests:** einen Review-Agenten für die Pull Requests bauen, die Testsuite schärfen

## Ideen für den Einstieg

- **Code erklären lassen:** „Zeig mir den Weg einer Überweisung vom Online-Banking bis in die Datenbank."
- **Klein anfangen:** Nehmt ein leichtes Ticket wie [MB-101](tickets/MB-101-dispo-limit.md) und lasst eure KI zuerst einen Plan schreiben, bevor Code entsteht.
- **Eigene Werkzeuge anlegen:** Das Repo enthält keine Anweisungen für KI-Werkzeuge. Legt euch eigene an und schaut, was sich dadurch verändert.

## Weiterlesen

- [Einstieg und alle Befehle](docs/README.md)
- [Architektur](docs/architektur.md)
- [Fachglossar](docs/glossar.md)
- [Produkte und Konditionen](docs/produkte.md)
- [Hausregeln für Code-Reviews](docs/hausregeln.md)
- [Architekturentscheidungen](docs/adr/)
- [Eingebettete Pakete und Lizenzen](THIRD_PARTY.md)
