# MB-205: Online-Banking barrierefrei machen

**Art:** Challenge

## Beschreibung

Das Online-Banking soll WCAG 2.1 AA erfüllen. Es muss sich vollständig mit der Tastatur bedienen lassen und mit einem Screenreader verständlich sein.

## Akzeptanzkriterien

Für alle Seiten: Anmeldung, Konten, Umsätze, Kontoauszug, Überweisung, Umbuchung, Postfach, Meine Daten.

- Die Sprache der Seite ist ausgezeichnet.
- Jede Seite hat einen eigenen, sprechenden Titel und eine Hauptüberschrift.
- Jedes Formularfeld hat ein zugeordnetes Label.
- Datentabellen haben Kopfzellen.
- Text hat einen Kontrast von mindestens 4,5:1 zum Hintergrund.
- Alle Funktionen sind per Tastatur erreichbar und auslösbar, der Fokus ist sichtbar.
- Bilder haben einen Alternativtext.
- Die bestehenden Tests bleiben grün.

## Schnittstelle

Die Seiten von `python3 run.py start` auf `http://127.0.0.1:8080`.
