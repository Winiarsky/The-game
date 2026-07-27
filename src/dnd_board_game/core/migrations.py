from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


Migration = Callable[[dict[str, Any]], dict[str, Any]]


class MigrationError(ValueError):
    """Raised when versioned data cannot be migrated deterministically."""


@dataclass(slots=True)
class MigrationRegistry:
    schema: str
    current_version: int
    minimum_version: int = 1
    _migrations: dict[int, Migration] = field(default_factory=dict)

    def register(self, from_version: int, migration: Migration) -> None:
        if from_version < self.minimum_version:
            raise ValueError("Migration source version is below the supported minimum.")
        if from_version >= self.current_version:
            raise ValueError("Migration source version must precede the current version.")
        if from_version in self._migrations:
            raise ValueError(
                f"Migration {self.schema} v{from_version}->v{from_version + 1} is already registered."
            )
        self._migrations[from_version] = migration

    def migrate(self, raw: object) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise MigrationError(f"{self.schema} payload must be an object.")
        data = dict(raw)
        if data.get("schema") != self.schema:
            raise MigrationError(f"Unknown schema: {data.get('schema')!r}.")
        version = data.get("schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise MigrationError(f"{self.schema}.schema_version must be an integer.")
        if version < self.minimum_version or version > self.current_version:
            raise MigrationError(
                f"Unsupported {self.schema} version: {version}; "
                f"supported range: {self.minimum_version}-{self.current_version}."
            )
        while version < self.current_version:
            migration = self._migrations.get(version)
            if migration is None:
                raise MigrationError(
                    f"Missing migration {self.schema} v{version}->v{version + 1}."
                )
            migrated = migration(dict(data))
            if not isinstance(migrated, dict):
                raise MigrationError(
                    f"Migration {self.schema} v{version}->v{version + 1} "
                    "did not return an object."
                )
            next_version = migrated.get("schema_version")
            if next_version != version + 1:
                raise MigrationError(
                    f"Migration {self.schema} v{version}->v{version + 1} "
                    f"returned version {next_version!r}."
                )
            if migrated.get("schema") != self.schema:
                raise MigrationError(
                    f"Migration {self.schema} v{version}->v{version + 1} "
                    "changed the schema id."
                )
            data = migrated
            version = next_version
        return data
