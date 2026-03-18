from __future__ import annotations

from statuses.base import Status
from statuses.classes.cleric.cleric import (
    CLERIC_DEITY_OPTIONS,
    CLERIC_DOMAIN_ADVANCED_SPELLS,
    CLERIC_DOMAIN_DESCRIPTIONS,
    CLERIC_DOMAIN_INITIAL_SPELLS,
)

DEITYS_DOMAIN_DESCRIPTION = (
    "Domena bostwa: wybierasz jedna z domen swojego bostwa i zyskujesz jej poczatkowy czar domenowy "
    "jako czar oddania (zaklecie Focus)."
)


def DeitysDomainStatus() -> Status:
    domain_choices_by_deity: dict[str, list[str]] = {}
    for deity_id, payload in dict(CLERIC_DEITY_OPTIONS or {}).items():
        data = dict(payload or {})
        choices = [str(item).strip().lower() for item in list(data.get("domain_choices") or []) if str(item).strip()]
        if choices:
            domain_choices_by_deity[str(deity_id).strip().lower()] = choices
    if "custom" not in domain_choices_by_deity:
        domain_choices_by_deity["custom"] = ["custom_domain_a", "custom_domain_b", "custom_domain_c"]

    return Status(
        id="deitys_domain",
        label="Domena bostwa",
        data={
            "ui_description": DEITYS_DOMAIN_DESCRIPTION,
            "ui_prompt": DEITYS_DOMAIN_DESCRIPTION,
            "ui_choice_kind": "champion_deitys_domain",
            "domain_choices_by_deity": domain_choices_by_deity,
            "domain_spell_placeholders": dict(CLERIC_DOMAIN_INITIAL_SPELLS),
            "domain_descriptions": dict(CLERIC_DOMAIN_DESCRIPTIONS),
            "domain_advanced_spell_placeholders": dict(CLERIC_DOMAIN_ADVANCED_SPELLS),
            "selected_domain": None,
            "domain_spell": None,
        },
    )


DEITYS_DOMAIN_STATUS = DeitysDomainStatus()

__all__ = [
    "DEITYS_DOMAIN_DESCRIPTION",
    "DeitysDomainStatus",
    "DEITYS_DOMAIN_STATUS",
]
