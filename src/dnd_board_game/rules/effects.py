from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnd_board_game.world import Coordinate


class EffectSourceType(StrEnum):
    ACTION = "action"
    SPELL = "spell"
    ITEM = "item"
    SCENE = "scene"
    CONDITION = "condition"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EffectSource:
    source_type: EffectSourceType
    id: str
    label: str = ""

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Effect source id cannot be empty.")


class EffectDuration(StrEnum):
    UNTIL_TURN_START = "until_turn_start"
    UNTIL_TURN_END = "until_turn_end"
    UNTIL_ROUND_END = "until_round_end"
    UNTIL_NEXT_ATTACK = "until_next_attack"
    WHILE_AT_POSITION = "while_at_position"
    CONCENTRATION = "concentration"
    UNTIL_SHORT_REST = "until_short_rest"
    UNTIL_LONG_REST = "until_long_rest"
    UNTIL_ENCOUNTER_END = "until_encounter_end"
    UNTIL_SCENARIO_END = "until_scenario_end"
    PERMANENT = "permanent"


class EffectStackingPolicy(StrEnum):
    REPLACE = "replace"
    REFRESH = "refresh"
    STACK = "stack"


class EffectEventType(StrEnum):
    ATTACK_HIT = "attack_hit"
    DAMAGE_TAKEN = "damage_taken"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    ROUND_ENDED = "round_ended"
    ATTACK_RESOLVED = "attack_resolved"
    ACTOR_MOVED = "actor_moved"
    CONCENTRATION_ENDED = "concentration_ended"
    SHORT_REST_COMPLETED = "short_rest_completed"
    LONG_REST_COMPLETED = "long_rest_completed"
    ENCOUNTER_ENDED = "encounter_ended"
    SCENARIO_ENDED = "scenario_ended"
    EFFECT_CONSUMED = "effect_consumed"


@dataclass(frozen=True, slots=True)
class EffectEvent:
    event_type: EffectEventType
    actor_id: str | None = None
    target_actor_id: str | None = None
    position: Coordinate | None = None
    effect_id: str | None = None


@dataclass(frozen=True, slots=True)
class AdditionalEffectExpiration:
    duration: EffectDuration
    actor_id: str | None = None
    target_actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class ActiveEffect:
    """Serializable runtime effect with explicit source and lifecycle.

    The first fields intentionally preserve the historical combat-effect
    constructor. Existing combat actions can therefore migrate to the shared
    lifecycle without changing their transport contract in one broad rewrite.
    """

    id: str
    actor_id: str
    kind: str
    label: str
    object_id: str
    value: int
    anchor_position: Coordinate | None = None
    base_ac: int | None = None
    source_actor_id: str | None = None
    target_actor_id: str | None = None
    source: EffectSource | None = None
    duration: EffectDuration | None = None
    stacking: EffectStackingPolicy = EffectStackingPolicy.REPLACE
    stacking_key: str = ""
    expiration_actor_id: str | None = None
    additional_expirations: tuple[AdditionalEffectExpiration, ...] = ()
    spell_level: int | None = None
    radius_feet: int = 0
    die_sides: int = 0
    modifier: int = 0
    uses_maximum: int = 0
    remaining_rounds: int | None = None
    excluded_positions: tuple[Coordinate, ...] = ()

    def __post_init__(self) -> None:
        duration_was_explicit = self.duration is not None
        if not self.id.strip():
            raise ValueError("Active effect id cannot be empty.")
        if not self.actor_id.strip():
            raise ValueError("Active effect actor_id cannot be empty.")
        if not self.kind.strip():
            raise ValueError("Active effect kind cannot be empty.")
        if self.spell_level is not None and self.spell_level < 0:
            raise ValueError("Active effect spell level cannot be negative.")
        if self.radius_feet < 0 or self.radius_feet % 5 != 0:
            raise ValueError("Active effect radius must be a non-negative multiple of 5 feet.")
        if self.die_sides < 0 or self.uses_maximum < 0:
            raise ValueError("Active effect dice and use limits cannot be negative.")
        if self.remaining_rounds is not None and self.remaining_rounds < 1:
            raise ValueError("Active effect remaining rounds must be positive.")
        if self.source is None:
            object.__setattr__(self, "source", _legacy_effect_source(self))
        if self.duration is None:
            object.__setattr__(self, "duration", _legacy_effect_duration(self.kind))
        if not self.stacking_key:
            object.__setattr__(self, "stacking_key", f"{self.actor_id}:{self.kind}")
        if self.expiration_actor_id is None:
            object.__setattr__(self, "expiration_actor_id", self.actor_id)
        if not self.additional_expirations and self.kind == "help_attack_advantage":
            object.__setattr__(
                self,
                "additional_expirations",
                (
                    AdditionalEffectExpiration(
                        EffectDuration.UNTIL_TURN_START,
                        actor_id=self.source_actor_id,
                    ),
                    AdditionalEffectExpiration(EffectDuration.UNTIL_ENCOUNTER_END),
                ),
            )
        elif not self.additional_expirations and self.kind in {
            "grant_ac_bonus_until_move",
            "grant_attack_bonus_while_on_object",
            "grant_next_attack_penalty",
            "dodge_until_next_turn",
            "disengage_until_turn_end",
            "ready_attack",
            "strength_potion",
        }:
            object.__setattr__(
                self,
                "additional_expirations",
                (AdditionalEffectExpiration(EffectDuration.UNTIL_ENCOUNTER_END),),
            )
        if duration_was_explicit and self.duration == EffectDuration.WHILE_AT_POSITION and self.anchor_position is None:
            raise ValueError("Position-bound effects require anchor_position.")

    def as_payload(self) -> dict[str, object]:
        assert self.source is not None
        assert self.duration is not None
        payload: dict[str, object] = {
            "id": self.id,
            "actor_id": self.actor_id,
            "kind": self.kind,
            "label": self.label,
            "object_id": self.object_id,
            "value": self.value,
            "value_label": effect_value_label(self),
            "expires": effect_expiration_label(self),
            "summary": effect_summary_label(self),
            "source": {
                "type": self.source.source_type.value,
                "id": self.source.id,
                "label": self.source.label,
            },
            "duration": self.duration.value,
            "stacking": self.stacking.value,
            "stacking_key": self.stacking_key,
            "additional_expirations": [
                {
                    "duration": expiration.duration.value,
                    "actor_id": expiration.actor_id,
                    "target_actor_id": expiration.target_actor_id,
                }
                for expiration in self.additional_expirations
            ],
            "spell_level": self.spell_level,
            "radius_feet": self.radius_feet,
            "die_sides": self.die_sides,
            "modifier": self.modifier,
            "uses_maximum": self.uses_maximum,
            "remaining_rounds": self.remaining_rounds,
            "excluded_positions": [
                [position.col, position.row]
                for position in self.excluded_positions
            ],
        }
        if self.anchor_position is not None:
            payload["anchor_position"] = [self.anchor_position.col, self.anchor_position.row]
        if self.base_ac is not None:
            payload["base_ac"] = self.base_ac
        if self.source_actor_id is not None:
            payload["source_actor_id"] = self.source_actor_id
        if self.target_actor_id is not None:
            payload["target_actor_id"] = self.target_actor_id
        return payload


@dataclass(frozen=True, slots=True)
class EffectApplicationResult:
    active_effects: tuple[ActiveEffect, ...]
    applied_effect: ActiveEffect
    replaced_effects: tuple[ActiveEffect, ...] = ()
    refreshed: bool = False


@dataclass(frozen=True, slots=True)
class EffectExpirationResult:
    active_effects: tuple[ActiveEffect, ...]
    expired_effects: tuple[ActiveEffect, ...]
    event: EffectEvent


def apply_active_effect(
    active_effects: tuple[ActiveEffect, ...],
    effect: ActiveEffect,
) -> EffectApplicationResult:
    if any(current.id == effect.id for current in active_effects) and effect.stacking == EffectStackingPolicy.STACK:
        raise ValueError(f"Active effect id already exists: {effect.id}.")
    if effect.stacking == EffectStackingPolicy.STACK:
        return EffectApplicationResult(active_effects + (effect,), effect)
    replaced = tuple(
        current
        for current in active_effects
        if current.stacking_key == effect.stacking_key
    )
    remaining = tuple(
        current
        for current in active_effects
        if current.stacking_key != effect.stacking_key
    )
    return EffectApplicationResult(
        remaining + (effect,),
        effect,
        replaced,
        refreshed=effect.stacking == EffectStackingPolicy.REFRESH and bool(replaced),
    )


def expire_active_effects(
    active_effects: tuple[ActiveEffect, ...],
    event: EffectEvent,
) -> EffectExpirationResult:
    expired = tuple(effect for effect in active_effects if _expires_on(effect, event))
    expired_ids = {effect.id for effect in expired}
    remaining = tuple(
        replace(effect, remaining_rounds=effect.remaining_rounds - 1)
        if (
            event.event_type == EffectEventType.ROUND_ENDED
            and effect.id not in expired_ids
            and effect.remaining_rounds is not None
        )
        else effect
        for effect in active_effects
        if effect.id not in expired_ids
    )
    return EffectExpirationResult(remaining, expired, event)


def effect_value_label(effect: ActiveEffect) -> str:
    if effect.kind == "grant_ac_bonus_until_move":
        return f"+{effect.value} AC"
    if effect.kind == "grant_attack_bonus_while_on_object":
        return f"{_format_signed(effect.value)} do ataku"
    if effect.kind == "grant_next_attack_penalty":
        return f"{_format_signed(effect.value)} do następnego ataku"
    if effect.kind == "dodge_until_next_turn":
        return "ataki przeciwko aktorowi mają utrudnienie"
    if effect.kind == "disengage_until_turn_end":
        return "bezpieczne odejście"
    if effect.kind == "help_attack_advantage":
        return "przewaga do ataku"
    if effect.kind == "ready_attack":
        return _ready_attack_trigger_label(effect)
    if effect.kind == "strength_potion":
        return f"{_format_signed(effect.value)} do ataku i obrażeń z Siły"
    if effect.kind == "concentration_attack_bonus":
        return f"{_format_signed(effect.value)} do ataku"
    if effect.kind == "bless_roll_bonus":
        return f"k{effect.value} do ataków i rzutów obronnych"
    if effect.kind == "bless_aura_source":
        return f"aura {effect.radius_feet} ft, k{effect.die_sides or effect.value} do ataków i save'ów"
    if effect.kind == "divine_care_aura_source":
        return f"aura {effect.radius_feet} ft, -{abs(effect.value)} do ataku i obrażeń wrogów"
    if effect.kind == "healing_grace_aura_source":
        return (
            f"aura {effect.radius_feet} ft, {effect.value}/{effect.uses_maximum} aktywacje, "
            f"+1k{effect.die_sides}+{effect.modifier} do leczenia"
        )
    if effect.kind == "divine_care_aura_penalty":
        return f"-{abs(effect.value)} do ataku i obrażeń"
    if effect.kind == "healing_grace_aura_member":
        return f"+1k{effect.die_sides}+{effect.modifier} do następnego leczenia w aurze"
    if effect.kind == "spell_ac_bonus":
        return f"{_format_signed(effect.value)} AC"
    if effect.kind in {"garran_defensive_stance_ac", "garran_shield_wall_member"}:
        return f"{_format_signed(effect.value)} KP"
    if effect.kind == "garran_shield_wall_source":
        return f"aura {effect.radius_feet} ft, +{effect.value} KP sojusznikom"
    if effect.kind == "garran_rally_advantage":
        return "przewaga na pierwszy test k20"
    if effect.kind == "garran_guard_companion":
        return "następny pojedynczy wrogi efekt trafia Garrana"
    if effect.kind == "garran_command_half_movement":
        return "połowa ruchu"
    if effect.kind == "garran_command_no_movement":
        return "brak dobrowolnego ruchu"
    return _format_signed(effect.value)


def effect_expiration_label(effect: ActiveEffect) -> str:
    assert effect.duration is not None
    legacy_labels = {
        "grant_ac_bonus_until_move": "znika po ruchu z pola",
        "grant_attack_bonus_while_on_object": "znika po zejściu z obiektu",
        "grant_next_attack_penalty": "znika po następnym ataku",
        "dodge_until_next_turn": "znika na początku następnej tury aktora",
        "disengage_until_turn_end": "znika na końcu tury",
        "help_attack_advantage": "znika po ataku albo na początku następnej tury pomagającego",
        "ready_attack": "znika po użyciu reakcji albo na początku następnej tury aktora",
        "strength_potion": "znika na początku następnej tury aktora",
        "concentration_attack_bonus": "znika po utracie koncentracji albo rzuceniu nowego czaru koncentracyjnego",
        "bless_roll_bonus": "znika po utracie koncentracji albo rzuceniu nowego czaru koncentracyjnego",
        "spell_ac_bonus": "znika na początku następnej tury chronionego aktora",
    }
    if effect.remaining_rounds is not None:
        suffix = (
            "runda"
            if effect.remaining_rounds == 1
            else "rundy"
            if 2 <= effect.remaining_rounds <= 4
            else "rund"
        )
        return f"pozostało {effect.remaining_rounds} {suffix} albo do utraty koncentracji"
    if effect.kind in legacy_labels:
        return legacy_labels[effect.kind]
    labels = {
        EffectDuration.UNTIL_TURN_START: "znika na początku następnej właściwej tury",
        EffectDuration.UNTIL_TURN_END: "znika na końcu właściwej tury",
        EffectDuration.UNTIL_ROUND_END: "znika na końcu rundy",
        EffectDuration.UNTIL_NEXT_ATTACK: "znika po następnym właściwym ataku",
        EffectDuration.WHILE_AT_POSITION: "znika po opuszczeniu wskazanego pola",
        EffectDuration.CONCENTRATION: "znika po zakończeniu koncentracji",
        EffectDuration.UNTIL_SHORT_REST: "znika po short reście",
        EffectDuration.UNTIL_LONG_REST: "znika po long reście",
        EffectDuration.UNTIL_ENCOUNTER_END: "znika po zakończeniu encountera",
        EffectDuration.UNTIL_SCENARIO_END: "znika po zakończeniu scenariusza",
        EffectDuration.PERMANENT: "nie wygasa automatycznie",
    }
    return labels[effect.duration]


def effect_summary_label(effect: ActiveEffect) -> str:
    assert effect.source is not None
    source = effect.source.label or effect.source.id
    return (
        f"{effect.label} | {effect_value_label(effect)} | "
        f"{effect_expiration_label(effect)} | źródło: {source}"
    )


def _expires_on(effect: ActiveEffect, event: EffectEvent) -> bool:
    assert effect.duration is not None
    if event.event_type == EffectEventType.EFFECT_CONSUMED:
        return bool(event.effect_id) and effect.id == event.effect_id
    if (
        event.event_type == EffectEventType.ROUND_ENDED
        and effect.remaining_rounds is not None
        and effect.remaining_rounds <= 1
    ):
        return True
    if (
        effect.kind == "guiding_bolt_mark"
        and event.event_type == EffectEventType.ATTACK_RESOLVED
        and event.target_actor_id == effect.actor_id
    ):
        return True
    if event.event_type == EffectEventType.SCENARIO_ENDED:
        return effect.duration != EffectDuration.PERMANENT or any(
            expiration.duration != EffectDuration.PERMANENT
            for expiration in effect.additional_expirations
        )
    if _duration_expires(
        effect,
        effect.duration,
        effect.expiration_actor_id,
        effect.target_actor_id,
        event,
    ):
        return True
    return any(
        _duration_expires(
            effect,
            expiration.duration,
            expiration.actor_id,
            expiration.target_actor_id,
            event,
        )
        for expiration in effect.additional_expirations
    )


def _duration_expires(
    effect: ActiveEffect,
    duration: EffectDuration,
    actor_id: str | None,
    target_actor_id: str | None,
    event: EffectEvent,
) -> bool:
    if duration == EffectDuration.PERMANENT:
        return False
    if event.event_type == EffectEventType.LONG_REST_COMPLETED:
        return duration != EffectDuration.PERMANENT
    if event.event_type == EffectEventType.SHORT_REST_COMPLETED:
        return duration == EffectDuration.UNTIL_SHORT_REST
    if event.event_type == EffectEventType.ENCOUNTER_ENDED:
        return duration == EffectDuration.UNTIL_ENCOUNTER_END
    if event.event_type == EffectEventType.CONCENTRATION_ENDED:
        return (
            duration == EffectDuration.CONCENTRATION
            and effect.source_actor_id == event.actor_id
        )
    if event.event_type == EffectEventType.TURN_START:
        return (
            duration == EffectDuration.UNTIL_TURN_START
            and actor_id == event.actor_id
        )
    if event.event_type == EffectEventType.TURN_END:
        return (
            duration == EffectDuration.UNTIL_TURN_END
            and actor_id == event.actor_id
        )
    if event.event_type == EffectEventType.ROUND_ENDED:
        return duration == EffectDuration.UNTIL_ROUND_END
    if event.event_type == EffectEventType.ATTACK_RESOLVED:
        target_matches = (
            target_actor_id is None
            or (
                event.target_actor_id is not None
                and target_actor_id == event.target_actor_id
            )
        )
        return (
            duration == EffectDuration.UNTIL_NEXT_ATTACK
            and actor_id == event.actor_id
            and target_matches
        )
    if event.event_type == EffectEventType.ACTOR_MOVED:
        return (
            duration == EffectDuration.WHILE_AT_POSITION
            and actor_id == event.actor_id
            and event.position != effect.anchor_position
        )
    return False


def _legacy_effect_duration(kind: str) -> EffectDuration:
    return {
        "grant_ac_bonus_until_move": EffectDuration.WHILE_AT_POSITION,
        "grant_attack_bonus_while_on_object": EffectDuration.WHILE_AT_POSITION,
        "grant_next_attack_penalty": EffectDuration.UNTIL_NEXT_ATTACK,
        "dodge_until_next_turn": EffectDuration.UNTIL_TURN_START,
        "disengage_until_turn_end": EffectDuration.UNTIL_TURN_END,
        "help_attack_advantage": EffectDuration.UNTIL_NEXT_ATTACK,
        "ready_attack": EffectDuration.UNTIL_TURN_START,
        "strength_potion": EffectDuration.UNTIL_TURN_START,
        "concentration_attack_bonus": EffectDuration.CONCENTRATION,
        "bless_roll_bonus": EffectDuration.CONCENTRATION,
    }.get(kind, EffectDuration.UNTIL_SCENARIO_END)


def _legacy_effect_source(effect: ActiveEffect) -> EffectSource:
    if effect.kind.startswith("concentration_"):
        source_type = EffectSourceType.SPELL
    elif effect.kind == "strength_potion":
        source_type = EffectSourceType.ITEM
    elif effect.object_id.startswith("combat_action:"):
        source_type = EffectSourceType.ACTION
    else:
        source_type = EffectSourceType.SCENE
    return EffectSource(source_type, effect.object_id or effect.kind, effect.label)


def _ready_attack_trigger_label(effect: ActiveEffect) -> str:
    labels = {
        "combat_action:ready:enemy_moves": "atak, gdy przeciwnik się poruszy",
        "combat_action:ready:enemy_attacks": "atak, gdy przeciwnik zaatakuje",
        "combat_action:ready:enemy_enters_reach": "atak, gdy przeciwnik wejdzie w zasięg",
    }
    return labels.get(effect.object_id, "przygotowany atak")


def _format_signed(value: int) -> str:
    return f"{value:+d}" if value else "0"
