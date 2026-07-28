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
        PendingSummon,
        PendingMagicMovement,
        PendingMultiTargetDamageSpell,
        PendingSpellDebuff,
        PendingSpellDispel,
    )
    from dnd_board_game.combat import (
        CombatContextMenu,
        EnemyAutoTurnResult,
        EnemyTurnPlan,
        ReactionWindow,
        SceneResult,
    )
    from dnd_board_game.exploration import NpcTransitionPlan, PendingEncounter

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
    npc_transition: NpcTransitionPlan | None = None
    enemy_turn_intent: EnemyTurnPlan | None = None
    enemy_turn_result: EnemyAutoTurnResult | None = None
    enemy_turn_ack_result: EnemyAutoTurnResult | None = None
    enemy_saving_throw: PendingEnemySavingThrow | None = None
    encounter_result: SceneResult | None = None
    player_attack: PendingPlayerAttack | None = None
    player_healing: PendingPlayerHealing | None = None
    area_spell: PendingAreaSpell | None = None
    summon: PendingSummon | None = None
    magic_movement: PendingMagicMovement | None = None
    multi_target_damage_spell: PendingMultiTargetDamageSpell | None = None
    spell_debuff: PendingSpellDebuff | None = None
    spell_dispel: PendingSpellDispel | None = None
    combat_interaction: PendingCombatInteraction | None = None
    combat_help: PendingCombatHelp | None = None
    combat_skill_check: PendingCombatSkillCheck | None = None
    combat_shove: PendingShove | None = None
    combat_grapple: PendingGrapple | None = None
    concentration_action: PendingConcentrationAction | None = None
    concentration_check: PendingConcentrationCheck | None = None
    combat_ready: PendingCombatReady | None = None
    opportunity_movement: PendingOpportunityMovement | None = None
    reaction_window: ReactionWindow | None = None
    cutting_words_reaction_resolved: bool | None = None
    defensive_spell_reaction_resolved: bool | None = None
    deflect_missiles_reaction_resolved: bool | None = None
    counterspell_reaction_resolved: bool | None = None
    retaliation_spell_reaction_resolved: bool | None = None
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
        self.summon = None
        self.magic_movement = None
        self.multi_target_damage_spell = None
        self.spell_debuff = None
        self.spell_dispel = None
        self.combat_interaction = None
        self.combat_help = None
        self.combat_skill_check = None
        self.combat_shove = None
        self.combat_grapple = None
        self.concentration_action = None
        self.combat_ready = None
        self.opportunity_movement = None
        self.combat_context_menu = None
