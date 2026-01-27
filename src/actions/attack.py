import logging
from pathlib import Path
import sys
from typing import Optional

from hero import Hero
from .base import ActionContext, BaseAction
from .actions_registy import register
from board import consts
from interactions.common import prompt_for_roll
from GameObjects.Enemies.basic_enemy import Enemy

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def _choose_hero(ctx: ActionContext) -> tuple[Optional[Hero], Optional[tuple[int, int]]]:
    heroes_positions = [hero.position for hero in ctx.game.heroes if hero.position is not None]
    if not heroes_positions:
        logger.warning("Brak bohaterów na planszy.")
        return None, None
    ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
    pos = ctx.game.conn.scan_board(heroes_positions)
    ctx.game.conn.leds_off()
    hero = ctx.game.board.occupant_at(pos)
    return hero, pos


def _choose_enemy(ctx: ActionContext) -> tuple[Optional[Enemy], Optional[tuple[int, int]]]:
    """Podświetla wszystkich wrogów na planszy – gracz wybiera cel na własną odpowiedzialność (zasięg/linie)."""
    enemy_positions: list[tuple[int, int]] = [
        enemy.position for enemy in ctx.game.enemies if getattr(enemy, "position", None) is not None
    ]
    if not enemy_positions:
        logger.info("Brak wrogów na planszy.")
        return None, None
    ctx.game.conn.set_leds(enemy_positions, consts.INTERACT_FIELD_RGB)
    pos = ctx.game.conn.scan_board(enemy_positions)
    ctx.game.conn.leds_off()
    enemy = ctx.game.board.occupant_at(pos)
    return enemy, pos


def _choose_damage_type(game) -> Optional[str]:
    options = ["sieczne", "obuchowe", "ogień", "lód", "brak obrażeń"]

    def _normalize(raw: str) -> Optional[str]:
        text = raw.strip().lower()
        if not text:
            return None
        # obsługa formatu "1: sieczne" / "1 sieczne"
        if ":" in text:
            parts = text.split(":", 1)
            left, right = parts[0].strip(), parts[1].strip()
            if left.isdigit():
                idx = int(left) - 1
                if 0 <= idx < len(options):
                    picked = options[idx]
                    return None if picked == "brak obrażeń" else picked
            text = right
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(options):
                picked = options[idx]
                return None if picked == "brak obrażeń" else picked
        for opt in options:
            if opt.lower() == text:
                return None if opt == "brak obrażeń" else opt
        return None

    ui = getattr(game, "ui", None)
    if ui and ui.enabled:
        choice = ui.prompt_choice("Wybierz typ obrażeń:", choices=[f"{i+1}: {opt}" for i, opt in enumerate(options)], source="attack")
        if choice:
            parsed = _normalize(choice)
            if parsed is not None:
                return parsed
    # fallback do konsoli
    print("Typy obrażeń:")
    for idx, name in enumerate(options, start=1):
        print(f"{idx}. {name}")
    while True:
        choice = input("Wybierz typ obrażeń (numer lub nazwa): ").strip().lower()
        parsed = _normalize(choice)
        if parsed is not None:
            return parsed
        print("Nieprawidłowy wybór, spróbuj ponownie.")


@register
class TestAttackAction(BaseAction):
    name = "test_attack"
    prompt_source = "Wybierz bohatera wykonującego atak"
    prompt_target = "Wybierz cel ataku"

    def on_choose_info(self, ctx: ActionContext):
        logger.info("Akcja test_attack: wybierz bohatera, podaj wynik testu ataku, wskaż przeciwnika, a po trafieniu przydziel obrażenia.")

    def execute(self, ctx: ActionContext):
        hero, hero_pos = _choose_hero(ctx)
        if hero is None:
            return
        enemy, enemy_pos = _choose_enemy(ctx)
        if enemy is None or enemy_pos is None:
            return
        roll = prompt_for_roll(f"Podaj wynik testu ataku przeciwko {getattr(enemy, 'name', 'przeciwnik')} (AC {getattr(enemy, 'ac', '?')}): ")
        hit = roll >= getattr(enemy, "ac", 10)
        if not hit:
            logger.info("Pudło (r=%s vs AC %s).", roll, getattr(enemy, "ac", "?"))
            return

        logger.info("Trafienie! (r=%s vs AC %s) Cel na %s.", roll, getattr(enemy, "ac", "?"), enemy_pos)
        if ctx.game.ui:
            ctx.game.ui_log(f"Trafienie! (r={roll} vs AC {getattr(enemy, 'ac', '?')}) Cel na {enemy_pos}.")
        dmg_type = _choose_damage_type(ctx.game)
        if dmg_type is None:
            logger.info("Brak przydzielonych obrażeń – kończę akcję ataku.")
            ctx.game.ui_log("Brak przydzielonych obrażeń – koniec akcji ataku.")
            return
        amount = prompt_for_roll(f"Ile obrażeń {dmg_type} zadajesz? ")
        _, defeated = enemy.apply_damage(amount, dmg_type)
        if defeated:
            try:
                ctx.game.board.remove(enemy_pos)
                try:
                    ctx.game.enemies.remove(enemy)
                except ValueError:
                    pass
            except Exception as exc:
                logger.error("Nie udało się usunąć przeciwnika z planszy: %s", exc)
            enemy.position = None
            logger.info("Przeciwnik pokonany.")
            ctx.game.ui_log("Przeciwnik pokonany.")
        else:
            logger.info("Obrażenia przyjęte, cel żyje (HP %s).", enemy.hp)
            ctx.game.ui_log(f"Obrażenia przyjęte, cel żyje (HP {enemy.hp}).")
