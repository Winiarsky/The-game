from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor, prepare_spells


@dataclass(frozen=True, slots=True)
class SpellPreparationTransition:
    actors: tuple[Actor, ...]
    actor_id: str
    prepared_spell_ids: tuple[str, ...]
    complete: bool


class SpellPreparationFlowService:
    """Coordinates a pre-scenario spell selection without knowing character classes."""

    def __init__(self, fixed_deck_actor_ids: tuple[str, ...] = ()) -> None:
        self.fixed_deck_actor_ids = frozenset(fixed_deck_actor_ids)

    def pending_actors(self, actors: tuple[Actor, ...]) -> tuple[Actor, ...]:
        return tuple(
            actor
            for actor in actors
            if str(actor.id) not in self.fixed_deck_actor_ids
            and actor.spell_preparation is not None
            and not actor.spell_preparation.confirmed
        )

    def confirm(
        self,
        *,
        actors: tuple[Actor, ...],
        actor_id: str,
        spell_ids: tuple[str, ...],
    ) -> SpellPreparationTransition:
        actor = next((candidate for candidate in actors if str(candidate.id) == actor_id), None)
        if actor is None:
            raise ValueError("Nieznana postać przygotowująca czary.")
        if actor.spell_preparation is None:
            raise ValueError(f"{actor.name} nie przygotowuje czarów.")
        if actor.spell_preparation.confirmed:
            raise ValueError(f"{actor.name} już potwierdził przygotowane czary.")
        profile = prepare_spells(actor.spell_preparation, spell_ids)
        updated_actor = replace(actor, spell_preparation=profile)
        updated_actors = tuple(updated_actor if candidate.id == actor.id else candidate for candidate in actors)
        return SpellPreparationTransition(
            actors=updated_actors,
            actor_id=actor_id,
            prepared_spell_ids=profile.prepared_spell_ids,
            complete=not self.pending_actors(updated_actors),
        )
