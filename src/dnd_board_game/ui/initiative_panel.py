"""Deterministic input state for the initiative dice panel."""

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class InitiativePanel:
    values: tuple[int, ...] = (10,)
    index: int = 0
    review: bool = False

    @property
    def enabled_slots(self) -> tuple[int, ...]:
        if self.review:
            return (28, 29)
        return (26, 27, 28, *((29,) if self.index > 0 else ()))

    def change(self, command: str, value: int | None = None) -> "InitiativePanel":
        if command not in {"minus", "plus", "accept", "back"}:
            raise ValueError("Nieznany przycisk panelu inicjatywy.")
        if command == "back":
            if self.review:
                return replace(self, review=False)
            return replace(self, index=max(0, self.index - 1))
        if self.review:
            raise ValueError("Najpierw wróć do poprawiania wyniku.")
        current = self.values[self.index] if value is None else value
        if (
            isinstance(current, bool)
            or not isinstance(current, int)
            or not 1 <= current <= 20
        ):
            raise ValueError("Wpisz naturalny wynik k20 od 1 do 20.")
        current = max(
            1, min(20, current + {"minus": -1, "plus": 1, "accept": 0}[command])
        )
        values = tuple(
            current if i == self.index else v for i, v in enumerate(self.values)
        )
        result = replace(self, values=values)
        if command == "accept":
            if self.index + 1 == len(values):
                return replace(result, review=True)
            return replace(result, index=self.index + 1)
        return result

    def as_payload(self) -> dict[str, object]:
        return {
            "values": list(self.values),
            "index": self.index,
            "review": self.review,
            "enabled_slots": list(self.enabled_slots),
        }
