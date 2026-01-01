#!/usr/bin/env python3
"""Central entry point: setup, data, services, tests and end of day."""
import argparse
import glob
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(ROOT, "vendor")
VENV = os.path.join(ROOT, ".venv")
DEPS = os.path.join(ROOT, ".deps")
DATA = os.path.join(ROOT, "data")
RUN_DIR = os.path.join(DATA, "run")
DEFAULT_DB = os.path.join(DATA, "musterbank.sqlite")
EOD_DATE = "2025-12-31"
SERVICES = {
    "payments": {"port": 8081, "module": "payments", "health": "/health"},
    "web": {"port": 8080, "module": "web", "health": "/login"},
}


def _venv_python():
    return os.path.join(VENV, "bin", "python")


def _setup_venv():
    try:
        subprocess.run([sys.executable, "-m", "venv", VENV], check=True, capture_output=True)
        subprocess.run(
            [_venv_python(), "-m", "pip", "install", "--no-index", "--find-links", VENDOR, "-r",
             os.path.join(ROOT, "requirements-dev.txt")],
            check=True, capture_output=True,
        )
    except (subprocess.CalledProcessError, OSError):
        shutil.rmtree(VENV, ignore_errors=True)
        return False
    return True


def _setup_unpack():
    os.makedirs(DEPS, exist_ok=True)
    for wheel in glob.glob(os.path.join(VENDOR, "*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(DEPS)


def cmd_setup(_args):
    if _setup_venv():
        print("Testwerkzeuge in .venv installiert (pip, nur aus vendor/).")
    else:
        _setup_unpack()
        print("pip oder venv fehlen: Testwerkzeuge nach .deps entpackt.")


def _test_command():
    """Interpreter and environment that can import the test tools."""
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT
    if os.path.exists(_venv_python()):
        return _venv_python(), env
    if os.path.isdir(DEPS):
        env["PYTHONPATH"] = os.pathsep.join([ROOT, DEPS])
        return sys.executable, env
    sys.exit("Bitte zuerst ausführen: python3 run.py setup")


def cmd_test(args):
    python, env = _test_command()
    if args.cov:
        code = subprocess.call(
            [python, "-m", "coverage", "run", "--source=core,payments,statements,web,tools", "-m", "pytest", "tests"]
            + args.pytest_args,
            cwd=ROOT, env=env,
        )
        subprocess.call([python, "-m", "coverage", "report", "--skip-empty"], cwd=ROOT, env=env)
        sys.exit(code)
    sys.exit(subprocess.call([python, "-m", "pytest", "tests"] + args.pytest_args, cwd=ROOT, env=env))


def cmd_data(args):
    sys.path.insert(0, ROOT)
    from tools.generate_data import main as generate_main
    generate_main(["--db", args.db, "--customers", str(args.customers), "--seed", str(args.seed)])


def _pid_file(name):
    return os.path.join(RUN_DIR, name + ".pid")


def _read_pid(name):
    try:
        with open(_pid_file(name)) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def _is_running(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_for(service):
    url = "http://127.0.0.1:%d%s" % (service["port"], service["health"])
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    return False


def cmd_start(args):
    if not os.path.exists(args.db):
        sys.exit("Keine Datenbank gefunden. Bitte zuerst ausführen: python3 run.py data")
    os.makedirs(RUN_DIR, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT
    for name, service in SERVICES.items():
        if _is_running(_read_pid(name)):
            print("%s läuft bereits." % name)
            continue
        with open(os.path.join(RUN_DIR, name + ".log"), "ab") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", service["module"], "--db", args.db, "--port", str(service["port"])],
                cwd=ROOT, env=env, stdout=log, stderr=log, start_new_session=True,
            )
        with open(_pid_file(name), "w") as fh:
            fh.write(str(process.pid))
        if not _wait_for(service):
            sys.exit("%s ist nicht gestartet, siehe data/run/%s.log" % (name, name))
        print("%s läuft auf http://127.0.0.1:%d" % (name, service["port"]))


def cmd_stop(_args):
    for name in SERVICES:
        pid = _read_pid(name)
        if _is_running(pid):
            os.kill(pid, signal.SIGTERM)
            print("%s gestoppt." % name)
        if os.path.exists(_pid_file(name)):
            os.remove(_pid_file(name))


def cmd_status(_args):
    for name, service in SERVICES.items():
        state = "läuft" if _is_running(_read_pid(name)) else "gestoppt"
        print("%-9s %-9s Port %d" % (name, state, service["port"]))


def _copy_database(source, target):
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()


def cmd_eod(args):
    if not os.path.exists(args.db):
        sys.exit("Keine Datenbank gefunden. Bitte zuerst ausführen: python3 run.py data")
    sys.path.insert(0, ROOT)
    from core.bank import BankCore
    from core.money import format_eur
    with tempfile.TemporaryDirectory() as tmp:
        path = args.db
        if not args.commit:
            path = os.path.join(tmp, "eod.sqlite")
            _copy_database(args.db, path)
        bank = BankCore(path)
        started = time.perf_counter()
        result = bank.run_end_of_day(args.date)
        elapsed = time.perf_counter() - started
        bank.close()
    print("Geschäftstag:  %s" % result["business_date"])
    print("Konten:        %d" % result["accounts"])
    print("Zinsen:        %s" % format_eur(result["interest_cents"]))
    print("Gebühren:      %s" % format_eur(result["fee_cents"]))
    print("Prüfsumme:     %s" % result["checksum"])
    print("Laufzeit:      %.2f s" % elapsed)
    if not args.commit:
        print("Testlauf auf einer Kopie, die Datenbank bleibt unverändert (--commit schreibt).")


def cmd_loadgen(args):
    sys.path.insert(0, ROOT)
    from tools.loadgen import main as loadgen_main
    loadgen_main(["--db", args.db, "--requests", str(args.requests), "--concurrency", str(args.concurrency)])


def main():
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description="Musterbank AG")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("setup", help="Testwerkzeuge aus vendor/ einrichten").set_defaults(func=cmd_setup)

    data = commands.add_parser("data", help="Demodaten erzeugen")
    data.add_argument("--db", default=DEFAULT_DB)
    data.add_argument("--customers", type=int, default=2000)
    data.add_argument("--seed", type=int, default=20250101)
    data.set_defaults(func=cmd_data)

    start = commands.add_parser("start", help="Web und Payments starten")
    start.add_argument("--db", default=DEFAULT_DB)
    start.set_defaults(func=cmd_start)
    commands.add_parser("stop", help="Dienste stoppen").set_defaults(func=cmd_stop)
    commands.add_parser("status", help="Status der Dienste").set_defaults(func=cmd_status)

    test = commands.add_parser("test", help="Tests ausführen")
    test.add_argument("--cov", action="store_true", help="mit Coverage-Bericht")
    test.add_argument("pytest_args", nargs=argparse.REMAINDER)
    test.set_defaults(func=cmd_test)

    eod = commands.add_parser("eod", help="Tagesendverarbeitung")
    eod.add_argument("--db", default=DEFAULT_DB)
    eod.add_argument("--date", default=EOD_DATE)
    eod.add_argument("--commit", action="store_true", help="in die Datenbank schreiben statt auf einer Kopie zu rechnen")
    eod.set_defaults(func=cmd_eod)

    loadgen = commands.add_parser("loadgen", help="Last gegen die lokale API")
    loadgen.add_argument("--db", default=DEFAULT_DB)
    loadgen.add_argument("--requests", type=int, default=500)
    loadgen.add_argument("--concurrency", type=int, default=8)
    loadgen.set_defaults(func=cmd_loadgen)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
