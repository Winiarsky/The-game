#!/usr/bin/env python3
"""Test v2 board presses against the 20x30 serpentine WLED mapping."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from board.connection import _open_serial_probe, _WledClient
from board.serial_v2 import SerialV2
from board.settings import hardware_scan_config, load_board_config, wled_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help='Port ESP32, np. /dev/ttyUSB0')
    parser.add_argument('--wled', help='Adres WLED, np. http://192.168.0.165')
    parser.add_argument('--dry-run', action='store_true', help='Odczyt USB bez sterowania LED')
    parser.add_argument('--color', default='FF0000')
    parser.add_argument('--brightness', type=int, default=180)
    args = parser.parse_args()
    if len(args.color) != 6 or any(c not in '0123456789abcdefABCDEF' for c in args.color):
        parser.error('--color wymaga sześciu cyfr HEX')
    config = load_board_config()
    scan = hardware_scan_config(config)
    if args.port:
        scan['serial_port'] = args.port
    lights = wled_config(config)
    if args.wled:
        lights['base_url'] = args.wled
    port = _open_serial_probe(scan)
    client = SerialV2(port.serial_handle, port.info)
    wled = None if args.dry_run else _WledClient(lights)
    color = [int(args.color[i:i + 2], 16) for i in (0, 2, 4)]
    index = 0
    try:
        print(f'Firmware v2 na {port.port}; Ctrl+C kończy test.', flush=True)
        while True:
            selected = client.read_input(None, context_key=f'led-test:{index}')
            if selected is None:
                continue
            col, row = selected
            led = col * 31 + (row if col % 2 == 0 else 29 - row)
            print(f'PRESS col={col:02d} row={row:02d} -> led={led:03d}', flush=True)
            if wled is not None:
                wled.set_leds([(led, color)], brightness=args.brightness, replace=True)
            index += 1
    except KeyboardInterrupt:
        return 0
    finally:
        client.close()
        if wled is not None:
            wled.clear()


if __name__ == '__main__':
    raise SystemExit(main())
