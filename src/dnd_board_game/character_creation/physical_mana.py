"""Explicit board-game profile; generic 5e characters keep their resource rules."""
from dataclasses import replace

from dnd_board_game.actors import Actor, FeatureGrant, FeatureSourceKind
from dnd_board_game.actors.resources import PHYSICAL_MANA_RESOURCES
from dnd_board_game.rules.physical_mana import hero_abilities, FLAWS, MANA_PASSIVES
from .loadout_repair import repair_mira_loadout

RETIRED_LORIAN = frozenset({
    "crossbowman", "bardic_inspiration", "provoking_shot", "faerie_fire",
    "hideous_laughter", "stage_command", "accelerated_refrain", "counterpoint",
    "cutting_words",
})


def apply_physical_mana_profile(actor: Actor) -> Actor:
    abilities = hero_abilities(str(actor.id))
    if not abilities:
        return actor
    known = {ability.id: ability for ability in abilities}
    features = tuple(
        replace(feature, resource_ids=(), source_ref="physical_mana:v02", description=known[feature.feature_id].description)
        if feature.feature_id in known else feature
        for feature in actor.features
        if feature.feature_id != "physical_mana_v02"
        and feature.feature_id != "pooled_mana_v01"
        and not (str(actor.id) == "lorian" and feature.feature_id in RETIRED_LORIAN and feature.feature_id not in known)
    )
    from dnd_board_game.rules.shared_mana_catalog import HOLY_SYMBOL
    if str(actor.id) == "dagna":
        from dnd_board_game.rules.physical_mana import mana_ability
        known[HOLY_SYMBOL.id] = mana_ability("dagna", HOLY_SYMBOL.id)
    features = tuple(
        replace(f, action_ids=tuple(a for a in f.action_ids if a in known))
        for f in features if f.feature_id != "shared_mana_v03"
    )
    flaw_id, flaw_name, flaw_text = FLAWS[str(actor.id)]
    passive_id, passive_name, passive_text = MANA_PASSIVES[str(actor.id)]
    overrides = {flaw_id: (flaw_name, flaw_text), passive_id: (passive_name, passive_text),
                 "channel_divinity_preserve_life": ("Zachowanie życia", known["preserve_life"].description) if "preserve_life" in known else ("", ""),
                 "mira_shadow_killer": ("Atak z cienia", "+1k6 za ukrycie przed celem lub własną flankę; +2k6 za oba. Raz we własnej turze, wybrane trafienie przed obrażeniami."),
                 "first_blood": ("Pierwsza krew", "+1k6 raz we własnej turze przy trafieniu łukiem celu z pełnymi PW.")}
    features = tuple(replace(f, label=overrides[f.feature_id][0], description=overrides[f.feature_id][1],
                             source_ref="physical_mana:v02", resource_ids=()) if f.feature_id in overrides else f
                     for f in features if not (str(actor.id) == "nimra" and f.feature_id == "arcane_recovery"))
    if not any(f.feature_id == passive_id for f in features):
        features += (FeatureGrant(passive_id, passive_name, FeatureSourceKind.CLASS, "physical_mana:v02", passive_text),)
    existing = {f.feature_id for f in features} | {action for f in features for action in f.action_ids}
    features += tuple(
        FeatureGrant(ability.id, ability.name, FeatureSourceKind.CLASS,
                     "physical_mana:v02", ability.description, action_ids=(ability.id,))
        for ability in known.values() if ability.id not in existing
    )
    features += (FeatureGrant("physical_mana_v02", "Fizyczna mana",
                              FeatureSourceKind.SCENARIO, "physical_mana:v02",
                              "Fizyczne karty many. W tym profilu obowiązują osobiste pule i oferta dwóch kart."),
                 FeatureGrant("shared_mana_v03", "Wspólna mana 0.3", FeatureSourceKind.SCENARIO,
                              "shared_mana:v03", "Obsługa płatności, podbić i efektów. Zasady doboru określa profil osobistych pul."))
    from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile, requirement_text, ability_description
    profile = hero_profile(str(actor.id))
    features = tuple(replace(f, label=profile["passive_name"], description=profile["passive"])
                     if f.feature_id == passive_id else
                     replace(f, label=profile["flaw_name"], description=profile["flaw"])
                     if f.feature_id == flaw_id else f for f in features)
    features += (FeatureGrant("pooled_mana_v01", "Osobista pula many", FeatureSourceKind.SCENARIO,
                              "pooled_mana:v01", "Dobieraj jedną z dwóch kart do 21+ pkt. Zachowuj ładunek; kolory dają premie, akcje spalają talię. Drain zbiera też spalone, wygasłe i uwięzione."),)
    features = tuple(replace(f, description=requirement_text(f.feature_id, str(actor.id)) + " " + ability_description(str(actor.id), f.feature_id))
                     if f.feature_id in known else f for f in features)
    spell_ids = tuple(spell_id for spell_id in actor.spell_ids if spell_id in known)
    from dnd_board_game.actors.mana_passives import normalize_mana_passives
    # The old per-hero passive ids must not accidentally enable native 5e hooks.
    features = tuple(f for f in features if f.feature_id != passive_id and f.feature_id != 'mana_saturation')
    features += (FeatureGrant('mana_saturation', 'Nasycenie maną', FeatureSourceKind.SCENARIO,
                              'mana_saturation:v1', profile['passive']),)
    return normalize_mana_passives(repair_mira_loadout(replace(
        actor, features=features, attacks_per_action=1,
        resource_pools=tuple(p for p in actor.resource_pools if p.id not in PHYSICAL_MANA_RESOURCES),
        spell_slots=(), spell_ids=spell_ids,
        spells=tuple(spell for spell in actor.spells if spell.id in spell_ids),
        spell_access=tuple(replace(access, resource_ids_by_spell=(), spell_ids=tuple(
            spell_id for spell_id in access.spell_ids if spell_id in spell_ids
        )) for access in actor.spell_access if any(i in spell_ids for i in access.spell_ids)),
    )))
