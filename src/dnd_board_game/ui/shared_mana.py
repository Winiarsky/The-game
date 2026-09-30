"""Physical card acknowledgements around the existing combat action flows."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import TYPE_CHECKING
from dnd_board_game.world import Coordinate

from dnd_board_game.combat.session import current_actor
from dnd_board_game.combat.shared_mana import quote_ability, expire_deck_effects
from dnd_board_game.rules.shared_mana import (
    ManaPhase, validate_card_operation, pay_mana, finish_mana_action,
    request_mana_end_turn, confirm_mana_refill, confirm_mana_discard,
    request_mana_refresh, confirm_mana_refresh,
)
from dnd_board_game.rules.shared_mana_catalog import shared_ability, SharedAbility


def declared_ability(hero_id: str, ability_id: str, *, runes: object = False) -> SharedAbility | None:
    if runes and not ability_id.startswith("basic_attack:"):
        from dnd_board_game.scenarios.rune_catalog import rune_card
        card = rune_card(hero_id, ability_id, pool=runes)
        return card.ability() if card else None
    from dnd_board_game.scenarios.character_text import present_ability
    if hero_id == "dagna" and ability_id == "spiritual_weapon_activation":
        return present_ability(SharedAbility(hero_id, ability_id, "", "D", "basic", "B", ""))
    if ability_id.startswith("basic_attack:"):
        return SharedAbility(hero_id, ability_id, "Zwykły atak", "A", "basic", "", "Zwykły atak bronią; uwzględnij skazę bohatera.")
    ability = shared_ability(hero_id, ability_id)
    return present_ability(ability) if ability else None

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


@dataclass(slots=True)
class ManaDeclaration:
    ability_id: str
    actor_id: str
    resume_method: str
    resume_arguments: dict[str, object] = field(default_factory=dict)
    boosts: dict[str, int] = field(default_factory=dict)
    stage: str = "payment"
    selected_boost: str = ""
    excluded_positions: tuple[Coordinate, ...] = ()
    extra_target_ids: tuple[str, ...] = ()
    substitution: bool = False
    selected_target_ids: tuple[str, ...] = ()
    rune_choices: dict[str, tuple[str, ...]] = field(default_factory=dict)
    rune_choice_step: str = ""
    rune_choices_complete: bool = False
    rune_flaw_only: bool = False
    basket_step: str = ""
    basket_helper: str = ""


def gate_payment(session: ExplorationUiSession, ability_id: str, resume: str,
                 arguments: dict[str, object] | None = None, *, actor_id: str = "") -> bool:
    state = session.combat_state
    if state is None or state.shared_mana is None:
        return False
    from .training_walkthrough import require_lesson_action
    require_lesson_action(session, ability_id)
    if ability_id == "counterattack_command" and state.shared_mana.command_step:
        return False
    actor = next((a for a in state.actors if str(a.id) == actor_id), current_actor(state))
    if state.shared_mana.runes is not None and ability_id == "mana_great_tuning":
        raise ValueError("Wielkie strojenie zostało zastąpione wariantem Odzysku energii.")
    ability = declared_ability(str(actor.id), ability_id, runes=state.shared_mana.runes)
    if ability is None:
        return False
    mana = state.shared_mana
    if mana.runes is None and ability_id == "hide" and any(e.actor_id == str(actor.id) and e.kind == "smoke_screen_hide_pending" for e in session.active_combat_effects):
        return False
    if ability_id == "hunters_mark":
        from dnd_board_game.application.player_combat_resource_flow import can_transfer_hunters_mark
        from .exploration_app import _combat_action_by_id
        action = _combat_action_by_id(session._active_encounter(), actor, ability_id)
        if action is not None and can_transfer_hunters_mark(state, session.active_combat_effects, actor, action):
            return False
    if mana.phase == ManaPhase.RESOLVING:
        if mana.pending_ability == ability_id and mana.pending_actor == str(actor.id):
            if mana.runes is not None and str(actor.id) == "erynd" and not mana.rune_flaw_paid:
                from dnd_board_game.combat.rune_flaws import rune_flaw_cost
                from .rune_payment import declaration_targets
                candidate = ManaDeclaration(ability_id, str(actor.id), resume, arguments or {},
                    boosts=dict(mana.pending_boosts), rune_flaw_only=True)
                if rune_flaw_cost(state, actor, ability_id, declaration_targets(session, candidate)).count:
                    if session.shared_mana_declaration is None:
                        session.shared_mana_declaration = candidate
                    return True
            return False
        raise ValueError("Najpierw dokończ opłaconą zdolność.")
    if mana.phase != ManaPhase.READY:
        raise ValueError("Najpierw potwierdź operację kart.")
    if ability_id.startswith("basic_attack:"):
        candidate = ManaDeclaration(ability_id, str(actor.id), resume, arguments or {})
        if not _quote(session, candidate).cards:
            return False
    if session.shared_mana_declaration is None:
        from dnd_board_game.combat.session import use_action_economy_cost
        from dnd_board_game.combat.action_economy import ActionEconomyCost
        if mana.runes is not None:
            from dnd_board_game.combat.runes import quote_runes
            quote_runes(state, actor, ability_id, {})
        elif ability.timing in {"A", "D"} and not state.turn_action.attack_action_active:
            check = use_action_economy_cost(state, ActionEconomyCost.ACTION if ability.timing == "A" else ActionEconomyCost.BONUS_ACTION)
            if not check.accepted:
                raise ValueError(check.message)
        session.shared_mana_declaration = ManaDeclaration(ability_id, str(actor.id), resume, arguments or {},
                                                        selected_boost=ability.boosts[0].id if ability.boosts else "")
    return True


def _quote(session: ExplorationUiSession, declaration: ManaDeclaration, *, substitution: bool | None = None):
    state = session.combat_state
    actor = next(a for a in state.actors if str(a.id) == declaration.actor_id)
    ability = declared_ability(declaration.actor_id, declaration.ability_id, runes=session.combat_state.shared_mana.runes)
    if state.shared_mana.runes is not None:
        if substitution:
            raise ValueError("Wybieraj wzmocnienia z karty postaci.")
        from dnd_board_game.combat.runes import quote_runes
        from dnd_board_game.combat.shared_mana import ManaQuote
        from dnd_board_game.combat.rune_flaws import rune_flaw_cost
        from .rune_payment import declaration_targets
        targets = declaration_targets(session, declaration)
        if declaration.ability_id.startswith("basic_attack:"):
            return ManaQuote((), (), False)
        from dnd_board_game.rules.rune_baskets import RuneBaskets
        if isinstance(state.shared_mana.runes, RuneBaskets):
            if declaration.rune_flaw_only:
                from collections import Counter
                flaw = rune_flaw_cost(state, actor, declaration.ability_id, targets)
                hand = state.shared_mana.runes.hand(declaration.actor_id)
                selected = declaration.rune_choices.get("payment", hand[:flaw.count])
                if len(selected) != flaw.count or Counter(selected) - Counter(hand):
                    raise ValueError("Wybierz własne runy na dopłatę skazy.")
                return ManaQuote(tuple(selected), flaw.reminders, False)
            from dnd_board_game.combat.rune_baskets import quote as basket_quote
            selected = declaration.rune_choices.get("payment")
            if selected is not None and not declaration.basket_helper:
                from dnd_board_game.scenarios.rune_catalog import rune_card
                card = rune_card(declaration.actor_id, declaration.ability_id, pool=state.shared_mana.runes)
                selected = (*selected, *card.payment(declaration.boosts)[1:])
            cards = basket_quote(state, actor, declaration.ability_id, declaration.boosts, selected,
                                 targets=targets, helper_id=declaration.basket_helper)
            return ManaQuote(cards, ("Żetony i reakcja pomocnika zostaną zużyte dopiero po końcowym potwierdzeniu.",), str(actor.id)=="nimra")
        flaw = rune_flaw_cost(state, actor, declaration.ability_id, targets)
        if declaration.rune_flaw_only:
            from dnd_board_game.rules.runes import plan_card_payment
            cards = plan_card_payment(state.shared_mana.runes.hand(declaration.actor_id), ("*",) * flaw.count,
                declaration.rune_choices.get("payment") if declaration.rune_choices_complete else None)
        else:
            cards = quote_runes(state, actor, declaration.ability_id, declaration.boosts,
                declaration.rune_choices.get("payment") if declaration.rune_choices_complete else None, targets=targets)
        reminders = ("Runy zostaną wydane dopiero po zatwierdzeniu.",) + flaw.reminders
        if declaration.ability_id == "mana_tuning":
            reminders += ("W osobnym kroku wybierzesz runę do wymiany; dopiero końcowe ✓ pobierze koszt.",)
        if declaration.ability_id == "counterattack_command":
            target_id = str(declaration.resume_arguments.get("target_id", ""))
            target = next((a for a in state.actors if str(a.id) == target_id), None)
            if target is not None:
                reminders += (f"Sojusznik {target.name} wybierze własną runę na Kontratak; wykorzysta także reakcję.",)
        return ManaQuote(cards, reminders, str(actor.id) == "nimra")
    target_ids = set()
    target = declaration.resume_arguments.get("target_id")
    if target:
        target_ids.add(target)
    for actor_id, amount in declaration.resume_arguments.get("allocations") or ():
        if amount > 0:
            target_ids.add(str(actor_id))
    if session.combat_targeting_class_feature_action_id == declaration.ability_id and session.combat_selected_class_feature_target_id:
        target_ids.add(session.combat_selected_class_feature_target_id)
    position = declaration.resume_arguments.get("position")
    if position is not None:
        target_ids.update(str(a.id) for a in state.actors if a.position == position)
    for pending in (session.pending_player_attack, session.pending_player_healing, session.pending_area_spell):
        if pending:
            target_ids.update(getattr(pending, "target_ids", ()))
            target_ids.add(getattr(pending, "target_id", ""))
    if state.shared_mana.pooled is not None:
        if substitution:
            raise ValueError("Kolor atutowy jest już uwzględniony w ładunku; nie zmienia fizycznego koloru karty.")
        from dnd_board_game.combat.pooled_mana import quote_pool
        from dnd_board_game.scenarios.pooled_mana_catalog import pool_ability, hero_profile
        return quote_pool(state, actor, ability, pool_ability(ability.id, str(actor.id)),
                          state.shared_mana.pooled.point_values(str(actor.id)) if str(actor.id) in state.shared_mana.pooled.heroes else {}, declaration.boosts,
                          targets=tuple(a for a in state.actors if str(a.id) in target_ids),
                          effects=session.active_combat_effects)
    return quote_ability(state, actor, ability, declaration.boosts,
                         targets=tuple(a for a in state.actors if str(a.id) in target_ids),
                         effects=session.active_combat_effects, substitution=declaration.substitution if substitution is None else substitution)


def payload(session: ExplorationUiSession) -> dict[str, object] | None:
    state = session.combat_state
    if state is None or state.shared_mana is None:
        return None
    mana = state.shared_mana
    result = mana.as_payload()
    if mana.pooled is not None:
        from .pooled_mana import view
        result["pool_view"] = view(session)
    if mana.runes is not None:
        from .runes import view
        result["rune_view"] = view(session)
    result["refresh_available"] = mana.runes is None and mana.pooled is None and mana.phase == ManaPhase.READY
    result["refill_count"] = 0 if mana.pooled is not None or mana.runes is not None else min(5-mana.market, mana.deck)
    if mana.command_step:
        participant = current_actor(state)
        from .shared_command import stage, instruction
        from .board_panel_symbols import ability_panel_slot, panel_icon
        command_stage = stage(session)
        result['command'] = dict(step=mana.command_step, total=2, actor_name=participant.name,
            stage=command_stage, instruction=instruction(session),
            can_confirm=command_stage in {'movement', 'confirm_attack', 'no_target'},
            can_back=command_stage == 'confirm_attack' or (command_stage == 'movement' and session.selected_combat_movement_path is not None),
            icon=panel_icon(ability_panel_slot('garran', 'counterattack_command')),
            movement_icon=panel_icon(0), attack_icon=panel_icon(1),
            next_instruction=('Po ataku aplikacja przekaże sterowanie sojusznikowi — także przy pudle.'
                if mana.command_step == 1 else 'Po tym ataku Rozkaz się zakończy — także przy pudle. Sojusznik zużywa reakcję.'))
        if command_stage == 'no_target':
            result['command']['next_instruction'] = ('✓ przekaże sterowanie sojusznikowi.'
                if mana.command_step == 1 else '✓ zakończy Rozkaz.')
    declaration = session.shared_mana_declaration
    if declaration and declaration.stage == "basket":
        result["declaration"] = dict(stage="basket", ability_id=declaration.ability_id, name="Koszyki run")
        return result
    if declaration:
        ability = declared_ability(declaration.actor_id, declaration.ability_id, runes=session.combat_state.shared_mana.runes)
        result["declaration"] = {
            "ability_id": ability.id, "actor_id": declaration.actor_id, "name": ability.name, "description": ability.description,
            "duration": ability.duration, "stage": declaration.stage, "basket_step": declaration.basket_step,
            "boosts": [dict(asdict(b), count=declaration.boosts.get(b.id, 0)) for b in ability.boosts],
            "selected_boost": declaration.selected_boost,
            "boost_options": boost_options(session, declaration) if declaration.stage == "payment" else [],
        }
        if declaration.stage == "rune_choices":
            result["declaration"].update(cost=[], reminders=[], error="")
            return result
        if mana.runes is not None and ability.id == "cunning_action":
            from .board_panel_symbols import panel_icon
            result["declaration"]["mode_options"] = [
                dict(slot=5+i, mode=mode, label=label, icon=panel_icon(5+i), selected=declaration.resume_arguments.get("mode") == mode)
                for i,(mode,label) in enumerate((("dash", "Sprint: dodatkowy ruch"), ("disengage", "Odwrót: ruch bez ataków okazyjnych")))]
        if mana.runes is not None and ability.id == "garran_command_halt" and declaration.stage == "payment" and declaration.boosts.get("target"):
            from dnd_board_game.combat.spells import grid_distance_feet
            first_id = session.combat_selected_class_feature_target_id or declaration.resume_arguments.get("target_id")
            first = next((a for a in state.actors if str(a.id) == first_id), None)
            owner = next(a for a in state.actors if str(a.id) == declaration.actor_id)
            result["declaration"]["targets"] = [dict(id=str(a.id), name=a.name) for a in state.actors
                if first and a.id != first.id and a.faction not in {owner.faction} and not a.is_defeated() and grid_distance_feet(first.position,a.position) <= 10]
        if mana.runes is not None and ability.id == "garran_guard_companion" and declaration.stage == "effect_roll":
            sides = 6 if declaration.boosts.get("reduce_d6") else 4
            result["declaration"].update(roll_sides=sides, roll_label=f"Redukcja obrażeń: k{sides}", roll=declaration.resume_arguments.get("natural_roll") or 1)
        if mana.runes is not None and ability.id == "garran_rally" and declaration.stage == "payment" and not declaration.boosts.get("all"):
            from dnd_board_game.combat.spells import grid_distance_feet
            owner = next(a for a in state.actors if str(a.id) == declaration.actor_id)
            result["declaration"]["targets"] = [dict(id=str(a.id), name=a.name) for a in state.actors
                if a.faction == owner.faction and not a.is_defeated() and grid_distance_feet(owner.position,a.position) <= 15]
        if mana.pooled is not None:
            from dnd_board_game.scenarios.pooled_mana_catalog import ability_description, requirement_text, load_catalog
            if ability.id in load_catalog()["abilities"]:
                if ability.id != "spiritual_weapon_activation":
                    from dnd_board_game.physical_cards.mana_ability_text import ability_sections
                    result["declaration"]["sections"] = ability_sections(declaration.actor_id, ability.id)
                    result["declaration"]["description"] = requirement_text(ability.id, declaration.actor_id) + " " + ability_description(declaration.actor_id, ability.id)
                else:
                    result["declaration"]["description"] = ability.description
        if ability.id == 'garran_guard_companion' and session.pending_enemy_turn_intent:
            intent = session.pending_enemy_turn_intent
            result['declaration']['context'] = (
                f'{intent.enemy.name} atakuje {intent.target.name}. Potwierdź osłonę przez ✓: '
                'Garran przejmie ten pojedynczy atak. Rzut wykonuje aplikacja przeciw KP Garrana; '
                'przy trafieniu PW traci Garran, a pomocnik nie otrzymuje obrażeń. ↩ rezygnuje z osłony.')
            result['declaration']['description'] = result['declaration']['context']
        if ability.id == "nimra_mind_break" and session.pending_player_attack:
            from dnd_board_game.combat.spells import grid_distance_feet
            first = next(a for a in state.actors if str(a.id) == session.pending_player_attack.target_id)
            owner = next(a for a in state.actors if str(a.id) == declaration.actor_id)
            result["declaration"].update(extra_targets=[{"id": str(a.id), "name": a.name} for a in state.actors
                if a.id != first.id and a.faction != owner.faction and not a.is_defeated() and grid_distance_feet(first.position, a.position) <= 10],
                extra_target_ids=list(declaration.extra_target_ids), extra_target_maximum=declaration.boosts.get("target", 0))
        if declaration.boosts.get("exclude", 0):
            pending_area = session.pending_area_spell or session.pending_concentration_action
            result["declaration"]["exclusion_fields"] = [list(p.as_tuple()) for p in getattr(pending_area, "area_positions", ())]
            result["declaration"]["excluded_positions"] = [list(p.as_tuple()) for p in declaration.excluded_positions]
        if ability.id == "shoulder_check" and declaration.stage == "effect_roll":
            count = declaration.boosts.get("damage", 0)
            damage = declaration.resume_arguments.get("shoulder_stage") == "damage"
            result["declaration"].update(roll_sides=6*count if damage else 20, roll_label=f"Suma {count}k6 obrażeń" if damage else "Naturalny k20 Atletyki", roll=declaration.resume_arguments.get("natural_roll") or (count if damage else 1))
        if ability.id == "counterattack_command":
            from dnd_board_game.combat.session import reaction_available_for
            from dnd_board_game.combat.spells import grid_distance_feet
            owner = current_actor(state)
            result["declaration"].update(targets=[{"id": str(a.id), "name": a.name} for a in state.actors
                if a.id != owner.id and a.faction == owner.faction and not a.is_unconscious() and not a.is_defeated()
                and grid_distance_feet(owner.position, a.position) <= 15 and reaction_available_for(state, a)],
                target_id=declaration.resume_arguments.get("target_id", ""))
        if ability.id in {"feint", "caring_gesture"}:
            from dnd_board_game.combat.shared_mana import adjacent
            owner = next(a for a in state.actors if str(a.id) == declaration.actor_id)
            result["declaration"].update(
                targets=[{"id": str(a.id), "name": a.name} for a in state.actors if adjacent(owner, a) and not a.is_dead() and (a.faction == owner.faction) == (ability.id == "caring_gesture")],
                target_id=declaration.resume_arguments.get("target_id", ""),
                roll_sides=4 if ability.id == "caring_gesture" else 0,
                roll=declaration.resume_arguments.get("natural_roll") or 1)
        if ability.id == "mana_inspiration":
            from dnd_board_game.combat.spells import grid_distance_feet
            from dnd_board_game.actors.resources import uses_shared_mana
            owner = next(a for a in state.actors if str(a.id) == declaration.actor_id)
            result["declaration"].update(targets=[{"id": str(a.id), "name": a.name}
                for a in state.actors if a.id != owner.id and a.faction == owner.faction
                and uses_shared_mana(a) and not a.is_unconscious() and not a.is_defeated()
                and grid_distance_feet(owner.position, a.position) <= 30],
                target_id=declaration.resume_arguments.get("target_id", ""))
        if declaration.stage == "payment":
            try:
                alternative = _quote(session, declaration, substitution=True)
                result["declaration"].update(substitution_available=True, substitution=declaration.substitution,
                    substitution_label=alternative.reminders[-1])
            except ValueError:
                result["declaration"]["substitution_available"] = False
        if declaration.stage == "bonus":
            from dnd_board_game.combat.spells import grid_distance_feet
            owner = next(a for a in state.actors if str(a.id) == declaration.actor_id)
            ward = declaration.ability_id == "garran_shield_wall"
            used = declaration.resume_arguments.get("used_targets", ())
            result["declaration"].update(targets=[{"id": str(a.id), "name": a.name} for a in state.actors
                if a.faction == owner.faction and not a.is_dead() and (not ward or (a.id != owner.id and str(a.id) not in used))
                and grid_distance_feet(a.position, owner.position) <= (5 if ward else 15)],
                target_id=declaration.resume_arguments.get("target_id", ""),
                roll_sides=0 if ward else 6, roll=declaration.resume_arguments.get("natural_roll"),
                remaining=declaration.resume_arguments["remaining"])
        if "targets" in result["declaration"]:
            from .shared_mana_board import target_selection
            result["declaration"]["target_selection"] = target_selection(
                session, declaration, result["declaration"]["targets"])
        if declaration.stage != "payment":
            result["declaration"].update(cost=list(ability.cost), reminders=[], error="")
            return result
        try:
            _preflight(session, declaration)
            quote = _quote(session, declaration)
            validate_card_operation(mana, ability.id, len(quote.cards))
            if mana.runes is None and mana.pooled is None and len(quote.cards) > mana.market:
                raise ValueError("Na rynku brakuje kart na pełny koszt.")
            from .training_walkthrough import payment_error
            shown_cost = quote.cards
            from dnd_board_game.rules.rune_baskets import RuneBaskets, NAMES
            if isinstance(mana.runes, RuneBaskets) and not declaration.rune_choices:
                from dnd_board_game.scenarios.rune_catalog import rune_card
                card = rune_card(declaration.actor_id, declaration.ability_id, pool=mana.runes)
                shown_cost = (NAMES[card.category],) if not declaration.rune_flaw_only else quote.cards
            elif mana.runes is not None and not isinstance(mana.runes, RuneBaskets) and not declaration.rune_choices_complete:
                from .rune_payment import requirements
                from dnd_board_game.rules.runes import card_payment_requirements
                shown_cost = card_payment_requirements(mana.runes.hand(declaration.actor_id), requirements(session, declaration))
            result["declaration"].update(cost=list(shown_cost), reminders=list(quote.reminders),
                error=payment_error(session, declaration.ability_id, declaration.boosts))
        except ValueError as exc:
            result["declaration"].update(cost=[], reminders=[], error=str(exc))
    return result


def boost_options(session: ExplorationUiSession, declaration: ManaDeclaration) -> list[dict[str, object]]:
    """Stable printed runes select explicit amounts, independently per color."""
    from .board_panel_symbols import SYMBOLS, panel_icon

    if session.combat_state.shared_mana.runes is not None:
        from .runes import boost_options as rune_boost_options
        return rune_boost_options(session, declaration)
    ability = declared_ability(declaration.actor_id, declaration.ability_id, runes=session.combat_state.shared_mana.runes)
    choices = []
    slot = 6
    for boost in ability.boosts:
        for amount in range(1, boost.maximum + 1):
            selected = declaration.boosts.get(boost.id, 0) == amount
            count = 0 if selected else amount
            candidate = replace(declaration, boosts={**declaration.boosts, boost.id: count})
            reason = ""
            if not selected:
                try:
                    quote = _quote(session, candidate)
                    validate_card_operation(session.combat_state.shared_mana, ability.id, len(quote.cards))
                    if session.combat_state.shared_mana.pooled is None and len(quote.cards) > session.combat_state.shared_mana.market:
                        raise ValueError("Na rynku brakuje kart na ten wariant.")
                except ValueError as exc:
                    reason = str(exc)
            choices.append(dict(slot=slot, rune_name=SYMBOLS[slot][0], icon=panel_icon(slot),
                                boost_id=boost.id, amount=amount, count=count, selected=selected,
                                color=boost.color, cost=["*"] * (2 * amount) if session.combat_state.shared_mana.pooled is not None else [boost.color] * amount,
                                effect=boost.label.split(": ", 1)[-1],
                                enabled=not reason, unavailable_reason=reason))
            slot += 1
    return choices


def settle_action(session: ExplorationUiSession) -> None:
    from .training_tutorial import record_ability
    state = session.combat_state
    if state is None or state.shared_mana is None:
        return
    if state.shared_mana.runes is None and state.shared_mana.pooled is None and state.status.value != "finished" and state.shared_mana.phase == ManaPhase.READY and state.shared_mana.deck == state.shared_mana.market == 0 and not session._combat_has_pending_resolution():
        session.combat_state = replace(state, shared_mana=request_mana_refresh(state.shared_mana, revision=state.shared_mana.revision))
        return
    if state.shared_mana.pooled is not None and state.shared_mana.phase == ManaPhase.READY:
        pool = state.shared_mana.pooled
        defeated = {str(a.id) for a in state.actors if a.is_defeated()}
        owner = next((owner for owner, cards in pool.prisons if owner in defeated and cards), None)
        if owner:
            from dnd_board_game.rules.shared_mana import sync_pool
            session.combat_state = replace(state, shared_mana=sync_pool(state.shared_mana,
                replace(pool, phase="release", captor=owner)))
            return
    if state.shared_mana.phase != ManaPhase.RESOLVING:
        return
    mana = state.shared_mana
    if mana.pending_ability == "reckless_attack" and any(e.kind == "mana_reckless" and e.actor_id == mana.pending_actor for e in session.active_combat_effects):
        session.combat_state = replace(state, shared_mana=finish_mana_action(mana, revision=mana.revision))
        record_ability(session, mana.pending_ability, mana.pending_actor)
        return
    if any(e.kind == "mana_weapon_control" for e in session.active_combat_effects):
        return
    if session.shared_mana_declaration is not None or session._combat_has_pending_resolution():
        return
    if mana.command_step:
        from .shared_command import prepare
        prepare(session)
        return
    if state.turn_action.attack_action_active and 0 < state.turn_action.attacks_used < state.turn_action.attacks_maximum:
        return
    if any((session.combat_targeting_attack_source_id, session.combat_targeting_healing_source_id,
            session.combat_targeting_class_feature_action_id, session.pending_nimra_metamagic_id)):
        return
    mana = state.shared_mana
    if mana.runes is None and mana.pending_ability in {"mana_tuning", "mana_recovery", "mana_great_tuning"}:
        session.shared_mana_declaration = ManaDeclaration(mana.pending_ability, mana.pending_actor, "", boosts=dict(mana.pending_boosts), stage="cards")
        return
    session.combat_state = replace(state, shared_mana=finish_mana_action(mana, revision=mana.revision))
    if mana.runes is not None:
        from .runes import finish_effects
        finish_effects(session, mana)
    session.active_combat_effects = tuple(e for e in session.active_combat_effects if e.object_id != "shared_technique_movement")
    session._record("shared_mana_action_finished", {"ability_id": mana.pending_ability, "market": session.combat_state.shared_mana.market})
    record_ability(session, mana.pending_ability, mana.pending_actor)


def gate_end_turn(session: ExplorationUiSession) -> bool:
    state = session.combat_state
    if state is None or state.shared_mana is None:
        return False
    from dnd_board_game.actors.resources import uses_shared_mana
    if not uses_shared_mana(current_actor(state)):
        return False
    mana = state.shared_mana
    if mana.phase == ManaPhase.RESOLVING and session.combat_targeting_attack_source_id == mana.pending_ability and not state.turn_action.attacks_used:
        from dnd_board_game.combat.session import use_turn_action
        spent = use_turn_action(state)
        if not spent.accepted:
            raise ValueError(spent.message)
        mana = finish_mana_action(mana, revision=mana.revision)
        state = replace(spent.state, shared_mana=mana)
        session.combat_state = state
        session.combat_targeting_attack_source_id = None
        session.active_combat_effects = tuple(e for e in session.active_combat_effects if e.object_id != "shared_technique_movement")
        session._add_message("Zakończenie techniki", "Niewykonane ataki przepadają; wydana mana i akcja pozostają zużyte.")
    if mana.phase == ManaPhase.RESOLVING and state.turn_action.attack_action_active and state.turn_action.attacks_used > 0:
        mana = finish_mana_action(mana, revision=mana.revision)
        state = replace(state, shared_mana=mana, turn_action=replace(state.turn_action, attacks_maximum=state.turn_action.attacks_used))
        session.combat_state = state
        session.active_combat_effects = tuple(e for e in session.active_combat_effects if e.object_id != "shared_technique_movement")
    if mana.end_turn_pending and mana.phase == ManaPhase.READY:
        return False
    if mana.phase == ManaPhase.READY:
        actor = current_actor(state)
        if any(e.kind == "rage" and e.actor_id == str(actor.id) for e in session.active_combat_effects) and (actor.is_unconscious() or not any(e.kind == "shared_offensive_used" and e.actor_id == str(actor.id) for e in session.active_combat_effects)):
            session._end_rage(str(actor.id), reason="tura bez działania ofensywnego albo utrata przytomności")
        from dnd_board_game.combat.shared_mana_end import prepare_shared_turn_end
        state, session.active_combat_effects, expired, triggers = prepare_shared_turn_end(session.combat_state, session.active_combat_effects)
        session._add_trigger_activation_notices(triggers)
        if expired:
            session._add_message("Koniec efektów tury", ", ".join(e.label for e in expired))
        mana = state.shared_mana
        if mana.pooled is not None or mana.runes is not None:
            session.combat_state = replace(state, shared_mana=replace(mana, end_turn_pending=True))
            return False
        session.combat_state = replace(state, shared_mana=request_mana_end_turn(mana, revision=mana.revision))
    return True


def command(session: ExplorationUiSession, data: dict[str, object]) -> dict[str, object]:
    state = session.combat_state
    if state is None or state.shared_mana is None:
        raise ValueError("Ta walka nie używa wspólnej many.")
    mana = state.shared_mana
    if type(data.get("revision")) is not int or data["revision"] != mana.revision:
        raise ValueError("Nieaktualny wybór many. Odśwież ekran.")
    action = data.get("command")
    from .rune_baskets import active as basket_active
    if basket_active(session):
        if str(action).startswith("basket_"):
            from .rune_baskets import command as basket_command
            return basket_command(session, data)
        if action == "pay" and session.shared_mana_declaration and session.shared_mana_declaration.basket_step != "final":
            from .rune_baskets import begin
            return begin(session)
        if action == "cancel" and session.shared_mana_declaration and session.shared_mana_declaration.basket_step == "parameters":
            declaration = session.shared_mana_declaration
            declaration.stage = "basket"
            declaration.basket_step = "resonance"
            declaration.boosts = {}
            declaration.basket_helper = ""
            from .rune_baskets import _updated
            return _updated(session)
        if action in {"boost", "boost_option"}:
            raise ValueError("Najpierw potwierdź cel i wybierz koszt podstawowy; potem wybierz Rezonans.")
    if mana.runes is not None and str(action).startswith("rune_"):
        from .runes import command as rune_command
        return rune_command(session, data)
    if mana.runes is not None and action in {"refresh", "refresh_done", "discard", "refill", "cards_done"}:
        raise ValueError("W tej walce dobór run odbywa się tylko raz, przed pierwszą rundą.")
    if mana.pooled is not None and str(action).startswith("pool_"):
        from .pooled_mana import command as pool_command
        return pool_command(session, data)
    if mana.pooled is not None and action in {"refresh", "refresh_done", "discard", "refill", "cards_done"}:
        raise ValueError("W tym profilu talia wraca na spód; tasowanie tylko na początku walki i przy drain.")
    declaration = session.shared_mana_declaration
    if declaration is not None and declaration.stage == "rune_choices" and action != "cancel":
        raise ValueError("W trakcie wyboru run nie można zmienić celu ani parametrów mocy. Cofnij wybory do podglądu.")
    if action == "mode":
        if declaration is None or declaration.stage != "payment" or declaration.ability_id != "cunning_action" or data.get("mode") not in {"dash", "disengage"}:
            raise ValueError("Wybierz Sprint albo Odwrót.")
        declaration.resume_arguments["mode"] = data["mode"]
        session.combat_state = replace(state, shared_mana=replace(mana, revision=mana.revision+1))
        session._sync_board_leds()
        return session.state_payload()
    if action == "boost_option":
        if declaration is None or declaration.stage != "payment" or type(data.get("slot")) is not int:
            raise ValueError("Brak podbicia do wyboru.")
        option = next((item for item in boost_options(session, declaration) if item["slot"] == data["slot"]), None)
        if option is None or not option["enabled"]:
            raise ValueError(option["unavailable_reason"] if option else "Nieznana runa podbicia.")
        return command(session, dict(command="boost", revision=mana.revision,
                                     boost_id=option["boost_id"], count=option["count"]))
    if action == "substitution":
        if declaration is None or declaration.stage != "payment" or type(data.get("enabled")) is not bool:
            raise ValueError("Brak deklaracji zamiany koloru.")
        if data["enabled"]:
            _quote(session, declaration, substitution=True)
        declaration.substitution = data["enabled"]
        session.combat_state = replace(state, shared_mana=replace(mana, revision=mana.revision+1))
    elif action == "extra_target":
        if declaration is None or declaration.stage != "payment" or declaration.ability_id != "nimra_mind_break":
            raise ValueError("Brak Załamania woli do zmiany.")
        selected = set(declaration.extra_target_ids)
        key = str(data.get("target_id", ""))
        selected.remove(key) if key in selected else selected.add(key)
        if len(selected) > declaration.boosts.get("target", 0):
            raise ValueError("Każdy dodatkowy cel wymaga czarnego podbicia.")
        declaration.extra_target_ids = tuple(sorted(selected))
        session.combat_state = replace(state, shared_mana=replace(mana, revision=mana.revision+1))
    elif action == "exclude":
        if declaration is None or declaration.stage != "payment" or not declaration.boosts.get("exclude", 0):
            raise ValueError("Wybierz podbicie wyłączające pola.")
        from dnd_board_game.world import Coordinate
        raw = data.get("position")
        if not isinstance(raw, list) or len(raw) != 2 or any(type(v) is not int for v in raw):
            raise ValueError("Nieprawidłowe pole.")
        position = Coordinate(*raw)
        pending = session.pending_area_spell or session.pending_concentration_action
        if position not in pending.area_positions:
            raise ValueError("Wybierz pole w obszarze zdolności.")
        selected = set(declaration.excluded_positions)
        selected.remove(position) if position in selected else selected.add(position)
        if len(selected) > 2:
            raise ValueError("Możesz wyłączyć najwyżej dwa pola.")
        declaration.excluded_positions = tuple(sorted(selected, key=lambda p: (p.col, p.row)))
        _refresh_preview(session, declaration)
        session.combat_state = replace(state, shared_mana=replace(mana, revision=mana.revision+1))
    elif action in {"target", "clear_targets"}:
        view = payload(session).get("declaration", {})
        selection = view.get("target_selection")
        if declaration is None or selection is None:
            raise ValueError("Brak celów do wyboru.")
        selected = list(selection["selected_ids"])
        if action == "clear_targets":
            selected = []
        else:
            key = str(data.get("target_id", ""))
            if key not in {target["id"] for target in selection["targets"]}:
                raise ValueError("Wybierz podświetlony, legalny cel.")
            if key in selected:
                selected.remove(key)
            elif selection["multiple"]:
                if len(selected) >= selection["maximum"]:
                    raise ValueError("Osiągnięto limit celów. Odznacz wybraną figurkę.")
                selected.append(key)
            else:
                selected = [key]
        if selection["multiple"]:
            declaration.selected_target_ids = tuple(selected)
        else:
            declaration.resume_arguments["target_id"] = selected[0] if selected else ""
        session.combat_state = replace(state, shared_mana=replace(mana, revision=mana.revision+1))
    elif action == "parameters":
        if declaration is None or declaration.stage not in {"payment", "effect_roll", "bonus"}:
            raise ValueError("Brak deklaracji do zmiany.")
        if "target_id" in data:
            selection = payload(session)["declaration"].get("target_selection")
            if selection is not None:
                key = str(data["target_id"])
                if key and key not in {target["id"] for target in selection["targets"]}:
                    raise ValueError("Wybierz podświetlony, legalny cel.")
                if selection["multiple"]:
                    declaration.selected_target_ids = (key,) if key else ()
        for key in ("target_id", "natural_roll"):
            if key in data:
                declaration.resume_arguments[key] = data[key]
        session.combat_state = replace(state, shared_mana=replace(mana, revision=mana.revision+1))
    elif action in {"boost", "select_boost", "cancel"}:
        if declaration is None or (declaration.stage != "payment" and not (action == "cancel" and declaration.stage == "rune_choices")):
            raise ValueError("Brak deklaracji do zmiany.")
        if action == "cancel":
            session.shared_mana_declaration = None
            if declaration.resume_method == "resolve_shared_guard":
                session.combat_state = replace(state, shared_mana=replace(mana, revision=mana.revision+1))
                return session.resolve_enemy_turn()
        else:
            if declaration.rune_flaw_only:
                raise ValueError("Wariant opłaconej mocy jest już ustalony; wybierz tylko runę na skazę.")
            declaration.rune_choices_complete = False
            declaration.rune_choices = {}
            ability = declared_ability(declaration.actor_id, declaration.ability_id, runes=session.combat_state.shared_mana.runes)
            key = str(data.get("boost_id", declaration.selected_boost))
            if key not in {b.id for b in ability.boosts}:
                raise ValueError("Nieznane podbicie.")
            if action == "boost":
                value = data.get("count")
                candidate = {key: value} if mana.runes is not None else {**declaration.boosts, key: value}
                if mana.runes is not None:
                    from dnd_board_game.combat.runes import quote_runes
                    actor = next(a for a in state.actors if str(a.id) == declaration.actor_id)
                    quote_runes(state, actor, declaration.ability_id, candidate)
                elif mana.pooled is None:
                    ability.payment(candidate)
                else:
                    from dnd_board_game.rules.pooled_mana_catalog import validate_boosts
                    validate_boosts(mana.pooled.hand(declaration.actor_id), candidate, ability.boosts, ability.boost_limit)
                declaration.boosts = candidate
            declaration.selected_boost = key
            if not declaration.boosts.get("exclude", 0):
                declaration.excluded_positions = ()
            _refresh_preview(session, declaration)
        session.combat_state = replace(state, shared_mana=replace(mana, revision=mana.revision+1))
    elif action == "pay":
        if declaration is None or declaration.stage != "payment":
            raise ValueError("Brak kosztu do potwierdzenia.")
        from .training_walkthrough import payment_error, paid as record_training_payment
        error = payment_error(session, declaration.ability_id, declaration.boosts)
        if error:
            raise ValueError(error)
        _preflight(session, declaration)
        quote = _quote(session, declaration)
        validate_card_operation(mana, declaration.ability_id, len(quote.cards))
        if mana.runes is not None and not basket_active(session):
            from .rune_payment import begin as begin_rune_choices
            if begin_rune_choices(session, declaration):
                return session.state_payload()
        rune_surcharge = 0
        if mana.runes is not None:
            from dnd_board_game.combat.rune_flaws import rune_flaw_cost
            from .rune_payment import declaration_targets
            payer = next(a for a in state.actors if str(a.id) == declaration.actor_id)
            rune_surcharge = rune_flaw_cost(state, payer, declaration.ability_id,
                                             declaration_targets(session, declaration)).count
        if declaration.rune_flaw_only:
            from dnd_board_game.rules.runes import spend_runes
            from dnd_board_game.rules.shared_mana import sync_runes
            if basket_active(session):
                from dnd_board_game.rules.rune_baskets import spend_tokens
                updated_pool = spend_tokens(mana.runes, {declaration.actor_id: quote.cards})
            else:
                updated_pool = spend_runes(mana.runes, declaration.actor_id, quote.cards)
            paid = replace(sync_runes(mana, updated_pool),
                           phase=mana.phase, rune_flaw_paid=True, rune_payment=(*mana.rune_payment, *quote.cards))
            session.combat_state = replace(state, shared_mana=paid)
            session.shared_mana_declaration = None
            session._record("rune_flaw_paid", {"ability_id": declaration.ability_id, "runes": list(quote.cards)})
            return getattr(session, declaration.resume_method)(**declaration.resume_arguments)
        if basket_active(session):
            from dnd_board_game.combat.rune_baskets import commit
            from .rune_payment import declaration_targets
            actor = next(a for a in state.actors if str(a.id) == declaration.actor_id)
            state = commit(state, actor, declaration.ability_id, declaration.boosts, quote.cards,
                           targets=declaration_targets(session, declaration), helper_id=declaration.basket_helper)
            paid = state.shared_mana
        else:
            paid = pay_mana(mana, revision=mana.revision, actor_id=declaration.actor_id,
                            ability_id=declaration.ability_id, count=len(quote.cards),
                            boosts=tuple(declaration.boosts.items()), echo_spell=quote.echo,
                            rune_payment=quote.cards if mana.runes is not None else None, rune_surcharge=rune_surcharge,
                            rune_exchange=next(iter(declaration.rune_choices.get("exchange", ())), ""),
                            rune_recovery=declaration.rune_choices.get("recovery", ()),
                            rune_ally_actor=str(declaration.resume_arguments.get("target_id", "")) if declaration.ability_id == "counterattack_command" else "",
                            rune_ally_payment=next(iter(declaration.rune_choices.get("partner", ())), ""))
            if mana.runes is not None:
                from dnd_board_game.combat.runes import commit_budget
                from dnd_board_game.scenarios.rune_catalog import rune_card
                actor = next(a for a in state.actors if str(a.id) == declaration.actor_id)
                state = commit_budget(state, actor, rune_card(declaration.actor_id, declaration.ability_id), declaration.boosts)
        if mana.runes is not None and declaration.ability_id == "garran_rally":
            chosen = declaration.selected_target_ids or tuple(v for v in (declaration.resume_arguments.get("target_id"),) if v)
            paid = replace(paid, attack_targets=chosen)
        if mana.runes is not None and declaration.ability_id == "garran_command_halt":
            first_id = session.combat_selected_class_feature_target_id or declaration.resume_arguments.get("target_id")
            paid = replace(paid, attack_targets=tuple(v for v in (first_id,*declaration.selected_target_ids) if v))
        session.combat_state = replace(state, shared_mana=paid)
        if basket_active(session) and declaration.boosts.get("rune_guard"):
            from dnd_board_game.combat.session import replace_actor
            actor = next(a for a in session.combat_state.actors if str(a.id) == declaration.actor_id)
            session.combat_state = replace_actor(session.combat_state, replace(actor, temp_hp=max(actor.temp_hp, 3)))
        record_training_payment(session, declaration.ability_id, declaration.boosts)
        if declaration.ability_id in {"unstoppable", "blade_dance"}:
            from dnd_board_game.combat.physical_mana import effect as marker
            from dnd_board_game.rules import apply_active_effect
            session.active_combat_effects = apply_active_effect(session.active_combat_effects, replace(marker(declaration.actor_id, "disengage_until_turn_end", "Ruch techniki bez ataków okazyjnych"), object_id="shared_technique_movement")).active_effects

        from dnd_board_game.combat.shared_mana import NON_OFFENSIVE
        if declaration.ability_id not in NON_OFFENSIVE and declaration.actor_id == mana.turn_actor:
            from dnd_board_game.combat.physical_mana import effect as marker
            from dnd_board_game.rules import apply_active_effect
            session.active_combat_effects = apply_active_effect(session.active_combat_effects,
                marker(declaration.actor_id, "shared_offensive_used", "Ofensywa w tej turze", 1)).active_effects
        from dnd_board_game.combat.shared_mana import paid_flaw_markers
        if mana.runes is None:
            session.active_combat_effects = paid_flaw_markers(declaration.actor_id, quote, session.active_combat_effects)
        if declaration.ability_id == "nimra_mind_break" and session.pending_player_attack:
            session.pending_player_attack = replace(session.pending_player_attack, shared_target_ids=declaration.extra_target_ids)
        session.shared_mana_declaration = None
        session._record("shared_mana_paid", {"ability_id": declaration.ability_id, "count": len(quote.cards), "boosts": declaration.boosts, "revision": paid.revision,
            "runes": list(quote.cards), "rune_choices": declaration.rune_choices})
        return getattr(session, declaration.resume_method)(**declaration.resume_arguments)
    elif action == "bonus":
        if declaration is None or declaration.stage != "bonus":
            raise ValueError("Brak podbicia do rozstrzygnięcia.")
        from dnd_board_game.combat.shared_mana_features import resolve_boost_support
        selection = payload(session)["declaration"]["target_selection"]
        targets = tuple(selection["selected_ids"])
        used = declaration.resume_arguments.get("used_targets", ())
        if not selection["can_confirm"]:
            raise ValueError("Wybierz podświetlony, legalny cel przed zatwierdzeniem.")
        updated, effects = state, session.active_combat_effects
        roll = declaration.resume_arguments.get("natural_roll")
        for target in targets:
            updated, effects = resolve_boost_support(updated, effects, declaration.ability_id,
                declaration.actor_id, target, 1 if roll is None else roll)
        session.combat_state = replace(updated, shared_mana=replace(updated.shared_mana, revision=mana.revision+1))
        session.active_combat_effects = effects
        remaining = declaration.resume_arguments["remaining"] - len(targets)
        if remaining:
            declaration.resume_arguments = {"remaining": remaining, "used_targets": (*used, *targets)}
            declaration.selected_target_ids = ()
        else:
            session.shared_mana_declaration = None
    elif action == "effect":
        if declaration is None or declaration.stage != "effect_roll":
            raise ValueError("Brak efektu do rozstrzygnięcia.")
        if declaration.resume_arguments.get("natural_roll") is None:
            declaration.resume_arguments["natural_roll"] = max(1, declaration.boosts.get("damage", 1)) if declaration.ability_id == "shoulder_check" and declaration.resume_arguments.get("shoulder_stage") == "damage" else 1
        if type(declaration.resume_arguments.get("natural_roll")) is not int:
            raise ValueError("Podaj wynik kości efektu.")
        if declaration.ability_id == "garran_guard_companion" and mana.runes is not None:
            from .shared_guard import resolve_guard
            session.shared_mana_declaration = None
            return resolve_guard(session, reduction_roll=declaration.resume_arguments["natural_roll"])
        if declaration.ability_id == "shoulder_check":
            from .shared_shoulder import resolve_shoulder_step
            return resolve_shoulder_step(session, declaration.resume_arguments["natural_roll"])
        from dnd_board_game.combat.shared_mana_features import resolve_simple_action
        resolve_simple_action(state, session.active_combat_effects, declaration.ability_id,
            target_id=str(declaration.resume_arguments.get("target_id", "")), roll=declaration.resume_arguments["natural_roll"])
        session.shared_mana_declaration = None
        return getattr(session, declaration.resume_method)(**declaration.resume_arguments)
    elif action == "cards_done":
        if declaration is None or declaration.stage != "cards":
            raise ValueError("Brak operacji kart do potwierdzenia.")
        session.combat_state = replace(state, shared_mana=finish_mana_action(mana, revision=mana.revision))
        session.shared_mana_declaration = None
        from .training_tutorial import record_ability
        record_ability(session, mana.pending_ability, mana.pending_actor)
    elif action == "refill":
        session.combat_state = replace(state, shared_mana=confirm_mana_refill(mana, revision=mana.revision))
    elif action == "discard":
        session.combat_state = replace(state, shared_mana=confirm_mana_discard(mana, revision=mana.revision))
    elif action == "refresh":
        if session._combat_has_pending_resolution() or declaration:
            raise ValueError("Dokończ akcję przed odświeżeniem talii.")
        session.combat_state = replace(state, shared_mana=request_mana_refresh(mana, revision=mana.revision))
    elif action == "refresh_done":
        updated = confirm_mana_refresh(mana, revision=mana.revision)
        state, effects = expire_deck_effects(state, session.active_combat_effects)
        session.combat_state = replace(state, shared_mana=updated)
        session.active_combat_effects = effects
        session._record("shared_mana_refreshed", {"cycle": updated.cycle})
    else:
        raise ValueError("Nieznane polecenie many.")
    current = session.combat_state.shared_mana
    if current.end_turn_pending and current.phase == ManaPhase.READY:
        return session.finish_combat_turn()
    session._sync_board_leds()
    return session.state_payload()


def _preflight(session: ExplorationUiSession, declaration: ManaDeclaration) -> None:
    state = session.combat_state
    if state.shared_mana.runes is None:
        return _legacy_preflight(session, declaration)
    from dnd_board_game.combat.runes import quote_runes
    actor = next(a for a in state.actors if str(a.id) == declaration.actor_id)
    if declaration.rune_flaw_only:
        if (state.shared_mana.phase != ManaPhase.RESOLVING or state.shared_mana.rune_flaw_paid
                or state.shared_mana.pending_ability != declaration.ability_id
                or state.shared_mana.pending_actor != declaration.actor_id):
            raise ValueError("Nieaktualna dopłata skazy.")
        _quote(session, declaration)
        return
    quote_runes(state, actor, declaration.ability_id, declaration.boosts)
    if declaration.ability_id == "optical_scope":
        from dnd_board_game.combat.lorian_features import is_lorian_hand_crossbow_source
        if not any(is_lorian_hand_crossbow_source(source) for source in session._attack_sources_for_actor(actor)):
            raise ValueError("Luneta optyczna wymaga wyposażonej kuszy ręcznej.")
    if declaration.ability_id == "garran_command_halt" and declaration.boosts.get("target"):
        from dnd_board_game.combat.spells import grid_distance_feet
        first_id = session.combat_selected_class_feature_target_id or declaration.resume_arguments.get("target_id")
        first = next((a for a in state.actors if str(a.id) == first_id), None)
        second = next((a for a in state.actors if str(a.id) in declaration.selected_target_ids), None)
        if first is None or second is None or first.id == second.id or second.faction == actor.faction or second.is_defeated() or grid_distance_feet(first.position,second.position) > 10:
            raise ValueError("Wskaż drugiego wroga do dwóch pól od pierwszego celu.")
    if declaration.ability_id == "cunning_action" and declaration.resume_arguments.get("mode") not in {"dash", "disengage"}:
        raise ValueError("Wybierz Sprint albo Odwrót runą na planszy.")
    if declaration.ability_id == "garran_rally" and not declaration.boosts.get("all"):
        chosen = declaration.selected_target_ids or tuple(v for v in (declaration.resume_arguments.get("target_id"),) if v)
        from dnd_board_game.combat.spells import grid_distance_feet
        eligible = {str(a.id) for a in state.actors if a.faction == actor.faction and not a.is_defeated() and grid_distance_feet(actor.position,a.position) <= 15}
        if not chosen or not set(chosen) <= eligible or len(chosen) > 1 + declaration.boosts.get("second", 0):
            raise ValueError("Wskaż na planszy uczestnika otrzymującego przewagę.")
    preview = replace(state.shared_mana, phase=ManaPhase.RESOLVING,
                      pending_ability=declaration.ability_id, pending_actor=declaration.actor_id,
                      pending_boosts=tuple(declaration.boosts.items()))
    session.combat_state = replace(state, shared_mana=preview)
    try:
        _legacy_preflight(session, declaration)
    finally:
        session.combat_state = state


def _legacy_preflight(session: ExplorationUiSession, declaration: ManaDeclaration) -> None:
    from dnd_board_game.combat.shared_mana_features import SIMPLE_ACTIONS, resolve_simple_action
    if declaration.ability_id == "aim":
        from dnd_board_game.combat.erynd_features import resolve_erynd_aim
        resolve_erynd_aim(session.combat_state, session.active_combat_effects)
    if declaration.resume_method == "select_player_healing_target_at_position":
        actor = current_actor(session.combat_state)
        session.player_area_healing_flow.select_healing_target(state=session.combat_state,
            board=session._active_encounter().board, source=session._selected_healing_source(actor),
            position=declaration.resume_arguments["position"])
    if declaration.resume_method == "confirm_player_attack_target" and session.pending_player_attack:
        from dnd_board_game.application.player_combat_action_flow import _validated_attack
        actor = current_actor(session.combat_state)
        pending = session.pending_player_attack
        source = session._attack_source_by_id(actor, pending.source_id, pending.cast_level)
        encounter = session._active_encounter()
        _validated_attack(session.combat_state, encounter.board, source, pending, encounter.scene_objects)
    if declaration.ability_id.startswith("mana_") and (session.combat_state.shared_mana.runes is None or declaration.ability_id == "mana_inspiration"):
        from dnd_board_game.combat.physical_mana import resolve_mana_support
        resolve_mana_support(session.combat_state, session.active_combat_effects,
            declaration.ability_id, str(declaration.resume_arguments.get("target_id", "")))
    if declaration.ability_id == "nimra_mind_break" and session.pending_player_attack:
        from dnd_board_game.combat.spells import grid_distance_feet
        from dnd_board_game.world import line_of_sight_clear
        state = session.combat_state
        first = next(a for a in state.actors if str(a.id) == session.pending_player_attack.target_id)
        caster = current_actor(state)
        if len(declaration.extra_target_ids) > declaration.boosts.get("target", 0):
            raise ValueError("Za mało podbić dla wybranych celów.")
        for key in declaration.extra_target_ids:
            target = next((a for a in state.actors if str(a.id) == key), None)
            if target is None or target.id == first.id or target.faction == caster.faction or target.is_defeated() or grid_distance_feet(first.position, target.position) > 10 or not line_of_sight_clear(session._active_encounter().board, caster.position, target.position):
                raise ValueError("Dodatkowy cel musi być widocznym wrogiem w 10 ft od pierwszego.")
    if declaration.ability_id == "garran_shield_wall":
        from dnd_board_game.combat.shared_mana import adjacent
        owner = current_actor(session.combat_state)
        eligible = [a for a in session.combat_state.actors if a.faction == owner.faction and adjacent(owner, a) and not a.is_dead()]
        if declaration.boosts.get("ward", 0) > len(eligible):
            raise ValueError("Każde białe podbicie wymaga innego sąsiadującego sojusznika.")
    if declaration.ability_id == "counterattack_command":
        from dnd_board_game.combat.shared_command import validate_command_target
        validate_command_target(session.combat_state, str(declaration.resume_arguments.get("target_id", "")))
    if declaration.ability_id in SIMPLE_ACTIONS:
        resolve_simple_action(session.combat_state, session.active_combat_effects, declaration.ability_id,
            target_id=str(declaration.resume_arguments.get("target_id", "")),
            roll=1 if declaration.ability_id == "caring_gesture" and declaration.stage == "payment" else declaration.resume_arguments.get("natural_roll"))


def _refresh_preview(session: ExplorationUiSession, declaration: ManaDeclaration) -> None:
    from dnd_board_game.combat.shared_mana_sources import boost_attack, boost_action
    from .exploration_app import _combat_action_by_id
    state = session.combat_state
    actor = current_actor(state)
    preview = replace(state.shared_mana, pending_ability=declaration.ability_id, pending_boosts=tuple(declaration.boosts.items()))
    encounter = session._active_encounter()
    pending = session.pending_area_spell
    if pending and pending.source_id == declaration.ability_id:
        source = boost_attack(session._attack_source_by_id(actor, pending.source_id, pending.cast_level), preview)
        transition = session.player_area_healing_flow.select_area_spell(state=state, board=encounter.board, source=source,
            position=pending.anchor, scene_objects=encounter.scene_objects, active_effects=session.active_combat_effects)
        pending = transition.pending
        protected_ids = {str(a.id) for a in state.actors if a.position in declaration.excluded_positions}
        session.pending_area_spell = replace(pending, excluded_positions=declaration.excluded_positions,
            unsculpted_target_ids=pending.target_ids, target_ids=tuple(key for key in pending.target_ids if key not in protected_ids))
    pending = session.pending_concentration_action
    if pending and pending.action_id == declaration.ability_id and pending.anchor is not None:
        action = boost_action(_combat_action_by_id(encounter, actor, pending.action_id), preview)
        pending = session.player_combat_resource_flow.select_concentration_area(state=state, board=encounter.board,
            action=action, pending=pending, position=pending.anchor)
        protected_ids = {str(a.id) for a in state.actors if a.position in declaration.excluded_positions}
        ids = tuple(key for key in pending.target_ids if key not in protected_ids)
        session.pending_concentration_action = replace(pending, target_ids=ids, selected_target_ids=ids, excluded_positions=declaration.excluded_positions)


def begin_support_bonus(session: ExplorationUiSession, ability_id: str) -> None:
    mana = session.combat_state.shared_mana
    if mana is None:
        return
    key = "ward" if ability_id == "garran_shield_wall" else "heal"
    count = dict(mana.pending_boosts).get(key, 0)
    if count:
        session.shared_mana_declaration = ManaDeclaration(ability_id, mana.pending_actor, "",
            {"remaining": count, "used_targets": ()}, stage="bonus")


def require_unpaid_cancellation(session: ExplorationUiSession) -> None:
    """Payment is a committed declaration; rolls and effects must be completed."""
    state = session.combat_state
    if state and state.shared_mana and state.shared_mana.phase == ManaPhase.RESOLVING:
        raise ValueError("Koszt został już rozliczony. Dokończ rzut i efekt opłaconej akcji.")


def complete_reaction_payment(session: ExplorationUiSession, ability_id: str) -> None:
    """Close one interrupt's payment so another hero may react to the same attack."""
    state = session.combat_state
    if state is None or state.shared_mana is None:
        return
    mana = state.shared_mana
    if mana.phase != ManaPhase.RESOLVING or mana.pending_ability != ability_id:
        return
    mana = finish_mana_action(mana, revision=mana.revision)
    if mana.phase == ManaPhase.REFRESH:
        mana = replace(mana, phase=ManaPhase.READY)
    session.combat_state = replace(state, shared_mana=mana)
    from .training_tutorial import record_ability
    record_ability(session, ability_id, state.shared_mana.pending_actor)
    if session.pending_enemy_turn_result is not None:
        result = session.pending_enemy_turn_result
        session.pending_enemy_turn_result = replace(result, state=replace(result.state, shared_mana=mana))
