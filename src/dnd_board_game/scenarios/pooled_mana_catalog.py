"""Versioned, file-backed balance catalogue for play, evaluation and printing."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from dnd_board_game.rules.pooled_mana_catalog import PoolAbility
from dnd_board_game.rules.pooled_mana import COLORS
from .character_text import revision, hero_text, action_text, passive_label

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "content/balance/pooled_mana/catalog.json"


def load_catalog(path: str = str(DEFAULT_PATH)) -> dict[str, object]:
    return _load_catalog(revision(Path(path)), revision())


@lru_cache(maxsize=8)
def _load_catalog(balance_revision: tuple, text_revision: tuple) -> dict[str, object]:
    data = json.loads(Path(balance_revision[0]).read_text())
    for hid, hero in data['heroes'].items():
        copy = hero_text(hid)
        hero['flaw_name'] = copy['flaw']['name']
        hero['flaw'] = copy['flaw']['description']
        hero['passive_name'] = 'Nasycenie maną'
        for color, passive in hero['color_passives'].items():
            passive['display'] = dict(copy['passives']['combat'][color])
            passive['label'] = passive_label(passive['display'])
        hero['passive'] = ' '.join(p['label'] for p in hero['color_passives'].values())
    for aid, entry in data['abilities'].items():
        entry.update({k: action_text(entry['hero'], aid)[k] for k in ('name', 'description')})
    if data.get("version") != 3:
        raise ValueError("Nieobsługiwana wersja katalogu pul many.")
    for hero in data["heroes"].values():
        trump = hero.get('trump_color')
        if trump not in COLORS or hero['values'] != {c: 2 if c == trump else 1 for c in COLORS}:
            raise ValueError('Bohater wymaga jednego koloru atutowego liczonego jako 2; pozostałe jako 1.')
        if set(hero["values"]) != set(COLORS) or any(type(v) is not int or v < 1 for v in hero["values"].values()):
            raise ValueError("Nieprawidłowe wartości kolorów bohatera.")
        if set(hero["color_passives"]) != set(COLORS):
            raise ValueError("Bohater wymaga pięciu pasywów kolorów.")
        allowed = {"wounded_melee_damage", "radiant_spell_damage", "audience_guard", "full_pool_spell_damage", "elemental_ward", "temp_hp", "feature", "melee_damage", "ranged_damage", "spell_damage", "attack", "ac", "heal", "heal_party", "heal_weakest", "burn_discount", "save_all", *("save_" + a for a in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"))}
        for passive in hero["color_passives"].values():
            if passive["kind"] not in allowed or type(passive["value"]) is not int or passive["value"] < 1 or type(passive["cap"]) is not int or passive["cap"] < 0:
                raise ValueError("Nieprawidłowy pasyw koloru.")
            expected_stacking = (passive['kind'] not in {'feature', 'temp_hp'} and not passive['kind'].startswith('heal')
                                 and (passive['cap'] == 0 or passive['cap'] > passive['value']))
            if passive.get('stackable') is not expected_stacking:
                raise ValueError('Obwódka kumulacji musi odpowiadać regule i limitowi pasywu.')
            if passive['kind'] == 'feature':
                from dnd_board_game.actors.mana_passives import FEATURE_LABELS
                features = passive.get('features', ())
                if not features or len(features) != len(set(features)) or any(f not in FEATURE_LABELS for f in features) or passive['value'] != 1 or passive['cap'] != 1:
                    raise ValueError('Odblokowanie wymaga znanych, niepowtarzalnych cech i limitu 1.')
    for key, value in data["abilities"].items():
        if value["minimum"] not in (0, 2, 4, 6):
            raise ValueError("Próg zdolności musi wynosić 0, 2, 4 albo 6 ładunku.")
        if value["hero"] not in data["heroes"]:
            raise ValueError("Zdolność ma nieznanego właściciela.")
        if any(n > 5 for n in value["required"].values()):
            raise ValueError("Warunek koloru jest nieosiągalny w najmniejszej talii.")
        PoolAbility(key, value["hero"], value["minimum"], tuple(value["required"].items()), value["free"], value["burn"])
    for entry in data.get("enemy_mana", {}).values():
        if entry["source"] not in {"offer", "deck"} or type(entry["count"]) is not int or entry["count"] < 1 or type(entry["period"]) is not int or entry["period"] < 1 or type(entry["prison"]) is not bool:
            raise ValueError("Nieprawidłowy atak przeciwnika na manę.")
    return data


def pool_ability(ability_id: str, hero_id: str = "", *, path: str = str(DEFAULT_PATH)) -> PoolAbility:
    if ability_id.startswith("basic_attack:"):
        return PoolAbility(ability_id, hero_id, 0, (), True, 0)
    value = load_catalog(path)["abilities"][ability_id]
    return PoolAbility(ability_id, value["hero"], value["minimum"], tuple(value["required"].items()), value["free"], value["burn"])


def hero_profile(hero_id: str, *, path: str = str(DEFAULT_PATH)) -> dict[str, object]:
    return load_catalog(path)["heroes"][hero_id]


def requirement_text(ability_id: str, hero_id: str = "") -> str:
    ability = pool_ability(ability_id, hero_id)
    if ability.free:
        return "Bez many; normalny koszt akcji i ograniczenia użycia."
    names = {"C": "czerwona", "B": "biała", "Z": "zielona", "F": "czarna", "N": "niebieska"}
    colors = ", ".join(f"{n} × {names[c]}" for c, n in ability.required)
    return f"Ładunek co najmniej {ability.minimum}/6" + (f" i {colors}" if colors else "") + (f". Zachowaj pulę; spal {ability.burn} " + ("kartę" if ability.burn == 1 else "karty" if ability.burn in (2, 3, 4) else "kart") + " z wierzchu po efekcie.")


def ability_description(hero_id: str, ability_id: str) -> str:
    from dnd_board_game.rules.shared_mana_catalog import shared_ability
    ability = shared_ability(hero_id, ability_id)
    text = action_text(hero_id, ability_id)
    boosts = text['boost_summary'] or ' '.join(
        f"{text['boosts'][b.id]} (maks. {b.maximum})" for b in ability.boosts)
    cost = (f'Każde podbicie: +2 spalone karty; łącznie maks. {min(ability.boost_limit, sum(b.maximum for b in ability.boosts))}. Kolor runy nie jest wymaganiem puli.' if ability.boosts else '')
    return ' '.join(part for part in (text['description'], boosts, cost) if part)
