from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class PreparableSpell:
    id: str
    label: str
    level: int

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Preparable spell id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Preparable spell label cannot be empty.")
        if self.level <= 0:
            raise ValueError("Only leveled spells can be prepared.")

    def as_payload(self, *, prepared: bool, always_prepared: bool) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "level": self.level,
            "prepared": prepared,
            "always_prepared": always_prepared,
        }


@dataclass(frozen=True, slots=True)
class SpellPreparationProfile:
    source_label: str
    preparation_limit: int
    available_spells: tuple[PreparableSpell, ...]
    prepared_spell_ids: tuple[str, ...] = ()
    always_prepared_spell_ids: tuple[str, ...] = ()
    confirmed: bool = False

    def __post_init__(self) -> None:
        if not self.source_label.strip():
            raise ValueError("Spell preparation source label cannot be empty.")
        if self.preparation_limit < 1:
            raise ValueError("Spell preparation limit must be positive.")
        available_ids = tuple(spell.id for spell in self.available_spells)
        if len(set(available_ids)) != len(available_ids):
            raise ValueError("Available preparation spells must be unique.")
        _validate_ids(self.prepared_spell_ids, available_ids, "Prepared")
        _validate_ids(self.always_prepared_spell_ids, available_ids, "Always prepared")
        if set(self.prepared_spell_ids).intersection(self.always_prepared_spell_ids):
            raise ValueError("Always prepared spells cannot also occupy preparation slots.")
        selectable_count = len(set(available_ids) - set(self.always_prepared_spell_ids))
        if self.preparation_limit > selectable_count:
            raise ValueError("Preparation limit exceeds the selectable spell count.")
        if len(self.prepared_spell_ids) > self.preparation_limit:
            raise ValueError("Prepared spell count exceeds the preparation limit.")

    def as_payload(self) -> dict[str, object]:
        prepared = set(self.prepared_spell_ids)
        always_prepared = set(self.always_prepared_spell_ids)
        return {
            "source_label": self.source_label,
            "preparation_limit": self.preparation_limit,
            "selected_count": len(self.prepared_spell_ids),
            "confirmed": self.confirmed,
            "spells": [
                spell.as_payload(
                    prepared=spell.id in prepared or spell.id in always_prepared,
                    always_prepared=spell.id in always_prepared,
                )
                for spell in self.available_spells
            ],
        }


def prepare_spells(
    profile: SpellPreparationProfile,
    spell_ids: tuple[str, ...],
) -> SpellPreparationProfile:
    normalized = tuple(dict.fromkeys(spell_id.strip() for spell_id in spell_ids if spell_id.strip()))
    if len(normalized) != len(spell_ids):
        raise ValueError("Prepared spell ids must be non-empty and unique.")
    _validate_ids(
        normalized,
        tuple(spell.id for spell in profile.available_spells),
        "Prepared",
    )
    if len(normalized) > profile.preparation_limit:
        raise ValueError("Prepared spell count exceeds the preparation limit.")
    if len(normalized) < profile.preparation_limit:
        raise ValueError(
            f"Exactly {profile.preparation_limit} spells must be prepared."
        )
    return replace(profile, prepared_spell_ids=normalized, confirmed=True)


def spell_is_prepared(
    profile: SpellPreparationProfile | None,
    spell_id: str,
    *,
    casting_kind: str,
    legacy_prepared: bool = True,
) -> bool:
    if casting_kind in {"none", "cantrip"}:
        return True
    if profile is None:
        return legacy_prepared
    return spell_id in profile.prepared_spell_ids or spell_id in profile.always_prepared_spell_ids


def _validate_ids(values: tuple[str, ...], available_ids: tuple[str, ...], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{label} spell ids must be unique.")
    unknown = set(values) - set(available_ids)
    if unknown:
        raise ValueError(f"{label} spells are not in the preparation pool: {', '.join(sorted(unknown))}.")
