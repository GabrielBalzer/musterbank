"""Online banking: server-side rendered pages on top of core, statements and the transfer API."""
import html
import json
import os
import re
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from string import Template
from urllib.parse import parse_qs, urlparse

from core.bank import BankCore
from core.errors import BankError, UnknownAccount
from core.iban import format_iban, normalize_iban
from core.mailbox import Mailbox
from core.money import format_eur, parse_eur
from statements.render import render_csv
from statements.service import StatementService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
STATIC_TYPES = {".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".js": "text/javascript; charset=utf-8"}
DEMO_PIN = "1234"
SESSION_HOURS = 8
COOKIE_NAME = "mb_session"
_ACCOUNT_PATH = re.compile(r"^/accounts/([A-Z0-9]+)$")
_STATEMENT_PATH = re.compile(r"^/statements/([A-Z0-9]+)$")
_MESSAGE_PATH = re.compile(r"^/mailbox/(\d+)$")


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def render(template_file, **context):
    with open(os.path.join(TEMPLATE_DIR, template_file), encoding="utf-8") as fh:
        template = Template(fh.read())
    return template.safe_substitute(**context)


def page(body, logged_in=True):
    nav = render("nav.html") if logged_in else ""
    return render("layout.html", nav=nav, body=body)


class WebHandler(BaseHTTPRequestHandler):
    server_version = "MusterbankWeb/1.8"

    def log_message(self, format, *args):
        pass

    # ---- plumbing ----

    def _send_html(self, status, content, cookie=None):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location, cookie=None):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _not_found(self):
        self._send_html(404, page("<p>Seite nicht gefunden</p>", logged_in=False))

    def _form(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8", "replace")
        return {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}

    def _session_token(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(COOKIE_NAME)
        return morsel.value if morsel else None

    def _current_customer(self, bank):
        token = self._session_token()
        if not token:
            return None
        row = bank.db.execute(
            "SELECT customer_id, expires_at FROM web_sessions WHERE token = ?", (token,)
        ).fetchone()
        if row is None or row["expires_at"] < _now_iso():
            return None
        return bank.getCustomer(row["customer_id"])

    def _own_account(self, bank, customer, iban):
        try:
            account = bank.getAccount(iban)
        except UnknownAccount:
            return None
        return account if account["customer_id"] == customer["id"] else None

    # ---- routing ----

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/static/"):
            self._serve_static(path[len("/static/"):])
            return
        bank = BankCore(self.server.db_path)
        try:
            if path == "/login":
                self._send_html(200, self._login_page())
                return
            customer = self._current_customer(bank)
            if customer is None:
                self._redirect("/login")
                return
            if path == "/":
                self._send_html(200, self._overview_page(bank, customer))
                return
            if path == "/transfer":
                self._send_html(200, self._transfer_page(bank, customer))
                return
            if path == "/profile":
                self._send_html(200, self._profile_page(customer))
                return
            if path == "/move":
                self._send_html(200, self._move_page(bank, customer))
                return
            if path == "/mailbox":
                self._send_html(200, self._mailbox_page(bank, customer))
                return
            match = _MESSAGE_PATH.match(path)
            if match:
                self._message_page(bank, customer, int(match.group(1)))
                return
            match = _ACCOUNT_PATH.match(path)
            if match:
                self._account_page(bank, customer, match.group(1))
                return
            match = _STATEMENT_PATH.match(path)
            if match:
                self._statement_page(bank, customer, match.group(1), parse_qs(parsed.query))
                return
            self._not_found()
        finally:
            bank.close()

    def do_POST(self):
        path = urlparse(self.path).path
        form = self._form()
        bank = BankCore(self.server.db_path)
        try:
            if path == "/login":
                self._handle_login(bank, form)
                return
            customer = self._current_customer(bank)
            if customer is None:
                self._redirect("/login")
                return
            if path == "/logout":
                self._handle_logout(bank)
            elif path == "/transfer":
                self._handle_transfer(bank, customer, form)
            elif path == "/profile":
                self._handle_profile(bank, customer, form)
            elif path == "/move":
                self._handle_move(bank, customer, form)
            else:
                self._not_found()
        finally:
            bank.close()

    def _serve_static(self, name):
        target = os.path.normpath(os.path.join(STATIC_DIR, name))
        ext = os.path.splitext(target)[1]
        if not target.startswith(STATIC_DIR + os.sep) or ext not in STATIC_TYPES or not os.path.isfile(target):
            self._not_found()
            return
        with open(target, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", STATIC_TYPES[ext])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- login ----

    def _login_page(self, error=""):
        error_html = '<div class="error">%s</div>' % esc(error) if error else ""
        return page(render("login.html", error=error_html), logged_in=False)

    def _handle_login(self, bank, form):
        customer = bank.get_customer_by_no(form.get("customer_no", "").strip())
        if customer is None or not secrets.compare_digest(form.get("pin", ""), DEMO_PIN):
            self._send_html(401, self._login_page("Kundennummer oder PIN ist falsch."))
            return
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        bank.db.execute(
            "INSERT INTO web_sessions (token, customer_id, expires_at) VALUES (?, ?, ?)",
            (token, customer["id"], expires.strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
        self._redirect("/", "%s=%s; HttpOnly; SameSite=Strict; Path=/" % (COOKIE_NAME, token))

    def _handle_logout(self, bank):
        bank.db.execute("DELETE FROM web_sessions WHERE token = ?", (self._session_token(),))
        self._redirect("/login", "%s=; Max-Age=0; Path=/" % COOKIE_NAME)

    # ---- pages ----

    def _overview_page(self, bank, customer):
        summary = bank.customer_summary(customer["id"])
        rows = []
        for acct in summary["accounts"]:
            rows.append(render("overview_row.html", iban=esc(acct["iban"]), iban_display=esc(format_iban(acct["iban"])),
                               product=esc(acct["product"]), balance=esc(acct["balance"])))
        body = render("overview.html", name=esc(summary["name"]), rows="\n".join(rows), total=esc(summary["total"]))
        return page(body)

    def _account_page(self, bank, customer, iban):
        account = self._own_account(bank, customer, iban)
        if account is None:
            self._not_found()
            return
        rows = []
        for line in StatementService(bank).recent_transactions(account["iban"], 50):
            rows.append(render("booking_row.html", booking_date=esc(line["booking_date"]),
                               value_date=esc(line["value_date"]), counterparty=esc(line["counterparty"]),
                               purpose=esc(line["purpose"]), amount=esc(line["amount"])))
        body = render("account.html", iban=esc(account["iban"]), iban_display=esc(format_iban(account["iban"])),
                      balance=esc(format_eur(account["balance_cents"])), rows="\n".join(rows))
        self._send_html(200, page(body))

    def _statement_page(self, bank, customer, iban, query):
        account = self._own_account(bank, customer, iban)
        if account is None:
            self._not_found()
            return
        month = query.get("month", ["2025-12"])[0]
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", month):
            self._not_found()
            return
        statement = StatementService(bank).monthly_statement(account["iban"], int(month[:4]), int(month[5:]))
        if query.get("format", [""])[0] == "csv":
            body = render_csv(statement).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        rows = []
        for line in statement["lines"]:
            rows.append(render("booking_row.html", booking_date=esc(line["booking_date"]),
                               value_date=esc(line["value_date"]), counterparty=esc(line["counterparty"]),
                               purpose=esc(line["purpose"]), amount=esc(line["amount"])))
        months = StatementService(bank).available_months(account["iban"])[:12]
        month_links = " ".join('<a href="/statements/%s?month=%s">%s</a>' % (esc(account["iban"]), esc(m), esc(m)) for m in months)
        content = render("statement.html", iban=esc(account["iban"]), iban_display=esc(format_iban(account["iban"])),
                         month=esc(month), month_links=month_links, opening=esc(format_eur(statement["opening_cents"])),
                         closing=esc(format_eur(statement["closing_cents"])), rows="\n".join(rows))
        self._send_html(200, page(content))

    def _move_page(self, bank, customer, error="", success=""):
        options = []
        for acct in bank.get_account_rows_for_customer(customer["id"]):
            if acct["product_code"] == "FESTGELD":
                continue
            label = "%s (%s)" % (format_iban(acct["iban"]), acct["product_name"])
            options.append('<option value="%s">%s</option>' % (esc(acct["iban"]), esc(label)))
        message = ""
        if error:
            message = '<div class="error">%s</div>' % esc(error)
        elif success:
            message = '<div class="success">%s</div>' % esc(success)
        body = render("move.html", message=message, options="\n".join(options))
        return page(body)

    def _handle_move(self, bank, customer, form):
        source = self._own_account(bank, customer, form.get("from_iban", ""))
        target = self._own_account(bank, customer, form.get("to_iban", ""))
        if source is None or target is None or source["iban"] == target["iban"]:
            self._send_html(400, self._move_page(bank, customer, error="Bitte zwei verschiedene eigene Konten auswählen."))
            return
        try:
            cents = parse_eur(form.get("amount", ""))
            bank.move_between_own_accounts(source["iban"], target["iban"], cents)
        except ValueError:
            self._send_html(400, self._move_page(bank, customer, error="Bitte einen gültigen Betrag eingeben."))
            return
        except BankError:
            self._send_html(409, self._move_page(bank, customer, error="Die Umbuchung wurde abgelehnt."))
            return
        self._send_html(200, self._move_page(bank, customer, success="Die Umbuchung wurde ausgeführt."))

    def _mailbox_page(self, bank, customer):
        rows = []
        for message in Mailbox(bank).list_messages(customer["id"]):
            status = "gelesen" if message["read_at"] else "neu"
            rows.append(render("mailbox_row.html", id=message["id"], created_at=esc(message["created_at"][:10]),
                               subject=esc(message["subject"]), status=status))
        body = render("mailbox.html", rows="\n".join(rows))
        return page(body)

    def _message_page(self, bank, customer, message_id):
        message = Mailbox(bank).read_message(customer["id"], message_id)
        if message is None:
            self._not_found()
            return
        body = render("message.html", subject=esc(message["subject"]), created_at=esc(message["created_at"][:10]),
                      text=esc(message["body"]))
        self._send_html(200, page(body))

    def _profile_page(self, customer, error="", success=""):
        message = ""
        if error:
            message = '<div class="error">%s</div>' % esc(error)
        elif success:
            message = '<div class="success">%s</div>' % esc(success)
        body = render("profile.html", message=message, customer_no=esc(customer["customer_no"]),
                      street=esc(customer["street"]), zip_code=esc(customer["zip"]), city=esc(customer["city"]),
                      email=esc(customer["email"]))
        return page(body)

    def _handle_profile(self, bank, customer, form):
        street = form.get("street", "").strip()
        zip_code = form.get("zip", "").strip()
        city = form.get("city", "").strip()
        email = form.get("email", "").strip()
        if not street or not city or not re.match(r"^[0-9]{5}$", zip_code):
            self._send_html(400, self._profile_page(customer, error="Bitte eine vollständige Anschrift angeben."))
            return
        if "@" not in email:
            self._send_html(400, self._profile_page(customer, error="Bitte eine gültige E-Mail-Adresse angeben."))
            return
        bank.updateCustomerAddress(customer["id"], street, zip_code, city)
        bank.update_customer_email(customer["id"], email)
        self._send_html(200, self._profile_page(bank.getCustomer(customer["id"]), success="Ihre Daten wurden gespeichert."))

    def _transfer_page(self, bank, customer, error="", success="", form=None):
        form = form or {}
        options = []
        for acct in bank.get_account_rows_for_customer(customer["id"]):
            if acct["product_code"] != "GIRO":
                continue
            selected = " selected" if acct["iban"] == form.get("debtor_iban") else ""
            options.append('<option value="%s"%s>%s</option>' % (esc(acct["iban"]), selected, esc(format_iban(acct["iban"]))))
        message = ""
        if error:
            message = '<div class="error">%s</div>' % esc(error)
        elif success:
            message = '<div class="success">%s</div>' % esc(success)
        body = render("transfer.html", message=message, options="\n".join(options),
                      creditor_name=esc(form.get("creditor_name", "")), creditor_iban=esc(form.get("creditor_iban", "")),
                      amount=esc(form.get("amount", "")), purpose=esc(form.get("purpose", "")))
        return page(body)

    def _handle_transfer(self, bank, customer, form):
        debtor = normalize_iban(form.get("debtor_iban", ""))
        if self._own_account(bank, customer, debtor) is None:
            self._send_html(400, self._transfer_page(bank, customer, error="Bitte ein eigenes Konto auswählen.", form=form))
            return
        try:
            amount_cents = parse_eur(form.get("amount", ""))
        except ValueError:
            self._send_html(400, self._transfer_page(bank, customer, error="Bitte einen gültigen Betrag eingeben.", form=form))
            return
        payload = {
            "debtor_iban": debtor,
            "creditor_iban": form.get("creditor_iban", ""),
            "creditor_name": form.get("creditor_name", ""),
            "amount": amount_cents / 100,
            "purpose": form.get("purpose", ""),
        }
        status, answer = call_payments(self.server.payments_url, payload)
        if status == 201:
            self._send_html(200, self._transfer_page(bank, customer, success="Die Überweisung wurde ausgeführt."))
            return
        self._send_html(status if status < 500 else 502,
                        self._transfer_page(bank, customer, error=_transfer_error(status, answer), form=form))


def _transfer_error(status, answer):
    if status == 409:
        return "Die Überweisung wurde abgelehnt, das Konto ist nicht ausreichend gedeckt oder gesperrt."
    if status in (400, 404):
        return "Bitte prüfen Sie Ihre Eingaben: %s" % answer.get("error", "ungültige Angaben")
    return "Die Überweisung ist derzeit nicht möglich."


def call_payments(base_url, payload):
    request = urllib.request.Request(
        base_url + "/transfers",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except ValueError:
            return exc.code, {}
    except urllib.error.URLError:
        return 503, {}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class WebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, db_path, payments_url):
        super().__init__(address, WebHandler)
        self.db_path = db_path
        self.payments_url = payments_url.rstrip("/")
