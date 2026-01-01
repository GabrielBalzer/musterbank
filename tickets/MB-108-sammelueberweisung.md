# MB-108: Sammelüberweisung per pain.001-Import

**Art:** Feature, **Schwierigkeit:** schwer

## Beschreibung

Geschäftskunden möchten viele Überweisungen auf einmal einreichen, etwa die Gehaltszahlungen eines Monats.

## Akzeptanzkriterien

- Die API nimmt eine pain.001-Datei entgegen (`urn:iso:std:iso:20022:tech:xsd:pain.001.001.09`).
- Vor dem ersten Buchen werden alle Zahlungen geprüft: IBANs, Beträge, Summe und Anzahl aus dem `GrpHdr`, Deckung für die Gesamtsumme.
- Die Einreichung wird ganz oder gar nicht ausgeführt.
- Dieselbe `MsgId` lässt sich nicht zweimal einreichen.
- Beträge werden centgenau übernommen.
- Die Antwort nennt je Zahlung die erzeugte Überweisungs-ID.
- Unvollständiges oder nicht wohlgeformtes XML ergibt `400`, fachliche Fehler ergeben `422` mit der Liste der betroffenen Zahlungen.

## Schnittstelle

`POST /transfers/batch` mit `Content-Type: application/xml`. Antwort `201` mit `{"msg_id": ..., "transfers": [{"end_to_end_id": ..., "id": ...}]}`.
