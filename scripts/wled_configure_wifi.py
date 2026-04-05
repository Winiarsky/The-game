#!/usr/bin/env python3
from __future__ import annotations

import argparse
import socket
import time
from typing import Iterable
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://4.3.2.1"


def _post_form(base_url: str, fields: dict[str, str], *, timeout: float) -> tuple[int, str]:
    body = parse.urlencode(fields).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}/settings/wifi",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8", errors="replace")
        return response.getcode(), payload


def _candidate_payloads(
    *,
    ssid: str,
    password: str,
    mdns: str,
    ap_ssid: str | None,
    ap_password: str | None,
) -> list[dict[str, str]]:
    common_legacy = {
        "CM": mdns,
        "AS": ap_ssid or "",
        "AP": ap_password or "",
    }
    common_modern = {
        "CM": mdns,
        "AS": ap_ssid or "",
        "AP": ap_password or "",
    }
    return [
        {
            **common_modern,
            "CS0": ssid,
            "CP0": password,
            "save": "1",
        },
        {
            **common_legacy,
            "CS": ssid,
            "CP": password,
            "save": "1",
        },
    ]


def _looks_successful(status: int, body: str) -> bool:
    lowered = body.lower()
    return status in {200, 204} or "save & connect" in lowered or "settings saved" in lowered


def _try_resolve(host: str) -> str | None:
    try:
        return socket.gethostbyname(host)
    except OSError:
        return None


def _wait_for_candidates(candidates: Iterable[str], *, seconds: float, interval: float) -> tuple[str, str] | None:
    started = time.monotonic()
    while (time.monotonic() - started) < seconds:
        for host in candidates:
            ip = _try_resolve(host)
            if ip:
                return host, ip
        time.sleep(interval)
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Konfiguruje WLED AP do lokalnej sieci Wi‑Fi przez formularz /settings/wifi."
    )
    parser.add_argument("--ssid", required=True, help="SSID sieci domowej 2.4 GHz.")
    parser.add_argument("--password", required=True, help="Hasło do sieci domowej.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Adres WLED AP. Domyślnie http://4.3.2.1",
    )
    parser.add_argument(
        "--mdns",
        default="wled",
        help="Nazwa mDNS po konfiguracji, np. wled albo board-leds.",
    )
    parser.add_argument(
        "--ap-ssid",
        default="",
        help="Opcjonalnie: nowa nazwa AP WLED. Puste zostawia domyślne zachowanie.",
    )
    parser.add_argument(
        "--ap-password",
        default="",
        help="Opcjonalnie: nowe hasło AP WLED. Puste zostawia domyślne zachowanie.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=45.0,
        help="Ile czekać na pojawienie się urządzenia po zapisaniu ustawień.",
    )
    parser.add_argument(
        "--check-host",
        action="append",
        default=[],
        help="Dodatkowy host do sprawdzenia po restarcie, np. --check-host board-leds.local",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout pojedynczego requestu HTTP.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.ssid.strip():
        parser.error("--ssid nie może być pusty")
    if not args.password:
        parser.error("--password nie może być puste")

    print(f"Łączę się z {args.base_url} i próbuję zapisać konfigurację Wi‑Fi dla SSID: {args.ssid}")
    submitted = False
    last_error: Exception | None = None

    for payload in _candidate_payloads(
        ssid=args.ssid.strip(),
        password=args.password,
        mdns=args.mdns.strip(),
        ap_ssid=args.ap_ssid.strip() or None,
        ap_password=args.ap_password or None,
    ):
        try:
            status, body = _post_form(args.base_url, payload, timeout=args.timeout)
            if _looks_successful(status, body):
                submitted = True
                break
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if not submitted:
        print("Nie udało się wysłać konfiguracji do WLED.")
        if last_error is not None:
            print(f"Ostatni błąd: {last_error}")
        print("Upewnij się, że komputer jest połączony z hotspotem WLED i że działa adres 4.3.2.1.")
        return 1

    print("Konfiguracja wysłana. WLED powinien się przełączyć do Twojej sieci i zrestartować.")
    print("Odłącz się od hotspotu WLED i wróć na swoją normalną sieć Wi‑Fi.")

    candidates = [f"{args.mdns}.local", "wled.local", *args.check_host]
    print(f"Próbuję odnaleźć urządzenie przez mDNS przez maks. {args.wait_seconds:.0f} s...")
    found = _wait_for_candidates(candidates, seconds=args.wait_seconds, interval=3.0)
    if found is None:
        print("Nie udało się automatycznie znaleźć urządzenia po nazwie.")
        print("Sprawdź listę klientów DHCP w routerze albo użyj skanera sieci.")
        return 0

    host, ip = found
    print(f"Urządzenie wygląda na dostępne pod: http://{host}  (IP: {ip})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
