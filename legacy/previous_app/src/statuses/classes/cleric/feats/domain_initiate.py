from __future__ import annotations

from statuses.base import Status

DOMAIN_INITIATE_DESCRIPTION = (
    "Domain Initiate: wybierasz domene z listy deity i zyskujesz jej initial domain spell "
    "(focus spell). Koszt rzucenia: 1 Focus Point."
)


def DomainInitiateStatus() -> Status:
    return Status(
        id="domain_initiate",
        label="Domain Initiate",
        stacks=True,
        data={
            "ui_description": DOMAIN_INITIATE_DESCRIPTION,
            "ui_choice_kind": "cleric_domain_initiate",
            "selected_domain": None,
            "domain_spell": None,
            "set_actor_attrs": {"focus_point": 1},
        },
    )


DOMAIN_INITIATE_STATUS = DomainInitiateStatus()

__all__ = [
    "DOMAIN_INITIATE_DESCRIPTION",
    "DomainInitiateStatus",
    "DOMAIN_INITIATE_STATUS",
]
