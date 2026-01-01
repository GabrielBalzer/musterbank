# MB-101: Dispo-Limit pro Konto

**Art:** Feature, **Schwierigkeit:** leicht

## Beschreibung

Der Überziehungsrahmen lässt sich bisher nur in der Sachbearbeitung setzen. Kundinnen und Kunden sollen ihn für ihr Girokonto selbst anpassen können, innerhalb einer Obergrenze von 5.000,00 €.

## Akzeptanzkriterien

- Der Rahmen lässt sich über die API lesen und ändern.
- Nur Girokonten haben einen änderbaren Rahmen, andere Produkte werden abgelehnt.
- Werte über 5.000,00 € oder unter 0 € werden abgelehnt.
- Ein Rahmen, der unter dem aktuellen Sollsaldo läge, wird abgelehnt.
- Eine Belastung über den neuen Rahmen hinaus wird abgelehnt, eine bis genau an den Rahmen geht durch.
- Das Online-Banking zeigt den Rahmen an und erlaubt die Änderung.

## Schnittstelle

- `GET /accounts/{iban}/overdraft-limit` liefert `{"iban": ..., "limit_cents": ...}`.
- `PUT /accounts/{iban}/overdraft-limit` mit `{"limit_cents": ...}` antwortet mit `200`. Ungültige Werte ergeben `422`, unbekannte Konten `404`.
