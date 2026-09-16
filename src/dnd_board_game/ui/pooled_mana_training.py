"""Physical fixtures and success boundaries for the mana lessons."""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession

from dnd_board_game.application.pooled_mana_training import lesson_hand, prepare_lesson
from dnd_board_game.rules.pooled_mana import PooledMana, attack_mana, release, start_turn
from dnd_board_game.rules.shared_mana import sync_pool
from dnd_board_game.scenarios.pooled_mana_catalog import pool_ability, hero_profile


@lru_cache(maxsize=256)
def prepared_hand(hero: str, ability_id: str, boost: str, copies: int) -> tuple[str, ...]:
    if ability_id == "pool_charge":
        from itertools import product
        from dnd_board_game.rules.pooled_mana import COLORS
        values = hero_profile(hero)["values"]
        hands = [tuple(c for c, n in zip(COLORS, counts) for _ in range(n))
                 for counts in product(range(copies + 1), repeat=5)
                 if sum(values[c] * n for c, n in zip(COLORS, counts)) == 20]
        return min(hands, key=lambda h: (len(h), h))
    from dnd_board_game.rules.shared_mana_catalog import shared_ability
    ability = shared_ability(hero, ability_id)
    color = next((b.color for b in ability.boosts if b.id == boost), "")
    return lesson_hand(pool_ability(ability_id, hero), hero_profile(hero)["values"], copies, color)


def preparation(s: ExplorationUiSession) -> str:
    from .training_walkthrough import current_step, hero_id
    from dnd_board_game.rules.pooled_mana import deck_copies
    step = current_step(s)
    if step is not None and step.ability.id == "pool_drain":
        return "Na potrzeby ćwiczenia po tasowaniu ułóż w talii tylko trzy karty, od wierzchu: czerwoną, białą, zieloną. Pozostałe 22 połóż jako spalone. Dopiero wtedy potwierdź ✓."
    if step is None or step.ability.category == "tutorial" and step.ability.id != "pool_charge":
        return ""
    cards = prepared_hand(hero_id(s), step.ability.id, step.boost_id, deck_copies(1))
    from .pooled_mana import NAMES
    text = "Po przetasowaniu kompletu przygotuj osobistą pulę: " + (", ".join(NAMES[c] for c in cards) if cards else "pusta — ta zdolność jest bez many") + ". Następnie odkryj dwie karty oferty; w tej przygotowanej lekcji nie dobierasz dodatkowej karty. "
    if step.ability.id == "pool_charge":
        text = text.replace("w tej przygotowanej lekcji nie dobierasz dodatkowej karty", "dobierz jedną kartę do przygotowanych 20 pkt")
    if step.ability.id in {"mana_recovery", "mana_great_tuning"}:
        from dnd_board_game.rules.pooled_mana import new_mana, confirm_shuffle
        pool = prepare_lesson(confirm_shuffle(new_mana((hero_id(s),), hero_id(s))), step.ability.id, cards)
        text += "Połóż jako spalone: " + ", ".join(NAMES[c] for c in pool.burned) + ". "
    return text


def after_shuffle(s: ExplorationUiSession, pool: PooledMana, *, was_drain: bool) -> PooledMana:
    from .training_walkthrough import exercising, current_step, hero_id, put
    if not exercising(s):
        return pool
    step = current_step(s)
    if was_drain:
        if step.ability.id == "pool_drain":
            success(s)
        return pool
    cards = () if step.ability.category == "tutorial" and step.ability.id != "pool_charge" else prepared_hand(hero_id(s), step.ability.id, step.boost_id, pool.copies)
    put(s, pool_reaction_started=False, pool_attack_done=False)
    return prepare_lesson(pool, step.ability.id, cards)


def success(s: ExplorationUiSession) -> None:
    from .training_walkthrough import put, complete_step
    put(s, phase="success", paid=False)
    complete_step(s)
    s.board_panel_context = None
    s.board_selection_revision += 1


def controls(s: ExplorationUiSession) -> list[dict[str, object]]:
    from .training_walkthrough import exercising, current_step, flag
    if not exercising(s) or s.combat_state.shared_mana.pooled.phase != "ready":
        return []
    key = current_step(s).ability.id
    if key == "pool_charge":
        return [dict(slot=28, command="pool_lesson_attack", label="Rozpocznij próbną kolejną turę — bez doboru")]
    if key == "pool_expire" and not flag(s, "pool_attack_done", False):
        return [dict(slot=28, command="pool_lesson_attack", label="Zakończ próbną rundę — jedna karta wygasa")]
    if key in {"pool_burn", "pool_prison", "pool_drain"}:
        if flag(s, "pool_attack_done", False):
            return [dict(slot=28, command="pool_lesson_release", label="Nessa: pokonaj więżącą kukłę i oddaj kartę na spód")]
        return [dict(slot=28, command="pool_lesson_attack", label="Nessa: uruchom zapowiedziany atak na manę")]
    return []


def lesson_command(s: ExplorationUiSession, pool: PooledMana, action: str) -> PooledMana:
    from .training_walkthrough import current_step, put
    if not any(c["command"] == action for c in controls(s)):
        raise ValueError("To polecenie nie należy do obecnego ćwiczenia.")
    key = current_step(s).ability.id
    if key == "pool_charge":
        pool = start_turn(pool, pool.actor)
        if pool.phase != "ready" or pool.draw_due:
            raise ValueError("Przygotowana pula nie osiągnęła 21 pkt.")
        success(s)
    elif key == "pool_expire":
        pool = start_turn(pool, "nessa", round_end=True)
        put(s, pool_attack_done=True)
    elif action == "pool_lesson_release":
        pool = release(pool, "recruitment_dummy")
        success(s)
    else:
        pool = attack_mana(pool, "deck" if key == "pool_drain" else "offer",
                           2 if key == "pool_drain" else 1,
                           captor="recruitment_dummy" if key == "pool_prison" else "")
        put(s, pool_attack_done=True)
        if key == "pool_burn":
            success(s)
    return pool


def synchronize(s: ExplorationUiSession) -> None:
    from .training_walkthrough import current_step, flag, put, hero_id
    from dnd_board_game.actors import Faction
    step = current_step(s)
    state = s.combat_state
    pool = state.shared_mana.pooled if state.shared_mana else None
    if pool is None or pool.phase != "ready":
        return
    if flag(s, "charge_pending_ability", ""):
        from .training_walkthrough import record_ability
        key = flag(s, "charge_pending_ability", "")
        put(s, charge_pending_ability="")
        record_ability(s, key, hero_id(s))
        return
    if step.ability.id == "pool_expire" and pool.expired:
        success(s)
    elif step.ability.id == "pool_draw" and pool.hand(hero_id(s)):
        success(s)
    elif step.ability.id == "pool_hold" and state.turn_action.attacks_used > 0 and not s._combat_has_pending_resolution():
        success(s)
    elif step.ability.timing == "R" and not flag(s, "pool_reaction_started", False):
        index = next(i for i, e in enumerate(state.initiative_order.entries) if e.actor.faction == Faction.ENEMY)
        enemy = state.initiative_order.entries[index].actor
        mana = sync_pool(replace(state.shared_mana, turn_actor=str(enemy.id)), start_turn(pool, str(enemy.id)))
        s.combat_state = replace(state, initiative_order=replace(state.initiative_order, current_index=index), shared_mana=mana)
        put(s, pool_reaction_started=True)
        s.resolve_enemy_turn()
