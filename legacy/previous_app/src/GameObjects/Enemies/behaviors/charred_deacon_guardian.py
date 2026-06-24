from __future__ import annotations

from GameObjects.Enemies.behaviors.basic_melee import basic_melee


def charred_deacon_guardian(enemy, game, combat_state, actions_left: int = 1) -> int:
    """AI bossa spalonej kaplicy: przywoluje blokery i walczy blisko oltarza."""
    try:
        from burned_chapel_encounter import active_cinders, altar_is_sealed, combat_round, prompt_info, summon_cinders
    except Exception:
        return basic_melee(enemy, game, combat_state, actions_left=actions_left)

    round_idx = combat_round(game)
    memory = getattr(enemy, "ai_memory", None)
    if not isinstance(memory, dict):
        memory = {}
        try:
            enemy.ai_memory = memory
        except Exception:
            pass

    if not altar_is_sealed(game):
        last_summon = memory.get("call_from_ashes_round")
        if last_summon != round_idx and len(active_cinders(game)) < 4:
            spawned = summon_cinders(game)
            memory["call_from_ashes_round"] = round_idx
            if spawned > 0:
                return 1

        last_grasp = memory.get("ashen_grasp_round")
        if last_grasp != round_idx:
            memory["ashen_grasp_round"] = round_idx
            prompt_info(
                game,
                "Popielny Chwyt",
                "Popielne rece chwytaja przejscia przy oltarzu i posagach. Traktujcie najblizsze pole z czerwonym zarem jako utrudniony teren do konca rundy.",
                source="ashen_grasp",
            )
            return 1

    return basic_melee(enemy, game, combat_state, actions_left=actions_left)
