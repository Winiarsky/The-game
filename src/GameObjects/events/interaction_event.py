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

        # wybór celu
        candidates = board.get_interactables_in_range(
            hero_pos, include_position=True, diagonal=True, include_hidden=True
        )
        positions_all = [pos for pos, _objs in candidates]
        positions_visible = [
            pos
            for pos, objs in candidates
            if any(not getattr(obj, "hidden", False) or getattr(obj, "revealed", False) for obj in objs)
        ]
        if positions_visible:
            game.conn.set_leds(positions_visible, consts.INTERACT_FIELD_RGB)
        target = game.conn.scan_board(None)  # None pozwala na anulowanie
        game.conn.leds_off()
        if target not in positions_all:
            logger.info("Nie ma tu nic ciekawego.")
            return EventResult.noop(message="Brak interakcji.")

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
        if not interactable.can_interact(actor, game):
            logger.info("Nie możesz teraz wejść w interakcję z tym obiektem.")
            return EventResult.noop(message="Brak możliwości interakcji.")

        action_id = self._choose_action(interactable, game)
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
                game.ui_event("info", {"text": message})

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

            action_id = self._choose_action(interactable, game)
            if not action_id:
                break

        return EventResult(success=True, consumed_action=self.consumes_action, message="Interakcja zakończona.")

    def _choose_action(self, interactable, game):
        actions = getattr(interactable, "available_actions", lambda: [])()
        if not actions:
            return None
        ui = getattr(game, "ui", None)
        if ui and ui.enabled:
            choice_meta = [
                {
                    "raw": act.id,
                    "label": act.label,
                    "desc": act.description or "",
                    "key": str(idx + 1),
                }
                for idx, act in enumerate(actions)
            ]
            ans = ui.prompt_choice(
                "Wybierz akcję",
                choices=[c["label"] for c in choice_meta],
                source="interaction",
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
