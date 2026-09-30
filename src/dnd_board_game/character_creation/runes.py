"""New-game rune profile; old saved mana actors are not migrated on load."""
from __future__ import annotations

from dataclasses import replace
from dnd_board_game.actors import Actor
from dnd_board_game.actors.features import FeatureGrant, FeatureSourceKind
from dnd_board_game.scenarios.rune_catalog import rune_cards


def apply_rune_profile(actor: Actor) -> Actor:
    if any(f.feature_id == "rune_resource_v01" for f in actor.features):
        return normalize_rune_features(actor)
    from .physical_mana import apply_physical_mana_profile
    from .rune_loadout import basic_rune_loadout
    actor = apply_physical_mana_profile(actor)
    actor = basic_rune_loadout(actor)
    features = tuple(f for f in actor.features if f.feature_id not in {"pooled_mana_v01", "mana_passives_v1", "mana_saturation"} and f.source_ref != "mana_saturation:color")
    cards = {card.id: card for card in rune_cards(str(actor.id))}
    features = tuple(replace(f, label="Runy bohatera", description="Koszty run i efekty kart postaci.")
                     if f.feature_id in {"physical_mana_v02", "shared_mana_v03"} else
                     replace(f, label=cards[f.feature_id].name, description=cards[f.feature_id].description, source_ref="runes:v01")
                     if f.feature_id in cards else f for f in features)
    ids = {f.feature_id for f in features}
    for marker in ("physical_mana_v02", "shared_mana_v03", "rune_resource_v01"):
        if marker not in ids:
            features += (FeatureGrant(marker, "Runy bohatera" if marker == "rune_resource_v01" else marker,
                FeatureSourceKind.SCENARIO, "runes:v01"),)
    granted = ids | {action for feature in features for action in feature.action_ids}
    for card in rune_cards(str(actor.id)):
        if card.id not in granted:
            features += (FeatureGrant(card.id, card.name, FeatureSourceKind.SCENARIO, "runes:v01", card.description, action_ids=(card.id,)),)
    return normalize_rune_features(replace(actor, features=features))


def normalize_rune_features(actor: Actor) -> Actor:
    """Refresh rune descriptions and retired grants without resetting actor state."""
    if not any(f.feature_id == "rune_resource_v01" for f in actor.features):
        return actor
    from dnd_board_game.scenarios.rune_traits import rune_flaw
    cards = {card.id: card for card in rune_cards(str(actor.id))}
    if not cards:
        return actor
    flaw = rune_flaw(str(actor.id))
    if any(f.feature_id == "rune_baskets_v02" for f in actor.features):
        from dnd_board_game.scenarios.rune_basket_catalog import basket_cards, load_rune_basket_catalog
        cards = {c.id: c for c in basket_cards(str(actor.id))}
        row = load_rune_basket_catalog()['heroes'][str(actor.id)]['flaw']
        flaw = replace(flaw, name=row['name'], body=row['description'])
    retired = {"mana_great_tuning", "turn_undead", "action_surge", "piercing_attack",
               "distracting_shout", "pooled_mana_v01", "mana_passives_v1", "mana_saturation",
               "nimra_sculpt_field", "nimra_distant_spell", "nimra_overcharged_spell",
               "nimra_forced_weave", "nimra_energy_transmutation"}
    features = []
    for feature in actor.features:
        if feature.feature_id in retired or feature.source_ref == "mana_saturation:color":
            continue
        card = cards.get(feature.feature_id) or next((cards[a] for a in feature.action_ids if a in cards), None)
        if card:
            feature = replace(feature, label=card.name, description=card.description, source_ref="runes:v01")
        elif feature.feature_id.startswith("flaw_"):
            feature = replace(feature, label=flaw.name, description=flaw.body, source_ref="runes:v01")
        elif feature.feature_id in {"physical_mana_v02", "shared_mana_v03"}:
            feature = replace(feature, label="Runy bohatera", description="Koszty run i efekty kart postaci.")
        features.append(feature)
    return replace(actor, features=tuple(features))


def apply_basket_profile(actor: Actor) -> Actor:
    actor = apply_rune_profile(actor)
    if not any(f.feature_id == "rune_baskets_v02" for f in actor.features):
        actor = replace(actor, features=(*actor.features, FeatureGrant("rune_baskets_v02", "Koszyki run", FeatureSourceKind.SCENARIO, "runes:baskets_v02")))
    return normalize_rune_features(actor)
