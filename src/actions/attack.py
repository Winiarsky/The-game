import logging
from pathlib import Path
import sys
from typing import Optional

from combat import effective_ac, flat_footed_penalty, refresh_flanking_statuses
from hero import Hero
from .base import ActionContext, BaseAction
from .actions_registy import register
from board import consts
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.Enemies.simple_enemy import Enemy
from action_events import ActionEventBus

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def _choose_hero(ctx: ActionContext) -> tuple[Optional[Hero], Optional[tuple[int, int]]]:
    actor = getattr(ctx, "actor", None)
    if actor in ctx.game.heroes and getattr(actor, "position", None) is not None:
        return actor, getattr(actor, "position", None)
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
        refresh_flanking_statuses(ctx.game)
        target_ac = effective_ac(enemy)
        base_ac = getattr(enemy, "ac", target_ac)
        penalty = flat_footed_penalty(enemy)
        if penalty:
            prompt_ac = f"{target_ac} (bazowe {base_ac}, -{penalty} flankowanie)"
        else:
            prompt_ac = str(base_ac)

        # emit wstępny – pozwala reakcjom blokować/przerywać atak
        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="attack_pre",
            action_tags=ctx.action_tags or ["attack_melee"],
            target=enemy,
            target_pos=enemy_pos,
        )
        roll = prompt_for_roll(
            f"Podaj wynik testu ataku przeciwko {getattr(enemy, 'name', 'przeciwnik')} (AC {prompt_ac}): "
        )
        hit = roll >= target_ac
        if not hit:
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id="attack_miss",
                action_tags=ctx.action_tags or ["attack_melee"],
                target=enemy,
                target_pos=enemy_pos,
            )
            return

        ac_note = "" if target_ac == base_ac else f" (po karach z flankowania, bazowe AC {base_ac})"
        logger.info("Trafienie! (r=%s vs AC %s%s) Cel na %s.", roll, target_ac, ac_note, enemy_pos)
        
        if ctx.game.ui:
            ctx.game.ui_log(f"Trafienie! (r={roll} vs AC {target_ac}) Cel na {enemy_pos}.")
        dmg_type = _choose_damage_type(ctx.game)
        if dmg_type is None:
            logger.info("Brak przydzielonych obrażeń – kończę akcję ataku.")
            ctx.game.ui_log("Brak przydzielonych obrażeń – koniec akcji ataku.")
            return
        amount = prompt_for_roll(f"Ile obrażeń {dmg_type} zadajesz? ")
        _, defeated = enemy.apply_damage(amount, dmg_type)

        # --- event akcji ---
        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="attack",
            action_tags=ctx.action_tags or ["attack_melee"],
            target=enemy,
            target_pos=enemy_pos,
            damage=amount,
            damage_type=dmg_type,
        )
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
        try:
            refresh_flanking_statuses(ctx.game)
        except Exception as exc:
            logger.error("Nie udało się odświeżyć flankowania po ataku: %s", exc)
