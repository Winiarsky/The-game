"""Shared, profile-specific passive notes for the UI and physical prints."""

from .boardgame_help import RuleNote
from dnd_board_game.actors import Actor, FeatureGrant
from dnd_board_game.rules.charge_rolls import uses_charge


HIDDEN_SKILL_FEATURES = frozenset({"expertise", "erynd_expertise", "jack_of_all_trades", "skill_versatility"})


def visible_character_features(actor: Actor) -> tuple[FeatureGrant, ...]:
    """Show active abilities, the flaw and current saturation in charge profiles."""
    return tuple(f for f in actor.features
                 if not uses_charge(actor) or (
                     f.feature_id not in HIDDEN_SKILL_FEATURES and (
                         f.action_ids or f.feature_id.startswith('flaw_')
                         or f.feature_id == 'mana_saturation'
                         or f.source_ref == 'mana_saturation:color')))


def physical_mana_passives(hero_id: str) -> tuple[RuleNote, ...]:
    from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
    profile = hero_profile(hero_id)
    return (RuleNote(profile['passive_name'], profile['passive']),)


def physical_mana_flaw(hero_id: str) -> RuleNote:
    from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
    profile = hero_profile(hero_id)
    name, body = profile["flaw_name"], profile["flaw"]
    return RuleNote(name, body)
