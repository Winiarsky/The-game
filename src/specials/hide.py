import logging

from interactions.common import StatusMixin
from specials.registry import register_special

logger = logging.getLogger(__name__)


@register_special(
    "hide",
    name="Ukrycie",
    aliases=["hide", "ukrycie"],
    description="Bohater nakłada na siebie status hide.",
)
def hide_ability(hero, ctx) -> bool:
    """Nadaj status 'hide' aktywnemu bohaterowi."""
    statuses = getattr(hero, "statuses", None)
    if isinstance(statuses, list):
        if "hide" not in statuses:
            statuses.append("hide")
    elif isinstance(hero, StatusMixin):
        hero.add_status("hide")  # type: ignore[attr-defined]
    else:
        try:
            hero.statuses = ["hide"]  # type: ignore[attr-defined]
        except Exception:
            logger.warning("Nie mogę ustawić statusu hide na %s", hero)
            return False

    logger.info("Zdolność: %s otrzymuje status hide.", getattr(hero, "name", "Bohater"))
    try:
        ctx.game.ui_log(f"{getattr(hero, 'name', 'Bohater')} ukrywa się.")
    except Exception:
        pass
    return True
