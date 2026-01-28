import logging
from typing import Optional, Tuple

import specials  # noqa: F401  # zapewnia rejestrację zdolności przy imporcie akcji

from actions.actions_registy import register
from actions.base import ActionContext, BaseAction
from board import consts
from hero import Hero
from specials.registry import get_special, list_specials

logger = logging.getLogger(__name__)


def _choose_hero(ctx: ActionContext) -> Tuple[Optional[Hero], Optional[tuple[int, int]]]:
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


@register
class SpecialAction(BaseAction):
    name = "special"
    prompt_source = "Wybierz zdolność specjalną"

    def on_choose_info(self, ctx: ActionContext):
        available = ", ".join(sorted(list_specials()))
        logger.info("Akcja specjalna – dostępne zdolności: %s", available)

    def execute(self, ctx: ActionContext):
        hero, _pos = _choose_hero(ctx)
        if hero is None:
            logger.info("Brak aktywnego bohatera z pozycją – przerwij akcję specjalną.")
            ctx.game.ui_log("Brak aktywnego bohatera – przerwano akcję specjalną.")
            return False

        while True:
            raw = ctx.game.conn.read_card("Podaj nazwę zdolności specjalnej:")
            query = raw.strip().lower()
            if not query:
                continue
            try:
                special = get_special(query)
            except KeyError as exc:
                logger.warning(str(exc))
                ctx.game.ui_log(str(exc))
                continue

            # podgląd zdolności (nazwa + obrazek jeśli istnieje)
            ctx.game.ui_event(
                "special_preview",
                {
                    "name": special.name,
                    "slug": special.slug,
                    "image": special.image,
                    "desc": special.description,
                },
            )

            decision = ctx.game.conn.read_card(
                f"Wybrano '{special.name}'. Potwierdź: ACCEPT / DECLINE",
                ["ACCEPT", "DECLINE", "+", "-"],
            ).strip().lower()
            if decision in ("decline", "-"):
                logger.info("Odrzucono zdolność %s – wracam do wyboru zdolności.", special.name)
                continue

            try:
                result = special.execute(hero, ctx)
            except Exception as exc:
                logger.error("Błąd podczas wykonywania zdolności %s: %s", special.name, exc)
                ctx.game.ui_log(f"Zdolność {special.name} nie powiodła się: {exc}")
                return False

            # result=False oznacza brak zużycia akcji (np. brak ścieżki) – wracamy do wyboru akcji
            return bool(result)
