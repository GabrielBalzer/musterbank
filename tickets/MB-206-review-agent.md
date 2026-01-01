# MB-206: Review-Agent für Pull Requests

**Art:** Challenge

## Beschreibung

In `reviews/` warten Pull Requests als Diff-Dateien auf ein Review. Baut einen Agenten oder Workflow, der sie gegen die Hausregeln prüft und entscheidet, ob sie angenommen werden können.

## Akzeptanzkriterien

- Der Agent prüft alle Dateien `reviews/PR-*.diff` gegen die Pflichtregeln R1 bis R4 aus `docs/hausregeln.md`.
- Für jeden Pull Request gibt es eine Entscheidung und bei Ablehnung die verletzten Regeln.
- Das Ergebnis lässt sich wiederholen: Ein neuer Lauf erzeugt die Datei erneut.
- Die Begründung nennt die betroffene Stelle.

## Schnittstelle

Ausgabe in `reviews/verdicts.json`:

```json
[
  {"pr": "PR-0001", "verdict": "approve", "rules": [], "reason": "..."},
  {"pr": "PR-0002", "verdict": "reject", "rules": ["R9"], "reason": "..."}
]
```
