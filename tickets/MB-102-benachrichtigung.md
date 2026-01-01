# MB-102: Benachrichtigung bei großen Abbuchungen

**Art:** Feature, **Schwierigkeit:** leicht

## Beschreibung

Wer sein Konto im Blick behalten will, soll bei großen Abbuchungen eine Nachricht im Postfach bekommen. Die Schwelle legt jede Person selbst fest.

## Akzeptanzkriterien

- Standardschwelle ist 1.000,00 € je Kunde, sie lässt sich ändern und mit `null` abschalten.
- Jede Belastung ab der Schwelle erzeugt genau eine Nachricht, egal über welchen Weg: Überweisung, Karte, Lastschrift, Barauszahlung.
- Eine Belastung knapp unter der Schwelle erzeugt keine Nachricht.
- Die Nachricht nennt Betrag, maskierte IBAN und Buchungstag.
- Abgelehnte Belastungen erzeugen keine Nachricht.
- Zinsen und Gebühren aus dem Tagesende lösen keine Nachricht aus.

## Schnittstelle

- `core.bank.BankCore.set_notification_threshold(customer_id, threshold_cents)` und `get_notification_threshold(customer_id)`
- Nachrichten erscheinen über `core.mailbox.Mailbox.list_messages(customer_id)`.
