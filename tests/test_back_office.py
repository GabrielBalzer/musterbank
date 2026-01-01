from datetime import date, datetime, timezone

import pytest

from core.dunning import DunningProcessor
from core.iban import build_de_iban
from core.legacy_import import LegacyFormatError, LegacyImporter, format_file, format_record, parse_file, parse_record
from core.mailbox import Mailbox
from core.reports import ReportGenerator

BOOKED_AT = datetime(2025, 3, 3, 10, 15, tzinfo=timezone.utc)
DAY = date(2025, 3, 3)


@pytest.fixture
def reports(bank, giro, tagesgeld):
    bank.credit(tagesgeld, 500000, at=BOOKED_AT)
    bank.debit(giro, 120000, at=BOOKED_AT, purpose="Grosser Kauf", counterparty_name="Silberau Apotheke")
    return ReportGenerator(bank)


def test_monthly_report(reports):
    report = reports.monthly_report(2025, 3)
    assert report["turnover"]
    assert "Art;Anzahl;Summe" in reports.monthly_report_csv(2025, 3)


def test_product_report(reports):
    assert "GIRO" in reports.product_report_csv()


def test_overdraft_report(reports):
    assert "NEIN" in reports.overdraft_report_csv()


def test_large_movements(reports):
    assert "Silberau Apotheke" in reports.large_movements_csv("2025-03-01", "2025-03-31", 100000)


def test_dormant(reports, bank, customer_id):
    idle = bank.open_account(customer_id, "GIRO", opened_on="2025-01-01")
    assert idle in reports.dormant_csv("2025-01-01")


def test_top_customers_and_city(reports):
    assert reports.top_customers()[0]["name"] == "Tilda Rosenthaler"
    assert reports.customers_by_city()[0]["city"] == "Musterstadt"


def test_age_structure(reports, bank):
    bank.createCustomer("Ole", "Jung", birth_date="2004-01-01")
    bank.createCustomer("Ida", "Alt", birth_date="1950-01-01")
    bank.createCustomer("Uwe", "Mittel", birth_date="1970-01-01")
    bank.createCustomer("Pia", "Offen")
    buckets = reports.age_structure(2025)
    assert sum(buckets.values()) == 5
    assert buckets["unbekannt"] == 1


def test_maturities(reports, bank, customer_id):
    fixed = bank.open_account(customer_id, "FESTGELD", opened_on="2025-01-01", maturity_date="2025-06-30")
    assert fixed in reports.maturities_csv("2025-06-01", "2025-06-30")


def test_forecast(reports, tagesgeld):
    assert reports.interest_forecast(tagesgeld, 30) > 0
    assert tagesgeld in reports.interest_forecast_csv(30)


def test_turnover_series(reports):
    assert len(reports.daily_turnover_series("2025-03-01", "2025-03-05")) == 5
    assert "Tag;Buchungen" in reports.daily_turnover_csv("2025-03-01", "2025-03-02")


def test_income_figures(reports, bank):
    bank.run_end_of_day("2025-03-31")
    assert reports.fee_income("2025-03-01", "2025-03-31") == 490
    assert reports.interest_paid("2025-03-01", "2025-03-31") > 0
    assert reports.interest_received("2025-03-01", "2025-03-31") > 0
    assert reports.eod_history()


def test_dunning_levels(bank, giro):
    bank.set_overdraft_limit(giro, 0)
    bank.post_booking(giro, -200000, "FEE", at=BOOKED_AT)
    processor = DunningProcessor(bank)
    assert processor.run("2025-03-03")["issued"][0]["level"] == 1
    assert processor.run("2025-03-05")["issued"] == []
    assert processor.run("2025-03-17")["issued"][0]["level"] == 2
    assert processor.run("2025-03-31")["issued"][0]["level"] == 3
    assert bank.getAccount(giro)["status"] == "BLOCKED"
    assert processor.run("2025-04-30")["issued"] == []
    assert len(processor.history(giro)) == 3


def test_dunning_resolves_after_payment(bank, giro):
    bank.set_overdraft_limit(giro, 0)
    bank.post_booking(giro, -200000, "FEE", at=BOOKED_AT)
    processor = DunningProcessor(bank)
    processor.run("2025-03-03")
    bank.post_booking(giro, 500000, "CREDIT", at=BOOKED_AT)
    assert processor.run("2025-03-04")["resolved"] == 1
    assert processor.open_notice(giro) is None


def test_dunning_letter_and_delivery(bank, giro, customer_id):
    bank.set_overdraft_limit(giro, 0)
    bank.post_booking(giro, -200000, "FEE", at=BOOKED_AT)
    processor = DunningProcessor(bank)
    processor.run("2025-03-03")
    notice = processor.open_notice(giro)
    assert "Tilda Rosenthaler" in processor.render_letter(notice["id"])
    with pytest.raises(ValueError):
        processor.render_letter(999)
    assert processor.deliver_letters("2025-03-03") == 1
    assert Mailbox(bank).unread_count(customer_id) == 1


def test_mailbox(bank, customer_id):
    box = Mailbox(bank)
    message_id = box.deliver(customer_id, "Willkommen", "Guten Tag")
    assert box.unread_count(customer_id) == 1
    assert box.list_messages(customer_id)
    assert box.read_message(customer_id, message_id)["subject"] == "Willkommen"
    assert box.unread_count(customer_id) == 0
    other = bank.createCustomer("Ben", "Zaunkoenig")
    assert box.read_message(other, message_id) is None
    assert not box.delete_message(other, message_id)
    assert box.delete_message(customer_id, message_id)


def test_legacy_record_round_trip(giro):
    record = parse_record(format_record(giro, DAY, DAY, -1250, "0020", "Rechnung"))
    assert record["iban"] == giro
    assert record["amount_cents"] == -1250
    assert record["kind"] == "TRANSFER_OUT"
    assert record["purpose"] == "Rechnung"


@pytest.mark.parametrize("line", ["kurz", "X" * 112])
def test_legacy_record_rejects_garbage(line):
    with pytest.raises(LegacyFormatError):
        parse_record(line)


def test_legacy_import(bank, giro):
    before = bank.getBalance(giro)
    text = format_file([(giro, DAY, DAY, 5000, "0051", "Eingang"), (giro, DAY, DAY, -1000, "0020", "Ausgang")])
    assert LegacyImporter(bank).import_text(text) == 2
    assert bank.getBalance(giro) == before + 4000


def test_legacy_import_is_all_or_nothing(bank, giro):
    before = bank.getBalance(giro)
    unknown = build_de_iban("01234500", 777)
    text = format_file([(giro, DAY, DAY, 5000, "0051", ""), (unknown, DAY, DAY, 100, "0051", "")])
    with pytest.raises(LegacyFormatError):
        LegacyImporter(bank).import_text(text)
    assert bank.getBalance(giro) == before


@pytest.mark.parametrize("mutate", [
    lambda text: text.split("\n", 1)[1],
    lambda text: text.rsplit("E0", 1)[0],
    lambda text: text.replace("E00000001", "E00000002"),
    lambda text: text[:-3] + "9\n\n",
])
def test_legacy_file_checks(giro, mutate):
    text = format_file([(giro, DAY, DAY, 5000, "0051", "")])
    with pytest.raises(LegacyFormatError):
        parse_file(mutate(text))
