from __future__ import annotations

from statuses.base import Status

TIGER_STANCE_DESCRIPTION = (
    "Tiger Stance: atakujesz profilem Tiger Claw (1k8 S, agile, finesse). "
    "Na critical hit dochodzi 1k4 persistent bleed. Przy Speed co najmniej 20 ft możesz wykonać Step na 10 ft."
)


def TigerStanceStatus() -> Status:
    return Status(
        id="tiger_stance",
        label="Tiger Stance",
        data={
            "ui_description": TIGER_STANCE_DESCRIPTION,
            "ui_prompt": TIGER_STANCE_DESCRIPTION,
        },
    )


TIGER_STANCE_STATUS = TigerStanceStatus()

__all__ = ["TigerStanceStatus", "TIGER_STANCE_STATUS", "TIGER_STANCE_DESCRIPTION"]
