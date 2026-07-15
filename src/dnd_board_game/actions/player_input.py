"""Typed slash-command hints for free-form exploration declarations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PlayerIntentHint(StrEnum):
    QUESTION = "question"
    SEARCH = "search"
    BUILD = "build"
    USE = "use"
    TAKE = "take"
    ACTION = "action"
    HELP = "help"


@dataclass(frozen=True, slots=True)
class SlashCommand:
    name: str
    label: str
    description: str
    intent: PlayerIntentHint
    placeholder: str

    def as_payload(self) -> dict[str, str]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "intent": self.intent.value,
            "placeholder": self.placeholder,
        }


SLASH_COMMANDS: tuple[SlashCommand, ...] = (
    SlashCommand("pytaj", "Zapytaj MG", "Zapytaj o scenę, możliwe podejście albo poproś o podpowiedź.", PlayerIntentHint.QUESTION, "O co pytacie MG?"),
    SlashCommand("szukaj", "Przeszukaj otoczenie", "Sprawdź jawne otoczenie albo zaproponuj dokładniejsze poszukiwanie.", PlayerIntentHint.SEARCH, "Czego lub gdzie szukacie?"),
    SlashCommand("zbuduj", "Zbuduj konstrukcję", "Zaproponuj konstrukcję z dostępnych materiałów.", PlayerIntentHint.BUILD, "Co chcecie zbudować i z czego?"),
    SlashCommand("uzyj", "Użyj elementu", "Wskaż istniejący lub znaleziony element i opisz jego zastosowanie.", PlayerIntentHint.USE, "Czego i w jaki sposób używacie?"),
    SlashCommand("wez", "Weź element", "Przenieś konkretny przenośny element ze sceny.", PlayerIntentHint.TAKE, "Co chcecie zabrać?"),
    SlashCommand("akcja", "Wykonaj działanie", "Jawnie zadeklaruj próbę zmiany sytuacji.", PlayerIntentHint.ACTION, "Co dokładnie robicie?"),
    SlashCommand("pomoc", "Pokaż komendy", "Wyświetl krótką listę dostępnych komend.", PlayerIntentHint.HELP, ""),
)


@dataclass(frozen=True, slots=True)
class ParsedPlayerInput:
    raw_text: str
    content: str
    command: SlashCommand | None = None

    @property
    def intent_hint(self) -> PlayerIntentHint | None:
        return self.command.intent if self.command is not None else None


def parse_player_input(raw_text: str) -> ParsedPlayerInput:
    """Parse an optional leading slash command without interpreting the action itself."""

    text = raw_text.strip()
    if not text.startswith("/"):
        return ParsedPlayerInput(raw_text=text, content=text)
    command_token, separator, remainder = text[1:].partition(" ")
    normalized_command = command_token.strip().lower()
    command = next((candidate for candidate in SLASH_COMMANDS if candidate.name == normalized_command), None)
    if command is None:
        raise ValueError(
            f"Nieznana komenda /{normalized_command}. Wpisz /pomoc, aby zobaczyć dostępne komendy."
        )
    content = remainder.strip() if separator else ""
    if command.intent != PlayerIntentHint.HELP and not content:
        raise ValueError(f"Po komendzie /{command.name} dopisz treść wiadomości.")
    return ParsedPlayerInput(raw_text=text, content=content, command=command)


def slash_commands_payload() -> list[dict[str, str]]:
    return [command.as_payload() for command in SLASH_COMMANDS]


def slash_help_message() -> str:
    return "\n".join(
        f"/{command.name} — {command.description}"
        for command in SLASH_COMMANDS
        if command.intent != PlayerIntentHint.HELP
    )
