#!/usr/bin/env python3
from __future__ import annotations

import argparse
import colorsys
import json
import time
from typing import Any
from urllib import error, parse, request


class WLEDError(RuntimeError):
    pass


def _state_url(host: str) -> str:
    text = str(host).strip()
    if not text:
        raise ValueError("host nie może być pusty")
    if "://" not in text:
        text = f"http://{text}"
    parsed = parse.urlsplit(text)
    if not parsed.netloc:
        raise ValueError("host musi być adresem IP, hostname albo URL-em do WLED")
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("obsługiwane są tylko adresy http:// albo https://")
    base = f"{parsed.scheme}://{parsed.netloc}"
    return f"{base}/json/state"


def _post_json(host: str, payload: dict[str, Any], *, timeout: float) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        _state_url(host),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            response.read()
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace").strip()
        message = details or exc.reason or "nieznany błąd HTTP"
        raise WLEDError(f"WLED zwrócił HTTP {exc.code}: {message}") from exc


def _parse_rgb(raw: str) -> list[int]:
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Kolor musi mieć format R,G,B")
    try:
        rgb = [max(0, min(int(part), 255)) for part in parts]
    except ValueError as exc:  # pragma: no cover - parser i tak łapie błąd
        raise argparse.ArgumentTypeError("Kolor musi mieć format R,G,B") from exc
    return rgb


def _scale_rgb(rgb: list[int], factor: float) -> list[int]:
    factor = max(0.0, min(float(factor), 1.0))
    return [int(channel * factor) for channel in rgb]


def _rgb_to_hex(rgb: list[int]) -> str:
    return f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _rgb_from_hue(hue: float) -> list[int]:
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
    return [int(r * 255), int(g * 255), int(b * 255)]


def _segment_payload(
    *,
    start_index: int,
    colors: list[list[int]],
    brightness: int,
) -> dict[str, Any]:
    return {
        "on": True,
        "bri": max(1, min(int(brightness), 255)),
        "seg": [
            {
                "id": 0,
                "start": start_index,
                "stop": start_index + len(colors),
                "fx": 0,
                "i": colors,
            }
        ],
    }


def _rainbow_frame(
    *,
    led_count: int,
    phase: float,
    chunk_start: int,
    chunk_size: int,
) -> dict[str, Any]:
    entries: list[Any] = [chunk_start]
    for index in range(chunk_size):
        color = _rgb_from_hue(phase + ((chunk_start + index) / max(1, led_count)))
        entries.append(_rgb_to_hex(color))
    return {"seg": [{"id": 0, "i": entries}]}


def _chase_frame(
    *,
    led_count: int,
    head_index: int,
    trail: int,
    head_color: list[int],
    background_color: list[int],
    start_index: int,
    brightness: int,
) -> dict[str, Any]:
    colors = [list(background_color) for _ in range(led_count)]
    safe_trail = max(0, int(trail))
    if 0 <= head_index < led_count:
        colors[head_index] = list(head_color)
    for offset in range(1, safe_trail + 1):
        tail_index = head_index - offset
        if tail_index < 0:
            break
        falloff = 1.0 - (offset / (safe_trail + 1))
        colors[tail_index] = _scale_rgb(head_color, falloff)
    return _segment_payload(start_index=start_index, colors=colors, brightness=brightness)


def _segment_setup_payload(
    *,
    start_index: int,
    led_count: int,
    brightness: int,
    background_color: list[int],
) -> dict[str, Any]:
    return {
        "on": True,
        "bri": max(1, min(int(brightness), 255)),
        "seg": [
            {
                "id": 0,
                "start": start_index,
                "stop": start_index + led_count,
                "col": [list(background_color), [0, 0, 0], [0, 0, 0]],
                "fx": 0,
            }
        ],
    }


def _chase_led_map(
    *,
    led_count: int,
    head_index: int,
    trail: int,
    head_color: list[int],
) -> dict[int, list[int]]:
    result: dict[int, list[int]] = {}
    safe_trail = max(0, int(trail))
    for offset in range(0, safe_trail + 1):
        idx = (head_index - offset) % led_count
        falloff = 1.0 - (offset / (safe_trail + 1 if safe_trail >= 0 else 1))
        color = list(head_color) if offset == 0 else _scale_rgb(head_color, falloff)
        if idx not in result:
            result[idx] = color
    return result


def _chase_sparse_payload(
    *,
    current_map: dict[int, list[int]],
    previous_map: dict[int, list[int]],
    background_color: list[int],
) -> dict[str, Any]:
    entries: list[Any] = []
    touched = sorted(set(previous_map) | set(current_map))
    for idx in touched:
        color = current_map.get(idx, background_color)
        entries.extend([idx, list(color)])
    return {"seg": [{"id": 0, "i": entries}]}


def _even_sparse_payload(
    *,
    start_led: int,
    end_led: int,
    color: list[int],
) -> dict[str, Any]:
    entries: list[Any] = []
    for led_number in range(start_led, end_led + 1):
        if led_number % 2 == 0:
            entries.extend([led_number - start_led, list(color)])
    return {"seg": [{"id": 0, "i": entries}]}


def _off_payload(*, start_index: int, led_count: int) -> dict[str, Any]:
    return _segment_payload(
        start_index=start_index,
        colors=[[0, 0, 0] for _ in range(led_count)],
        brightness=255,
    )


def _rainbow_chunks(
    *,
    led_count: int,
    phase: float,
    chunk_size: int = 256,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for chunk_start in range(0, led_count, chunk_size):
        payloads.append(
            _rainbow_frame(
                led_count=led_count,
                phase=phase,
                chunk_start=chunk_start,
                chunk_size=min(chunk_size, led_count - chunk_start),
            )
        )
    return payloads


def _resolve_range(*, start_led: int, end_led: int) -> tuple[int, int]:
    if start_led <= 0:
        raise ValueError("--start-led musi być >= 1")
    if end_led < start_led:
        raise ValueError("--end-led musi być >= --start-led")
    start_index = start_led - 1
    led_count = end_led - start_led + 1
    return start_index, led_count


def run_animation(
    *,
    host: str,
    mode: str,
    start_led: int,
    end_led: int,
    fps: float,
    speed: float,
    brightness: int,
    duration: float | None,
    timeout: float,
    trail: int,
    color: list[int],
    background: list[int],
) -> None:
    start_index, led_count = _resolve_range(start_led=start_led, end_led=end_led)
    if mode == "even":
        _post_json(
            host,
            _segment_setup_payload(
                start_index=start_index,
                led_count=led_count,
                brightness=brightness,
                background_color=background,
            ),
            timeout=timeout,
        )
        _post_json(
            host,
            _even_sparse_payload(start_led=start_led, end_led=end_led, color=color),
            timeout=timeout,
        )
        return

    frame_delay = 1.0 / max(fps, 1.0)
    started_at = time.monotonic()
    phase = 0.0
    phase_step = speed / max(fps, 1.0)
    head_position = 0.0
    previous_map: dict[int, list[int]] = {}

    if mode in {"chase", "rainbow"}:
        _post_json(
            host,
            _segment_setup_payload(
                start_index=start_index,
                led_count=led_count,
                brightness=brightness,
                background_color=background,
            ),
            timeout=timeout,
        )

    while True:
        if mode == "rainbow":
            payloads = _rainbow_chunks(led_count=led_count, phase=phase)
            phase = (phase + phase_step) % 1.0
        else:
            head_index = int(head_position) % led_count
            current_map = _chase_led_map(
                led_count=led_count,
                head_index=head_index,
                trail=trail,
                head_color=color,
            )
            payload = _chase_sparse_payload(
                current_map=current_map,
                previous_map=previous_map,
                background_color=background,
            )
            previous_map = current_map
            head_position = (head_position + (speed / max(fps, 1.0))) % led_count
            payloads = [payload]

        for payload in payloads:
            _post_json(host, payload, timeout=timeout)

        if duration is not None and (time.monotonic() - started_at) >= duration:
            break
        time.sleep(frame_delay)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Proste animacje WLED: rainbow albo biegnące światełko na zadanym zakresie LED-ów."
    )
    parser.add_argument("--host", required=True, help="Adres IP lub hostname urządzenia WLED, np. 192.168.1.50")
    parser.add_argument(
        "--mode",
        choices=("chase", "rainbow", "even"),
        default="chase",
        help="Tryb animacji/rysowania. Domyślnie chase.",
    )
    parser.add_argument(
        "--start-led",
        type=int,
        default=1,
        help="Pierwszy LED w numeracji 1-based. Domyślnie 1.",
    )
    parser.add_argument(
        "--end-led",
        type=int,
        default=600,
        help="Ostatni LED w numeracji 1-based. Domyślnie 600.",
    )
    parser.add_argument("--fps", type=float, default=12.0, help="Liczba klatek na sekundę. Domyślnie 12.")
    parser.add_argument(
        "--speed",
        type=float,
        default=3.0,
        help="Dla chase: ile LED-ów główka przeskakuje na sekundę. Dla rainbow: tempo przesuwu koloru.",
    )
    parser.add_argument("--brightness", type=int, default=96, help="Jasność WLED 1-255. Domyślnie 96.")
    parser.add_argument(
        "--trail",
        type=int,
        default=8,
        help="Długość ogona dla trybu chase. Domyślnie 8.",
    )
    parser.add_argument(
        "--color",
        type=_parse_rgb,
        default=_parse_rgb("255,160,40"),
        help="Kolor główki w formacie R,G,B. Domyślnie 255,160,40.",
    )
    parser.add_argument(
        "--background",
        type=_parse_rgb,
        default=_parse_rgb("0,0,0"),
        help="Kolor tła segmentu w formacie R,G,B. Domyślnie 0,0,0.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Czas animacji w sekundach. Dla trybu even ignorowane.",
    )
    parser.add_argument(
        "--clear-on-exit",
        action="store_true",
        help="Po zakończeniu gasi używany zakres LED-ów.",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout pojedynczego requestu HTTP.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.fps <= 0:
        parser.error("--fps musi być > 0")
    if args.speed <= 0:
        parser.error("--speed musi być > 0")
    if args.duration is not None and args.duration <= 0:
        parser.error("--duration musi być > 0")

    try:
        run_animation(
            host=args.host,
            mode=args.mode,
            start_led=args.start_led,
            end_led=args.end_led,
            fps=args.fps,
            speed=args.speed,
            brightness=args.brightness,
            duration=args.duration,
            timeout=args.timeout,
            trail=args.trail,
            color=args.color,
            background=args.background,
        )
    except KeyboardInterrupt:
        print("\nPrzerwano animację.")
    except ValueError as exc:
        print(f"Błąd parametrów: {exc}")
        return 1
    except WLEDError as exc:
        print(f"Błąd odpowiedzi WLED: {exc}")
        return 1
    except error.URLError as exc:
        print(f"Błąd połączenia z WLED ({args.host}): {exc}")
        return 1
    finally:
        if args.clear_on_exit:
            try:
                start_index, led_count = _resolve_range(start_led=args.start_led, end_led=args.end_led)
                _post_json(
                    args.host,
                    _segment_setup_payload(
                        start_index=start_index,
                        led_count=led_count,
                        brightness=args.brightness,
                        background_color=[0, 0, 0],
                    ),
                    timeout=args.timeout,
                )
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
