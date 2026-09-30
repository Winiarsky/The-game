"""Combat declarations and reported wave consequences; never tracks physical cards."""
from dataclasses import replace
from typing import Sequence

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.actors.resources import uses_physical_mana
from dnd_board_game.rules import ActiveEffect, EffectDuration, apply_active_effect
from dnd_board_game.rules.physical_mana import mana_ability, hero_abilities, turn_supply, HERO_NOTES, FLAWS, MANA_PASSIVES
from .session import CombatState, CombatStatus, current_actor
from .conditions import condition_blocks_actions
from .action_economy import ActionUse, ActionEconomyCost
from .session import use_action_economy_cost
from .spells import grid_distance_feet
from .physical_mana_movement import movement_mana_notice


def effect(actor_id: str, kind: str, label: str, value: int = 0,
           duration: EffectDuration = EffectDuration.UNTIL_TURN_END) -> ActiveEffect:
    return ActiveEffect(id=f"{kind}:{actor_id}", actor_id=actor_id, kind=kind,
                        label=label, object_id=f"physical_mana:{kind}", value=value,
                        duration=duration)


def is_basic_weapon(actor: Actor, source: object) -> bool:
    return (uses_physical_mana(actor)
            and getattr(getattr(source, "source_type", None), "value", "") == "weapon"
            and mana_ability(str(actor.id), getattr(source, "id", "")) is None)


def can_declare_attack_series(actor: Actor) -> bool:
    """Only Lorian may buy multiple ordinary attacks with physical mana."""
    from dnd_board_game.actors.resources import uses_shared_mana
    return uses_physical_mana(actor) and not uses_shared_mana(actor) and str(actor.id) == "lorian"


def reconcile_attack_series(
    state: CombatState, effects: tuple[ActiveEffect, ...]
) -> tuple[CombatState, tuple[ActiveEffect, ...]]:
    """Retire obsolete ordinary series in physical-mana saves; keep techniques."""
    restricted_ids = {
        str(actor.id) for actor in state.actors
        if uses_physical_mana(actor) and not can_declare_attack_series(actor)
    }
    actor_id = str(current_actor(state).id)
    old_basic_series = actor_id in restricted_ids and any(
        e.actor_id == actor_id and (
            e.kind == "mana_attack_series"
            or (e.kind == "mana_series_source" and e.object_id == "basic")
        ) for e in effects
    )
    if old_basic_series and state.turn_action.attack_action_active:
        state = replace(state, turn_action=replace(state.turn_action, attacks_maximum=1))
    return state, tuple(
        e for e in effects
        if not (e.actor_id in restricted_ids and e.kind == "mana_attack_series")
    )


def reconcile_rage_rounds(
    state: CombatState, effects: tuple[ActiveEffect, ...]
) -> tuple[ActiveEffect, ...]:
    """Upgrade the former one-turn physical rage without changing generic 5e saves."""
    rounds_by_actor = {}
    for actor in state.actors:
        if not uses_physical_mana(actor):
            continue
        started = next((e.value for e in effects
                        if e.actor_id == str(actor.id) and e.kind == "rage_duration"), state.round_number)
        duration = max(1, (actor.ability_scores.constitution - 10) // 2
                       + (actor.ability_scores.strength - 10) // 2)
        rounds_by_actor[str(actor.id)] = max(1, duration - max(0, state.round_number - started))
    return tuple(
        replace(e, duration=EffectDuration.UNTIL_ENCOUNTER_END,
                remaining_rounds=rounds_by_actor[e.actor_id])
        if e.actor_id in rounds_by_actor and e.kind in {"rage", "rage_duration"}
        and e.remaining_rounds is None and e.duration == EffectDuration.UNTIL_TURN_START
        else e for e in effects
    )


def declare_series(state: CombatState, effects: tuple[ActiveEffect, ...], count: int) -> tuple[ActiveEffect, ...]:
    actor = current_actor(state)
    if not uses_physical_mana(actor) or state.status != CombatStatus.ACTIVE:
        raise ValueError("Ta walka nie używa fizycznej many.")
    if not can_declare_attack_series(actor):
        raise ValueError("Liczbę zwykłych ataków wybiera tylko Lorian. Pozostali wykonują jeden atak.")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("Podaj dodatnią całkowitą liczbę ataków.")
    if series_count(actor, effects) is not None or state.turn_action.action_use != ActionUse.ACTION_AVAILABLE or state.turn_action.attack_action_active:
        raise ValueError("Rozpoczętej serii nie można powiększyć ani rozpocząć kolejnej akcji.")
    if actor.is_defeated() or condition_blocks_actions(state.condition_states, str(actor.id)):
        raise ValueError("Stan postaci blokuje atak.")
    return apply_active_effect(effects, effect(str(actor.id), "mana_attack_series",
                                              f"Seria: {count} ataków · {count} dowolnej many", count)).active_effects


def series_count(actor: Actor, effects: Sequence[ActiveEffect]) -> int | None:
    if not can_declare_attack_series(actor):
        return None
    return next((e.value for e in effects if e.actor_id == str(actor.id)
                 and e.kind == "mana_attack_series"), None)


def attack_maximum(actor: Actor, source: object, effects: Sequence[ActiveEffect], fallback: int, state: CombatState | None = None) -> int:
    if not uses_physical_mana(actor):
        return fallback
    if is_basic_weapon(actor, source):
        if not can_declare_attack_series(actor):
            return 1
        count = series_count(actor, effects)
        if count is None:
            raise ValueError("Najpierw zadeklaruj liczbę ataków. Każdy kosztuje 1 dowolną manę.")
        return count
    if state is not None and state.shared_mana is not None:
        key = getattr(source, 'id', '')
        boosts = dict(state.shared_mana.pending_boosts)
        if key in {'optical_scope', 'anchoring_arrow'}:
            return 1 + boosts.get('shot', 0)
        return {'double_shot': 2, 'reaper': 3, 'unstoppable': 2, 'blade_dance': 2}.get(key, 1)
    return 2 if getattr(source, "id", "") in {"double_shot", "optical_scope"} else 1


def mana_payload(state: CombatState, effects: Sequence[ActiveEffect], source: object | None,
                 *, targeting: bool = False) -> dict[str, object] | None:
    heroes = tuple(a for a in state.actors if uses_physical_mana(a))
    if not heroes:
        return None
    actor = current_actor(state)
    from .physical_mana_summon import available_weapon
    hero_id = str(actor.id)
    count = series_count(actor, effects)
    movement = movement_mana_notice(state, effects)
    return {
        "movement": movement.as_payload() if movement is not None else None,
        "weapon_available": available_weapon(state) is not None and state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE,
        "weapon_control": any(e.kind == "mana_weapon_control" for e in effects),
        "loan_available": loan_reactor(state) is not None,
        "version": "0.2", "actor_id": hero_id, "actor_name": actor.name,
        "active_hero": uses_physical_mana(actor),
        "supply": turn_supply(hero_id, green_surge=any(e.kind == "mana_wave_3" for e in effects)),
        "setup": {"deck": 10 * len(heroes) + 10, "market": len(heroes) + 4, "start": 3},
        "abilities": [a.as_payload() for a in hero_abilities(hero_id)],
        "hero_notes": HERO_NOTES.get(hero_id, ""),
        "flaw": FLAWS.get(hero_id, ("", "", ""))[2],
        "mana_passive": MANA_PASSIVES.get(hero_id, ("", "", ""))[2],
        "needs_attack_count": bool(can_declare_attack_series(actor) and targeting and source and is_basic_weapon(actor, source)
                                   and count is None and not state.turn_action.attack_action_active),
        "series": {"declared": count, "used": state.turn_action.attacks_used,
                   "remaining": max(0, (count or state.turn_action.attacks_maximum)-state.turn_action.attacks_used)},
        "selected_cost": (mana_ability(hero_id, getattr(source, "id", "")).cost_label
                          if source and mana_ability(hero_id, getattr(source, "id", ""))
                          else "1 dowolna za każdy atak"),
        "threat": max((e.value for e in effects if e.kind == "mana_threat"), default=0),
        "waves": [e.as_payload() for e in effects if e.kind in {f"mana_wave_{i}" for i in WAVES}],
        "pending_waves": [e.as_payload() for e in effects if e.kind == "mana_wave_pending"],
        "wave_rules": [{"number": i, "name": name, "description": description} for i, (name, description) in WAVES.items()],
        "support_targets": [{"id": str(a.id), "name": a.name} for a in state.actors if a.id != actor.id and a.faction == actor.faction and not a.is_defeated() and not a.is_unconscious() and grid_distance_feet(actor.position, a.position) <= 30],
    }


WAVES = {
    1: ("Żar", "Raz we własnej turze zastąp czerwoną manę dowolną kartą. Wrogowie: dodatkowe +1 obrażeń ataków."),
    2: ("Ciężkie powietrze", "Szybkość −10 ft, minimum 5. Ruch opłacony niebieską maną omija ten efekt w tej turze."),
    3: ("Zielony przypływ", "Stara rezerwa i pojemność +1. Dobór nadal 3. Po wygaśnięciu odrzuć nadmiar."),
    4: ("Blada osłona", "Wszyscy: +1 KP. Pierwsze leczenie każdego bohatera w rundzie: +2 PW."),
    5: ("Czarne zakłócenie", "Przeciążenie odrzuca 3 karty talii. Pierwsza własna zdolność: jedną czarną manę można wydać jako dowolny kolor."),
    6: ("Przetasowanie prądów", "Każdy bohater w inicjatywie może wymienić jedną kartę z rynkiem, bez doboru."),
}


def report_wave(state: CombatState, effects: tuple[ActiveEffect, ...], event: int) -> tuple[ActiveEffect, ...]:
    if state.status != CombatStatus.ACTIVE or not any(uses_physical_mana(a) for a in state.actors):
        raise ValueError("Fale zgłasza się podczas walki z fizyczną maną.")
    if isinstance(event, bool) or not isinstance(event, int) or event not in WAVES:
        raise ValueError("Podaj wynik wydarzenia od 1 do 6.")
    serial = 1 + max((e.value for e in effects if e.kind == "mana_wave_serial"), default=0)
    owner = str(next(a for a in state.actors if uses_physical_mana(a)).id)
    updated = apply_active_effect(effects, effect(owner, "mana_wave_serial", "Zgłoszone fale", serial,
                                                  EffectDuration.UNTIL_ENCOUNTER_END)).active_effects
    return (*updated, replace(effect(owner, "mana_wave_pending", f"Fala {serial}: {WAVES[event][0]}", event,
                                    EffectDuration.UNTIL_ENCOUNTER_END),
                              id=f"mana_wave_pending:{serial}", stacking_key=f"mana_wave_pending:{serial}"))


def resolve_waves(state: CombatState, effects: tuple[ActiveEffect, ...]) -> tuple[ActiveEffect, ...]:
    pending = tuple(e for e in effects if e.kind == "mana_wave_pending")
    if not pending:
        return effects
    result = tuple(e for e in effects if e.kind != "mana_wave_pending")
    threat = min(3, max((e.value for e in result if e.kind == "mana_threat"), default=0) + len(pending))
    owner = pending[0].actor_id
    result = apply_active_effect(result, effect(owner, "mana_threat", "Zagrożenie", threat,
                                               EffectDuration.UNTIL_ENCOUNTER_END)).active_effects
    swaps = 0
    for pending_wave in pending:
        number = pending_wave.value
        if number == 6:
            swaps += 1
        label = f"{WAVES[number][0]} · {swaps} kolejki wymian" if number == 6 else WAVES[number][0]
        result = apply_active_effect(result, effect(owner, f"mana_wave_{number}", label, swaps if number == 6 else number,
                                                   EffectDuration.UNTIL_ROUND_END)).active_effects
    return result


def resolve_mana_support(state: CombatState, effects: tuple[ActiveEffect, ...], action_id: str,
                         target_id: str = "") -> tuple[CombatState, tuple[ActiveEffect, ...], str]:
    actor = current_actor(state)
    ability = mana_ability(str(actor.id), action_id)
    if state.shared_mana and state.shared_mana.runes:
        from dnd_board_game.scenarios.rune_catalog import rune_card
        if rune_card(str(actor.id), action_id) is None:
            raise ValueError("Ta zdolność nie ma dostępnej karty runicznej.")
    if not uses_physical_mana(actor) or ability is None or not action_id.startswith("mana_") or ability.timing == "R":
        raise ValueError("Ta zdolność nie jest dostępną akcją zarządzania maną.")
    if condition_blocks_actions(state.condition_states, str(actor.id)) or actor.is_defeated():
        raise ValueError("Stan postaci blokuje działanie.")
    target = None
    if action_id in {"mana_inspiration", "mana_transfer"}:
        target = next((a for a in state.actors if str(a.id) == target_id), None)
        if (target is None or target.id == actor.id or target.faction != actor.faction or not uses_physical_mana(target)
                or target.is_defeated() or target.is_unconscious()
                or grid_distance_feet(actor.position, target.position) > 30):
            raise ValueError("Wybierz innego przytomnego bohatera w 30 ft.")
    spent = use_action_economy_cost(state, ActionEconomyCost.ACTION if ability.timing == "A" else ActionEconomyCost.BONUS_ACTION)
    if not spent.accepted:
        raise ValueError(spent.message)
    if action_id == "mana_inspiration" and target is not None:
        effects = apply_active_effect(effects, replace(
            effect(str(target.id), "bardic_inspiration" if state.shared_mana else "mana_inspiration",
                   "Inspiracja: +1k4 do jednego ataku albo obrony" if state.shared_mana else "Inspiracja barw: jedna karta jako dowolny kolor", 4 if state.shared_mana else 1,
                   EffectDuration.UNTIL_TURN_START), source_actor_id=str(actor.id), expiration_actor_id=str(actor.id), die_sides=4 if state.shared_mana else None,
                   object_id="class_feature:mana_inspiration"
        )).active_effects
    if state.shared_mana and state.shared_mana.runes:
        from dnd_board_game.rules.rune_baskets import RuneBaskets, start_recharge
        if isinstance(state.shared_mana.runes, RuneBaskets):
            from dnd_board_game.rules.shared_mana import finish_mana_action, sync_runes
            mana = spent.state.shared_mana
            if action_id in {"mana_tuning", "mana_recovery"}:
                count = 1 if action_id == "mana_tuning" else 3 if dict(mana.pending_boosts).get("recover_more") else 2
                finished = finish_mana_action(mana, revision=mana.revision)
                pool = start_recharge(finished.runes, str(actor.id), count)
                return replace(spent.state, shared_mana=sync_runes(finished, pool)), effects, "Wybierz kategorię i rzuć k4 za każde ładowane miejsce."
            return spent.state, effects, ability.description
        from dnd_board_game.rules.runes import exchange_rune, recover_rune
        from dnd_board_game.scenarios.rune_catalog import rune_card
        pool = state.shared_mana.runes
        if action_id == "mana_tuning":
            if not state.shared_mana.rune_exchange:
                raise ValueError("Najpierw wybierz runę do wymiany.")
            pool = exchange_rune(pool, str(actor.id), state.shared_mana.rune_exchange)
        elif action_id in {"mana_recovery", "mana_great_tuning"}:
            from collections import Counter
            selected = state.shared_mana.rune_recovery
            amount = 3 if dict(state.shared_mana.pending_boosts).get("recover_more") else 2
            if (not selected or len(selected) > amount
                    or Counter(selected) - Counter(state.shared_mana.rune_recovery_available)):
                raise ValueError("Wybierz runy odrzucone przed opłaceniem Odzysku.")
            for rune in selected:
                pool = recover_rune(pool, str(actor.id), rune)
        updated = replace(spent.state, shared_mana=replace(spent.state.shared_mana, runes=pool, deck=len(pool.deck), discard=len(pool.discard)))
        card = rune_card(str(actor.id), action_id)
        return updated, effects, card.description if card else ability.description
    return spent.state, effects, f"{ability.name} · wydaj: {ability.cost_label}. {ability.description}"


def loan_reactor(state: CombatState) -> Actor | None:
    from .session import reaction_available_for
    target = current_actor(state)
    if not uses_physical_mana(target) or target.is_unconscious() or target.is_defeated():
        return None
    return next((a for a in state.actors if str(a.id) == 'lorian' and a.id != target.id
                 and uses_physical_mana(a) and not a.is_unconscious() and not a.is_defeated()
                 and grid_distance_feet(a.position, target.position) <= 30
                 and reaction_available_for(state, a)), None)


def validate_series_source(state: CombatState, source: object, effects: Sequence[ActiveEffect]) -> None:
    actor = current_actor(state)
    if not uses_physical_mana(actor):
        return
    basic = is_basic_weapon(actor, source)
    if basic and not can_declare_attack_series(actor) and state.turn_action.attacks_used >= 1:
        raise ValueError("Zwykły Atak tej postaci obejmuje tylko jedno uderzenie. Akcja jest już zużyta.")
    declared = series_count(actor, effects)
    if declared is not None and not basic:
        raise ValueError('Zwykła seria nie obejmuje technik specjalnych. Anuluj niewykonaną deklarację albo zakończ serię.')
    lock = next((e.object_id for e in effects if e.actor_id == str(actor.id) and e.kind == 'mana_series_source'), None)
    if state.turn_action.attack_action_active and lock and lock != ('basic' if basic else getattr(source, 'id', '')):
        raise ValueError('Dokończ rozpoczętą serię. Nie można zamienić jej ataków na inną zdolność.')


def bind_series_source(actor: Actor, source: object, effects: tuple[ActiveEffect, ...]) -> tuple[ActiveEffect, ...]:
    if not uses_physical_mana(actor):
        return effects
    return apply_active_effect(effects, replace(effect(str(actor.id), 'mana_series_source', 'Rodzaj rozpoczętej serii'),
                               object_id='basic' if is_basic_weapon(actor, source) else getattr(source, 'id', ''))).active_effects
