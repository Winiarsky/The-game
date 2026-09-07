"""Author-directed setup ordering for the revised Hungry Shadows map."""

from __future__ import annotations

from dnd_board_game.combat import EnvironmentSetupEntry, SetupStep, SetupStepKind


def battle_briefing(
    environment: tuple[EnvironmentSetupEntry, ...], *, solo: bool = False
) -> tuple[str, ...]:
    entry_id = "v6_battle_briefing_solo" if solo else "v6_battle_briefing"
    return next((entry.mechanics for entry in environment if entry.id == entry_id), ())


def order_battle_setup(
    steps: tuple[SetupStep, ...],
    environment: tuple[EnvironmentSetupEntry, ...],
    *,
    solo: bool = False,
) -> tuple[SetupStep, ...]:
    """Terrain before formation; a final player briefing before initiative."""
    briefing = battle_briefing(environment, solo=solo)
    if not briefing:
        return steps
    entries = {entry.id: entry for entry in environment}
    terrain: list[SetupStep] = []
    for entry_id, label, color in (
        ("v6_blocking_setup", "Wrak i skarpa", (220, 70, 60)),
        ("v6_cover_setup", "Osłony kierunkowe", (240, 190, 70)),
        ("v6_difficult_setup", "Błoto i strumień", (120, 150, 210)),
    ):
        entry = entries[entry_id]
        terrain.append(
            SetupStep(
                kind=SetupStepKind.ENVIRONMENT,
                label=label,
                positions=entry.positions,
                color=color,
                message=f"Sprawdźcie na nadruku: {entry.name}. Znaczniki LED wskazują obiekty; ich pełny zasięg pokazuje obrys na mapie.",
                mechanics=entry.mechanics,
            )
        )
    actors = tuple(step for step in steps if step.kind == SetupStepKind.ACTORS)
    enemies = tuple(step for step in steps if step.kind == SetupStepKind.ENEMIES)
    return (
        steps[0],
        *terrain,
        *actors,
        *enemies,
        SetupStep(
            kind=SetupStepKind.ENVIRONMENT,
            label="Cel i zasady starcia",
            positions=(),
            color=(240, 190, 70),
            message="Wybierzcie podejście do wraku. Po potwierdzeniu przejdziecie do przygotowania inicjatywy.",
            mechanics=briefing,
        ),
    )
