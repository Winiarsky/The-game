"""Choose a legal reaction before its existing resolver confirms or spends it."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, TYPE_CHECKING

from dnd_board_game.combat.reactions import ReactionKind, ReactionOption, ReactionStage, ReactionWindow
from dnd_board_game.combat.runes import quote_runes
from dnd_board_game.combat.session import reaction_available_for
from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.scenarios.rune_catalog import rune_card

if TYPE_CHECKING:
    from dnd_board_game.world import Coordinate
    from .exploration_app import ExplorationUiSession, BoardScanTarget

WEAPON_REACTIONS = {ReactionKind.OPPORTUNITY_ATTACK, ReactionKind.READY_ATTACK}
CARD_IDS = {ReactionKind.CUTTING_WORDS: "cutting_words", ReactionKind.INSTINCTIVE_DODGE: "instinctive_dodge"}


def ability_id(option: ReactionOption) -> str:
    return CARD_IDS.get(option.kind, option.effect_id or "")


def select_option(window: ReactionWindow, option_id: str) -> ReactionWindow:
    """Preserve consumed history and every other pending option, including actors."""
    if window.stage != ReactionStage.CHOICE:
        raise ValueError("Najpierw dokończ rozpoczętą reakcję.")
    chosen = next((option for option in window.remaining_options if option.id == option_id), None)
    if chosen is None:
        raise ValueError("Ta reakcja nie jest już dostępna.")
    remaining = tuple(option for option in window.remaining_options if option.id != chosen.id)
    return replace(window, options=(*window.options[:window.current_index], chosen, *remaining), choice_confirmed=False)


def _available(s: ExplorationUiSession) -> tuple[ReactionOption, ...]:
    state, window = s.combat_state, s.pending_reaction_window
    if (state is None or state.shared_mana is None or state.shared_mana.runes is None or window is None
            or window.stage != ReactionStage.CHOICE or window.choice_confirmed or s.shared_mana_declaration is not None
            or state.shared_mana.phase.value != "ready"):
        return ()
    actors = {str(a.id): a for a in state.actors}
    result = []
    for option in window.remaining_options:
        actor = actors.get(option.reactor_actor_id)
        if actor is None or not reaction_available_for(state, actor):
            continue
        if option.kind not in WEAPON_REACTIONS:
            key = ability_id(option)
            try:
                quote_runes(state, actor, key, {})
            except ValueError:
                continue
        result.append(option)
    return tuple(result)


def view(s: ExplorationUiSession) -> dict[str, Any] | None:
    """Actor fields select whose reaction runes are shown; symbols never collide."""
    from .board_panel_symbols import panel_icon, SYMBOLS
    from dnd_board_game.rules.rune_baskets import NAMES
    options = _available(s)
    window = s.pending_reaction_window
    if not options or (len(options) == 1 and options[0] == window.current_option):
        return None
    actors = {str(a.id): a for a in s.combat_state.actors}
    actor_ids = tuple(dict.fromkeys(option.reactor_actor_id for option in options))
    current = window.current_option
    selected_actor = current.reactor_actor_id if current.reactor_actor_id in actor_ids else actor_ids[0]
    own = [option for option in options if option.reactor_actor_id == selected_actor]
    # If ready and opportunity attacks share an event, reserve weapon slot 1
    # for the ordinary opportunity attack and expose the other choice separately.
    reserved = {1} if any(option.kind == ReactionKind.OPPORTUNITY_ATTACK for option in own) else set()
    choices = []
    used = set()
    for option in own:
        card = rune_card(option.reactor_actor_id, ability_id(option), pool=s.combat_state.shared_mana.runes) if option.kind not in WEAPON_REACTIONS else None
        preferred = card.slot if card else 1
        if preferred in used or (preferred in reserved and option.kind != ReactionKind.OPPORTUNITY_ATTACK):
            preferred = next(slot for slot in range(5, 24) if slot not in used and slot not in reserved
                             and slot not in {rune_card(o.reactor_actor_id, ability_id(o)).slot for o in own if rune_card(o.reactor_actor_id, ability_id(o))})
        used.add(preferred)
        choices.append(dict(id=option.id, actor=option.reactor_actor_id, label=option.label or ("Atak okazyjny bronią" if option.kind == ReactionKind.OPPORTUNITY_ATTACK else card.name if card else "Przygotowany atak"),
                            kind=option.kind.value, target=option.target_actor_id, selected=option.id == current.id,
                            slot=preferred, position=[panel_position(preferred).col, panel_position(preferred).row],
                            icon=panel_icon(preferred), rune_name=SYMBOLS[preferred][0],
                            cost=[] if card is None else [NAMES[card.category] if card.category else card.rune]))
    return dict(active=True, selected=current.id, selected_actor=selected_actor,
                actor_name=actors[selected_actor].name, confirm_available=current in options,
                revision=s.board_selection_revision,
                actors=[dict(id=key, name=actors[key].name, position=[actors[key].position.col, actors[key].position.row], selected=key == selected_actor) for key in actor_ids],
                choices=choices, instruction="Wybierz reakcję runą. Pole figurki zmienia bohatera; ✓ zatwierdza wybraną reakcję. Atak okazyjny bronią nie kosztuje run.")


def choose(s: ExplorationUiSession, option_id: str, *, revision: int | None = None) -> dict[str, object]:
    if revision is not None and (type(revision) is not int or revision != s.board_selection_revision):
        raise ValueError("Ten wybór reakcji jest nieaktualny.")
    options = _available(s)
    selected = next((option for option in options if option.id == option_id), None)
    if selected is None:
        raise ValueError("Ta reakcja nie jest dostępna albo brakuje run.")
    s.pending_reaction_window = select_option(s.pending_reaction_window, selected.id)
    s._activate_current_reaction_option()
    s.board_panel_context = None
    s.board_selection_revision += 1
    s._record("combat_reaction_selected", dict(option=selected.id, actor=selected.reactor_actor_id, kind=selected.kind.value))
    s._sync_board_leds()
    return s.state_payload()


def confirm(s: ExplorationUiSession, *, revision: int | None = None) -> dict[str, object]:
    """Finish choosing; the existing card/weapon resolver owns the actual action."""
    if revision is not None and (type(revision) is not int or revision != s.board_selection_revision):
        raise ValueError("Ten wybór reakcji jest nieaktualny.")
    window = s.pending_reaction_window
    if window is None or window.current_option not in _available(s):
        raise ValueError("Wybrana reakcja nie jest już dostępna.")
    s.pending_reaction_window = replace(window, choice_confirmed=True)
    s.board_panel_context = None
    s.board_selection_revision += 1
    s._record("combat_reaction_choice_confirmed", dict(option=window.current_option.id, actor=window.current_option.reactor_actor_id))
    s._sync_board_leds()
    return s.state_payload()


def scan_target(s: ExplorationUiSession) -> BoardScanTarget | None:
    from .exploration_app import BoardScanTarget
    from dnd_board_game.world import Coordinate
    p = view(s)
    if p is None:
        return None
    fields = tuple(Coordinate(*actor["position"]) for actor in p["actors"])
    slots = tuple(choice["slot"] for choice in p["choices"])
    controls = (28, 29) if p["confirm_available"] else (29,)
    positions = (*fields, *(panel_position(slot) for slot in (*slots, *controls)))
    selected = next((choice["slot"] for choice in p["choices"] if choice["selected"]), None)
    colors = {slot: (255, 220, 130) if slot == selected else (165, 135, 70) for slot in slots}
    base = LedFeedback((LedFrame(fields, LedColor.INTERACTIVE_OBJECT, LedRole.MARKER),))
    return BoardScanTarget(positions=positions, feedback=panel_feedback(slots, control_slots=controls, action_colors=colors, base=base), empty_message=p["instruction"])


def select_position(s: ExplorationUiSession, position: Coordinate) -> dict[str, object] | None:
    p = view(s)
    if p is None:
        return None
    if position == panel_position(28) and p["confirm_available"]:
        return confirm(s)
    choice = next((choice for choice in p["choices"] if panel_position(choice["slot"]) == position), None)
    if choice:
        return choose(s, choice["id"])
    actor = next((actor for actor in p["actors"] if actor["position"] == [position.col, position.row]), None)
    if actor:
        selected = next(option for option in _available(s) if option.reactor_actor_id == actor["id"])
        return choose(s, selected.id)
    return None  # Existing decline handler advances or closes the reaction window.
