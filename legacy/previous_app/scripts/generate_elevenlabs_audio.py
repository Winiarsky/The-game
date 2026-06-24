from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from audio_prompts_excel import DEFAULT_OUTPUT, ROOT, read_xlsx


DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_SOUND_MODEL = "eleven_text_to_sound_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_SOUND_API_URL = "https://api.elevenlabs.io/v1/sound-generation"


def _is_tts_row(row: dict[str, str]) -> bool:
    kind = row.get("kind", "").lower()
    target = row.get("target_path", "")
    return "voiceover" in kind or "/voiceover/" in target


def _row_kind(row: dict[str, str]) -> str:
    kind = row.get("kind", "").lower()
    target = row.get("target_path", "").lower()
    if "voiceover" in kind or "/voiceover/" in target:
        return "voiceover"
    if "ambience" in kind or "/ambience/" in target:
        return "ambience"
    if "music" in kind or "/music/" in target:
        return "music"
    if "sfx" in kind or "/sfx/" in target:
        return "sfx"
    return kind or "audio"


def _matches_target_filters(row: dict[str, str], exact: set[str], prefixes: tuple[str, ...]) -> bool:
    if not exact and not prefixes:
        return True
    target = row.get("target_path", "").strip()
    return target in exact or any(target.startswith(prefix) for prefix in prefixes)


def _selected_rows(
    rows: Iterable[dict[str, str]],
    scenario_id: str,
    include_non_voiceover: bool,
    kinds: set[str],
    target_paths: set[str],
    target_prefixes: tuple[str, ...],
):
    for row in rows:
        if scenario_id and row.get("scenario_id") != scenario_id:
            continue
        row_kind = _row_kind(row)
        if kinds and row_kind not in kinds:
            continue
        if not _matches_target_filters(row, target_paths, target_prefixes):
            continue
        text = row.get("text", "").strip()
        target = row.get("target_path", "").strip()
        if not text or not target:
            continue
        if not include_non_voiceover and not _is_tts_row(row):
            continue
        yield row


def _request_tts(
    *,
    api_key: str,
    voice_id: str,
    text: str,
    model_id: str,
    output_format: str,
    timeout: int,
) -> bytes:
    params = urlencode({"output_format": output_format})
    url = f"{DEFAULT_API_URL.format(voice_id=voice_id)}?{params}"
    payload = json.dumps({"text": text, "model_id": model_id}).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _request_sound_generation(
    *,
    api_key: str,
    text: str,
    model_id: str,
    output_format: str,
    duration_seconds: float | None,
    loop: bool,
    prompt_influence: float | None,
    timeout: int,
) -> bytes:
    params = urlencode({"output_format": output_format})
    payload: dict[str, object] = {"text": text, "model_id": model_id, "loop": loop}
    if duration_seconds is not None:
        payload["duration_seconds"] = duration_seconds
    if prompt_influence is not None:
        payload["prompt_influence"] = prompt_influence
    request = Request(
        f"{DEFAULT_SOUND_API_URL}?{params}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _target_file(row: dict[str, str], output_root: Path) -> Path:
    return output_root / row["scenario_id"] / row["target_path"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate ElevenLabs TTS audio files from assets/ui_v2/audio_prompts.xlsx."
    )
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--scenario-id", default="", help="Optional scenario_id filter, e.g. bandit_cave.")
    parser.add_argument("--voice-id", default=os.environ.get("ELEVENLABS_VOICE_ID", ""))
    parser.add_argument("--api-key", default=os.environ.get("ELEVENLABS_API_KEY", ""))
    parser.add_argument("--model-id", default=os.environ.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL))
    parser.add_argument("--sound-model-id", default=os.environ.get("ELEVENLABS_SOUND_MODEL_ID", DEFAULT_SOUND_MODEL))
    parser.add_argument("--output-format", default=os.environ.get("ELEVENLABS_OUTPUT_FORMAT", DEFAULT_OUTPUT_FORMAT))
    parser.add_argument("--output-root", type=Path, default=ROOT / "assets/ui_v2")
    parser.add_argument(
        "--kinds",
        default="",
        help="Comma-separated filter: voiceover,sfx,music,ambience. Defaults to voiceover only.",
    )
    parser.add_argument("--target-path", action="append", default=[], help="Exact target_path from the Excel file.")
    parser.add_argument("--target-prefix", action="append", default=[], help="target_path prefix from the Excel file.")
    parser.add_argument("--include-non-voiceover", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.2, help="Seconds to wait between API calls.")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--sfx-duration", type=float, default=0.0, help="Optional duration for sfx generations.")
    parser.add_argument("--music-duration", type=float, default=30.0, help="Duration for music generations, max 30.")
    parser.add_argument("--ambience-duration", type=float, default=30.0, help="Duration for ambience generations, max 30.")
    parser.add_argument("--prompt-influence", type=float, default=0.3)
    parser.add_argument("--no-loop", action="store_true", help="Disable loop=true for music and ambience.")
    args = parser.parse_args()

    if not args.api_key and not args.dry_run:
        raise SystemExit("Missing ELEVENLABS_API_KEY or --api-key.")
    requested_kinds = {item.strip().lower() for item in args.kinds.split(",") if item.strip()}
    include_non_voiceover = args.include_non_voiceover or bool(requested_kinds - {"voiceover"})
    if (not requested_kinds or "voiceover" in requested_kinds) and not args.voice_id and not args.dry_run:
        raise SystemExit("Missing ELEVENLABS_VOICE_ID or --voice-id.")

    xlsx = args.xlsx if args.xlsx.is_absolute() else ROOT / args.xlsx
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    rows = list(
        _selected_rows(
            read_xlsx(xlsx),
            args.scenario_id,
            include_non_voiceover,
            requested_kinds,
            set(args.target_path),
            tuple(args.target_prefix),
        )
    )
    if args.limit:
        rows = rows[: args.limit]

    generated = 0
    skipped = 0
    for row in rows:
        target = _target_file(row, output_root)
        row_kind = _row_kind(row)
        if target.exists() and not args.overwrite:
            print(f"skip existing: {target.relative_to(ROOT)}")
            skipped += 1
            continue
        print(f"generate {row_kind}: {target.relative_to(ROOT)}")
        if args.dry_run:
            generated += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if row_kind == "voiceover":
                audio = _request_tts(
                    api_key=args.api_key,
                    voice_id=args.voice_id,
                    text=row["text"],
                    model_id=args.model_id,
                    output_format=args.output_format,
                    timeout=args.timeout,
                )
            else:
                duration = None
                if row_kind == "sfx" and args.sfx_duration > 0:
                    duration = args.sfx_duration
                if row_kind == "music":
                    duration = args.music_duration
                if row_kind == "ambience":
                    duration = args.ambience_duration
                audio = _request_sound_generation(
                    api_key=args.api_key,
                    text=row["text"],
                    model_id=args.sound_model_id,
                    output_format=args.output_format,
                    duration_seconds=duration,
                    loop=(row_kind in {"music", "ambience"} and not args.no_loop),
                    prompt_influence=args.prompt_influence,
                    timeout=args.timeout,
                )
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"ElevenLabs HTTP {exc.code} for {target}: {detail}") from exc
        except URLError as exc:
            raise SystemExit(f"ElevenLabs request failed for {target}: {exc}") from exc
        target.write_bytes(audio)
        generated += 1
        if args.sleep:
            time.sleep(args.sleep)

    print(f"Done. generated={generated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
