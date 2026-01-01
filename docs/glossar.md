# Fachglossar

## Buchungstag

Der Kalendertag, an dem eine Buchung im Konto erfasst wird. Maßgeblich ist die Ortszeit der Bank, also Europe/Berlin, auch wenn der Zeitstempel in UTC vorliegt.

## Valuta (Wertstellung)

Der Tag, ab dem ein Betrag für die Zinsberechnung zählt. Standardmäßig ist das der Buchungstag, an Nicht-Bankarbeitstagen der nächste Bankarbeitstag.

Die Valuta kann vom Buchungstag abweichen: Eine Kartenzahlung wird oft später gebucht, aber auf den Einsatztag valutiert. Für Zinsen zählt immer die Valuta.

## Bankarbeitstag

Montag bis Freitag, außer den Bankfeiertagen der Musterbank AG: Neujahr, Karfreitag, Ostermontag, 1. Mai, Christi Himmelfahrt, Pfingstmontag, 3. Oktober, 24., 25., 26. und 31. Dezember.

## Zinsperiode

Der Zeitraum, für den Zinsen abgerechnet werden. Sie umfasst alle Kalendertage von ihrem ersten bis zu ihrem letzten Tag, beide einschließlich. Eine Abschlussperiode für den Monat März läuft also vom 1. bis zum 31. März.

Maßgeblich ist für jeden Tag der Tagesendsaldo nach Valuta.

## Zinstage-Konventionen

Die Konvention legt fest, wie Tage gezählt werden und wie viele Tage ein Jahr hat.

| Konvention | Tage | Jahr | Bedeutung |
|---|---|---|---|
| `ACT/365` | tatsächliche Kalendertage | 365 | Jeder Kalendertag zählt einmal, das Jahr hat immer 365 Tage. |
| `ACT/360` | tatsächliche Kalendertage | 360 | Jeder Kalendertag zählt einmal, das Jahr hat 360 Tage. |
| `30E/360` | jeder Monat 30 Tage | 360 | Der 31. zählt nicht. Der letzte Februartag zählt für die fehlenden Tage mit, sodass der Februar ebenfalls auf 30 Tage kommt. |

Formel für einen Tag: `Tagesendsaldo × Zinssatz × Tagesgewicht ÷ Jahrestage`.

## Rundung

Zinsen werden tagesgenau ohne Zwischenrundung summiert und erst am Ende auf Cent gerundet. Es gilt die kaufmännische Rundung: Ab einem halben Cent wird vom Nullpunkt weg gerundet.

## Beträge

Beträge werden centgenau geführt. Siehe [ADR-001](adr/ADR-001-betraege-in-cent.md).

## IBAN

Internationale Kontonummer nach ISO 13616. Eine IBAN ist gültig, wenn alle Bedingungen erfüllt sind:

1. Sie hat die für das Land vorgeschriebene Länge, in Deutschland genau 22 Zeichen.
2. Sie besteht aus Länderkennzeichen, zwei Prüfziffern und der Kontokennung.
3. Die Prüfziffernrechnung nach Modulo 97 ergibt 1.

Leerzeichen und Kleinschreibung spielen keine Rolle. Die Bankleitzahl der Musterbank AG lautet `01234500`.

## Überziehungsrahmen (Dispo)

Der Betrag, um den ein Konto ins Minus gehen darf. Belastungen über den Rahmen hinaus werden abgelehnt. Gebühren und Zinsen werden auch dann gebucht, wenn sie den Rahmen überschreiten.

## Abschluss

Die Gutschrift oder Belastung der aufgelaufenen Zinsen. Je nach Produkt monatlich, quartalsweise oder bei Fälligkeit, siehe [Produkte](produkte.md).

## Verrechnungskonto

Internes Konto für Zahlungen an andere Banken. Es hält das Gegenstück solcher Buchungen, bis es ausgeglichen wird.

## Empfängerüberprüfung (Verification of Payee)

Prüfung vor einer Überweisung, ob der angegebene Empfängername zur IBAN passt. Das Ergebnis ist einer von drei Werten:

| Ergebnis | Bedeutung |
|---|---|
| Match | Der Name stimmt überein. |
| Close Match | Der Name ähnelt dem Kontoinhaber, zum Beispiel ein Tippfehler. Der Auftraggeber sieht den korrekten Namen und entscheidet. |
| No Match | Der Name passt nicht. |

## Idempotenz

Eine Operation ist idempotent, wenn sie bei mehrfacher Ausführung dasselbe Ergebnis hat wie bei einmaliger. Bei Zahlungen verhindert ein Idempotency-Key, dass ein wiederholter Aufruf doppelt bucht.

## camt.053

ISO-20022-Format für elektronische Kontoauszüge (Bank to Customer Statement). Das Gegenstück für Überweisungsaufträge ist pain.001.

## Festgeld

Einlage mit festem Fälligkeitstag. Die Zinsen werden bei Fälligkeit gutgeschrieben, das Konto wechselt in den Status `MATURED`.

## Mahnstufen

Liegt ein Konto über dem Überziehungsrahmen, folgen Erinnerung, zweite Erinnerung und letzte Mahnung im Abstand von mindestens 14 Tagen. Mit der letzten Mahnung wird das Konto gesperrt.
