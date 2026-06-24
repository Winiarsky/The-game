from __future__ import annotations

from statuses.base import Status

TITAN_SLINGER_DESCRIPTION = (
    "Fluff: Niziolki wyspecjalizowane w procach ucza sie wykorzystywac rozped i slabiej chronione miejsca wielkich przeciwnikow.\n"
    "Mechanika:\n"
    "- Kiedy: Gdy trafisz slingiem lub halfling sling staff Large albo wieksze stworzenie.\n"
    "- Efekt:\n"
    "  - Kosc obrazen broni rosnie o 1 krok.\n"
    "  - Warunki feata sa juz zapisane w danych runtime: odpowiednia bron, cel Large+ i wzrost kosci o 1 stopien.\n"
    "  - Pelne automatyczne dopiecie bonusu do wszystkich eventow ataku slingiem jest jeszcze do domkniecia.\n"
    "  - Przykład: sling 1k6 trafiajacy ogra powinien liczyc obrazenia jak 1k8."
)


def TitanSlingerStatus() -> Status:
    """Feat: Titan Slinger."""
    return Status(
        id="titan_slinger",
        label="Titan Slinger",
        data={
            "ui_description": TITAN_SLINGER_DESCRIPTION,
            "titan_slinger_weapon_ids": ["sling", "halfling_sling_staff"],
            "titan_slinger_min_target_size": "large",
            "titan_slinger_damage_die_step_increase": 1,
        },
    )


TITAN_SLINGER_STATUS = TitanSlingerStatus()

__all__ = ["TitanSlingerStatus", "TITAN_SLINGER_STATUS", "TITAN_SLINGER_DESCRIPTION"]
