from __future__ import annotations

from statuses.base import Status

TWIN_FEINT_DESCRIPTION = (
    "Fluff: Twin Feint to sekwencja dwoch szybkich ciosow, w ktorej pierwszy atak odwraca uwage celu, a drugi wykorzystuje otwarta garde.\n"
    "Mechanika:\n"
    "- Kiedy: Gdy masz dwie bronie melee 1H i chcesz nacisnac jednym celem cala sekwencje.\n"
    "- Efekt:\n"
    "  - Koszt: 2 akcje.\n"
    "  - Wykonujesz 2 melee Strikes dwiema broniami przeciw temu samemu celowi.\n"
    "  - Drugi atak dostaje wymuszone off-guard zrodla Twin Feint.\n"
    "  - To bardzo dobrze wspiera Sneak Attack na drugim trafieniu.\n"
    "  - Przyklad: walczysz dwoma daggerami, pierwszy cios tylko naciska cel, a drugi korzysta z off-guard i latwiej wbija sneak damage."
)


def TwinFeintStatus() -> Status:
    return Status(
        id="twin_feint",
        label="Twin Feint",
        data={
            "ui_description": TWIN_FEINT_DESCRIPTION,
            "ui_prompt": TWIN_FEINT_DESCRIPTION,
            "allowed_classes": ["rogue"],
        },
    )


TWIN_FEINT_STATUS = TwinFeintStatus()

__all__ = ["TWIN_FEINT_DESCRIPTION", "TwinFeintStatus", "TWIN_FEINT_STATUS"]
