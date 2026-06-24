from __future__ import annotations

import argparse
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "assets/ui_v2/AUDIO_REGEN_QUEUE.md"

SCENARIO_KINDS = {
    "ashen_oath": "voiceover,music",
    "bandit_cave": "voiceover,sfx,music",
}


def read_queue(path: Path) -> dict[str, list[str]]:
    scenario = ""
    targets: dict[str, list[str]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## assets/ui_v2/ashen_oath/"):
            scenario = "ashen_oath"
            continue
        if line.startswith("## assets/ui_v2/bandit_cave/"):
            scenario = "bandit_cave"
            continue
        if not scenario or not line.startswith("- `"):
            continue
        parts = line.split("`")
        if len(parts) >= 3:
            targets[scenario].append(parts[1])
    return dict(targets)


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate audio targets listed in AUDIO_REGEN_QUEUE.md.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", default="0.35")
    parser.add_argument("--timeout", default="90")
    args = parser.parse_args()

    queue = args.queue if args.queue.is_absolute() else ROOT / args.queue
    targets_by_scenario = read_queue(queue)
    for scenario_id, targets in targets_by_scenario.items():
        kinds = SCENARIO_KINDS[scenario_id]
        command = [
            "python",
            "scripts/generate_elevenlabs_audio.py",
            "--scenario-id",
            scenario_id,
            "--kinds",
            kinds,
            "--overwrite",
            "--sleep",
            args.sleep,
            "--timeout",
            args.timeout,
        ]
        if args.dry_run:
            command.append("--dry-run")
        for target in targets:
            command.extend(["--target-path", target])
        subprocess.run(command, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
