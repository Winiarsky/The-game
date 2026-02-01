import logging
from pathlib import Path
import sys
from time import sleep

from .actions_registy import register
from .base import ActionContext, BaseAction
from board import consts

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


logger = logging.getLogger(__name__)


@register
class InteractAction(BaseAction):
    name = "interact"
    prompt_source = "Wybierz bohatera do interakcji"
    prompt_target = "Wybierz obiekt do interakcji"

    def on_choose_info(self, ctx: ActionContext):
        logger.info("Akcja interakcji: wybierz bohatera, potem obiekt w zasięgu.")

    def _choose_hero(self, ctx: ActionContext):
        actor = getattr(ctx, "actor", None)
        if actor in ctx.game.heroes and getattr(actor, "position", None) is not None:
            return actor, getattr(actor, "position", None)
        heroes_positions = [hero.position for hero in ctx.game.heroes if hero.position is not None]
        if not heroes_positions:
            logger.warning("Brak bohaterów na planszy.")
            return None, None
        ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
        source = ctx.game.conn.scan_board(heroes_positions)
        ctx.game.conn.leds_off()
        board = ctx.game.board
        hero = board.occupant_at(source)
        return hero, source

    def _choose_interactable(self, ctx: ActionContext, hero_pos):
        board = ctx.game.board
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
            ctx.game.conn.set_leds(positions_visible, consts.INTERACT_FIELD_RGB)
        target = ctx.game.conn.scan_board(None) # tu musi byc None zeby moc zakonczyc akcje
        ctx.game.conn.leds_off()
        if target not in positions_all:
            logger.info("Nie ma tu nic ciekawego.")
            return None
        return target

    def execute(self, ctx: ActionContext):
        hero, hero_pos = self._choose_hero(ctx)
        if hero is None or hero_pos is None:
            return

        target = self._choose_interactable(ctx, hero_pos)
        if target is None:
            return

        interactables = [
            i
            for i in ctx.game.board.interactables_at(target)
            if (not getattr(i, "hidden", False) or getattr(i, "revealed", False) or getattr(i, "allow_hidden_interaction", False))
        ]
        if target != hero_pos:
            interactables = [
                i for i in interactables if not getattr(i, "require_same_cell_interact", False)
            ]
        if not interactables:
            logger.info("Wybrane pole nie ma obiektu do interakcji.")
            return

        interactable = interactables[0]  # na razie pierwszy z listy
        if getattr(interactable, "hidden", False) and not getattr(interactable, "revealed", False):
            if getattr(interactable, "allow_hidden_interaction", False):
                interactable.revealed = True
                logger.info("Odkrywasz ukryty element.")
                ctx.game.conn.set_leds([target], consts.HIDDEN_REVEAL_RGB)
                sleep(consts.RESPONSE_DELAY)
                ctx.game.conn.leds_off()
            else:
                logger.info("Nic tu nie znajdujesz.")
                return
        if getattr(interactable, "require_same_cell_interact", False) and target != hero_pos:
            logger.info("Musisz stanąć na tym polu, aby wejść w interakcję.")
            return
        if not interactable.can_interact(hero, ctx.game):
            logger.info("Nie możesz teraz wejść w interakcję z tym obiektem.")
            return

        action_id = self._choose_action(interactable, ctx.game)
        while True:
            interaction = interactable.actions.get(action_id) if action_id else None

            # emit przed wykonaniem (widoczny w UI/reakcjach)
            tags = interaction.tags if interaction and getattr(interaction, "tags", None) else ["interact", "manipulate"]
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id=action_id or "interaction",
                action_tags=tags,
                target=interactable,
                target_pos=target,
            )

            message = interactable.interact(hero, ctx.game, action_id=action_id)
            if message:
                logger.info(message)
                ctx.game.ui_log(message)
                ctx.game.ui_event("info", {"text": message})

            interaction = interactable.actions.get(action_id) if action_id else None
            if interaction is None or interaction.end_interaction:
                ctx.game.events.safe_emit_action(
                    actor=hero,
                    action_id="interaction_end",
                    action_tags=["interaction_end"],
                    target=interactable,
                    target_pos=target,
                )
                break

            action_id = self._choose_action(interactable, ctx.game)
            if not action_id:
                break

    def _choose_action(self, interactable, game):
        actions = getattr(interactable, "available_actions", lambda: [])()
        if not actions:
            return None
        ui = getattr(game, "ui", None)
        if ui and ui.enabled:
            choices = [
                f"{idx}: {action.label}{' — ' + action.description if action.description else ''}"
                for idx, action in enumerate(actions, start=1)
            ]
            ans = ui.prompt_choice("Wybierz akcję (numer lub nazwa): ", choices=choices, source="interaction")
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
