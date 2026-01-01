"""HTTP API of the transfer service."""
import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Tuple
from urllib.parse import parse_qs, urlparse

from payments.models import TransferRequest, ValidationError
from payments.service import AccountNotFound, TransferRejected, TransferService

log = logging.getLogger("musterbank.payments")

MAX_BODY_BYTES = 64 * 1024
_TRANSFER_PATH = re.compile(r"^/transfers/(\d+)$")
_BALANCE_PATH = re.compile(r"^/accounts/([A-Za-z0-9]+)/balance$")


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "MusterbankPayments/2.3"
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("%s %s", self.address_string(), format % args)

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Any:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise ValidationError("Content-Length is required")
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValidationError("body is too large")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValidationError("body is incomplete")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ValidationError("body is not valid JSON")

    def _service(self) -> TransferService:
        return TransferService(self.server.db_path)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        parsed = urlparse(self.path)
        if parsed.path == "/transfers":
            status, payload = self._list_transfers(parse_qs(parsed.query))
            self._send_json(status, payload)
            return
        match = _TRANSFER_PATH.match(self.path)
        if match:
            status, payload = self._get_transfer(int(match.group(1)))
            self._send_json(status, payload)
            return
        match = _BALANCE_PATH.match(self.path)
        if match:
            status, payload = self._get_balance(match.group(1))
            self._send_json(status, payload)
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/transfers":
            self._send_json(404, {"error": "not found"})
            return
        try:
            request = TransferRequest.from_json(self._read_json())
        except ValidationError as exc:
            self.close_connection = True
            self._send_json(400, {"error": str(exc)})
            return
        status, payload = self._create_transfer(request)
        self._send_json(status, payload)

    def _create_transfer(self, request: TransferRequest) -> Tuple[int, Any]:
        service = self._service()
        try:
            transfer = service.create_transfer(request)
            return 201, transfer.to_json()
        except ValidationError as exc:
            return 400, {"error": str(exc)}
        except AccountNotFound:
            return 404, {"error": "unknown account"}
        except TransferRejected as exc:
            return 409, {"error": "rejected", "reason": str(exc)}
        finally:
            service.close()

    def _get_transfer(self, transfer_id: int) -> Tuple[int, Any]:
        service = self._service()
        try:
            transfer = service.get_transfer(transfer_id)
        finally:
            service.close()
        if transfer is None:
            return 404, {"error": "unknown transfer"}
        return 200, transfer.to_json()

    def _list_transfers(self, query: Any) -> Tuple[int, Any]:
        debtor = query.get("debtor_iban", [""])[0]
        if not debtor:
            return 400, {"error": "debtor_iban is required"}
        try:
            limit = min(int(query.get("limit", ["50"])[0]), 200)
        except ValueError:
            return 400, {"error": "limit must be a number"}
        service = self._service()
        try:
            transfers = service.list_transfers(debtor, limit)
        finally:
            service.close()
        return 200, {"transfers": [transfer.to_json() for transfer in transfers]}

    def _get_balance(self, iban: str) -> Tuple[int, Any]:
        service = self._service()
        try:
            cents = service.get_balance(iban)
        except AccountNotFound:
            return 404, {"error": "unknown account"}
        finally:
            service.close()
        return 200, {"iban": iban, "balance_cents": cents, "balance": cents / 100}


class PaymentsServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: Tuple[str, int], db_path: str):
        super().__init__(address, ApiHandler)
        self.db_path = db_path
