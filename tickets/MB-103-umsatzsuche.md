# MB-103: Umsatzsuche mit Filtern

**Art:** Feature, **Schwierigkeit:** leicht

## Beschreibung

In der Umsatzliste fehlt eine Suche. Wer eine bestimmte Abbuchung sucht, muss sich bisher durch alle Monate klicken.

## Akzeptanzkriterien

- Filter nach Zeitraum, Betrag von/bis, Buchungsart und Freitext.
- Der Freitext sucht ohne Beachtung der Groß- und Kleinschreibung in Name und Verwendungszweck.
- Filter sind kombinierbar, ohne Filter kommen alle Umsätze.
- Ergebnisse sind nach Buchungstag absteigend sortiert.
- Benutzereingaben landen nur als Parameter im SQL.
- Das Online-Banking bietet das Suchformular auf der Umsatzseite an.

## Schnittstelle

`statements.service.StatementService.search(iban, from_date=None, to_date=None, min_cents=None, max_cents=None, kind=None, text=None)` liefert eine Liste von Umsatzzeilen im Format von `transactions()`. `min_cents` und `max_cents` beziehen sich auf den Betrag ohne Vorzeichen.
