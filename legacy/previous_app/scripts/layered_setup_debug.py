from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
for path in (ROOT_DIR, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from board import Connection
from layered_scenarios import build_layered_setup_plan, load_layered_scenario


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug LED setup dla warstwowego scenariusza.")
    parser.add_argument("--scenario", required=True, help="Nazwa scenariusza z katalogu scenarios_layered lub ścieżka do pliku.")
    parser.add_argument("--board-backend", choices=["hardware", "simulator"], default="hardware")
    parser.add_argument("--board-url", help="URL backendu symulatora planszy.")
    parser.add_argument("--board-serial-port", help="Port USB planszy.")
    parser.add_argument("--wled-url", help="Adres WLED, np. http://192.168.0.50.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_layered_scenario(args.scenario)
    plan = build_layered_setup_plan(payload)
    conn = Connection(
        backend=args.board_backend,
        simulator_url=args.board_url,
        serial_port=args.board_serial_port,
        wled_url=args.wled_url,
    )

    try:
        print(f"Scenariusz: {payload.get('name') or args.scenario}")
        print(f"Kroki setupu: {len(plan)}")
        for index, step in enumerate(plan, start=1):
            positions = [tuple(pos) for pos in list(step.get("positions") or [])]
            color = list(step.get("color") or [0, 255, 0])
            print(f"\n[{index}/{len(plan)}] {step.get('prompt')}")
            if step.get("edges"):
                print(f"Krawędzie: {step['edges']}")
            if positions:
                print(f"Pola: {positions}")
                conn.set_leds(positions, color)
            try:
                answer = input("Enter = następny krok, q = wyjście: ").strip().lower()
            except EOFError:
                break
            finally:
                conn.leds_off()
            if answer == "q":
                break
    finally:
        try:
            conn.leds_off()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
