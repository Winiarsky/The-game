from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = ROOT / "scenarios"
AUDIO_PROMPTS = ROOT / "assets/ui_v2/ashen_oath/AUDIO_PROMPTS.md"
START_MARKER = "<!-- BEGIN GENERATED RUNTIME DIALOGUE VOICEOVER PROMPTS -->"
END_MARKER = "<!-- END GENERATED RUNTIME DIALOGUE VOICEOVER PROMPTS -->"


def _slug(value: object) -> str:
    raw = str(value or "").strip().lower()
    raw = raw.replace("ł", "l").replace("Ł", "l")
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_") or "line"


def _text(value: object) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _iter_dialog_lines(map_id: str, npc_id: str, dialog: dict[str, Any]):
    for node_id, node in dialog.items():
        if not isinstance(node, dict):
            continue
        text = _text(node.get("text"))
        if text:
            yield f"{map_id}_{npc_id}_{node_id}_opening", text
        for option in list(node.get("options") or []):
            if not isinstance(option, dict):
                continue
            option_id = _slug(option.get("id") or option.get("label"))
            for key in ("text", "result_text"):
                text = _text(option.get(key))
                if text:
                    yield f"{map_id}_{npc_id}_{node_id}_{option_id}_{key}", text
            skill = option.get("skill_check")
            if not isinstance(skill, dict):
                continue
            outcomes = skill.get("outcomes")
            if not isinstance(outcomes, dict):
                continue
            for outcome, spec in outcomes.items():
                if not isinstance(spec, dict):
                    continue
                text = _text(spec.get("text"))
                if text:
                    yield f"{map_id}_{npc_id}_{node_id}_{option_id}_{outcome}", text


def _iter_skill_challenge_lines(map_id: str, config: dict[str, Any]):
    challenge_id = _slug(config.get("challenge_id") or config.get("label"))
    for key in ("intro", "success_message", "failure_message"):
        text = _text(config.get(key))
        if text:
            yield f"{map_id}_{challenge_id}_{key}", text
    outcomes = config.get("outcome_messages")
    if isinstance(outcomes, dict):
        for outcome, text_raw in outcomes.items():
            text = _text(text_raw)
            if text:
                yield f"{map_id}_{challenge_id}_{outcome}", text


def _iter_scenario_lines(path: Path):
    map_id = path.stem.replace("ashen_oath_", "")
    payload = json.loads(path.read_text(encoding="utf-8"))
    for obj in payload.get("objects", []) or []:
        object_id = str(obj.get("object_id") or "").strip()
        for inst in obj.get("instances", []) or []:
            config = dict(inst.get("config") or {})
            if object_id == "skill_challenge":
                yield from _iter_skill_challenge_lines(map_id, config)
                continue
            dialog = config.get("dialog")
            if isinstance(dialog, dict):
                npc_id = _slug(config.get("npc_id") or config.get("name") or object_id)
                yield from _iter_dialog_lines(map_id, npc_id, dialog)


def build_section() -> str:
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path in sorted(SCENARIOS_DIR.glob("ashen_oath_*.json")):
        for raw_id, text in _iter_scenario_lines(path):
            base = _slug(raw_id)
            line_id = base
            suffix = 2
            while line_id in seen:
                line_id = f"{base}_{suffix}"
                suffix += 1
            seen.add(line_id)
            rows.append((line_id, text))

    lines = [
        START_MARKER,
        "",
        "## Generated runtime dialogue prompts",
        "",
        "Generated from `scenarios/ashen_oath_*.json` by `scripts/export_ashen_oath_voiceover_prompts.py`.",
        "Use these prompts to create optional NPC/skill-challenge voiceover files.",
        "",
    ]
    for line_id, text in rows:
        lines.extend(
            [
                f"### `audio/voiceover/runtime_dialogue/{line_id}_001.mp3`",
                "",
                text,
                "",
            ]
        )
    lines.append(END_MARKER)
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    section = build_section()
    original = AUDIO_PROMPTS.read_text(encoding="utf-8") if AUDIO_PROMPTS.exists() else ""
    if START_MARKER in original and END_MARKER in original:
        before = original.split(START_MARKER, 1)[0].rstrip()
        after = original.split(END_MARKER, 1)[1].lstrip()
        updated = before + "\n\n" + section + ("\n" + after if after else "")
    else:
        updated = original.rstrip() + "\n\n" + section
    AUDIO_PROMPTS.write_text(updated, encoding="utf-8")
    print(AUDIO_PROMPTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
