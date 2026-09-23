"""Explicit, reversible rune selections before committing an ability."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

from dnd_board_game.actors import Actor
from dnd_board_game.rules.runes import available_payment_runes, card_payment_requirements
from dnd_board_game.scenarios.rune_catalog import rune_card

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession
    from .shared_mana import ManaDeclaration


def requirements(session: ExplorationUiSession, declaration: ManaDeclaration) -> tuple[str, ...]:
    from dnd_board_game.combat.runes import rune_requirements
    state = session.combat_state
    actor = next(a for a in state.actors if str(a.id) == declaration.actor_id)
    if declaration.rune_flaw_only:
        from dnd_board_game.combat.rune_flaws import rune_flaw_cost
        return ("*",) * rune_flaw_cost(state, actor, declaration.ability_id, declaration_targets(session, declaration)).count
    return rune_requirements(state, actor, declaration.ability_id, declaration.boosts,
                             targets=declaration_targets(session, declaration))


def declaration_targets(session: ExplorationUiSession, declaration: ManaDeclaration) -> tuple[Actor, ...]:
    """Targets already selected through the board, including area spells."""
    ids = {str(declaration.resume_arguments.get("target_id", ""))}
    ids.update(str(a) for a, amount in declaration.resume_arguments.get("allocations") or () if amount > 0)
    ids.update(declaration.selected_target_ids)
    ids.update(declaration.extra_target_ids)
    if getattr(session, "combat_targeting_class_feature_action_id", None) == declaration.ability_id:
        ids.add(getattr(session, "combat_selected_class_feature_target_id", None))
    position = declaration.resume_arguments.get("position")
    ids.update(str(a.id) for a in session.combat_state.actors if position is not None and a.position == position)
    for name in ("pending_player_attack", "pending_player_healing", "pending_area_spell"):
        pending = getattr(session, name, None)
        if pending:
            ids.update(getattr(pending, "target_ids", ()))
            ids.add(getattr(pending, "target_id", ""))
    return tuple(a for a in session.combat_state.actors if str(a.id) in ids)


def _steps(session: ExplorationUiSession, declaration: ManaDeclaration) -> tuple[str, ...]:
    pool = session.combat_state.shared_mana.runes
    expanded = card_payment_requirements(pool.hand(declaration.actor_id), requirements(session, declaration))
    result = ["payment"] if "*" in expanded else []
    if declaration.ability_id == "counterattack_command":
        result.append("partner")
    if declaration.ability_id == "mana_tuning":
        result.append("exchange")
    if declaration.ability_id == "mana_recovery":
        result.append("recovery")
    return tuple(result)


def selected_payment(session: ExplorationUiSession, declaration: ManaDeclaration) -> tuple[str, ...]:
    from dnd_board_game.combat.runes import quote_runes
    state = session.combat_state
    actor = next(a for a in state.actors if str(a.id) == declaration.actor_id)
    selected = declaration.rune_choices.get("payment")
    if declaration.rune_flaw_only:
        from dnd_board_game.rules.runes import plan_card_payment
        return plan_card_payment(state.shared_mana.runes.hand(declaration.actor_id), requirements(session, declaration), selected)
    return quote_runes(state, actor, declaration.ability_id, declaration.boosts, selected,
                       targets=declaration_targets(session, declaration))


def _spec(session: ExplorationUiSession, declaration: ManaDeclaration, step: str) -> dict[str, object]:
    pool = session.combat_state.shared_mana.runes
    actor_id = declaration.actor_id
    if step == "payment":
        required = requirements(session, declaration)
        expanded = card_payment_requirements(pool.hand(actor_id), required)
        count = expanded.count("*")
        return dict(actor=actor_id, title="Wybierz runy do zapłaty", minimum=count, maximum=count,
            source=available_payment_runes(pool.hand(actor_id), required),
            reserved=tuple(r for r in expanded if r != "*"),
            instruction=f"Wskaż {count} dowolne runy. Wymagane symbole są już zarezerwowane.")
    if step == "partner":
        actor_id = str(declaration.resume_arguments.get("target_id", ""))
        return dict(actor=actor_id, title="Runa sojusznika na Kontratak", minimum=1, maximum=1,
            source=pool.hand(actor_id), reserved=(),
            instruction="Sojusznik wybiera jedną własną runę; Kontratak wykorzysta również jego reakcję.")
    remaining = list(pool.hand(actor_id))
    for rune in selected_payment(session, declaration):
        remaining.remove(rune)
    if step == "exchange":
        return dict(actor=actor_id, title="Wybierz runę do wymiany", minimum=1, maximum=1,
            source=tuple(remaining), reserved=(),
            instruction="Wybierz runę pozostałą po zapłacie. Zastąpi ją wierzchnia runa talii.")
    maximum = min(3 if declaration.boosts.get("recover_more") else 2, 7-len(remaining), len(pool.discard))
    return dict(actor=actor_id, title="Wybierz runy do odzyskania", minimum=1, maximum=maximum,
        source=pool.discard, reserved=(),
        instruction=f"Wybierz od 1 do {maximum} run odrzuconych wcześniej. Koszt tej mocy nie jest dostępny do odzyskania.")


def validate_choices(session: ExplorationUiSession, declaration: ManaDeclaration) -> None:
    for step in _steps(session, declaration):
        spec = _spec(session, declaration, step)
        chosen = declaration.rune_choices.get(step, ())
        if (not spec["minimum"] <= len(chosen) <= spec["maximum"]
                or Counter(chosen) - Counter(spec["source"])):
            raise ValueError("Dokończ wybór dostępnych run przed zatwierdzeniem mocy.")


def begin(session: ExplorationUiSession, declaration: ManaDeclaration) -> bool:
    steps = _steps(session, declaration)
    if not steps:
        return False
    if declaration.rune_choices_complete:
        validate_choices(session, declaration)
        return False
    declaration.stage = "rune_choices"
    declaration.rune_choice_step = steps[0]
    declaration.rune_choices = {}
    _changed(session)
    return True


def view(session: ExplorationUiSession) -> dict[str, object] | None:
    declaration = session.shared_mana_declaration
    if declaration is None or declaration.stage != "rune_choices":
        return None
    from .runes import RUNE_SLOTS
    from .board_panel_symbols import panel_icon
    spec = _spec(session, declaration, declaration.rune_choice_step)
    chosen = declaration.rune_choices.get(declaration.rune_choice_step, ())
    remaining = Counter(spec["source"]) - Counter(chosen)
    actor = next(a for a in session.combat_state.actors if str(a.id) == spec["actor"])
    can_confirm = (spec["minimum"] <= len(chosen) <= spec["maximum"]
                   and not (Counter(chosen) - Counter(spec["source"])))
    choices = [dict(slot=RUNE_SLOTS[r], rune=r, count=n, label=f"{r} ×{n}", command="rune_choice_take")
               for r, n in remaining.items() if n > 0 and len(chosen) < spec["maximum"]]
    if can_confirm:
        choices.append(dict(slot=28, label="Zatwierdź wybór", command="rune_choice_confirm"))
    choices.append(dict(slot=29, label="Cofnij ostatni wybór" if chosen else "Wróć", command="rune_choice_back"))
    steps = _steps(session, declaration)
    last = declaration.rune_choice_step == steps[-1]
    return dict(phase="rune_choices", actor=spec["actor"], actor_name=actor.name,
        title=spec["title"], instruction=spec["instruction"] + " Kliknięcie wybiera jedną sztukę; ↩ cofa. "
            + ("✓ zatwierdzi całą moc i pobierze wybrane runy." if last else "✓ przejdzie do kolejnego wyboru bez pobierania run."),
        selected=list(chosen), selected_slots=[RUNE_SLOTS[r] for r in set(chosen)],
        reserved=list(spec["reserved"]), minimum=spec["minimum"], maximum=spec["maximum"], can_confirm=can_confirm,
        choices=[dict(c, icon=panel_icon(c["slot"])) for c in choices],
        source=[dict(rune=r, count=n, slot=RUNE_SLOTS[r], icon=panel_icon(RUNE_SLOTS[r]),
            enabled=bool(remaining[r]) and len(chosen) < spec["maximum"], selected=Counter(chosen)[r], remaining=remaining[r])
            for r,n in Counter(spec["source"]).items()],
        payment=list(selected_payment(session, declaration)) if declaration.rune_choice_step != "payment" or can_confirm else [],
        partner=list(declaration.rune_choices.get("partner", ())))


def _changed(session: ExplorationUiSession) -> None:
    state = session.combat_state
    session.combat_state = replace(state, shared_mana=replace(state.shared_mana, revision=state.shared_mana.revision+1))
    session.board_panel_context = None
    session._sync_board_leds()


def command(session: ExplorationUiSession, data: dict[str, object]) -> dict[str, object]:
    declaration = session.shared_mana_declaration
    current = view(session)
    if current is None:
        raise ValueError("Nie trwa wybór run dla mocy.")
    step = declaration.rune_choice_step
    picked = declaration.rune_choices.get(step, ())
    action = data.get("command")
    if action == "rune_choice_take":
        rune = str(data.get("rune", ""))
        if not any(c.get("rune") == rune for c in current["choices"]):
            raise ValueError("Wybierz dostępną, podświetloną runę.")
        declaration.rune_choices[step] = (*picked, rune)
    elif action == "rune_choice_back":
        if picked:
            declaration.rune_choices[step] = picked[:-1]
        else:
            steps = _steps(session, declaration)
            index = steps.index(step)
            if index:
                previous = steps[index-1]
                for later in steps[index:]:
                    declaration.rune_choices.pop(later, None)
                declaration.rune_choice_step = previous
                declaration.rune_choices[previous] = declaration.rune_choices.get(previous, ())[:-1]
            else:
                declaration.stage = "payment"
                declaration.rune_choices = {}
                declaration.rune_choice_step = ""
    elif action == "rune_choice_confirm":
        if not current["can_confirm"]:
            raise ValueError("Najpierw wybierz wymaganą liczbę run.")
        steps = _steps(session, declaration)
        index = steps.index(step)
        if index + 1 < len(steps):
            declaration.rune_choice_step = steps[index+1]
        else:
            validate_choices(session, declaration)
            declaration.rune_choices_complete = True
            declaration.stage = "payment"
            _changed(session)
            from .shared_mana import command as mana_command
            return mana_command(session, dict(command="pay", revision=session.combat_state.shared_mana.revision))
    else:
        raise ValueError("Nieznana operacja wyboru run.")
    _changed(session)
    return session.state_payload()
