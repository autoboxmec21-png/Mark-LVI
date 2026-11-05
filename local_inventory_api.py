"""Local inventory API for Mark-LVI.

This module serves a local JSON inventory over HTTP on 127.0.0.1 only. It is
explicitly limited to read-only inventory data that the user has already placed in
config/local_inventory.json. It does not scan or probe any network or device.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parent
DEFAULT_FILE = ROOT / "config" / "local_inventory.json"
HOST = "127.0.0.1"
PORT = 8765


def inventory_path() -> Path:
    """Return the path to the inventory file, creating the directory if needed."""
    path = DEFAULT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps({"devices": []}, indent=2),
            encoding="utf-8",
        )
    return path


class InventoryRequestHandler(BaseHTTPRequestHandler):
    """A minimal read-only HTTP endpoint for a local device inventory."""

    def do_GET(self):
        if self.path not in ("/devices", "/devices/"):
            self.send_error(404, "Not found")
            return

        token = os.environ.get("MARK_LVI_INVENTORY_TOKEN", "")
        if token:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {token}":
                self.send_error(401, "Unauthorized")
                return

        try:
            payload = json.loads(inventory_path().read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Inventory JSON must contain a top-level object.")
            devices = payload.get("devices", [])
            if not isinstance(devices, list):
                raise ValueError("'devices' must be a list.")
        except Exception as exc:  # pragma: no cover - server-side error path
            self.send_error(500, f"Inventory read failed: {exc}")
            return

        body = json.dumps({"devices": devices}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[inventory-api] {self.address_string()} - {fmt % args}")


def run_server(host: str = HOST, port: int = PORT, token: str | None = None) -> tuple[HTTPServer, Thread]:
    """Start a local HTTP server that only serves inventory data.

    Returns the HTTPServer instance and a background thread.
    """
    from threading import Thread

    if token is not None:
        os.environ["MARK_LVI_INVENTORY_TOKEN"] = str(token)

    server = HTTPServer((host, port), InventoryRequestHandler)
    thread = Thread(target=server.serve_forever, daemon=True, name="mark-local-inventory")
    thread.start()
    return server, thread


if __name__ == "__main__":
    token = os.environ.get("MARK_LVI_INVENTORY_TOKEN")
    print(f"Starting local inventory API on http://{HOST}:{PORT}/devices")
    if token:
        print("Authorization required: Authorization: Bearer <MARK_LVI_INVENTORY_TOKEN>")
    else:
        print("No Authorization token configured; the endpoint is open on localhost only.")
    run_server(HOST, PORT, token)
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping local inventory API.")
