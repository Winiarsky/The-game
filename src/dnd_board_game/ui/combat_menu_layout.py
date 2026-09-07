"""Presentation groups based on action economy, independent of keyboard bindings."""

from dnd_board_game.actors import Actor
from dnd_board_game.actors.resources import uses_physical_mana
from dnd_board_game.combat.context_menu import CombatMenuAction, CombatMenuOption
from dnd_board_game.rules.physical_mana import mana_ability
from dnd_board_game.combat.action_economy import ActionEconomyCost, ActionUse
from dnd_board_game.combat.session import CombatState, can_pay_action_economy_cost


def menu_action_economy_payload(
    option: CombatMenuOption, actor: Actor, *, default_cost: str = "action"
) -> dict[str, str]:
    if option.action in {
        CombatMenuAction.OPEN_WEAPON_MENU,
        CombatMenuAction.OPEN_ITEM_MENU,
        CombatMenuAction.END_TURN,
    }:
        group = "control"
    elif option.action in {CombatMenuAction.MOVE, CombatMenuAction.STAND_UP}:
        group = "movement"
    elif option.action == CombatMenuAction.TWO_WEAPON_ATTACK:
        group = "bonus_action"
    elif option.action in {
        CombatMenuAction.END_HIDE,
        CombatMenuAction.DROP_PRONE,
    } or option.id in {"combat-action:hunters_mark:transfer", "nimra-metamagic:cancel"}:
        group = "free"
    else:
        ability = (
            mana_ability(str(actor.id), option.action_id or option.source_id or "")
            if uses_physical_mana(actor)
            else None
        )
        group = (
            {"A": "action", "D": "bonus_action", "R": "reaction", "MOD": "modifier"}[
                ability.timing
            ]
            if ability
            else default_cost
        )
    labels = {
        "action": "Akcja główna",
        "bonus_action": "Akcja dodatkowa",
        "reaction": "Reakcja",
        "movement": "Ruch",
        "free": "Bez osobnej akcji",
        "modifier": "Wzmocnienie · bez osobnej akcji",
        "control": "Ekwipunek i tura",
        "object_interaction": "Interakcja z przedmiotem",
    }
    return {"action_economy": group, "action_economy_label": labels[group]}


def menu_cost_available(
    state: CombatState,
    group: str,
    *,
    movement_feet: int,
    continues_attack: bool = False,
) -> bool:
    """A remaining attack belongs only to its existing action, not other abilities."""
    if group == "action" and continues_attack:
        return True
    if group == "movement":
        return movement_feet >= 5
    if group == "modifier":
        return (
            state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
            or continues_attack
        )
    if group in {"control", "free"}:
        return True
    return can_pay_action_economy_cost(state, ActionEconomyCost(group))
