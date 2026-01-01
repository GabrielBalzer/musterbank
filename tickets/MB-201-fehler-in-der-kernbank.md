# MB-201: Fehler in der Kernbank finden und belegen

**Art:** Challenge

## Beschreibung

Die Fachabteilung findet in Abrechnungen und Kontrollen immer wieder Abweichungen, die niemand erklären kann. Die Tests sind trotzdem grün.

Findet Fehler in der Kernbank und belegt jeden mit einem Test, der vor dem Fix rot und danach grün ist.

## Akzeptanzkriterien

- Zu jedem gefundenen Fehler gibt es einen Test, der ihn nachweist, und einen Fix.
- Maßstab für richtiges Verhalten sind `docs/glossar.md`, `docs/produkte.md`, `docs/architektur.md` und die ADRs.
- Die bestehenden Tests bleiben grün.

## Schnittstelle

Die öffentlichen Schnittstellen aus `docs/architektur.md`. Tests gehören nach `tests/`.
