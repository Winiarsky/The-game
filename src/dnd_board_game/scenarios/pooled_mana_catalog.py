"""Versioned, file-backed balance catalogue for play, evaluation and printing."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from dnd_board_game.rules.pooled_mana_catalog import PoolAbility
from dnd_board_game.rules.pooled_mana import COLORS

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "content/balance/pooled_mana/catalog.json"


@lru_cache(maxsize=8)
def load_catalog(path: str = str(DEFAULT_PATH)) -> dict[str, object]:
    data = json.loads(Path(path).read_text())
    if data.get("version") != 2:
        raise ValueError("Nieobsługiwana wersja katalogu pul many.")
    for hero in data["heroes"].values():
        if set(hero["values"]) != set(COLORS) or any(type(v) is not int or v < 1 for v in hero["values"].values()):
            raise ValueError("Nieprawidłowe wartości kolorów bohatera.")
        if set(hero["color_passives"]) != set(COLORS):
            raise ValueError("Bohater wymaga pięciu pasywów kolorów.")
        allowed = {"feature", "melee_damage", "ranged_damage", "spell_damage", "attack", "ac", "heal", "heal_party", "heal_weakest", "burn_discount", "save_all", *("save_" + a for a in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"))}
        for passive in hero["color_passives"].values():
            if passive["kind"] not in allowed or type(passive["value"]) is not int or passive["value"] < 1 or type(passive["cap"]) is not int or passive["cap"] < 0:
                raise ValueError("Nieprawidłowy pasyw koloru.")
            expected_stacking = (passive['kind'] != 'feature' and not passive['kind'].startswith('heal')
                                 and (passive['cap'] == 0 or passive['cap'] > passive['value']))
            if passive.get('stackable') is not expected_stacking:
                raise ValueError('Obwódka kumulacji musi odpowiadać regule i limitowi pasywu.')
            if passive['kind'] == 'feature':
                from dnd_board_game.actors.mana_passives import FEATURE_LABELS
                features = passive.get('features', ())
                if not features or len(features) != len(set(features)) or any(f not in FEATURE_LABELS for f in features) or passive['value'] != 1 or passive['cap'] != 1:
                    raise ValueError('Odblokowanie wymaga znanych, niepowtarzalnych cech i limitu 1.')
    for key, value in data["abilities"].items():
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
    return f"Co najmniej {ability.minimum} pkt" + (f" i {colors}" if colors else "") + (f". Zachowaj pulę; spal {ability.burn} " + ("kartę" if ability.burn == 1 else "karty" if ability.burn in (2, 3, 4) else "kart") + " z wierzchu po efekcie.")


def ability_description(hero_id: str, ability_id: str) -> str:
    from dnd_board_game.rules.shared_mana_catalog import shared_ability
    ability = shared_ability(hero_id, ability_id)
    entry = load_catalog()["abilities"][ability_id]
    description = entry.get("description", ability.description)
    if ability_id == "spiritual_weapon":
        description = description.replace("D + biała", "D, bez many")
    duration = {"O": "Do mana draina, chyba że opisany warunek lub koncentracja zakończy wcześniej.",
                "T": "Do początku następnej tury źródła, chyba że efekt wykorzystano wcześniej."}.get(ability.duration, "")
    boosts = " ".join(f"{b.label} (maks. {b.maximum})" for b in ability.boosts)
    return " ".join(p for p in (description, duration, boosts,
                    f"Łącznie najwyżej {ability.boost_limit} podbicia, każde kosztuje dodatkowe 2 spalone karty; kolor jest symbolem wariantu, nie wymaganiem puli." if boosts else "") if p)
