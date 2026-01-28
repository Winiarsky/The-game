import logging

from interactions.common import StatusMixin
from specials.registry import register_special
from statuses import HideStatus

logger = logging.getLogger(__name__)


@register_special(
    "hide",
    name="Ukrycie",
    aliases=["hide", "ukrycie"],
    description="Bohater nakłada na siebie status hide.",
)
def hide_ability(hero, ctx) -> bool:
    """Nadaj status 'hide' aktywnemu bohaterowi."""
    try:
        if hasattr(hero, "add_status"):
            added = hero.add_status(HideStatus())  # type: ignore[attr-defined]
            if not added:
                logger.info("Bohater już ma status hide.")
        else:
            statuses = getattr(hero, "statuses", None)
            if isinstance(statuses, list):
                if "hide" not in statuses:
                    statuses.append(HideStatus())
            else:
                hero.statuses = [HideStatus()]  # type: ignore[attr-defined]
    except Exception:
        logger.warning("Nie mogę ustawić statusu hide na %s", hero)
        return False

    logger.info("Zdolność: %s otrzymuje status hide.", getattr(hero, "name", "Bohater"))
    try:
        ctx.game.ui_log(f"{getattr(hero, 'name', 'Bohater')} ukrywa się.")
    except Exception:
        pass
    return True
