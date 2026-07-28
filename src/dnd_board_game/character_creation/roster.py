"""File-backed storage for versioned saved-character documents."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import json
from pathlib import Path
import re
from uuid import uuid4

from .models import CharacterBuildResources, CharacterCatalog, CreatedCharacter
from .serialization import character_record_payload, created_character_from_payload


_CHARACTER_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_RECORD_SUFFIX = ".character.json"


@dataclass(frozen=True, slots=True)
class CharacterRosterError:
    path: Path
    message: str


@dataclass(frozen=True, slots=True)
class CharacterRosterScan:
    characters: tuple[CreatedCharacter, ...]
    errors: tuple[CharacterRosterError, ...] = ()


class CharacterRoster:
    """Stores source choices and rebuilds derived actors while reading."""

    def __init__(
        self,
        root: str | Path,
        catalog: CharacterCatalog,
        resources: CharacterBuildResources,
    ) -> None:
        self.root = Path(root)
        self.catalog = catalog
        self.resources = resources

    def scan(self) -> CharacterRosterScan:
        if not self.root.exists():
            return CharacterRosterScan(())
        characters: list[CreatedCharacter] = []
        errors: list[CharacterRosterError] = []
        for path in sorted(self.root.glob(f"*{_RECORD_SUFFIX}")):
            try:
                characters.append(self._load_path(path))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(CharacterRosterError(path, str(exc)))
        characters.sort(key=lambda item: (item.actor.name.casefold(), str(item.actor.id)))
        return CharacterRosterScan(tuple(characters), tuple(errors))

    def load(self, character_id: str) -> CreatedCharacter:
        path = self._record_path(character_id)
        if not path.is_file():
            raise ValueError("Nie znaleziono zapisanej postaci.")
        return self._load_path(path)

    def save(
        self,
        character: CreatedCharacter,
        *,
        overwrite: bool = False,
    ) -> Path:
        character_id = str(character.actor.id)
        path = self._record_path(character_id)
        if path.exists() and not overwrite:
            raise ValueError("Postać o takim id już istnieje. Wybierz inne id.")
        payload = character_record_payload(character)
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / f".{character_id}.{uuid4().hex}.tmp"
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return path

    def delete(self, character_id: str) -> Path:
        path = self._record_path(character_id)
        if not path.is_file():
            raise ValueError("Nie znaleziono zapisanej postaci.")
        trash = self.root / ".trash"
        trash.mkdir(parents=True, exist_ok=True)
        deleted_path = trash / f"{character_id}.{uuid4().hex}{_RECORD_SUFFIX}"
        path.replace(deleted_path)
        return deleted_path

    def update_experience(
        self,
        character_id: str,
        experience_points: int,
    ) -> CreatedCharacter:
        """Atomically persist runtime XP without copying mutable encounter state."""
        if experience_points < 0:
            raise ValueError("Punkty doświadczenia nie mogą być ujemne.")
        character = self.load(character_id)
        updated = replace(
            character,
            actor=replace(
                character.actor,
                experience_points=experience_points,
            ),
        )
        self.save(updated, overwrite=True)
        return updated

    def _load_path(self, path: Path) -> CreatedCharacter:
        raw = json.loads(path.read_text(encoding="utf-8"))
        character = created_character_from_payload(raw, self.catalog, self.resources)
        expected_id = path.name[: -len(_RECORD_SUFFIX)]
        if str(character.actor.id) != expected_id:
            raise ValueError("Id postaci nie zgadza się z nazwą pliku.")
        return character

    def _record_path(self, character_id: str) -> Path:
        normalized = character_id.strip()
        if not _CHARACTER_ID.fullmatch(normalized):
            raise ValueError("Nieprawidłowe id postaci.")
        return self.root / f"{normalized}{_RECORD_SUFFIX}"
