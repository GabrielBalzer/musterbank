# Musterbank AG: Einstieg

Die Musterbank AG ist eine fiktive Regionalbank. Alle Daten sind erfunden. Das Repo läuft ohne Netzwerkzugriff und braucht nur Python 3.10 oder neuer.

## Setup

```bash
python3 run.py setup     # Testwerkzeuge aus vendor/ einrichten, kein Netzwerk nötig
python3 run.py data      # Demodaten nach data/musterbank.sqlite schreiben
python3 run.py start     # Online-Banking und Überweisungs-API starten
```

- Online-Banking: <http://127.0.0.1:8080>, Anmeldung mit Kundennummer `K00000001` und PIN `1234`. Die PIN gilt für alle Demokunden.
- Überweisungs-API: <http://127.0.0.1:8081>

`setup` nutzt `pip` und `venv`, falls vorhanden, und entpackt die Wheels aus `vendor/` sonst nach `.deps/`. Für die Bank selbst ist `setup` nicht nötig, sie kommt mit der Standardbibliothek aus.

## Befehle

| Befehl | Zweck |
|---|---|
| `python3 run.py setup` | Testwerkzeuge einrichten |
| `python3 run.py data [--customers N] [--seed S]` | Demodaten erzeugen, ersetzt eine vorhandene Datenbank |
| `python3 run.py start` / `stop` / `status` | Dienste steuern, Logs unter `data/run/` |
| `python3 run.py test [--cov] [pytest-Argumente]` | Tests ausführen, optional mit Coverage-Bericht |
| `python3 run.py eod [--date JJJJ-MM-TT] [--commit]` | Tagesendverarbeitung, gibt Prüfsumme und Laufzeit aus |
| `python3 run.py loadgen [--requests N] [--concurrency N]` | Last gegen die laufende API |
| `python3 tools/admin.py --help` | Sachbearbeitung: Kunden, Konten, Berichte, Mahnlauf |
| `python3 tools/reconcile.py` | Salden gegen das Buchungsjournal abgleichen |
| `python3 -m statements --iban DE.. --month 2025-12` | Kontoauszug auf der Konsole |

`run.py eod` rechnet standardmäßig auf einer Kopie der Datenbank. Dadurch lässt sich der Lauf wiederholen und vergleichen. `--commit` schreibt das Ergebnis in die Datenbank.

## Daten

Der Generator erzeugt mit festem Seed Kunden, Konten und das Kalenderjahr 2025. Gleicher Seed und gleiche Größe ergeben dieselben Daten. Der Standardlauf für das Tagesende ist der 31.12.2025.

Für größere Datenmengen: `python3 run.py data --customers 40000`.

## Grenzen dieser Umgebung

Das Online-Banking ist eine Demo: eine PIN für alle, nur fiktive Daten, nur `127.0.0.1`. Es ist nicht für den Betrieb außerhalb dieser Umgebung gedacht.

## Weiterlesen

- [Architektur](architektur.md)
- [Fachglossar](glossar.md)
- [Produkte und Konditionen](produkte.md)
- [Hausregeln für Code-Reviews](hausregeln.md)
- [Architekturentscheidungen](adr/)
