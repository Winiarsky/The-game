"""Read-only presentation of the guild briefing from authoritative scene state."""

from __future__ import annotations

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.exploration import NpcInteraction, NpcRuntimeState


def briefing_contract(flags: SceneFlags) -> dict[str, object]:
    """Summarize agreed amounts; viewing this never transfers money or items."""
    base = int(scene_flag(flags, "contract.base_reward_gp_per_hero", 10))
    bonus = int(scene_flag(flags, "contract.hazard_bonus_gp_per_hero", 0))
    advance = int(scene_flag(flags, "contract.advance_gp_per_hero", 0))
    survivors = int(scene_flag(flags, "contract.survivor_bonus_gp_each", 0))
    expenses = str(scene_flag(flags, "contract.expense_policy", "standard"))
    package = str(scene_flag(flags, "contract.preparation_package", ""))
    return {
        "status": "Ustalone" if scene_flag(flags, "nessa_contract_resolved", False)
        or scene_flag(flags, "guild_briefing_complete", False) else "Warunki wyjściowe",
        "rows": [
            {"label": "Stawka podstawowa / bohater", "value": f"{base} szt. złota"},
            {"label": "Dopłata za ryzyko / bohater", "value": f"{bonus} szt. złota"},
            {"label": "Zaliczka wypłacona / bohater", "value": f"{advance} szt. złota — odliczana od wypłaty"},
            {"label": "Po wykonaniu misji / bohater", "value": f"{max(0, base + bonus - advance)} szt. złota"},
            {"label": "Premia do wspólnej puli", "value": f"{survivors} szt. złota za każdą uratowaną osobę" if survivors else "Brak"},
            {"label": "Rozliczenie wydatków", "value": {
                "standard": "Standardowe zasady Gildii",
                "preapproved_only": "Tylko wydatki zatwierdzone przed wyprawą",
                "receipts_only": "Wyłącznie zaakceptowane rachunki",
            }.get(expenses, "Zgodnie z ustaleniami z Nessą")},
            {"label": "Wydane zaopatrzenie", "value": {
                "guild_medical_pack": "Pakiet medyczny Gildii",
                "guild_supply_pack": "Pakiet zaopatrzenia Gildii",
            }.get(package, "Brak dodatkowego pakietu")},
        ],
    }


def decorate_nessa_briefing(
    payload: dict[str, object],
    npc: NpcInteraction,
    flags: SceneFlags,
    runtime: NpcRuntimeState | None,
    actors: tuple[Actor, ...],
) -> None:
    """Keep authored slots visible without making consumed actions executable."""
    available = {goal["id"]: goal for goal in payload["goals"]}
    party_ids = {str(actor.id) for actor in actors}
    events = runtime.relationship_events if runtime else ()
    displayed: list[dict[str, object]] = []
    for slot, goal in enumerate(npc.goals, 1):
        item = dict(available.get(goal.id, goal.as_payload()))
        item["slot"] = slot
        item["badge"] = "Erynd · Test" if goal.assigned_actor_id else (
            "Rozmowa" if goal.resolution_mode.value == "automatic" else "Test"
        )
        event = next((event for event in reversed(events) if event.intent in goal.intent_ids), None)
        permission = npc.policy.intent_permission(goal.intent_ids[0])
        completion_flags = {
            "ask_nessa_about_disappearance": ("nessa_disappearance_info_learned",),
            "ask_nessa_about_cargo": ("nessa_cargo_info_learned",),
            "ask_nessa_about_people": ("nessa_personnel_info_learned",),
            "read_nessa_priorities": ("knowledge.nessa_true_priority_known", "nessa_priorities_closed"),
            "review_transport_documents": ("knowledge.convoy_route_magic_suspected", "nessa_documents_reviewed"),
            "negotiate_nessa_reward": ("nessa_contract_resolved",),
            "finish_nessa_briefing": ("guild_briefing_complete",),
        }
        consumed_flag = next((key for key in completion_flags.get(goal.id, ())
                              if bool(scene_flag(flags, key, False))), None)
        completed = event is not None or consumed_flag is not None
        unavailable_actor = bool(actors and goal.required_party_actor_id
                                 and goal.required_party_actor_id not in party_ids)
        read_only = completed or goal.id not in available or unavailable_actor
        item["read_only"] = read_only
        item["topic_status"] = "Omówione" if completed else "Niedostępne" if read_only else ""
        if read_only:
            # Neither automatic submission nor actor/card selection is valid for a recap.
            item.update(check_participants="no_actor", allowed_check_participants=[],
                        eligible_actor_ids=[], social_skill_options=[], assigned_actor_id=None)
            if completed:
                response = goal.grounded_response
                success = event.outcome == "success" if event else consumed_flag not in {
                    "nessa_priorities_closed", "nessa_documents_reviewed",
                }
                body = (response.success_message if success else response.failure_message) if response else "Warunki znajdziecie na karcie umowy."
                # Prefer actual resolved text, including outcome-specific negotiation amounts.
                if event and event.summary:
                    body = event.summary
                item["recap"] = {
                    "narration": response.player_narration if response and success else "",
                    "speech": response.npc_response if response and success else "",
                    "result": body,
                }
            else:
                item["recap"] = {"result": (
                    "Erynd nie uczestniczy w tej wyprawie. Trasę i ostatni kontakt poznacie w rozmowie o zaginięciu."
                    if unavailable_actor else "Ten temat nie został rozstrzygnięty przed zamknięciem ustaleń."
                )}
        if permission and permission.argument_evaluation:
            item["negotiation_targets"] = [
                {"label": target.label, "description": target.description, "skill": target.skill}
                for target in permission.targets
            ]
            item["known_arguments"] = [
                leverage.label for leverage in permission.argument_evaluation.leverages
                if all(bool(scene_flag(flags, key, False)) for key in leverage.required_flags)
            ]
        if goal.id == "finish_nessa_briefing":
            item["confirmation_note"] = "Pozostałe tematy są opcjonalne. Zakończenie odprawy zamyka negocjacje i testy; podróż rozpoczniesz osobno przy bramie."
        displayed.append(item)
    payload["goals"] = displayed
    payload["briefing_contract"] = briefing_contract(flags)
