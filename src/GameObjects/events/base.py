"""Podstawowe klasy dla nowego sterowania opartego o eventy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging

from prompt_copy import prompt_value

logger = logging.getLogger(__name__)
_MISSING = object()


def format_range_text(max_range_feet: int | None) -> str:
    if max_range_feet is None:
        return "bez limitu zasiegu"
    try:
        return f"w zasiegu {int(max_range_feet)} ft"
    except Exception:
        return "w dostepnym zasiegu"


def format_board_selection_message(
    subject: str,
    *,
    max_range_feet: int | None = None,
    confirmation: str | None = None,
    alternative: str | None = None,
) -> str:
    fallback = f"Wybierz {str(subject or 'podswietlone pole').strip()}"
    if max_range_feet is not None:
        fallback = f"{fallback} {format_range_text(max_range_feet)}"
    fallback = f"{fallback} na planszy."
    if confirmation:
        fallback = f"{fallback} Po wyborze {str(confirmation).strip().rstrip('.') }."
    if alternative:
        fallback = f"{fallback} {str(alternative).strip().rstrip('.') }."
    range_suffix = f" {format_range_text(max_range_feet)}" if max_range_feet is not None else ""
    confirmation_suffix = f" Po wyborze {str(confirmation).strip().rstrip('.') }." if confirmation else ""
    alternative_suffix = f" {str(alternative).strip().rstrip('.') }." if alternative else ""
    return str(
        prompt_value(
            "events.board_selection_message",
            "body_markdown",
            fallback,
            subject=str(subject or "podswietlone pole").strip(),
            range_suffix=range_suffix,
            confirmation_suffix=confirmation_suffix,
            alternative_suffix=alternative_suffix,
        )
    )


def format_default_prompt_body(
    text: str,
    *,
    kind: str,
) -> tuple[str, str]:
    body = str(text or "").strip()
    if not body:
        return "", ""
    kind_key = "choice" if str(kind or "").strip().lower() == "choice" else "info"
    default_suffix = (
        "Wybierz opcje i potwierdz wybor." if kind_key == "choice" else "Zapoznaj sie z informacja i potwierdz, gdy bedziesz gotow."
    )
    default_next_hint = "Wybierz opcje w panelu promptu." if kind_key == "choice" else "Potwierdz prompt, gdy bedziesz gotow."
    rendered_body = prompt_value(
        f"events.default_prompt_body.{kind_key}",
        "body_markdown",
        None,
        body=body,
    )
    next_hint = str(
        prompt_value(
            f"events.default_prompt_body.{kind_key}",
            "next_hint",
            default_next_hint,
            body=body,
        )
    )
    if rendered_body:
        return str(rendered_body), next_hint
    if not body.endswith(default_suffix):
        body = f"{body}\n\n{default_suffix}"
    return body, next_hint


def build_prompt_communication(
    message: str,
    *,
    summary: str = "Co robić teraz",
    source: str = "event_prompt",
    priority: str = "info",
    semantic_type: str | None = None,
    dedupe_key: str | None = None,
    next_hint: str | None = None,
    blocking: bool = True,
    channel: str | None = None,
) -> dict[str, Any] | None:
    text = str(message or "").strip()
    if not text:
        return None
    try:
        from narration import build_narration_communication
    except Exception:
        return None
    effective_channel = str(channel or ("prompt" if blocking else "timeline"))
    effective_semantic = str(semantic_type or ("required_action" if blocking else "status_update"))
    return build_narration_communication(
        summary=summary,
        body_markdown=text,
        dedupe_key=dedupe_key,
        priority=priority,
        semantic_type=effective_semantic,
        channel=effective_channel,
        blocking=blocking,
        next_hint=next_hint,
    )


def emit_prompt_narration(
    game,
    message: str,
    *,
    summary: str = "Co robić teraz",
    source: str = "event_prompt",
    priority: str = "info",
    semantic_type: str | None = None,
    dedupe_key: str | None = None,
    next_hint: str | None = None,
    blocking: bool = True,
    channel: str | None = None,
) -> bool:
    text = str(message or "").strip()
    if not text:
        return False
    player_prompt = getattr(game, "player_prompt", None)
    if player_prompt is not None:
        try:
            scope_key = (
                "enemy_turn" if str(source or "").startswith("enemy") else
                "hero_turn:targeting" if any(token in str(source or "") for token in ("target", "pick_", "magic")) else
                "system"
            )
            if blocking:
                player_prompt.info(
                    summary or "Co robić teraz",
                    body_markdown=text,
                    summary=summary,
                    source=source,
                    priority=priority,
                    semantic_type=semantic_type or "required_action",
                    dedupe_key=dedupe_key,
                    scope_key=scope_key,
                )
            else:
                player_prompt.card(
                    kind="narration",
                    title=summary or "Co się dzieje",
                    body_markdown=text,
                    summary=summary,
                    priority=priority,
                    scope_key=scope_key,
                    dedupe_key=dedupe_key,
                )
            return True
        except Exception:
            logger.debug("Nie udało się wysłać promptowej narracji przez PromptFacade.", exc_info=True)
    narrator = getattr(game, "ui_narration", None)
    if callable(narrator):
        try:
            narrator(
                text,
                summary=summary,
                source=source,
                priority=priority,
                semantic_type=semantic_type or ("required_action" if blocking else "status_update"),
                dedupe_key=dedupe_key,
                channel=channel or ("prompt" if blocking else "timeline"),
                blocking=blocking,
                next_hint=next_hint,
            )
            return True
        except Exception:
            logger.debug("Nie udało się wysłać promptowej narracji do UI.", exc_info=True)
    ui_log = getattr(game, "ui_log", None)
    if callable(ui_log):
        try:
            ui_log(text)
            return True
        except Exception:
            logger.debug("Nie udało się wysłać fallbackowego logu promptowego.", exc_info=True)
    return False


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
                        allow_rage_manipulate = has_status("moment_of_clarity_active")
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
                        if sid == "moment_of_clarity_active" or item == "moment_of_clarity_active":
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
