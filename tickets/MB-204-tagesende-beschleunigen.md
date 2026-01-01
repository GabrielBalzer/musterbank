# MB-204: Tagesendverarbeitung beschleunigen

**Art:** Challenge

## Beschreibung

Mit wachsendem Bestand dauert das Tagesende immer länger. Auf einem großen Datensatz sind es einige Minuten.

```bash
python3 run.py data --customers 40000 --db data/gross.sqlite
python3 run.py eod --db data/gross.sqlite
```

## Akzeptanzkriterien

- Das Tagesende läuft auf dem großen Datensatz mindestens zehnmal schneller als vorher.
- Das Ergebnis ist centgenau gleich: Die Prüfsumme von `run.py eod` ändert sich nicht.
- Ein Abbruch mitten im Lauf hinterlässt keine halben Kontoabschlüsse.
- Die bestehenden Tests bleiben grün.

## Schnittstelle

`python3 run.py eod` und `BankCore.run_end_of_day(date)`. Die Prüfsumme und die Laufzeit stehen in der Ausgabe.
