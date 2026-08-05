from dnd_board_game.actors import Actor, ActorId, Faction, PreparableSpell, SpellPreparationProfile
from dnd_board_game.application import SpellPreparationFlowService
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, *, preparation: bool = True) -> Actor:
    profile = (
        SpellPreparationProfile(
            source_label="lista próbna",
            preparation_limit=1,
            available_spells=(PreparableSpell("bless", "Błogosławieństwo", 1),),
            prepared_spell_ids=("bless",),
        )
        if preparation
        else None
    )
    return Actor(
        ActorId(actor_id),
        actor_id,
        10,
        10,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        spell_preparation=profile,
    )


def test_flow_confirms_only_actor_requiring_preparation() -> None:
    service = SpellPreparationFlowService()
    actors = (_actor("cleric"), _actor("fighter", preparation=False))

    transition = service.confirm(actors=actors, actor_id="cleric", spell_ids=("bless",))

    assert transition.complete is True
    assert transition.actors[0].spell_preparation is not None
    assert transition.actors[0].spell_preparation.confirmed is True
    assert service.pending_actors(transition.actors) == ()


def test_fixed_personal_deck_skips_pre_scenario_preparation() -> None:
    service = SpellPreparationFlowService(("dagna", "nimra"))
    actors = (_actor("dagna"), _actor("nimra"), _actor("custom_cleric"))

    assert tuple(str(actor.id) for actor in service.pending_actors(actors)) == (
        "custom_cleric",
    )
