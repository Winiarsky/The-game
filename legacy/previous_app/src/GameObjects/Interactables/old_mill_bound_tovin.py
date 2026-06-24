from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from old_mill_encounter import flag_enabled, increase_alarm, reveal_hidden_route, secure_tovin, set_flag
from skills import Skill


class OldMillBoundTovin(InteractableMixin):
    def __init__(self, *, dc: int = 14, label: str = "Zwiazany Tovin") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "old_mill_bound_tovin"
        self.npc_id = "tovin_barrow"
        self.name = str(label or "Zwiazany Tovin")
        self.dc = int(dc or 14)
        self.register_action(
            Interaction(
                id="ask_what_happened",
                label="Zapytaj, co widzial",
                description="Krotki dialog sledczy z Tovinem.",
                handler=OldMillBoundTovin.action_ask,
                end_interaction=False,
            )
        )
        for skill in (Skill.THIEVERY.value, Skill.ATHLETICS.value, Skill.MEDICINE.value, Skill.DIPLOMACY.value):
            self.register_action(
                Interaction(
                    id=f"secure_{skill}",
                    label=f"Zabezpiecz Tovina: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_secure(actor, game, skill_id),
                    end_interaction=False,
                    tags=[skill, "old_mill", "hostage"],
                )
            )
        self.register_action(
            Interaction(
                id="reveal_route",
                label="Popros o droge do ruin",
                description="Jesli Tovin ufa druzynie, wskaze tylny trakt.",
                handler=OldMillBoundTovin.action_route,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakoncz", handler=lambda *_: "Tovin kiwa glowa i czeka cicho."))

    def action_ask(self, actor, game, _payload=None) -> str:
        set_flag(game, "tovin_saw_false_ash")
        set_flag(game, "false_ash_hint")
        message = (
            "Tovin szepcze, ze ludzie Odrana wniesli worki czarnego pylu jeszcze przed pozarem kaplicy. "
            "Jeden powiedzial: 'Mira ma pasowac do historii'."
        )
        if flag_enabled(game, "relic_theft_discovered"):
            message += " Gdy wspominacie relikwiarz, Tovin blednie: slyszal, jak straznik kazal ukryc 'metalowa rzecz z kaplicy' poza mlynem."
        return message

    def action_secure(self, actor, game, skill_id: str) -> str:
        bonus = 2 if flag_enabled(game, "elna_tovin_fear_seen") or flag_enabled(game, "public_square_heartened") else 0
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "old_mill", "hostage", "tovin"],
            game=game,
            base_modifier=bonus,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            return f"{secure_tovin(game)} (wynik: {outcome}, suma: {result.total})"
        if outcome == "critical_failure":
            increase_alarm(game, reason="Tovin wpada w panike i szarpie wiezy. Straznicy uslyszeli halas.")
        return f"Tovin nadal jest zwiazany albo zbyt spanikowany, by ruszyc. (wynik: {outcome}, suma: {result.total})"

    def action_route(self, actor, game, _payload=None) -> str:
        if flag_enabled(game, "tovin_secured") or flag_enabled(game, "tovin_ready_to_testify") or flag_enabled(game, "public_square_heartened"):
            return reveal_hidden_route(game)
        set_flag(game, "mill_hidden_route_hint")
        return "Tovin wskazuje tylna sciane, ale trzesie sie za mocno, by opisac mechanizm. Macie podpowiedz do dalszego szukania."


META = GameObjectMeta(
    object_id="old_mill_bound_tovin",
    label="Zwiazany Tovin",
    color="#93c5fd",
    category="Interactables",
    placement="cell",
    description="Zakladnik w Starym Mlynie; dialog, ratunek i wskazanie traktu.",
    logic_cls=OldMillBoundTovin,
    default_config={"dc": 14, "label": "Zwiazany Tovin"},
)
