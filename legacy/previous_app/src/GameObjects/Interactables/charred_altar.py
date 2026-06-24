from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources


class CharredAltar(InteractableMixin):
    def __init__(self, *, altar_id: str = "charred_altar", dc: int = 16) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.altar_id = str(altar_id or "charred_altar")
        self.scenario_object_id = self.altar_id
        self.name = "Spalony ołtarz"
        self.label = "Spalony ołtarz"
        self.interaction_label = "Spalony ołtarz"
        self.dc = int(dc or 16)
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(Interaction(id="approach", label="Podejdź do ołtarza", description="Budzi Spalonego Diakona.", handler=CharredAltar.action_approach, end_interaction=False))
        self.register_action(Interaction(id="seal_religion", label="Rytual: Religia", description=f"Religia DC {self.dc}.", handler=CharredAltar.action_seal_religion, end_interaction=False))
        self.register_action(Interaction(id="seal_occultism", label="Rytual: Okultyzm", description=f"Okultyzm DC {self.dc}.", handler=CharredAltar.action_seal_occultism, end_interaction=False))
        self.register_action(Interaction(id="use_holy_water", label="Użyj wody święconej", description="Jednorazowy, bezpieczny postęp sealu.", handler=CharredAltar.action_use_holy_water, end_interaction=False))
        self.register_action(Interaction(id="use_saint_symbol", label="Połóż pęknięty symbol", description="Użyj symbolu z konfesjonału.", handler=CharredAltar.action_use_saint_symbol, end_interaction=False))
        self.register_action(Interaction(id="damage_altar", label="Uszkodź ołtarz", description="Brutalny postęp sealu, zawsze zadaje obrażenia.", handler=CharredAltar.action_damage_altar, end_interaction=False))
        self.register_action(Interaction(id="leave", label="Zakończ", description="Zakończ interakcję.", handler=lambda *_: "Koniec interakcji."))

    def available_actions(self, actor=None, game=None):
        actions = list(super().available_actions())
        if game is None:
            return actions

        from burned_chapel_encounter import altar_is_sealed, can_attempt_seal_this_round, ensure_state

        state = ensure_state(game)
        triggered = bool(state.get("altar_triggered"))
        sealed = altar_is_sealed(game)
        can_seal = can_attempt_seal_this_round(game)

        filtered = []
        for action in actions:
            if action.id == "approach" and triggered:
                continue
            if action.id in {"seal_religion", "seal_occultism", "use_holy_water", "use_saint_symbol", "damage_altar"}:
                if sealed or not can_seal:
                    continue
            filtered.append(action)
        return filtered

    def interaction_prompt_body(self, actor=None, game=None) -> str | None:
        if game is None:
            return None
        from burned_chapel_encounter import can_attempt_seal_this_round, ensure_state

        state = ensure_state(game)
        progress = int(state.get("seal_progress", 0) or 0)
        required = int(state.get("seal_required", 3) or 3)
        if bool(state.get("altar_sealed")):
            return "Ołtarz jest zablokowany. Spalony Diakon nie ma już kotwicy rytuału."
        if bool(state.get("altar_triggered")) and not can_attempt_seal_this_round(game):
            return (
                f"Postęp sealu: {progress}/{required}. "
                "W tej rundzie ołtarz przyjął już jeden rytuał. Popiół musi opaść, zanim spróbujecie ponownie."
            )
        return f"Postęp sealu: {progress}/{required}. Każda runda pozwala zwiększyć seal tylko raz."

    def on_enter(self, actor, game) -> str | None:
        return self.action_approach(actor, game, None)

    def action_approach(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import trigger_altar

        return trigger_altar(game)

    def _seal_check(self, actor, game, skill_id: str) -> str:
        from burned_chapel_encounter import add_seal_progress, apply_backlash, can_attempt_seal_this_round, seal_round_gate_message, trigger_altar

        trigger_altar(game)
        if not can_attempt_seal_this_round(game):
            return seal_round_gate_message(game)
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "burned_chapel", "altar", "seal"],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            _ok, msg = add_seal_progress(game, actor=actor, method=skill_id)
            return f"{msg} (wynik: {outcome}, suma: {result.total})"
        penalty = apply_backlash(game, actor=actor, reason=f"{skill_id}_failure")
        return f"Rytuał wymyka się spod kontroli. {penalty} (wynik: {outcome}, suma: {result.total})"

    def action_seal_religion(self, actor, game, _payload=None) -> str:
        return self._seal_check(actor, game, "religion")

    def action_seal_occultism(self, actor, game, _payload=None) -> str:
        return self._seal_check(actor, game, "occultism")

    def action_use_holy_water(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import add_seal_progress, can_attempt_seal_this_round, consume_holy_water, seal_round_gate_message, trigger_altar

        trigger_altar(game)
        if not can_attempt_seal_this_round(game):
            return seal_round_gate_message(game)
        consumed, note = consume_holy_water(game, actor)
        if not consumed:
            return note
        _ok, msg = add_seal_progress(game, actor=actor, method="holy_water", backlash=False)
        return f"{note} Woda syczy na kamieniu. {msg}"

    def action_use_saint_symbol(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import add_seal_progress, can_attempt_seal_this_round, ensure_state, seal_round_gate_message, trigger_altar

        trigger_altar(game)
        if not can_attempt_seal_this_round(game):
            return seal_round_gate_message(game)
        state = ensure_state(game)
        if not bool(state.get("saint_symbol_found")):
            return "Nie macie jeszcze symbolu, który mógłby zamknąć tę warstwę rytuału."
        if bool(state.get("saint_symbol_used")):
            return "Pęknięty symbol świętego już leży na ołtarzu."
        state["saint_symbol_used"] = True
        _ok, msg = add_seal_progress(game, actor=actor, method="saint_symbol", backlash=False)
        return f"Pęknięty symbol świętego pęka na ołtarzu. {msg}"

    def action_damage_altar(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import add_seal_progress, can_attempt_seal_this_round, seal_round_gate_message, trigger_altar

        trigger_altar(game)
        if not can_attempt_seal_this_round(game):
            return seal_round_gate_message(game)
        if actor is not None and hasattr(actor, "apply_damage"):
            try:
                actor.apply_damage(2, "shadow")
            except Exception:
                pass
        _ok, msg = add_seal_progress(game, actor=actor, method="physical_damage", backlash=False)
        return f"Uderzenie w ołtarz odbija się ciemnym płomieniem. {msg}"


META = GameObjectMeta(
    object_id="charred_altar",
    label="Spalony ołtarz",
    color="#dc2626",
    category="Interactables",
    placement="cell",
    description="Ołtarz w spalonej kaplicy: rozpoczyna walkę z bossem i pilnuje postępu sealu.",
    logic_cls=CharredAltar,
    default_config={"altar_id": "charred_altar", "dc": 16},
)


__all__ = ["CharredAltar", "META"]
