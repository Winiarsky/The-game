"""Validated content boundary for the accepted directed rune-memory profile."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.rules.resonance import PROFILE
from dnd_board_game.rules.rune_modifiers import validate_modifiers
from dnd_board_game.ui.board_panel_symbols import RUNES, rune_slot

CATALOG_PATH = Path(__file__).resolve().parents[3] / "content/print/rune_relations_v03/catalog.json"


def legal_memories(relations: Mapping[str, list[str]], limit: int) -> tuple[tuple[str, ...], ...]:
    """Enumerate short legal windows to check that printed conditions are reachable."""
    windows: list[tuple[str, ...]] = []
    frontier = [(rune,) for rune in relations]
    for _ in range(limit):
        windows.extend(frontier)
        frontier = [(*path, rune) for path in frontier for rune in relations[path[-1]]]
    return tuple(windows)


def validate_catalog(data: dict[str, Any]) -> None:
    """Validate the complete seven-hero edition without imposing old mode prices."""
    if type(data.get("version")) is not int or data["version"] != 3 or data.get("profile") != PROFILE or data.get("stage") not in {"cards_mock", "runtime"}:
        raise ValueError("Nieprawidłowy profil lub etap katalogu relacji run v0.3.")
    rules = data["rules"]
    if rules.get("resonance_model") != "directed_rune_memory" or rules.get("memory_limit") != 3:
        raise ValueError("Relacje run wymagają pamięci trzech wpisów.")
    if (rules.get("start_charges"), rules.get("max_charges"), rules.get("focus_die"), rules.get("regeneration_die")) != (20, 20, 20, 4):
        raise ValueError("Wymagane 20 ładunków, Skupienie 1k20 i odzysk 1k4.")
    if rules.get("regeneration_limit") != "once_per_hero_per_round" or rules.get("save_dc_base") != 10:
        raise ValueError("Nieprawidłowy limit odzysku lub podstawa ST.")
    policies = {"bonus_timing": "before_new_rune_after_continuity_check", "mismatch": "clear_before_base_action_then_start_new_chain",
        "wave_behavior": "universal_bridge_without_copy_or_substitution", "end_without_power": "end_of_conscious_hero_turn",
        "finisher_miss": "pay_and_clear_after_resolution", "temporary_effects": "own_duration_survives_chain_end"}
    if any(rules.get(key) != value for key, value in policies.items()):
        raise ValueError("Katalog musi zachować zaakceptowane terminy i sposób kontynuacji.")
    starter = rules["starter_runes"]
    if len(starter) != 10 or len(set(starter)) != 10 or set(starter) - {name for name, _ in RUNES}:
        raise ValueError("Wymagane dziesięć różnych run początkowych panelu.")
    if [r["name"] for r in data["runes"]] != starter:
        raise ValueError("Opisy run muszą odpowiadać runom początkowym.")
    if rules.get("focus_rune") != "Spirala" or rules.get("information_slot") != rune_slot("Gwiazda"):
        raise ValueError("Spirala i Gwiazda pozostają przyciskami sterowania.")
    reserved = rules["reserved_runes"]
    if len(reserved) != 9 or len(set(reserved)) != 9 or set(reserved) != {name for name, _ in RUNES} - set(starter) - {"Spirala"}:
        raise ValueError("Dziewięć pozostałych run należy zachować do rozwoju.")
    relations = rules["rune_relations"]
    if set(relations) != set(starter):
        raise ValueError("Każda runa początkowa wymaga własnej listy kontynuacji.")
    for source, targets in relations.items():
        if not isinstance(targets, list) or len(set(targets)) != len(targets) or set(targets) - set(starter):
            raise ValueError(f"Nieprawidłowe kontynuacje runy {source}.")
        if source == "Fala":
            valid = set(targets) == set(starter)
        else:
            valid = len(targets) == 4 and "Fala" in targets and source not in targets
        if not valid:
            raise ValueError(f"Runa {source}: trzy kontynuacje oraz Fala; Fala łączy wszystkie runy.")
    if rules.get("wave_owner") != "nimra" or rules.get("rune_presence") != "boolean":
        raise ValueError("Fala należy tylko do Nimry; obecność run nie kumuluje premii.")
    if set(data["heroes"]) != set(PLAYABLE_HERO_IDS):
        raise ValueError("Wymagane wszystkie siedem postaci.")
    memories = legal_memories(relations, 3)
    card_ids: set[str] = set()
    produced: set[str] = set()
    for hero_id, hero in data["heroes"].items():
        count = 5 if hero_id == "nimra" else 4
        cards = hero["cards"]
        if len(cards) != count or len({c["rune"] for c in cards}) != count:
            raise ValueError(f"{hero_id}: wymagane {count} moce pod różnymi runami.")
        if len(hero["regeneration"]) != 2 or not all(hero["regeneration"]):
            raise ValueError(f"{hero_id}: wymagane dwa wyzwalacze wspólnego odzysku.")
        for card in cards:
            if card["id"] in card_ids:
                raise ValueError("Powtórzony identyfikator mocy.")
            card_ids.add(card["id"])
            rune = card["rune"]
            produced.add(rune)
            if rune not in starter or (rune == "Fala" and (hero_id != "nimra" or card["id"] != "misty_step")):
                raise ValueError("Moc wymaga runy początkowej; Fala należy tylko do Mglistego kroku Nimry.")
            if type(card["cost"]) is not int or not 3 <= card["cost"] <= 8 or {"base_cost", "enhanced_cost"} & card.keys():
                raise ValueError("Moc wymaga jednego kosztu od 3 do 8 ładunków.")
            if card["budget"] not in {"S", "A+S", "M+S"} or not all(card.get(key) for key in ("name", "target", "effect", "requirements")):
                raise ValueError("Niepełny opis lub nieprawidłowy budżet mocy.")
            validate_modifiers(card.get("base_modifiers", {}))
            required = card.get("requires_resonance", [])
            if "ends_resonance" in card and type(card["ends_resonance"]) is not bool:
                raise ValueError("Znacznik wyładowania musi być logiczny.")
            if bool(required) != bool(card.get("ends_resonance", False)) or (required and len(required) != 2):
                raise ValueError("Wyładowanie wymaga dwóch symboli i wygasza pamięć.")
            conditions = [required] if required else []
            for bonus in card["resonance_bonuses"]:
                if not bonus.get("text") or not bonus.get("modifiers"):
                    raise ValueError("Każda premia wymaga opisu i rzeczywistego efektu.")
                validate_modifiers(bonus["modifiers"])
                conditions.append(bonus["requires"])
            for symbols in conditions:
                if not isinstance(symbols, list) or not 1 <= len(symbols) <= 2 or len(set(symbols)) != len(symbols) or set(symbols) - set(starter):
                    raise ValueError("Warunek mocy wymaga różnych run początkowych.")
                if not any(set(symbols) <= set(memory) and rune in relations[memory[-1]] for memory in memories):
                    raise ValueError(f"Nieosiągalny warunek mocy {card['id']}.")
    if produced != set(starter):
        raise ValueError("Każda runa początkowa wymaga przynajmniej jednej mocy.")


def load_rune_relation_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_catalog(data)
    return data


def load_rune_relation_player_aid(path: Path | None = None, *, catalog: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """UI and printable help derive their relation table from the same catalog."""
    path = path or CATALOG_PATH.parents[2] / "scenarios/misja_0_dzwon/text/sciaga_relacje_v03.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    catalog = catalog if catalog is not None else load_rune_relation_catalog()
    for page in data["pages"]:
        for section in page["sections"]:
            if section.pop("relation_table", False):
                section["table"] = [["Ostatnia runa", "Podtrzymasz tymi runami"],
                    *[[rune, ", ".join(catalog["rules"]["rune_relations"][rune])]
                      for rune in catalog["rules"]["starter_runes"] if rune != "Fala"]]
    return data["pages"]
