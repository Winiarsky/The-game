"""Podstawowe klasy dla nowego sterowania opartego o eventy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)
_MISSING = object()


def actor_state_fallback_key(actor) -> str:
    return f"actor:{getattr(actor, 'object_id', None) or getattr(actor, 'name', None) or id(actor)}"


def mapping_get_actor(mapping: dict[Any, Any], actor, default=None):
    if not isinstance(mapping, dict):
        return default
    try:
        return mapping.get(actor, default)
    except TypeError:
        return mapping.get(actor_state_fallback_key(actor), default)


def mapping_setdefault_actor(mapping: dict[Any, Any], actor, default_factory=dict):
    if not isinstance(mapping, dict):
        return default_factory() if callable(default_factory) else default_factory

    try:
        value = mapping.get(actor, _MISSING)
    except TypeError:
        value = _MISSING
    if value is not _MISSING:
        return value

    fallback_key = actor_state_fallback_key(actor)
    value = mapping.get(fallback_key, _MISSING)
    if value is not _MISSING:
        return value

    value = default_factory() if callable(default_factory) else default_factory
    try:
        mapping[actor] = value
    except TypeError:
        mapping[fallback_key] = value
    return value


@dataclass
class EventContext:
    """Kontekst przekazywany do eventów."""

    game: Any
    actor: Any | None = None
    tags: list[str] | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def in_combat(self) -> bool:
        from states.combat import Combat  # lokalny import by uniknąć cykli

        return isinstance(getattr(self.game, "state", None), Combat)

    @property
    def in_exploration(self) -> bool:
        return not self.in_combat


@dataclass
class EventResult:
    """Standardowy wynik wykonania eventu."""

    success: bool = True
    consumed_action: bool = True
    actions_spent: int | None = None
    message: str | None = None
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def cancelled(cls, *, message: str | None = None) -> "EventResult":
        return cls(success=False, consumed_action=False, message=message)

    @classmethod
    def noop(cls, *, message: str | None = None) -> "EventResult":
        return cls(success=True, consumed_action=False, message=message)


class GameEvent:
    """Bazowa klasa wszystkich eventów-akcji."""

    # unikalna nazwa karty/eventu
    name: str = "event"
    # domyślne tagi (mogą być rozszerzane przez ctx.tags)
    default_tags: list[str] | None = None
    # dostępność w fazach
    available_in_combat: bool = True
    available_in_exploration: bool = True
    # czy zużywa slot akcji bohatera
    consumes_action: bool = True

    def pre(self, ctx: EventContext) -> EventResult:
        """Hook przed głównym wykonaniem. Zwróć EventResult.cancelled by przerwać."""
        return EventResult()

    def execute(self, ctx: EventContext) -> EventResult:
        """Główna logika eventu."""
        raise NotImplementedError

    def post(self, ctx: EventContext, result: EventResult) -> None:
        """Hook po wykonaniu (nie powinien zmieniać consumed_action)."""
        return None

    # --- helpers ---
    def _effective_tags(self, ctx: EventContext) -> list[str]:
        tags: list[str] = []
        if self.default_tags:
            tags.extend(self.default_tags)
        if ctx.tags:
            tags.extend([t for t in ctx.tags if t not in tags])
        return tags

    def run(self, ctx: EventContext) -> EventResult:
        """Wykonaj pełny lifecycle: pre -> execute -> post."""
        actor = ctx.actor
        if actor is not None:
            try:
                from statuses import action_block_reason

                reason = action_block_reason(
                    actor,
                    action_tags=self._effective_tags(ctx),
                    action_name=getattr(self, "name", None),
                    target=(ctx.metadata or {}).get("target") if isinstance(ctx.metadata, dict) else None,
                )
                if reason:
                    return EventResult.cancelled(message=str(reason))
            except Exception:
                pass
        if actor is not None and "move" in self._effective_tags(ctx):
            has_status = getattr(actor, "has_status", None)
            if callable(has_status):
                try:
                    if has_status("immobilized"):
                        return EventResult.cancelled(message="Nie możesz się ruszyć (immobilized).")
                except Exception:
                    pass
            else:
                for item in getattr(actor, "statuses", []) or []:
                    if getattr(item, "id", None) == "immobilized" or item == "immobilized":
                        return EventResult.cancelled(message="Nie możesz się ruszyć (immobilized).")
        if actor is not None:
            tags = self._effective_tags(ctx)
            if "manipulate" in tags or "manipulation" in tags:
                has_status = getattr(actor, "has_status", None)
                allow_rage_manipulate = False
                if callable(has_status):
                    try:
                        allow_rage_manipulate = has_status("moment_of_clarity")
                    except Exception:
                        allow_rage_manipulate = False
                    try:
                        if has_status("rage"):
                            if (
                                not allow_rage_manipulate
                                and "shove" not in tags
                                and "grapple" not in tags
                                and getattr(self, "name", "") not in ("shove", "grapple")
                            ):
                                return EventResult.cancelled(message="Rage: nie możesz używać akcji z tagiem manipulate.")
                    except Exception:
                        pass
                else:
                    has_rage = False
                    for item in getattr(actor, "statuses", []) or []:
                        sid = getattr(item, "id", None)
                        if sid == "moment_of_clarity" or item == "moment_of_clarity":
                            allow_rage_manipulate = True
                        if sid == "rage" or item == "rage":
                            has_rage = True
                    if has_rage:
                        if (
                            not allow_rage_manipulate
                            and "shove" not in tags
                            and "grapple" not in tags
                            and getattr(self, "name", "") not in ("shove", "grapple")
                        ):
                            return EventResult.cancelled(message="Rage: nie możesz używać akcji z tagiem manipulate.")
        pre_res = self.pre(ctx)
        if not pre_res.success:
            return pre_res
        try:
            result = self.execute(ctx)
        except Exception as exc:  # pragma: no cover - log dla stabilności
            logger.error("Event %s failed: %s", self.name, exc, exc_info=True)
            return EventResult(success=False, consumed_action=False, message=str(exc))
        try:
            self.post(ctx, result)
        except Exception:  # pragma: no cover - nie blokuj dalszych akcji
            logger.debug("Post hook failed for %s", self.name, exc_info=True)
        return result


class ActionCostEvent(GameEvent):
    """Bazowy event z kontrolą kosztu akcji (1-3) w walce."""

    actions_cost: int = 1
    consumes_action: bool = True

    def _actions_remaining(self, ctx: EventContext, actor) -> int | None:
        combat_state = getattr(ctx.game, "state", None)
        if combat_state is None:
            return None
        try:
            limit = getattr(combat_state, "ACTION_LIMIT", None)
            used = mapping_get_actor(getattr(combat_state, "actions_used", {}), actor, 0)
            if limit is None:
                return None
            return int(limit) - int(used)
        except Exception:
            return None

    def _trait_usage_payload(self, ctx: EventContext, actor) -> dict[str, Any] | None:
        if not ctx.in_combat or actor is None:
            return None
        combat_state = getattr(ctx.game, "state", None)
        attack_state = getattr(combat_state, "attack_state", None)
        if not isinstance(attack_state, dict):
            return None
        payload = mapping_get_actor(attack_state, actor)
        if isinstance(payload, dict):
            return payload
        return mapping_setdefault_actor(attack_state, actor, dict)

    def pre(self, ctx: EventContext) -> EventResult:
        if not self.consumes_action:
            return EventResult()
        if not ctx.in_combat:
            return EventResult()
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak aktora do wykonania akcji.")
        try:
            cost = int(self.actions_cost)
        except Exception:
            cost = 1
        cost = min(3, max(1, cost))
        self.actions_cost = cost
        remaining = self._actions_remaining(ctx, actor)
        if remaining is not None and cost > remaining:
            msg = f"Za mało akcji: potrzebne {cost}, dostępne {remaining}."
            return EventResult.cancelled(message=msg)

        tags = set(self._effective_tags(ctx))
        payload = self._trait_usage_payload(ctx, actor)
        if payload is not None:
            used_flourish = bool(payload.get("used_flourish_action", False))
            used_attack = bool(payload.get("used_attack_action", False))
            try:
                used_attack = used_attack or int(payload.get("attacks_this_turn", 0) or 0) > 0
            except Exception:
                pass

            if "flourish" in tags and used_flourish:
                return EventResult.cancelled(
                    message="Flourish: możesz użyć tylko jednej akcji z tym traitem na turę."
                )
            if "open" in tags and used_attack:
                return EventResult.cancelled(
                    message="Open: tej akcji nie można użyć po wykonaniu ataku w tej turze."
                )
        return EventResult()


class ThreeActionEvent(ActionCostEvent):
    """Wygodny bazowy event 3-akcyjny."""

    actions_cost: int = 3
