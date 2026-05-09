from __future__ import annotations

import logging

from time import sleep

from board import consts

from .base import EventContext, EventResult, GameEvent
from .registry import register_event
# zapewnij rejestrację eventów checków zanim będą dispatchowane
import GameObjects.events.checks.skill_check_event  # noqa: F401

logger = logging.getLogger(__name__)


@register_event
class InteractionEvent(GameEvent):
    name = "interaction"
    default_tags = ["interaction", "manipulate"]
    consumes_action = True

    @staticmethod
    def _display_name(obj) -> str:
        for attr in (
            "interaction_label",
            "challenge_label",
            "name",
            "label",
            "seek_label",
            "scenario_object_label",
            "object_label",
        ):
            value = getattr(obj, attr, None)
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = None
            text = str(value or "").strip()
            if text:
                return text
        object_id = str(getattr(obj, "object_id", "") or getattr(obj, "scenario_object_id", "") or "").strip()
        if object_id and object_id != obj.__class__.__name__:
            return object_id.replace("_", " ").strip().title()
        return obj.__class__.__name__

    def execute(self, ctx: EventContext) -> EventResult:
        game = ctx.game
        actor = ctx.actor
        if actor not in getattr(game, "heroes", []) or getattr(actor, "position", None) is None:
            heroes_positions = [hero.position for hero in getattr(game, "heroes", []) if hero.position is not None]
            if not heroes_positions:
                logger.warning("Brak bohaterów na planszy.")
                return EventResult.cancelled(message="Brak bohaterów na planszy.")
            game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
            source = game.conn.scan_board(heroes_positions)
            game.conn.leds_off()
            actor = game.board.occupant_at(source)

        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Nie wybrano bohatera do interakcji.")

        hero_pos = actor.position
        board = game.board

        def _visible_and_available(obj) -> bool:
            if getattr(obj, "hidden", False) and not getattr(obj, "revealed", False):
                return False
            checker = getattr(obj, "can_interact", None)
            if not callable(checker):
                return True
            try:
                return bool(checker(actor, game))
            except Exception:
                return False

        # wybór celu
        candidates = board.get_interactables_in_range(
            hero_pos, include_position=True, diagonal=True, include_hidden=True
        )
        positions_visible = [
            pos
            for pos, objs in candidates
            if any(_visible_and_available(obj) for obj in objs)
        ]
        if not positions_visible:
            message = (
                "Brak interakcji w zasięgu. Podejdź bliżej do NPC albo podświetlonego obiektu "
                "i wybierz Interakcję ponownie."
            )
            ui = getattr(game, "ui", None)
            if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
                try:
                    ui.prompt_info(
                        "Brak interakcji w zasięgu",
                        prompt_long=message,
                        source="interaction_no_targets",
                        prompt_id="interaction.no_targets",
                    )
                except Exception:
                    game.ui_log(message)
            else:
                game.ui_log(message)
            return EventResult.noop(message="Brak interakcji w zasięgu.")
        if positions_visible:
            game.conn.set_leds(positions_visible, consts.INTERACT_FIELD_RGB)
        ui = getattr(game, "ui", None)
        if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
            labels = []
            for idx, pos in enumerate(positions_visible, start=1):
                names = [
                    self._display_name(obj)
                    for obj in board.interactables_at(pos)
                    if _visible_and_available(obj)
                ]
                if names:
                    labels.append(f"{idx}. {', '.join(names)}: pole {pos}")
            body = (
                "Wybierz cel interakcji, klikając jedno z podświetlonych pól.\n\n"
                + "\n".join(labels)
            )
            try:
                game.player_prompt.create(
                    "Wybierz cel interakcji",
                    kind="info",
                    source="interaction_target",
                    body_markdown=body,
                    summary="Kliknij podświetlone pole NPC lub obiektu.",
                    scope_key="hero_turn:targeting",
                    dedupe_key="interaction:target",
                    input_mode="board_click",
                    cancel_enabled=True,
                    confirm_enabled=False,
                    prompt_id="interaction.target",
                )
            except Exception:
                pass
        target = game.conn.scan_board(positions_visible)
        game.conn.leds_off()
        if target is None:
            logger.info("Anulowano wybór celu interakcji.")
            return EventResult.noop(message="Anulowano interakcję.")
        if target not in positions_visible:
            logger.info("Nie ma tu dostępnej interakcji.")
            return EventResult.noop(message="Brak dostępnej interakcji.")

        interactables = [
            i
            for i in board.interactables_at(target)
            if (not getattr(i, "hidden", False) or getattr(i, "revealed", False) or getattr(i, "allow_hidden_interaction", False))
        ]
        if target != hero_pos:
            interactables = [
                i for i in interactables if not getattr(i, "require_same_cell_interact", False)
            ]
        if not interactables:
            logger.info("Wybrane pole nie ma obiektu do interakcji.")
            return EventResult.noop(message="Brak obiektu do interakcji.")
        interactables = [i for i in interactables if _visible_and_available(i)]
        if not interactables:
            logger.info("Wybrane pole nie ma teraz dostępnej interakcji.")
            return EventResult.noop(message="Brak dostępnej interakcji.")

        interactable = interactables[0]
        if getattr(interactable, "hidden", False) and not getattr(interactable, "revealed", False):
            if getattr(interactable, "allow_hidden_interaction", False):
                interactable.revealed = True
                on_reveal = getattr(interactable, "on_reveal", None)
                if callable(on_reveal):
                    try:
                        extra = on_reveal(game, source_actor=actor)
                    except TypeError:
                        extra = on_reveal(game)
                    except Exception:
                        extra = None
                    if extra:
                        game.ui_log(str(extra))
                logger.info("Odkrywasz ukryty element.")
                game.conn.set_leds([target], consts.HIDDEN_REVEAL_RGB)
                sleep(consts.RESPONSE_DELAY)
                game.conn.leds_off()
            else:
                logger.info("Nic tu nie znajdujesz.")
                return EventResult.noop(message="Brak efektu interakcji.")
        if getattr(interactable, "require_same_cell_interact", False) and target != hero_pos:
            logger.info("Musisz stanąć na tym polu, aby wejść w interakcję.")
            return EventResult.noop(message="Musisz stanąć na tym polu.")
        action_id = self._choose_action(interactable, game, actor=actor)
        while True:
            interaction = interactable.actions.get(action_id) if action_id else None
            tags = interaction.tags if interaction and getattr(interaction, "tags", None) else self._effective_tags(ctx)
            emitted = game.events.safe_emit_action(
                return_event=True,
                actor=actor,
                action_id=action_id or "interaction",
                action_tags=tags,
                target=interactable,
                target_pos=target,
            )
            if isinstance(emitted, dict) and bool(emitted.get("disrupted", False)):
                msg = "Interakcja przerwana przez Atak okazyjny."
                try:
                    game.ui_log(msg)
                except Exception:
                    pass
                return EventResult(success=False, consumed_action=True, actions_spent=1, message=msg)

            message = interactable.interact(actor, game, action_id=action_id)
            if message:
                logger.info(message)
                game.ui_log(message)
                payload = {"text": message}
                audio_getter = getattr(interactable, "interaction_result_audio", None)
                if callable(audio_getter):
                    try:
                        audio = audio_getter(action_id, message)
                    except TypeError:
                        audio = audio_getter(message)
                    except Exception:
                        audio = None
                    if audio:
                        payload["audio"] = str(audio)
                game.ui_event("info", payload)

            interaction = interactable.actions.get(action_id) if action_id else None
            if interaction is None or getattr(interaction, "end_interaction", False):
                game.events.safe_emit_action(
                    actor=actor,
                    action_id="interaction_end",
                    action_tags=["interaction_end"],
                    target=interactable,
                    target_pos=target,
                )
                break

            action_id = self._choose_action(interactable, game, actor=actor)
            if not action_id:
                break

        return EventResult(success=True, consumed_action=self.consumes_action, message="Interakcja zakończona.")

    def _prompt_value(self, interactable, name: str, actor, game) -> str | None:
        method = getattr(interactable, name, None)
        if not callable(method):
            return None
        try:
            value = method(actor, game)
        except TypeError:
            try:
                value = method()
            except Exception:
                return None
        except Exception:
            return None
        text = str(value or "").strip()
        return text or None

    def _choose_action(self, interactable, game, actor=None):
        actions = getattr(interactable, "available_actions", lambda: [])()
        if not actions:
            return None
        ui = getattr(game, "ui", None)
        if ui and ui.enabled:
            display_name = self._display_name(interactable)
            default_title = f"{display_name}: wybierz akcję" if display_name else "Wybierz akcję"
            title = self._prompt_value(interactable, "interaction_prompt_title", actor, game) or default_title
            subtitle = self._prompt_value(interactable, "interaction_prompt_summary", actor, game)
            body = self._prompt_value(interactable, "interaction_prompt_body", actor, game)
            details = self._prompt_value(interactable, "interaction_prompt_details", actor, game)
            audio = self._prompt_value(interactable, "interaction_prompt_audio", actor, game)
            choice_meta = [
                {
                    "raw": act.id,
                    "label": act.label,
                    "desc": act.description or "",
                    "desc_short": act.description or "",
                    "detail": act.description or "",
                    "key": str(idx + 1),
                }
                for idx, act in enumerate(actions)
            ]
            ans = ui.prompt_choice(
                title,
                choices=[c["label"] for c in choice_meta],
                source="interaction",
                subtitle=subtitle,
                prompt_long=body,
                details_markdown=details,
                audio=audio,
                layout="dialog",
                choice_meta=choice_meta,
            )
            if ans:
                normalized = ans.strip()
                if normalized.isdigit():
                    idx = int(normalized) - 1
                    if 0 <= idx < len(actions):
                        return actions[idx].id
                for act in actions:
                    if normalized.lower() in (act.id.lower(), act.label.lower()):
                        return act.id
                if ":" in normalized:
                    prefix = normalized.split(":")[0].strip()
                    if prefix.isdigit():
                        idx = int(prefix) - 1
                        if 0 <= idx < len(actions):
                            return actions[idx].id
        if ui and not getattr(ui, "allow_cli_fallback", False):
            return None

        print("Możliwe akcje:")
        for idx, action in enumerate(actions, start=1):
            desc = f" — {action.description}" if action.description else ""
            print(f"{idx}. {action.label}{desc}")
        choice = input("Wybierz numer akcji (Enter aby wyjść): ").strip()
        if not choice:
            return None
        if not choice.isdigit():
            return None
        index = int(choice) - 1
        if index < 0 or index >= len(actions):
            return None
        return actions[index].id
