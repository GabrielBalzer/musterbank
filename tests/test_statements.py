from datetime import datetime, timezone

import pytest

from statements.__main__ import main as statements_main
from statements.render import render_csv, render_text
from statements.service import StatementService

BOOKED_AT = datetime(2025, 3, 3, 10, 15, tzinfo=timezone.utc)


@pytest.fixture
def service(bank, giro):
    bank.debit(giro, 2500, at=BOOKED_AT, counterparty_name="Silberau Apotheke", purpose="Einkauf")
    bank.credit(giro, 300000, "SALARY", at=BOOKED_AT, counterparty_name="Birkenried GmbH", purpose="Gehalt")
    return StatementService(bank)


def test_transactions(service, giro):
    assert service.transactions(giro, "2025-03-01", "2025-03-31")
    assert service.recent_transactions(giro, 2)


def test_monthly_statement(service, giro):
    statement = service.monthly_statement(giro, 2025, 3)
    assert statement["holder"] == "Tilda Rosenthaler"
    assert statement["closing_cents"] == statement["opening_cents"] + statement["credits_cents"] + statement["debits_cents"]
    assert len(statement["lines"]) == 2


def test_turnover_by_kind(service, giro):
    totals = service.turnover_by_kind(giro, "2025-03-01", "2025-03-31")
    assert totals["SALARY"]["amount_cents"] == 300000


def test_months_and_yearly_overview(service, giro):
    assert "2025-03" in service.available_months(giro)
    overview = service.yearly_overview(giro, 2025)
    assert len(overview["months"]) == 12
    assert overview["months"][2]["credits_cents"] == 300000


def test_render_text(service, giro):
    text = render_text(service.monthly_statement(giro, 2025, 3))
    assert "Kontoauszug" in text
    assert "Silberau Apotheke" in text


def test_render_csv(service, giro):
    text = render_csv(service.monthly_statement(giro, 2025, 3))
    assert text.startswith("Buchungstag;")
    assert "3000,00" in text
    assert "-25,00" in text


def test_cli(service, giro, db_path, capsys):
    statements_main(["--db", db_path, "--iban", giro, "--month", "2025-03"])
    assert "Kontoauszug" in capsys.readouterr().out
    statements_main(["--db", db_path, "--iban", giro, "--month", "2025-03", "--format", "csv"])
    assert "Buchungstag" in capsys.readouterr().out
