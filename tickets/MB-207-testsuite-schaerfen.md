# MB-207: Testsuite schärfen

**Art:** Challenge

## Beschreibung

Die Coverage ist hoch, aber sie sagt wenig: Viele Tests führen Code nur aus, ohne das Ergebnis wirklich zu prüfen. Verbessert die Suite so, dass sie echte Fehler findet.

## Akzeptanzkriterien

- Tests prüfen fachliche Ergebnisse auf den Cent, nicht nur `> 0` oder „läuft durch".
- Grenzfälle der Fachregeln sind abgedeckt.
- Tests sind deterministisch und verlassen sich nicht auf Timing.
- Die Suite läuft weiterhin schnell, unter einer Minute.

## Schnittstelle

`python3 run.py test --cov`

## Idee

Coverage zeigt nur, welcher Code läuft. Ob Tests einen Fehler bemerken würden, zeigt Mutation Testing: kleine Änderungen am Code, und die Suite muss rot werden. Ein einfacher Mutator lässt sich mit dem Modul `ast` schnell selbst bauen.
