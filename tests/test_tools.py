import os
import subprocess
import sys

import pytest

from core.bank import BankCore
from tools import admin, generate_data, loadgen, reconcile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def small_db(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("data") / "small.sqlite")
    generate_data.generate(path, customers=25, seed=7)
    return path


def test_generator_counts(small_db):
    bank = BankCore(small_db)
    assert len(bank.listCustomers(limit=100)) == 25
    assert bank.db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] > 500
    bank.close()


def test_generated_balances_match_journal(small_db):
    bank = BankCore(small_db)
    assert reconcile.find_differences(bank) == []
    bank.close()


def test_generated_ibans_are_valid(small_db):
    from core.iban import validate_iban

    bank = BankCore(small_db)
    rows = bank.db.execute("SELECT iban FROM accounts").fetchall()
    assert all(validate_iban(row["iban"]) for row in rows)
    bank.close()


def test_generator_is_reproducible(tmp_path):
    results = []
    for name in ("a.sqlite", "b.sqlite"):
        path = str(tmp_path / name)
        generate_data.generate(path, customers=10, seed=3)
        bank = BankCore(path)
        results.append(bank.run_end_of_day("2025-12-31")["checksum"])
        bank.close()
    assert results[0] == results[1]


def test_generator_main(tmp_path, capsys):
    generate_data.main(["--db", str(tmp_path / "x.sqlite"), "--customers", "3"])
    assert "3 Kunden" in capsys.readouterr().out


def test_loadgen(db_path, bank, giro, payments_url):
    assert loadgen.load_debtors(db_path) == [giro]
    result = loadgen.run_load(payments_url, [giro], requests=8, concurrency=2)
    assert result["requests"] == 8
    assert result["statuses"]


def test_loadgen_main(db_path, bank, giro, payments_url, capsys):
    loadgen.main(["--db", db_path, "--url", payments_url, "--requests", "4", "--concurrency", "2"])
    assert "Anfragen" in capsys.readouterr().out


@pytest.mark.parametrize("arguments,expected", [
    (["customer", "e"], "Treffer"),
    (["report", "products"], "Produkt"),
    (["report", "overdrafts"], "IBAN"),
    (["report", "month", "--period", "2025-06"], "Art"),
    (["report", "forecast", "--period", "30"], "Schaetzung"),
    (["accounts", "K00000001"], "Summe"),
])
def test_admin_reports(small_db, capsys, arguments, expected):
    admin.main(["--db", small_db] + arguments)
    assert expected in capsys.readouterr().out


def test_admin_account_commands(db_path, bank, giro, capsys):
    admin.main(["--db", db_path, "bookings", giro])
    admin.main(["--db", db_path, "block", giro])
    assert bank.getAccount(giro)["status"] == "BLOCKED"
    admin.main(["--db", db_path, "unblock", giro])
    admin.main(["--db", db_path, "limit", giro, "100,00"])
    assert bank.getAccount(giro)["overdraft_limit_cents"] == 10000
    admin.main(["--db", db_path, "dunning", "2025-03-03"])
    assert "Mahnungen" in capsys.readouterr().out


def test_admin_unknown_customer(db_path, bank):
    with pytest.raises(SystemExit):
        admin.main(["--db", db_path, "accounts", "K99999999"])


def test_reconcile_reports_differences(db_path, bank, giro, capsys):
    assert reconcile.main(["--db", db_path]) == 0
    bank.db.execute("UPDATE accounts SET balance_cents = balance_cents + 1 WHERE iban = ?", (giro,))
    assert reconcile.main(["--db", db_path]) == 1
    assert giro in capsys.readouterr().out


def test_run_eod_on_copy(small_db):
    output = subprocess.run([sys.executable, "run.py", "eod", "--db", small_db], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert "Prüfsumme" in output
    bank = BankCore(small_db)
    assert bank.db.execute("SELECT COUNT(*) FROM eod_runs").fetchone()[0] == 0
    bank.close()


def test_schema_version_is_current(bank):
    from core.db import MIGRATIONS_DIR, current_version

    assert current_version(bank.db) == len(os.listdir(MIGRATIONS_DIR))
