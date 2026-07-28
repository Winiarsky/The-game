"""Install the curated one-character-per-class starter roster."""

from __future__ import annotations

from pathlib import Path
from shutil import copyfile

from dnd_board_game.character_creation import (
    CharacterRoster,
    build_character,
    default_character_drafts,
    load_character_catalog,
    load_character_resources,
    validate_character_draft,
)


def install_default_roster(
    character_dir: str | Path = "data/characters",
    portrait_source_dir: str | Path = "assets/character_portraits/default_roster",
) -> tuple[int, int]:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    character_root = Path(character_dir)
    portrait_source_root = Path(portrait_source_dir)
    portrait_target_root = character_root / "portraits" / "default_roster"
    roster = CharacterRoster(character_root, catalog, resources)
    installed = 0
    skipped = 0
    for draft in default_character_drafts():
        portrait_name = Path(draft.portrait).name
        portrait_source = portrait_source_root / portrait_name
        if not portrait_source.is_file():
            raise ValueError(f"Brak źródłowego portretu: {portrait_source}")
        portrait_target = portrait_target_root / portrait_name
        if not portrait_target.exists():
            portrait_target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(portrait_source, portrait_target)
        validation = validate_character_draft(draft, catalog)
        if not validation.valid:
            details = "; ".join(issue.message for issue in validation.issues)
            raise ValueError(f"{draft.id}: {details}")
        target = character_root / f"{draft.id}.character.json"
        if target.exists():
            skipped += 1
            continue
        roster.save(build_character(draft, catalog, resources))
        installed += 1
    return installed, skipped


def main() -> int:
    installed, skipped = install_default_roster()
    print(f"Zainstalowano: {installed}; pominięto istniejące: {skipped}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
