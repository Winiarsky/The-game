from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnd_board_game.application import (
        CombatApproachInteractionPlan,
        PendingAreaSpell,
        PendingCombatInteraction,
        PendingCombatSkillCheck,
        PendingGrapple,
        PendingShove,
        PendingConcentrationAction,
        PendingConcentrationCheck,
        PendingEnemySavingThrow,
        PendingPlayerAttack,
        PendingPlayerHealing,
        PendingShortRest,
    )
    from dnd_board_game.combat import CombatContextMenu, EnemyAutoTurnResult, EnemyTurnPlan
    from dnd_board_game.exploration import PendingEncounter

    from .exploration_app import (
        PendingCombatHelp,
        PendingCombatReady,
        PendingEnemyOpportunityAttack,
        PendingInteraction,
        PendingOpportunityMovement,
        PendingApproachPickup,
        PendingReadyAttack,
    )


@dataclass(slots=True)
class UiPendingState:
    """Transient choices that may suspend the current UI flow.

    Concrete pending payload types remain owned by the flow that creates them.
    Imports used only for annotations avoid introducing runtime coupling back to
    the UI coordinator.
    """

    interaction: PendingInteraction | None = None
    encounter: PendingEncounter | None = None
    enemy_turn_intent: EnemyTurnPlan | None = None
    enemy_turn_result: EnemyAutoTurnResult | None = None
    enemy_turn_ack_result: EnemyAutoTurnResult | None = None
    enemy_saving_throw: PendingEnemySavingThrow | None = None
    player_attack: PendingPlayerAttack | None = None
    player_healing: PendingPlayerHealing | None = None
    area_spell: PendingAreaSpell | None = None
    combat_interaction: PendingCombatInteraction | None = None
    combat_help: PendingCombatHelp | None = None
    combat_skill_check: PendingCombatSkillCheck | None = None
    combat_shove: PendingShove | None = None
    combat_grapple: PendingGrapple | None = None
    concentration_action: PendingConcentrationAction | None = None
    concentration_check: PendingConcentrationCheck | None = None
    combat_ready: PendingCombatReady | None = None
    opportunity_movement: PendingOpportunityMovement | None = None
    enemy_opportunity_attack: PendingEnemyOpportunityAttack | None = None
    ready_attack: PendingReadyAttack | None = None
    short_rest: PendingShortRest | None = None
    combat_context_menu: CombatContextMenu | None = None
    approach_interaction: CombatApproachInteractionPlan | None = None
    approach_pickup: PendingApproachPickup | None = None

    def clear_player_choices(self) -> None:
        self.player_attack = None
        self.player_healing = None
        self.area_spell = None
        self.combat_interaction = None
        self.combat_help = None
        self.combat_skill_check = None
        self.combat_shove = None
        self.combat_grapple = None
        self.concentration_action = None
        self.combat_ready = None
        self.opportunity_movement = None
        self.combat_context_menu = None
