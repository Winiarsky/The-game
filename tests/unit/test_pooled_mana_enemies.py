from dataclasses import replace

import pytest

from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for
from tests.unit.test_pooled_mana_runtime import prepare, send
from dnd_board_game.actors import FeatureGrant, FeatureSourceKind
from dnd_board_game.combat.pooled_mana import enemy_pressure
from dnd_board_game.scenarios.pooled_mana_catalog import load_catalog
from dnd_board_game.rules.pooled_mana import attack_mana
from dnd_board_game.rules.shared_mana import sync_pool


def test_enemy_burn_only_on_hit_and_scheduled_round_once(heroes, tmp_path):
    s = session_for(heroes["garran"], tmp_path, pooled=True)
    prepare(s)
    enemy = next(a for a in s.combat_state.actors if str(a.id) != "garran")
    enemy = replace(enemy, features=(*enemy.features, FeatureGrant("mana_burn_offer", "Spalanie", FeatureSourceKind.MONSTER, "test", "Spal kartę.")))
    state = s.combat_state
    assert enemy_pressure(state, enemy, load_catalog()["enemy_mana"], hit=True)[0] == state
    state = replace(state, initiative_order=replace(state.initiative_order, round_number=2))
    assert enemy_pressure(state, enemy, load_catalog()["enemy_mana"], hit=False)[0] == state
    updated, message = enemy_pressure(state, enemy, load_catalog()["enemy_mana"], hit=True)
    assert message and updated.shared_mana.pooled.burned == ("B",)
    assert enemy_pressure(updated, enemy, load_catalog()["enemy_mana"], hit=True)[0] == updated


def test_dead_captor_releases_cards_only_after_physical_confirmation(heroes, tmp_path):
    s = session_for(heroes["garran"], tmp_path, pooled=True)
    prepare(s)
    enemy = next(a for a in s.combat_state.actors if str(a.id) != "garran")
    pool = attack_mana(s.combat_state.shared_mana.pooled, "offer", captor=str(enemy.id))
    s.combat_state = replace(s.combat_state, shared_mana=sync_pool(s.combat_state.shared_mana, pool),
                            actors=tuple(replace(a, hp=0) if a.id == enemy.id else a for a in s.combat_state.actors))
    s.state_payload()
    assert s.combat_state.shared_mana.pooled.phase == "release"
    send(s, "pool_release")
    assert not s.combat_state.shared_mana.pooled.prisons
    assert s.combat_state.shared_mana.pooled.deck[-1] == "B"


def test_final_tutorial_enemy_burn_survives_result_confirmation(tmp_path):
    from random import Random
    from tests.unit.test_training_walkthrough import prepared, prepare_pool
    from dnd_board_game.application.training_walkthrough import steps
    from dnd_board_game.ui.training_tutorial import acknowledge, notice_id
    from dnd_board_game.combat import current_actor

    class HitRng(Random):
        def randint(self, a: int, b: int) -> int:
            return b

    s = prepared(tmp_path, "dagna", len(steps("dagna")))
    acknowledge(s, notice_id(s))
    s.submit_encounter_initiative_roll(20)
    prepare_pool(s)
    send(s, "pool_take", index=0)
    s.finish_combat_turn()
    assert str(current_actor(s.combat_state).id) == "recruitment_dummy"
    s.combat_state = replace(s.combat_state, initiative_order=replace(s.combat_state.initiative_order, round_number=2))
    s.encounter_rng = HitRng()
    s.resolve_enemy_turn()
    if s.pending_enemy_turn_result or s.pending_enemy_turn_intent:
        s._commit_pending_enemy_turn()
    assert s.pending_enemy_turn_ack_result
    assert s.combat_state.shared_mana.pooled.phase == "burn"
    with pytest.raises(ValueError, match="spalenie"):
        s.confirm_enemy_turn_result()
    send(s, "pool_color", color="Z")
    send(s, "pool_color", color="N")
    s.confirm_enemy_turn_result()
    assert s.combat_state.shared_mana.pooled.burned == ("Z", "N")
    assert s.combat_state.shared_mana.pooled.hand("dagna")
    assert s.combat_state.shared_mana.pooled.phase == "expire"
    send(s, "pool_color", color="F")
    assert s.combat_state.shared_mana.pooled.expired == ("F",)
    assert s.combat_state.shared_mana.pooled.phase == "reveal"


@pytest.mark.parametrize('feature', ['mana_burn_offer', 'mana_burn_deck', 'mana_prison'])
def test_monster_mana_features_load_as_real_content_mechanics(feature):
    import json
    from pathlib import Path
    from dnd_board_game.scenarios.loader import _parse_feature_definition
    data = json.loads((Path('content/features') / (feature + '.json')).read_text())
    assert _parse_feature_definition(data, 'enemy').definition.id == feature
    data['grants']['mana_pressure'] = 'unknown'
    with pytest.raises(ValueError, match='mana_pressure'):
        _parse_feature_definition(data, 'enemy')
