from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from character_creation.pipeline import (
    _STARTER_SHOP_OFFERS,
    _ancestry_fluff_sentence,
    _ancestry_mechanics_desc_pl,
    _create_shop_item,
    _ensure_structured_choice_desc,
    _item_choice_desc,
    _structured_choice_desc,
    _status_choice_desc,
    hero_from_snapshot,
)
from character_creation.repository import CharacterRepository
from character_creation.catalog import (
    ANCESTRY_FEAT_IDS_BY_ANCESTRY,
    ANCESTRY_IDS,
    CLASS_FEAT_CHOICES_MANUAL,
    HERITAGE_IDS_BY_ANCESTRY,
    list_background_status_ids,
    resolve_status,
)
from statuses.base import Status
from states.start import Start
from character_creation.pipeline import create_character


def test_character_repository_save_load_and_list(tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")
    snapshot = {
        "character_id": "hero_test",
        "name": "Test Hero",
        "class_id": "fighter",
        "ancestry_id": "human",
        "level": 1,
    }
    saved_id = repo.save_character(snapshot)
    assert saved_id == "hero_test"

    listing = repo.list_characters()
    assert listing
    assert listing[0]["character_id"] == "hero_test"
    loaded = repo.load_character("hero_test")
    assert loaded is not None
    assert loaded["name"] == "Test Hero"


def test_character_creation_catalog_includes_gnome_with_heritages_and_feats():
    assert "gnome" in ANCESTRY_IDS
    assert HERITAGE_IDS_BY_ANCESTRY.get("gnome")
    assert ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("gnome")
    assert resolve_status("gnome") is not None


def test_versatile_heritage_description_keeps_mechanics_after_structuring():
    status = resolve_status("versatile_heritage")
    assert status is not None
    base_desc = _status_choice_desc(status, "Dziedzictwo ancestry.")
    assert "Brak dodatkowych informacji mechanicznych." not in base_desc

    rebuilt = _ensure_structured_choice_desc(
        label="Wszechstronne dziedzictwo",
        desc=base_desc,
        choice_id="versatile_heritage",
    )
    assert "Brak dodatkowych informacji mechanicznych." not in rebuilt
    assert "general feat" in rebuilt.lower()


def test_structured_ancestry_description_preserves_multiline_effect_block():
    status = resolve_status("human")
    assert status is not None
    base_desc = _structured_choice_desc(
        name="Czlowiek",
        fluff=_ancestry_fluff_sentence("human", status),
        mechanics=_ancestry_mechanics_desc_pl(status),
        when="Natychmiast po potwierdzeniu wyboru ancestry.",
    )
    rebuilt = _ensure_structured_choice_desc(
        label="Czlowiek",
        desc=base_desc,
        choice_id="human",
    )
    assert "Brak dodatkowych informacji mechanicznych." not in rebuilt
    assert "HP ancestry: 8" in rebuilt
    assert "Predkosc bazowa: 25 stop" in rebuilt
    assert "Boosty atrybutow: Dowolna, Dowolna" in rebuilt


def test_character_repository_serializes_status_objects_in_payload(tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")
    snapshot = {
        "character_id": "hero_status_obj",
        "name": "Status Obj Hero",
        "status_data": {
            "wizard": {
                "wizard_setup": {
                    "granted_statuses": [Status(id="arcane_sense", label="Arcane Sense")],
                }
            }
        },
    }
    repo.save_character(snapshot)
    loaded = repo.load_character("hero_status_obj")
    assert loaded is not None
    granted = (((loaded.get("status_data") or {}).get("wizard") or {}).get("wizard_setup") or {}).get("granted_statuses")
    assert isinstance(granted, list)
    assert granted
    first = granted[0]
    assert isinstance(first, dict)
    assert first.get("id") == "arcane_sense"


def test_hero_from_snapshot_restores_core_fields():
    snapshot = {
        "character_id": "hero_alpha",
        "name": "Alpha",
        "class_id": "fighter",
        "ancestry_id": "human",
        "heritage_id": "half_elf",
        "ancestry_feat_id": "natural_ambition",
        "background_id": "background_acolyte",
        "portrait_image": "/static/portraits/portrait_warrior.svg",
        "status_ids": ["human", "half_elf", "natural_ambition", "background_acolyte", "fighter"],
        "status_data": {},
        "ability_scores": {
            "strength": 18,
            "dexterity": 14,
            "constitution": 12,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
        },
        "ability_modifiers": {
            "strength": 4,
            "dexterity": 2,
            "constitution": 1,
            "intelligence": 0,
            "wisdom": 0,
            "charisma": 0,
        },
        "skill_ranks": {"athletics": "trained"},
        "skill_modifiers": {"athletics": 7},
        "trained_skills": ["athletics"],
        "lore_skills": ["Scribing Lore"],
        "languages": ["common"],
        "traits": ["human", "humanoid"],
        "perception_rank": "expert",
        "perception_bonus": 5,
        "save_ranks": {"fortitude": "expert", "reflex": "expert", "will": "trained"},
        "fortitude_bonus": 6,
        "reflex_bonus": 5,
        "will_bonus": 3,
        "weapon_proficiency_ranks": {"simple": "trained", "martial": "trained", "unarmed": "trained"},
        "defense_proficiency_ranks": {"unarmored": "trained", "light": "trained"},
        "max_hp": 20,
        "base_speed_feet": 25,
        "ac": 15,
    }
    hero = hero_from_snapshot(snapshot)
    assert getattr(hero, "name", "") == "Alpha"
    assert getattr(hero, "class_name", "") == "fighter"
    assert getattr(hero, "image", "") == "/static/portraits/portrait_warrior.svg"
    assert hero.has_status("background_acolyte")
    assert hero.max_hp == 20
    assert hero.ac == 15
    assert getattr(hero, "athletics_bonus", 0) == 7


def test_hero_from_snapshot_compresses_untrained_maps():
    snapshot = {
        "character_id": "hero_sparse",
        "name": "Sparse",
        "skill_ranks": {
            "athletics": "trained",
            "arcana": "untrained",
            "stealth": "expert",
        },
        "save_ranks": {
            "fortitude": "trained",
            "reflex": "untrained",
            "will": "expert",
        },
        "ability_modifiers": {
            "strength": 3,
            "dexterity": 2,
            "constitution": 1,
            "wisdom": 0,
            "intelligence": 0,
            "charisma": 0,
        },
        "perception_rank": "trained",
    }
    hero = hero_from_snapshot(snapshot)
    assert hero.skill_ranks == {"athletics": "trained", "stealth": "expert"}
    assert hero.save_ranks == {"fortitude": "trained", "will": "expert"}
    assert "arcana" not in hero.skill_ranks
    assert "reflex" not in hero.save_ranks


def test_hero_from_snapshot_applies_canny_acumen_rank_upgrade():
    snapshot = {
        "character_id": "hero_canny",
        "name": "Canny",
        "level": 1,
        "status_ids": ["canny_acumen"],
        "status_data": {
            "canny_acumen": {
                "canny_acumen_choice": "reflex",
                "canny_acumen_rank": "expert",
            }
        },
        "ability_modifiers": {
            "strength": 0,
            "dexterity": 2,
            "constitution": 0,
            "intelligence": 0,
            "wisdom": 0,
            "charisma": 0,
        },
    }
    hero = hero_from_snapshot(snapshot)
    assert hero.save_ranks == {"reflex": "expert"}
    assert hero.reflex_bonus == 7  # level 1 + expert 4 + DEX 2


def test_hero_from_snapshot_applies_skilled_heritage_progression():
    snapshot = {
        "character_id": "hero_skilled",
        "name": "Skilled",
        "level": 5,
        "status_ids": ["skilled_heritage"],
        "status_data": {
            "skilled_heritage": {
                "skilled_heritage_skill": "stealth",
                "trained_skills": ["stealth"],
                "skilled_heritage_progression": {"5": "expert"},
            }
        },
        "ability_modifiers": {
            "strength": 0,
            "dexterity": 3,
            "constitution": 0,
            "intelligence": 0,
            "wisdom": 0,
            "charisma": 0,
        },
    }
    hero = hero_from_snapshot(snapshot)
    assert hero.skill_ranks.get("stealth") == "expert"
    assert "stealth" in hero.trained_skills
    assert getattr(hero, "stealth_bonus", 0) == 12  # level 5 + expert 4 + DEX 3


class _UiStub:
    enabled = True
    allow_cli_fallback = False

    def __init__(self, answer: str):
        self.answer = answer
        self.calls: list[dict[str, object]] = []

    def prompt_choice(self, *_args, **_kwargs):
        self.calls.append({"args": _args, "kwargs": dict(_kwargs)})
        return self.answer


@dataclass
class _GameStub:
    ui: _UiStub
    logs: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.logs.append(str(message))


def test_start_pick_existing_hero(monkeypatch, tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")
    repo.save_character(
        {
            "character_id": "hero_pick",
            "name": "Pick Me",
            "class_id": "fighter",
            "ancestry_id": "human",
            "status_ids": ["human", "fighter"],
            "status_data": {},
        }
    )
    game = _GameStub(ui=_UiStub("Pick Me"))
    start = Start(game)  # type: ignore[arg-type]
    monkeypatch.setattr(start, "_character_repository", lambda: repo)

    hero = start._pick_or_create_hero(set())
    assert hero is not None
    assert getattr(hero, "name", "") == "Pick Me"
    assert hero.has_status("fighter")


def test_start_pick_existing_hero_includes_preview_in_choice_meta(monkeypatch, tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")
    repo.save_character(
        {
            "character_id": "hero_preview",
            "name": "Podglad",
            "class_id": "fighter",
            "ancestry_id": "human",
            "heritage_id": "half_elf",
            "portrait_image": "/static/portraits/portrait_warrior.svg",
            "level": 2,
            "status_ids": ["human", "fighter"],
            "status_data": {},
        }
    )
    ui = _UiStub("Podglad")
    game = _GameStub(ui=ui)
    start = Start(game)  # type: ignore[arg-type]
    monkeypatch.setattr(start, "_character_repository", lambda: repo)

    hero = start._pick_or_create_hero(set())
    assert hero is not None
    assert ui.calls
    call_kwargs = dict(ui.calls[0].get("kwargs") or {})
    choice_meta = list(call_kwargs.get("choice_meta") or [])
    entry = next((item for item in choice_meta if str(item.get("raw") or "").strip().lower() == "hero_preview"), None)
    assert entry is not None
    preview = entry.get("hero_preview")
    assert isinstance(preview, dict)
    assert preview.get("name") == "Podglad"
    assert preview.get("class_id") == "fighter"
    assert preview.get("ancestry_id") == "human"
    assert preview.get("image") == "/static/portraits/portrait_warrior.svg"


def test_starting_shop_offers_create_items():
    for offer in _STARTER_SHOP_OFFERS:
        item = _create_shop_item(offer)
        assert item is not None, f"Brak obiektu dla oferty: {offer}"


def test_starting_shop_offers_include_two_handed_sword_and_axe():
    offer_ids = {str(offer.get("id") or "").strip().lower() for offer in _STARTER_SHOP_OFFERS}
    assert "greatsword" in offer_ids
    assert "greataxe" in offer_ids


def test_starting_shop_weapon_desc_contains_damage_and_trait_mechanics():
    offer = next((row for row in _STARTER_SHOP_OFFERS if str(row.get("id") or "").strip().lower() == "longbow"), None)
    assert offer is not None
    item = _create_shop_item(offer)
    assert item is not None
    text = _item_choice_desc(offer, item, owned=0)
    assert "Fluff:" in text
    assert "Mechanika:" in text
    assert "Kiedy:" in text
    assert "Efekt:" in text
    assert "Atak:" in text
    assert "Traitsy:" in text
    assert "Dzialanie traits:" in text
    assert " | " not in text


def test_starting_shop_armor_desc_contains_core_armor_stats_and_trait_mechanics():
    offer = next((row for row in _STARTER_SHOP_OFFERS if str(row.get("id") or "").strip().lower() == "full_plate"), None)
    assert offer is not None
    item = _create_shop_item(offer)
    assert item is not None
    text = _item_choice_desc(offer, item, owned=0)
    assert "Bonus AC:" in text
    assert "Max DEX:" in text
    assert "Wymaganie STR:" in text
    assert "Kara do testow" in text
    assert "Kara do predkosci:" in text
    assert "Bulk:" in text
    assert "Traitsy:" in text
    assert "Dzialanie traits:" in text
    assert " | " not in text


def test_background_choice_desc_contains_fluff_and_mechanics_and_feat_effect():
    status = resolve_status("background_acolyte")
    assert status is not None
    text = _status_choice_desc(status, "Tlo postaci.")
    assert "Fluff:" in text
    assert "Mechanika:" in text
    assert "Kiedy:" in text
    assert "Efekt:" in text
    assert "Gwarantowany feat:" in text
    assert " | " not in text


def test_background_choice_desc_feat_effect_is_mechanical_for_streetwise():
    status = resolve_status("background_detective")
    assert status is not None
    text = _status_choice_desc(status, "Tlo postaci.")
    assert "Gwarantowany feat: Streetwise" in text
    assert "Mechanika:" in text
    assert "Kiedy:" in text
    assert "+2 status" in text


def test_goblin_ancestry_fluff_is_narrative_and_mechanics_are_numeric():
    status = resolve_status("goblin")
    assert status is not None
    fluff = _ancestry_fluff_sentence("goblin", status)
    mechanics = _ancestry_mechanics_desc_pl(status)
    assert "Punkty Zycia" not in fluff
    assert "impulsywne" in fluff.lower() or "zadziorne" in fluff.lower()
    assert "HP ancestry:" in mechanics
    assert "Predkosc bazowa:" in mechanics
    assert "Boosty atrybutow:" in mechanics
    assert "Wada atrybutu:" in mechanics


def test_barbarian_instinct_choice_desc_mentions_rage_window():
    status = resolve_status("dragon_instinct")
    assert status is not None
    text = _status_choice_desc(status, "Instynkt barbarzyńcy.")
    assert "Rage" in text or "rage" in text


def test_sensate_gnome_choice_desc_points_to_perception_seek_bonus():
    status = resolve_status("sensate_gnome")
    assert status is not None
    text = _status_choice_desc(status, "Heritage gnom.")
    assert "Perception" in text or "Percepcja" in text
    assert "seek" in text.lower() or "szukaj" in text.lower()
    assert "+2 circumstance" in text


def test_fey_touched_gnome_choice_desc_mentions_cantrip_and_primal_innate():
    status = resolve_status("fey_touched_gnome")
    assert status is not None
    text = _status_choice_desc(status, "Heritage gnom.")
    lower = text.lower()
    assert "cantrip" in lower
    assert "primal" in lower
    assert "kiedy:" in lower and "efekt:" in lower


def test_barbarian_manual_class_feats_are_available_in_registry():
    for feat_id in CLASS_FEAT_CHOICES_MANUAL.get("barbarian", []):
        assert resolve_status(feat_id) is not None, feat_id


def test_hero_from_snapshot_restores_inventory_items():
    snapshot = {
        "character_id": "hero_eq",
        "name": "Eq Hero",
        "class_id": "fighter",
        "weapon_loadout": ["longsword"],
        "inventory_items": [
            {
                "item_id": "longsword",
                "category": "weapon",
                "name": "Longsword",
                "price_cp": 100,
                "bulk": 1,
            },
            {
                "item_id": "healer_tools",
                "category": "gear",
                "name": "Narzedzia medyka",
                "price_cp": 500,
                "bulk": 1,
            },
        ],
    }
    hero = hero_from_snapshot(snapshot)
    item_ids = {str(getattr(item, "item_id", "") or "").strip().lower() for item in list(getattr(hero, "inventory", []) or [])}
    assert "longsword" in item_ids
    assert "healer_tools" in item_ids


def test_hero_from_snapshot_restores_missing_class_feat_status_from_class_feat_ids():
    snapshot = {
        "character_id": "hero_barb_feat",
        "name": "Kroll",
        "class_id": "barbarian",
        "status_ids": ["barbarian", "giant_instinct"],
        "class_feat_ids": ["sudden_charge"],
    }
    hero = hero_from_snapshot(snapshot)
    assert hero.has_status("barbarian")
    assert hero.has_status("sudden_charge")


def test_bard_repertoire_is_set_during_character_creation(monkeypatch, tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")

    class _CreationGameStub:
        def __init__(self):
            self.ui = None
            self.logs: list[str] = []

        def ui_log(self, message: str) -> None:
            self.logs.append(str(message))

        def ui_hero(self, *_args, **_kwargs):
            return None

        def ui_active_actor(self, *_args, **_kwargs):
            return None

    game = _CreationGameStub()

    heritage_id = str((HERITAGE_IDS_BY_ANCESTRY.get("elf") or [""])[0] or "")
    ancestry_feat_id = ""
    for candidate in list(ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("elf") or []):
        status = resolve_status(candidate)
        data = getattr(status, "data", None) or {}
        if not data.get("ui_choice_kind"):
            ancestry_feat_id = str(candidate)
            break
    if not ancestry_feat_id:
        ancestry_feat_id = str((ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("elf") or [""])[0] or "")

    background_id = "background_acolyte"
    if resolve_status(background_id) is None:
        background_id = str((list_background_status_ids() or [""])[0] or "")

    def _fake_pick_portrait(_game, **_kwargs):
        return "/static/placeholder.png"

    def _fake_prompt_text(_game, *, title, **_kwargs):
        if "imię" in str(title).lower() or "imie" in str(title).lower():
            return "Lira"
        return "tekst"

    def _fake_pick_one(_game, *, title, **_kwargs):
        if str(title).startswith("KROK 2: Wybór Ancestry"):
            return "elf"
        if str(title).startswith("KROK 3: Wybór Heritage"):
            return heritage_id
        if str(title).startswith("KROK 4: Ancestry Feat"):
            return ancestry_feat_id
        if str(title).startswith("KROK 5: Background"):
            return background_id
        if str(title).startswith("KROK 6: Wybór Klasy"):
            return "bard"
        return None

    monkeypatch.setattr("character_creation.pipeline._pick_portrait_image", _fake_pick_portrait)
    monkeypatch.setattr("character_creation.pipeline._prompt_text", _fake_prompt_text)
    monkeypatch.setattr("character_creation.pipeline._pick_one", _fake_pick_one)
    monkeypatch.setattr("character_creation.pipeline._pick_ability", lambda *_a, **_k: "charisma")
    monkeypatch.setattr("character_creation.pipeline._pick_additional_skills", lambda *_a, **_k: [])
    monkeypatch.setattr("character_creation.pipeline._resolve_background_training_choice", lambda *_a, **_k: (None, None))
    monkeypatch.setattr("character_creation.pipeline._run_starting_equipment_step", lambda *_a, **_k: None)
    monkeypatch.setattr("character_creation.pipeline._prompt_info", lambda *_a, **_k: None)

    result = create_character(game, repo)
    assert result is not None
    bard_setup = result.hero.get_status_data("bard", "bard_setup", {})
    assert isinstance(bard_setup, dict)
    assert len(list(bard_setup.get("known_cantrips") or [])) == 7
    assert len(list(bard_setup.get("known_rank_1_spells") or [])) == 2
    assert int(bard_setup.get("rank_1_slots_per_day", 0) or 0) == 2

    snapshot_bard_setup = (
        (((result.snapshot.get("status_data") or {}).get("bard") or {}).get("bard_setup") or {})
    )
    assert isinstance(snapshot_bard_setup, dict)
    assert len(list(snapshot_bard_setup.get("known_cantrips") or [])) == 7
    assert len(list(snapshot_bard_setup.get("known_rank_1_spells") or [])) == 2
    assert int(snapshot_bard_setup.get("rank_1_slots_per_day", 0) or 0) == 2


def test_class_key_ability_is_visible_in_live_preview_during_class_setup(monkeypatch, tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")

    class _CreationGameStub:
        def __init__(self):
            self.ui = None
            self.logs: list[str] = []
            self.snapshots: list[dict[str, object]] = []

        def ui_log(self, message: str) -> None:
            self.logs.append(str(message))

        def ui_hero(self, hero, note: str | None = None):
            self.snapshots.append(
                {
                    "note": str(note or ""),
                    "ability_scores": dict(getattr(hero, "ability_scores", {}) or {}),
                    "class_id": str(getattr(hero, "class_id", "") or ""),
                    "ancestry_id": str(getattr(hero, "ancestry_id", "") or ""),
                }
            )

        def ui_active_actor(self, *_args, **_kwargs):
            return None

    game = _CreationGameStub()
    heritage_id = str((HERITAGE_IDS_BY_ANCESTRY.get("human") or [""])[0] or "")
    ancestry_feat_id = str((ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("human") or [""])[0] or "")
    background_id = str((list_background_status_ids() or [""])[0] or "")
    fighter_feat = str((CLASS_FEAT_CHOICES_MANUAL.get("fighter") or [""])[0] or "")

    def _fake_pick_portrait(_game, **_kwargs):
        return "/static/placeholder.png"

    def _fake_prompt_text(_game, *, title, **_kwargs):
        if "imię" in str(title).lower() or "imie" in str(title).lower():
            return "Brutus"
        return "tekst"

    def _fake_pick_one(_game, *, title, **_kwargs):
        if str(title).startswith("KROK 2: Wybór Ancestry"):
            return "human"
        if str(title).startswith("KROK 3: Wybór Heritage"):
            return heritage_id
        if str(title).startswith("KROK 4: Ancestry Feat"):
            return ancestry_feat_id
        if str(title).startswith("KROK 5: Background"):
            return background_id
        if str(title).startswith("KROK 6: Wybór Klasy"):
            return "fighter"
        if str(title).startswith("KROK 11: Class Feat"):
            return fighter_feat
        return None

    def _fake_pick_ability(_game, *, allowed, **_kwargs):
        options = list(allowed or [])
        return str(options[0]) if options else None

    monkeypatch.setattr("character_creation.pipeline._pick_portrait_image", _fake_pick_portrait)
    monkeypatch.setattr("character_creation.pipeline._prompt_text", _fake_prompt_text)
    monkeypatch.setattr("character_creation.pipeline._pick_one", _fake_pick_one)
    monkeypatch.setattr("character_creation.pipeline._pick_ability", _fake_pick_ability)
    monkeypatch.setattr("character_creation.pipeline._pick_additional_skills", lambda *_a, **_k: [])
    monkeypatch.setattr("character_creation.pipeline._resolve_background_training_choice", lambda *_a, **_k: (None, None))
    monkeypatch.setattr("character_creation.pipeline._run_starting_equipment_step", lambda *_a, **_k: None)
    monkeypatch.setattr("character_creation.pipeline._prompt_info", lambda *_a, **_k: None)

    result = create_character(game, repo)
    assert result is not None

    class_setup_snapshot = next(
        (
            row
            for row in game.snapshots
            if "KROK 6A: Setup klasy" in str(row.get("note") or "")
            and "Key Ability:" in str(row.get("note") or "")
        ),
        None,
    )
    assert class_setup_snapshot is not None
    assert str(class_setup_snapshot.get("class_id") or "").strip().lower() == "fighter"
    assert str(class_setup_snapshot.get("ancestry_id") or "").strip().lower() == "human"
    scores = dict(class_setup_snapshot.get("ability_scores") or {})
    # W preview KROK 6A widoczne sa juz boosty ancestry/background + key ability.
    assert int(scores.get("strength", 0) or 0) >= 12


def test_champion_natural_ambition_deitys_domain_does_not_prompt_for_deity_twice(monkeypatch, tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")

    class _StatusUiCapture:
        enabled = True
        allow_cli_fallback = False

        def __init__(self):
            self.answers = ["1", "1", "iomedae", "deitys_domain", "truth"]
            self.prompts: list[str] = []

        def prompt_choice(self, prompt, choices=None, **_kwargs):
            self.prompts.append(str(prompt or ""))
            if self.answers:
                return self.answers.pop(0)
            if choices:
                return choices[0]
            return None

        def prompt_info(self, *_args, **_kwargs):
            return None

    class _CreationGameStub:
        def __init__(self):
            self.ui = None
            self.logs: list[str] = []

        def ui_log(self, message: str) -> None:
            self.logs.append(str(message))

        def ui_hero(self, *_args, **_kwargs):
            return None

        def ui_active_actor(self, *_args, **_kwargs):
            return None

    game = _CreationGameStub()
    ui = _StatusUiCapture()

    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    heritage_id = str((HERITAGE_IDS_BY_ANCESTRY.get("human") or [""])[0] or "")
    ancestry_feat_id = "natural_ambition"
    background_id = "background_acolyte"
    if resolve_status(background_id) is None:
        background_id = str((list_background_status_ids() or [""])[0] or "")
    champion_feat = "ranged_reprisal"
    if champion_feat not in set(CLASS_FEAT_CHOICES_MANUAL.get("champion") or []):
        champion_feat = str((CLASS_FEAT_CHOICES_MANUAL.get("champion") or [""])[0] or "")

    def _fake_pick_portrait(_game, **_kwargs):
        return "/static/placeholder.png"

    def _fake_prompt_text(_game, *, title, **_kwargs):
        if "imię" in str(title).lower() or "imie" in str(title).lower():
            return "Aegis"
        return "tekst"

    def _fake_pick_one(_game, *, title, **_kwargs):
        if str(title).startswith("KROK 2: Wybór Ancestry"):
            return "human"
        if str(title).startswith("KROK 3: Wybór Heritage"):
            return heritage_id
        if str(title).startswith("KROK 4: Ancestry Feat"):
            return ancestry_feat_id
        if str(title).startswith("KROK 5: Background"):
            return background_id
        if str(title).startswith("KROK 6: Wybór Klasy"):
            return "champion"
        if str(title).startswith("KROK 11: Class Feat"):
            return champion_feat
        return None

    def _fake_pick_ability(_game, *, allowed, **_kwargs):
        options = list(allowed or [])
        return str(options[0]) if options else None

    monkeypatch.setattr("character_creation.pipeline._pick_portrait_image", _fake_pick_portrait)
    monkeypatch.setattr("character_creation.pipeline._prompt_text", _fake_prompt_text)
    monkeypatch.setattr("character_creation.pipeline._pick_one", _fake_pick_one)
    monkeypatch.setattr("character_creation.pipeline._pick_ability", _fake_pick_ability)
    monkeypatch.setattr("character_creation.pipeline._pick_additional_skills", lambda *_a, **_k: [])
    monkeypatch.setattr("character_creation.pipeline._resolve_background_training_choice", lambda *_a, **_k: (None, None))
    monkeypatch.setattr("character_creation.pipeline._run_starting_equipment_step", lambda *_a, **_k: None)
    monkeypatch.setattr("character_creation.pipeline._prompt_info", lambda *_a, **_k: None)

    result = create_character(game, repo)
    assert result is not None
    assert result.hero.has_status("champion")
    assert result.hero.has_status("natural_ambition")
    assert result.hero.get_status_data("natural_ambition", "class_feat", None) == "deitys_domain"
    assert result.hero.get_status_data("deitys_domain", "selected_domain", None) == "truth"

    prompt_text = "\n".join(ui.prompts)
    assert prompt_text.count("Champion: wybierz deity") == 1
    assert "Deity's Domain: wybierz deity" not in prompt_text


def test_champion_invalid_preselected_class_feat_is_corrected_after_setup(monkeypatch, tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")

    class _StatusUiCapture:
        enabled = True
        allow_cli_fallback = False

        def __init__(self):
            self.answers = ["1", "1", "iomedae"]
            self.prompts: list[str] = []

        def prompt_choice(self, prompt, choices=None, **_kwargs):
            self.prompts.append(str(prompt or ""))
            if self.answers:
                return self.answers.pop(0)
            if choices:
                return choices[0]
            return None

        def prompt_info(self, *_args, **_kwargs):
            return None

    class _CreationGameStub:
        def __init__(self):
            self.ui = None
            self.logs: list[str] = []

        def ui_log(self, message: str) -> None:
            self.logs.append(str(message))

        def ui_hero(self, *_args, **_kwargs):
            return None

        def ui_active_actor(self, *_args, **_kwargs):
            return None

    game = _CreationGameStub()
    ui = _StatusUiCapture()

    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    heritage_id = str((HERITAGE_IDS_BY_ANCESTRY.get("human") or [""])[0] or "")
    ancestry_feat_id = ""
    for candidate in list(ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("human") or []):
        status = resolve_status(candidate)
        data = getattr(status, "data", None) or {}
        if not data.get("ui_choice_kind"):
            ancestry_feat_id = str(candidate)
            break
    if not ancestry_feat_id:
        ancestry_feat_id = str((ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("human") or [""])[0] or "")
    background_id = "background_acolyte"
    if resolve_status(background_id) is None:
        background_id = str((list_background_status_ids() or [""])[0] or "")

    def _fake_pick_portrait(_game, **_kwargs):
        return "/static/placeholder.png"

    def _fake_prompt_text(_game, *, title, **_kwargs):
        if "imię" in str(title).lower() or "imie" in str(title).lower():
            return "Aegis"
        return "tekst"

    def _fake_pick_one(_game, *, title, **_kwargs):
        if str(title).startswith("KROK 2: Wybór Ancestry"):
            return "human"
        if str(title).startswith("KROK 3: Wybór Heritage"):
            return heritage_id
        if str(title).startswith("KROK 4: Ancestry Feat"):
            return ancestry_feat_id
        if str(title).startswith("KROK 5: Background"):
            return background_id
        if str(title).startswith("KROK 6: Wybór Klasy"):
            return "champion"
        if str(title).startswith("KROK 11: Class Feat"):
            return "unimpeded_step"
        if str(title).startswith("KROK 11A: Class Feat (korekta po setupie)"):
            return "ranged_reprisal"
        return None

    def _fake_pick_ability(_game, *, allowed, **_kwargs):
        options = list(allowed or [])
        return str(options[0]) if options else None

    monkeypatch.setattr("character_creation.pipeline._pick_portrait_image", _fake_pick_portrait)
    monkeypatch.setattr("character_creation.pipeline._prompt_text", _fake_prompt_text)
    monkeypatch.setattr("character_creation.pipeline._pick_one", _fake_pick_one)
    monkeypatch.setattr("character_creation.pipeline._pick_ability", _fake_pick_ability)
    monkeypatch.setattr("character_creation.pipeline._pick_additional_skills", lambda *_a, **_k: [])
    monkeypatch.setattr("character_creation.pipeline._resolve_background_training_choice", lambda *_a, **_k: (None, None))
    monkeypatch.setattr("character_creation.pipeline._run_starting_equipment_step", lambda *_a, **_k: None)
    monkeypatch.setattr("character_creation.pipeline._prompt_info", lambda *_a, **_k: None)

    result = create_character(game, repo)
    assert result is not None
    assert result.hero.has_status("champion")
    assert result.hero.has_status("ranged_reprisal")
    assert not result.hero.has_status("unimpeded_step")
