"""Isolated UI audit server and Chrome; opt in to hardware with explicit addresses.

Requires installed Chrome, requests and websocket-client (browser driver).
Does not write production save files. The read-only LED endpoint adds evidence,
not game controls. Use Ctrl+C to close Chrome and release the board.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path[:0] = [
    str(Path(__file__).resolve().parents[1] / "src"),
    str(Path(__file__).resolve().parents[1]),
]
from flask import g, request
from werkzeug.serving import make_server
from dnd_board_game.ui.exploration_app import ExplorationUiSession, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial-port", required=True)
    parser.add_argument("--wled-url", required=True)
    parser.add_argument(
        "--report", type=Path, default=Path("docs/playtests/2026-09-18-misja0")
    )
    parser.add_argument(
        "--runtime", type=Path, default=Path("/tmp/mission0-audit-runtime")
    )
    args = parser.parse_args()
    args.report.mkdir(parents=True, exist_ok=True)
    args.runtime.mkdir(parents=True, exist_ok=True)
    session = ExplorationUiSession(
        "content/scenarios/misja_0_dzwon/scenario.json",
        save_dir=args.runtime / "saves",
        observation_dir=args.runtime / "observations",
        automatic_checkpoints=True,
    )
    session.configure_board(
        backend="hardware",
        board_url="",
        board_serial_port=args.serial_port,
        wled_url=args.wled_url,
        scan_timeout_s=30,
    )
    app = create_app(session)

    @app.before_request
    def start() -> None:
        g.audit_started = time.monotonic()

    @app.after_request
    def record(response: Any) -> Any:
        if request.path.startswith("/api/") or request.method == "POST":
            entry = dict(
                time=time.time(),
                path=request.path,
                method=request.method,
                status=response.status_code,
                ms=round((time.monotonic() - g.audit_started) * 1000),
            )
            if request.method == "POST":
                entry["input"] = request.get_json(silent=True) or request.form.to_dict(
                    flat=False
                )
            if response.status_code >= 400:
                entry["error"] = response.get_data(as_text=True)[:1500]
            with (args.report / "http.jsonl").open("a") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return response

    @app.get("/__audit/led-status")
    def led_status() -> dict[str, Any]:
        return (
            session.board_adapter.connection.led_status if session.board_adapter else {}
        )

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = make_server("127.0.0.1", 8765, app, threaded=True)
    with (args.runtime / "chrome.log").open("w") as chrome_log:
        chrome = subprocess.Popen(
            [
                "google-chrome",
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--disable-background-networking",
                "--no-proxy-server",
                "--remote-debugging-port=9223",
                "--remote-allow-origins=*",
                "--user-data-dir=" + str(args.runtime / "chrome-profile"),
                "http://127.0.0.1:8765/",
            ],
            stdout=subprocess.DEVNULL,
            stderr=chrome_log,
        )

        def terminate(*_args: Any) -> None:
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, terminate)
        print("Audit UI: http://127.0.0.1:8765/ — CDP: 9223", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            chrome.terminate()
            session.shutdown_board()
            server.server_close()


if __name__ == "__main__":
    main()
