from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat.hp_engine import apply_damage


class DummyUi:
    def __init__(self) -> None:
        self.enabled = True
        self.calls: list[dict[str, object]] = []

    def prompt_info(self, title: str, *, prompt_long: str | None = None, source: str | None = None, **extra):
        self.calls.append(
            {
                "title": title,
                "prompt_long": prompt_long,
                "source": source,
                "extra": dict(extra),
            }
        )
        return "ok"


class HeroLike:
    def __init__(self) -> None:
        self.name = "Freya"
        self.object_id = "hero-1"
        self.character_id = "freya"
        self.wounds = 0
        self.max_hp = 16
        self.temp_hp = 0
        self.statuses = []


def test_apply_damage_prompts_for_player_wounds(monkeypatch):
    from combat import hp_engine

    ui = DummyUi()
    monkeypatch.setattr(hp_engine, "_is_player_wound_target", lambda actor: True)
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    actor = HeroLike()
    info = apply_damage(actor, 5, "slashing", source="enemy_strike")

    assert int(info["hp_damage"]) == 5
    assert actor.wounds == 5
    assert len(ui.calls) == 1
    assert ui.calls[0]["title"] == "Rany: Freya"
    assert "Freya otrzymuje **5** ran." in str(ui.calls[0]["prompt_long"])
    assert ui.calls[0]["source"] == "enemy_strike"


def test_apply_damage_skips_prompt_for_non_player_targets(monkeypatch):
    from combat import hp_engine

    ui = DummyUi()
    monkeypatch.setattr(hp_engine, "_is_player_wound_target", lambda actor: False)
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    actor = HeroLike()
    apply_damage(actor, 3, "fire", source="spell:fire")

    assert actor.wounds == 3
    assert ui.calls == []
