from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import time
from typing import Any, Callable

from communication import make_communication, normalize_communication


SESSION_RESET_COMMAND = "__session_reset__"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _markdown(value: Any) -> str | None:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return text or None


def _first_line(value: Any) -> str:
    raw = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _stable_key(*parts: Any) -> str:
    joined = "|".join(_text(part).lower() for part in parts if _text(part))
    if not joined:
        return ""
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]
    return digest


def _default_scope_key(source: str, prompt_type: str) -> str:
    normalized_source = _text(source).lower()
    if normalized_source.startswith("encounter_setup") or normalized_source.startswith("setup"):
        return "setup"
    if normalized_source.startswith("intent"):
        return "hero_turn:intent"
    if "target" in normalized_source or "analysis" in normalized_source:
        return "hero_turn:targeting"
    if normalized_source.startswith("enemy_") or normalized_source.startswith("enemy"):
        return "enemy_turn"
    if normalized_source.startswith("scenario_transition") or normalized_source.startswith("scenario_flow"):
        return "scenario_transition"
    if normalized_source.startswith("character_creation"):
        return "character_creation"
    if prompt_type == "roll":
        return "hero_turn:resolution"
    return "system"


def _normalize_prompt_key(value: Any) -> str:
    raw = _text(value).lower().replace(" ", "_")
    return raw


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = _text(value).lower()
    if not normalized:
        return None
    if normalized in {"1", "true", "yes", "y", "on", "required", "require", "ack", "pause"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "none", "skip", "passive", "silent"}:
        return False
    return None


def _default_prompt_key(*, source: str = "", prompt_type: str = "info", event_type: str = "", card_kind: str = "") -> str:
    source_key = _normalize_prompt_key(source)
    prompt_type_key = _normalize_prompt_key(prompt_type) or "info"
    event_key = _normalize_prompt_key(event_type)
    card_kind_key = _normalize_prompt_key(card_kind)
    if source_key:
        if prompt_type_key:
            return f"ui.{prompt_type_key}.{source_key}"
        return source_key
    if event_key:
        return f"event.{event_key}"
    if card_kind_key:
        return f"card.{card_kind_key}"
    return "system.unnamed"


def _derive_prompt_key(
    *,
    explicit: Any = None,
    source: str = "",
    prompt_type: str = "info",
    event_type: str = "",
    card_kind: str = "",
    communication: dict[str, Any] | None = None,
) -> str:
    if _text(explicit):
        return _normalize_prompt_key(explicit)
    communication = dict(communication or {})
    context = dict(communication.get("context") or {})
    for candidate in (
        context.get("prompt_key"),
        context.get("prompt_id"),
        communication.get("prompt_key"),
        communication.get("prompt_id"),
    ):
        if _text(candidate):
            return _normalize_prompt_key(candidate)
    return _default_prompt_key(
        source=source,
        prompt_type=prompt_type,
        event_type=event_type,
        card_kind=card_kind,
    )


def _card_kind_from_event(event_type: str, communication: dict[str, Any], payload: dict[str, Any] | None = None) -> str:
    payload = dict(payload or {})
    kind = _text((communication or {}).get("kind")).lower()
    if not kind:
        kind = _text(payload.get("kind")).lower()
    if kind in {"narration", "result", "debug", "idle", "system"}:
        return kind
    if bool((communication or {}).get("debug_only")) or _text((communication or {}).get("priority")).lower() == "debug":
        return "debug"
    if event_type == "idle_hint":
        return "idle"
    if _text((communication or {}).get("semantic_type")).lower() == "result":
        return "result"
    if event_type in {"log", "info", "narration"}:
        return "narration"
    return "system"


def _should_ingest_player_event(
    event_type: str,
    payload: dict[str, Any],
    communication: dict[str, Any],
) -> bool:
    normalized_event_type = _text(event_type).lower()
    if normalized_event_type != "log":
        return True
    if bool((payload or {}).get("_communication_explicit")):
        return True
    if bool((communication or {}).get("debug_only")):
        return True
    if _text((payload or {}).get("tag")).lower() == "debug":
        return True
    if _text((payload or {}).get("level")).lower() in {"warn", "warning", "error", "fatal"}:
        return True
    if bool((communication or {}).get("blocking")):
        return True
    if _text((communication or {}).get("semantic_type")).lower() in {"result", "required_action"}:
        return True
    return False


@dataclass(slots=True)
class PlayerPrompt:
    id: str
    session_id: str
    revision: int
    source: str
    prompt_type: str
    title: str
    prompt_key: str | None = None
    summary: str | None = None
    body_markdown: str | None = None
    details_markdown: str | None = None
    choices: list[str] = field(default_factory=list)
    choice_meta: list[dict[str, Any]] = field(default_factory=list)
    input_mode: str | None = None
    answer_placeholder: str | None = None
    roll_stack: dict[str, Any] | None = None
    modifiers: dict[str, Any] | None = None
    priority: str = "action"
    blocking: bool = True
    scope_key: str = "system"
    dedupe_key: str | None = None
    replaces_prompt_id: str | None = None
    status: str = "pending"
    answer: Any = None
    created_at: float = field(default_factory=time.time)
    layout: str | None = None
    image: str | None = None
    action_desc: str | None = None
    desc: str | None = None
    communication: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = data.pop("prompt_type")
        data["prompt"] = self.title
        return data


@dataclass(slots=True)
class PlayerCard:
    id: str
    session_id: str
    revision: int
    seq: int
    kind: str
    title: str
    prompt_key: str | None = None
    summary: str | None = None
    body_markdown: str | None = None
    details_markdown: str | None = None
    priority: str = "info"
    scope_key: str = "system"
    dedupe_key: str | None = None
    created_at: float = field(default_factory=time.time)
    communication: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlayerViewState:
    session_id: str
    revision: int
    active_prompt: dict[str, Any] | None
    focus_card: dict[str, Any] | None
    idle_state: dict[str, Any] | None
    journal: list[dict[str, Any]]
    debug_feed: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PromptDirector:
    def __init__(
        self,
        *,
        session_id: str,
        journal_limit: int = 120,
        debug_limit: int = 80,
        prompt_limit: int = 300,
        publisher: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.journal_limit = max(10, int(journal_limit))
        self.debug_limit = max(10, int(debug_limit))
        self.prompt_limit = max(20, int(prompt_limit))
        self._publisher = publisher
        self._prompt_counter = 0
        self._card_counter = 0
        self._revision = 0
        self.session_id = _text(session_id) or "ui-session-1"
        self.prompts: dict[str, PlayerPrompt] = {}
        self.prompt_order: list[str] = []
        self.journal: list[PlayerCard] = []
        self.debug_feed: list[PlayerCard] = []
        self.active_prompt_id: str | None = None
        self.focus_card_id: str | None = None
        self.idle_card_id: str | None = None

    def set_publisher(self, publisher: Callable[[str, dict[str, Any]], None] | None) -> None:
        self._publisher = publisher

    @property
    def revision(self) -> int:
        return int(self._revision)

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if callable(self._publisher):
            self._publisher(event_type, payload)

    def _bump_revision(self) -> int:
        self._revision += 1
        return self._revision

    def _next_prompt_id(self) -> str:
        self._prompt_counter += 1
        return str(self._prompt_counter)

    def _next_card_id(self) -> str:
        self._card_counter += 1
        return f"card-{self._card_counter}"

    def _current_prompt(self) -> PlayerPrompt | None:
        if not self.active_prompt_id:
            return None
        prompt = self.prompts.get(self.active_prompt_id)
        if prompt is None:
            self.active_prompt_id = None
            return None
        return prompt

    def _card_by_id(self, card_id: str | None) -> PlayerCard | None:
        if not card_id:
            return None
        for collection in (self.journal, self.debug_feed):
            for card in collection:
                if card.id == card_id:
                    return card
        return None

    def _view_state_payload(self, *, runtime_status: dict[str, Any] | None = None) -> dict[str, Any]:
        current_prompt = self._current_prompt()
        focus_card = self._card_by_id(self.focus_card_id)
        idle_card = self._card_by_id(self.idle_card_id)
        payload = PlayerViewState(
            session_id=self.session_id,
            revision=self.revision,
            active_prompt=current_prompt.to_dict() if current_prompt else None,
            focus_card=focus_card.to_dict() if focus_card else None,
            idle_state=idle_card.to_dict() if idle_card else None,
            journal=[item.to_dict() for item in self.journal],
            debug_feed=[item.to_dict() for item in self.debug_feed],
        ).to_dict()
        if runtime_status is not None:
            payload["runtime_status"] = dict(runtime_status)
        return payload

    def snapshot(self, *, runtime_status: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._view_state_payload(runtime_status=runtime_status)

    def _sync_active_prompt(self) -> None:
        if self.active_prompt_id:
            active = self.prompts.get(self.active_prompt_id)
            if active and active.status == "pending" and active.session_id == self.session_id:
                return
        self.active_prompt_id = None
        for prompt_id in self.prompt_order:
            prompt = self.prompts.get(prompt_id)
            if prompt is None:
                continue
            if prompt.session_id != self.session_id:
                continue
            if prompt.status != "pending":
                continue
            self.active_prompt_id = prompt.id
            return

    def _register_prompt(
        self,
        prompt: PlayerPrompt,
        *,
        runtime_status: dict[str, Any] | None = None,
        activate: bool = True,
    ) -> dict[str, Any]:
        duplicate = self._find_pending_prompt_duplicate(prompt)
        if duplicate is not None:
            return duplicate.to_dict()
        self.prompts[prompt.id] = prompt
        self.prompt_order.append(prompt.id)
        if len(self.prompt_order) > self.prompt_limit:
            self.prompt_order = self.prompt_order[-self.prompt_limit :]
        self._supersede_prompt(prompt)
        if activate or self._current_prompt() is None:
            self.active_prompt_id = prompt.id
        else:
            self._sync_active_prompt()
        payload = prompt.to_dict()
        self._publish("prompt_created", payload)
        self._publish("view_state", self._view_state_payload(runtime_status=runtime_status))
        return payload

    def _find_pending_prompt_duplicate(self, prompt: PlayerPrompt) -> PlayerPrompt | None:
        dedupe_text = _text(prompt.dedupe_key)
        title_text = _text(prompt.title)
        body_text = _text(prompt.body_markdown)
        scope_text = _text(prompt.scope_key)
        for prompt_id in reversed(self.prompt_order[-10:]):
            existing = self.prompts.get(prompt_id)
            if existing is None:
                continue
            if existing.session_id != prompt.session_id:
                continue
            if existing.status != "pending":
                continue
            if dedupe_text and dedupe_text == _text(existing.dedupe_key):
                return existing
            if scope_text and scope_text != _text(existing.scope_key):
                continue
            if title_text != _text(existing.title):
                continue
            if body_text and body_text == _text(existing.body_markdown):
                return existing
        return None

    def _store_card(self, card: PlayerCard) -> None:
        if card.kind == "debug":
            self.debug_feed.insert(0, card)
            self.debug_feed = self.debug_feed[: self.debug_limit]
            return
        if card.kind == "idle":
            self.idle_card_id = card.id
        self.journal.insert(0, card)
        self.journal = self.journal[: self.journal_limit]
        self.focus_card_id = card.id

    def _make_card(
        self,
        *,
        kind: str,
        title: str,
        summary: str | None,
        body_markdown: str | None,
        details_markdown: str | None,
        priority: str,
        scope_key: str,
        dedupe_key: str | None,
        communication: dict[str, Any] | None,
        prompt_key: str | None,
    ) -> PlayerCard:
        revision = self._bump_revision()
        return PlayerCard(
            id=self._next_card_id(),
            session_id=self.session_id,
            revision=revision,
            seq=self._card_counter,
            kind=kind,
            prompt_key=_text(prompt_key) or None,
            title=_text(title) or "Karta",
            summary=_markdown(summary),
            body_markdown=_markdown(body_markdown),
            details_markdown=_markdown(details_markdown),
            priority=_text(priority) or "info",
            scope_key=_text(scope_key) or "system",
            dedupe_key=_text(dedupe_key) or None,
            communication=dict(communication or {}) or None,
        )

    def _find_recent_card_duplicate(
        self,
        *,
        kind: str,
        title: str,
        body_markdown: str | None,
        scope_key: str,
        dedupe_key: str | None,
    ) -> PlayerCard | None:
        candidates = [*self.journal[:5], *self.debug_feed[:5]]
        title_text = _text(title)
        body_text = _text(body_markdown)
        scope_text = _text(scope_key)
        dedupe_text = _text(dedupe_key)
        for existing in candidates:
            if existing.session_id != self.session_id:
                continue
            if existing.kind != kind:
                continue
            if dedupe_text and dedupe_text == _text(existing.dedupe_key):
                return existing
            if scope_text and scope_text != _text(existing.scope_key):
                continue
            if title_text != _text(existing.title):
                continue
            if body_text and body_text == _text(existing.body_markdown):
                return existing
        return None

    def add_card(
        self,
        *,
        kind: str,
        title: str,
        summary: str | None = None,
        body_markdown: str | None = None,
        details_markdown: str | None = None,
        priority: str = "info",
        scope_key: str = "system",
        dedupe_key: str | None = None,
        communication: dict[str, Any] | None = None,
        runtime_status: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self._find_recent_card_duplicate(
            kind=kind,
            title=title,
            body_markdown=body_markdown,
            scope_key=scope_key,
            dedupe_key=dedupe_key,
        )
        if existing is not None:
            return existing.to_dict()
        card = self._make_card(
            kind=kind,
            title=title,
            summary=summary,
            body_markdown=body_markdown,
            details_markdown=details_markdown,
            priority=priority,
            scope_key=scope_key,
            dedupe_key=dedupe_key,
            communication=communication,
            prompt_key=_derive_prompt_key(
                explicit=(communication or {}).get("prompt_key") or (communication or {}).get("prompt_id"),
                source=_text((communication or {}).get("source") or (communication or {}).get("event_type")),
                event_type=_text((communication or {}).get("event_type")),
                card_kind=kind,
                communication=communication,
            ),
        )
        self._store_card(card)
        payload = card.to_dict()
        self._publish("card_added", payload)
        self._publish("view_state", self._view_state_payload(runtime_status=runtime_status))
        if self._should_require_ack_for_card(card):
            self._enqueue_card_prompt(card, runtime_status=runtime_status)
        return payload

    def _should_require_ack_for_card(self, card: PlayerCard) -> bool:
        if card.session_id != self.session_id:
            return False
        if card.kind in {"debug", "idle"}:
            return False
        communication = dict(card.communication or {})
        if "ack_required" in communication:
            explicit_ack = _optional_bool(communication.get("ack_required"))
            if explicit_ack is not None:
                return explicit_ack
        pause_policy = _text(communication.get("pause_policy")).lower()
        if pause_policy in {"none", "skip", "passive", "silent", "no_ack"}:
            return False
        if pause_policy in {"ack", "require_ack", "required", "pause"}:
            return True
        if bool(communication.get("debug_only")):
            return False
        if bool(communication.get("blocking")):
            return False
        if _text(communication.get("channel")).lower() == "details":
            return False
        return True

    def _enqueue_card_prompt(
        self,
        card: PlayerCard,
        *,
        runtime_status: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        communication = dict(card.communication or {})
        prompt_body = card.body_markdown or card.summary or card.title
        source = _text(communication.get("event_type") or card.kind or "card_ack")
        scope_key = f"ack:{card.seq}"
        dedupe_key = _text(card.dedupe_key) or f"card_ack:{card.id}"
        prompt = PlayerPrompt(
            id=self._next_prompt_id(),
            session_id=card.session_id,
            revision=self._bump_revision(),
            source=source,
            prompt_type="info",
            prompt_key=_text(card.prompt_key) or _derive_prompt_key(source=source, prompt_type="info", card_kind=card.kind, communication=communication),
            title=card.title,
            summary=card.summary,
            body_markdown=prompt_body,
            details_markdown=card.details_markdown,
            input_mode="confirm",
            priority="action" if card.priority == "info" else card.priority,
            blocking=True,
            scope_key=scope_key,
            dedupe_key=f"{dedupe_key}:ack",
            status="pending",
            communication=make_communication(
                channel="prompt",
                priority="action" if card.priority == "info" else card.priority,
                semantic_type="required_action",
                title=card.title,
                summary=card.summary,
                body_markdown=prompt_body,
                details_markdown=card.details_markdown,
                cta="Enter, aby przejść do kolejnego kroku.",
                dedupe_key=f"{dedupe_key}:ack",
                blocking=True,
                context={
                    **dict(communication.get("context") or {}),
                    "scope_key": scope_key,
                    "card_id": card.id,
                    "card_seq": card.seq,
                },
            ),
        )
        return self._register_prompt(
            prompt,
            runtime_status=runtime_status,
            activate=self._current_prompt() is None,
        )

    def _prompt_payload(
        self,
        data: dict[str, Any],
        *,
        session_id: str,
    ) -> PlayerPrompt:
        prompt_text = _text(data.get("prompt"))
        prompt_type = _text(data.get("kind") or data.get("prompt_type")).lower() or "info"
        source = _text(data.get("source")) or "system"
        communication = normalize_communication(
            event_type="prompt",
            payload={**dict(data), "prompt": prompt_text},
            prompt=True,
        )
        title = _text(data.get("title") or communication.get("title") or prompt_text or "Prompt")
        body_markdown = _markdown(
            data.get("body_markdown")
            or communication.get("body_markdown")
            or data.get("prompt_long")
            or prompt_text
        )
        summary = _markdown(data.get("summary") or communication.get("summary") or data.get("subtitle") or _first_line(body_markdown or title))
        details_markdown = _markdown(data.get("details_markdown") or communication.get("details_markdown"))
        scope_key = _text(data.get("scope_key")) or _text((communication.get("context") or {}).get("scope_key")) or _default_scope_key(source, prompt_type)
        dedupe_key = _text(data.get("dedupe_key") or communication.get("dedupe_key")) or f"prompt:{_stable_key(session_id, scope_key, source, title, body_markdown)}"
        input_mode = _text(data.get("input_mode"))
        if not input_mode:
            if prompt_type == "roll":
                input_mode = "roll"
            elif prompt_type == "choice":
                input_mode = "choice"
            elif prompt_type == "info":
                input_mode = "confirm"
            else:
                input_mode = "text"
        revision = self._bump_revision()
        choices = list(data.get("choices") or []) if isinstance(data.get("choices"), list) else []
        choice_meta = list(data.get("choice_meta") or []) if isinstance(data.get("choice_meta"), list) else []
        raw_roll_stack = data.get("roll_stack")
        raw_modifiers = data.get("modifiers")
        roll_stack = dict(raw_roll_stack) if isinstance(raw_roll_stack, dict) and raw_roll_stack else None
        modifiers = dict(raw_modifiers) if isinstance(raw_modifiers, dict) and raw_modifiers else None
        envelope = make_communication(
            channel="prompt",
            priority=_text(data.get("priority") or communication.get("priority") or "action"),
            semantic_type=_text(data.get("semantic_type") or communication.get("semantic_type") or "required_action"),
            title=title,
            summary=summary,
            body_markdown=body_markdown,
            details_markdown=details_markdown,
            cta=_text(data.get("cta") or communication.get("cta")) or None,
            dedupe_key=dedupe_key,
            blocking=True,
            ack_required=_optional_bool(communication.get("ack_required")) if "ack_required" in communication else None,
            pause_policy=_text(communication.get("pause_policy")) or None,
            context={
                **dict(communication.get("context") or {}),
                "scope_key": scope_key,
                "prompt_key": _derive_prompt_key(
                    explicit=data.get("prompt_key") or data.get("prompt_id"),
                    source=source,
                    prompt_type=prompt_type,
                    communication=communication,
                ),
            },
            progress=dict(communication.get("progress") or {}) or None,
        )
        passthrough_keys = {"cta"}
        for key in passthrough_keys:
            value = communication.get(key)
            if value not in (None, "", {}, []):
                envelope[key] = value
        return PlayerPrompt(
            id=_text(data.get("id")) or self._next_prompt_id(),
            session_id=session_id,
            revision=revision,
            source=source,
            prompt_type=prompt_type,
            prompt_key=_derive_prompt_key(
                explicit=data.get("prompt_key") or data.get("prompt_id"),
                source=source,
                prompt_type=prompt_type,
                communication=communication,
            ),
            title=title,
            summary=summary,
            body_markdown=body_markdown,
            details_markdown=details_markdown,
            choices=choices,
            choice_meta=choice_meta,
            input_mode=input_mode,
            answer_placeholder=_text(data.get("answer_placeholder")) or None,
            roll_stack=roll_stack,
            modifiers=modifiers,
            priority=_text(data.get("priority") or communication.get("priority") or "action"),
            blocking=True,
            scope_key=scope_key,
            dedupe_key=dedupe_key,
            replaces_prompt_id=None,
            status="pending",
            layout=_text(data.get("layout")) or None,
            image=_text(data.get("image")) or None,
            action_desc=_text(data.get("action_desc")) or None,
            desc=_text(data.get("desc")) or None,
            communication=envelope,
        )

    def _supersede_prompt(self, prompt: PlayerPrompt) -> None:
        for prompt_id in list(self.prompt_order):
            existing = self.prompts.get(prompt_id)
            if existing is None or existing.id == prompt.id:
                continue
            if existing.session_id != prompt.session_id:
                continue
            if existing.status != "pending":
                continue
            if existing.scope_key != prompt.scope_key:
                continue
            existing.status = "superseded"
            existing.revision = self._bump_revision()
            prompt.replaces_prompt_id = existing.id
            self._publish(
                "prompt_closed",
                {
                    "id": existing.id,
                    "prompt_key": existing.prompt_key,
                    "status": existing.status,
                    "replaced_by": prompt.id,
                    "scope_key": existing.scope_key,
                    "session_id": existing.session_id,
                    "revision": existing.revision,
                },
            )

    def create_prompt_from_api(
        self,
        data: dict[str, Any],
        *,
        session_id: str,
        runtime_status: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prompt = self._prompt_payload(data, session_id=session_id)
        return self._register_prompt(prompt, runtime_status=runtime_status, activate=True)

    def list_prompts(self, *, session_id: str | None = None) -> list[dict[str, Any]]:
        effective_session_id = _text(session_id)
        items: list[dict[str, Any]] = []
        for prompt_id in self.prompt_order:
            prompt = self.prompts.get(prompt_id)
            if prompt is None:
                continue
            if effective_session_id and prompt.session_id != effective_session_id:
                continue
            items.append(prompt.to_dict())
        return items

    def get_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        prompt = self.prompts.get(_text(prompt_id))
        if prompt is None:
            return None
        return prompt.to_dict()

    def answer_prompt(
        self,
        prompt_id: str,
        answer: Any,
        *,
        current_session_id: str,
        runtime_status: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        prompt = self.prompts.get(_text(prompt_id))
        if prompt is None:
            return None
        if prompt.status != "pending":
            return {
                "id": prompt.id,
                "prompt_key": prompt.prompt_key,
                "answer": prompt.answer,
                "session_id": prompt.session_id,
                "ignored": True,
                "status": prompt.status,
            }
        prompt.status = "answered"
        prompt.answer = answer
        prompt.revision = self._bump_revision()
        if prompt.session_id == _text(current_session_id) and self.active_prompt_id == prompt.id:
            self.active_prompt_id = None
            self._sync_active_prompt()
        payload = {
            "id": prompt.id,
            "prompt_key": prompt.prompt_key,
            "answer": answer,
            "session_id": prompt.session_id,
            "status": prompt.status,
            "revision": prompt.revision,
            "scope_key": prompt.scope_key,
        }
        self._publish("prompt_closed", payload)
        self._publish("view_state", self._view_state_payload(runtime_status=runtime_status))
        return payload

    def cancel_scope(
        self,
        scope_key: str,
        *,
        session_id: str | None = None,
        runtime_status: dict[str, Any] | None = None,
    ) -> int:
        effective_session_id = _text(session_id) or self.session_id
        changed = 0
        for prompt_id in list(self.prompt_order):
            prompt = self.prompts.get(prompt_id)
            if prompt is None:
                continue
            if prompt.session_id != effective_session_id:
                continue
            if prompt.status != "pending":
                continue
            if prompt.scope_key != _text(scope_key):
                continue
            prompt.status = "cancelled"
            prompt.revision = self._bump_revision()
            changed += 1
            self._publish(
                "prompt_closed",
                {
                    "id": prompt.id,
                    "prompt_key": prompt.prompt_key,
                    "status": prompt.status,
                    "session_id": prompt.session_id,
                    "revision": prompt.revision,
                    "scope_key": prompt.scope_key,
                },
            )
        self._sync_active_prompt()
        if changed:
            self._publish("view_state", self._view_state_payload(runtime_status=runtime_status))
        return changed

    def rotate_session(
        self,
        new_session_id: str,
        *,
        retired_answer: Any = SESSION_RESET_COMMAND,
        runtime_status: dict[str, Any] | None = None,
    ) -> int:
        previous_session_id = self.session_id
        retired = 0
        for prompt_id in list(self.prompt_order):
            prompt = self.prompts.get(prompt_id)
            if prompt is None:
                continue
            if prompt.session_id != previous_session_id:
                continue
            if prompt.status != "pending":
                continue
            prompt.status = "answered"
            prompt.answer = retired_answer
            prompt.revision = self._bump_revision()
            retired += 1
        self.session_id = _text(new_session_id) or self.session_id
        self.active_prompt_id = None
        self.focus_card_id = None
        self.idle_card_id = None
        self.journal = []
        self.debug_feed = []
        self._bump_revision()
        self._publish("view_state", self._view_state_payload(runtime_status=runtime_status))
        return retired

    def journal_after(self, after_seq: int) -> dict[str, list[dict[str, Any]]]:
        return {
            "journal": [item.to_dict() for item in reversed([card for card in self.journal if int(card.seq) > int(after_seq)])],
            "debug_feed": [item.to_dict() for item in reversed([card for card in self.debug_feed if int(card.seq) > int(after_seq)])],
        }

    def _has_matching_pending_prompt(self, *, dedupe_key: str | None, title: str, body_markdown: str | None) -> bool:
        title_text = _text(title)
        body_text = _text(body_markdown)
        for prompt_id in reversed(self.prompt_order):
            prompt = self.prompts.get(prompt_id)
            if prompt is None:
                continue
            if prompt.session_id != self.session_id:
                continue
            if prompt.status != "pending":
                continue
            if dedupe_key and dedupe_key == prompt.dedupe_key:
                return True
            if title_text and title_text == _text(prompt.title) and body_text and body_text == _text(prompt.body_markdown):
                return True
        return False

    def ingest_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        runtime_status: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        normalized = dict(payload or {})
        communication = normalize_communication(
            event_type=event_type,
            payload=normalized,
            prompt=False,
        )
        if not _should_ingest_player_event(event_type, normalized, communication):
            return None
        title = _text(communication.get("title") or normalized.get("title") or normalized.get("tag") or event_type)
        body_markdown = _markdown(communication.get("body_markdown") or normalized.get("message") or normalized.get("text"))
        details_markdown = _markdown(communication.get("details_markdown"))
        summary = _markdown(communication.get("summary") or _first_line(body_markdown or title))
        scope_key = _text(normalized.get("scope_key") or (communication.get("context") or {}).get("scope_key")) or _default_scope_key(_text(normalized.get("source")), "info")
        dedupe_key = _text(normalized.get("dedupe_key") or communication.get("dedupe_key")) or None
        if (bool(communication.get("blocking")) or _text(communication.get("channel")).lower() == "prompt") and self._has_matching_pending_prompt(
            dedupe_key=dedupe_key,
            title=title,
            body_markdown=body_markdown,
        ):
            return None
        card = self.add_card(
            kind=_card_kind_from_event(event_type, communication, normalized),
            title=title or "Karta",
            summary=summary,
            body_markdown=body_markdown,
            details_markdown=details_markdown,
            priority=_text(communication.get("priority") or "info"),
            scope_key=scope_key,
            dedupe_key=dedupe_key,
            communication={
                **communication,
                "event_type": event_type,
                "source": _text(normalized.get("source")),
                "prompt_id": _text(normalized.get("prompt_id")) or None,
                "prompt_key": _text(normalized.get("prompt_key")) or None,
            },
            runtime_status=runtime_status,
        )
        return card


class GamePromptFacade:
    def __init__(self, game: Any):
        self.game = game

    @property
    def _ui(self) -> Any:
        return getattr(self.game, "ui", None)

    def _prompt_communication(
        self,
        *,
        title: str,
        summary: str | None,
        body_markdown: str | None,
        details_markdown: str | None = None,
        priority: str = "action",
        semantic_type: str = "required_action",
        dedupe_key: str | None = None,
        scope_key: str | None = None,
        blocking: bool = True,
        progress: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        prompt_key: str | None = None,
        ack_required: bool | None = None,
        pause_policy: str | None = None,
    ) -> dict[str, Any]:
        extra_context = dict(context or {})
        if scope_key:
            extra_context["scope_key"] = scope_key
        if prompt_key:
            extra_context["prompt_key"] = _text(prompt_key)
        return make_communication(
            channel="prompt" if blocking else "timeline",
            priority=priority,
            semantic_type=semantic_type,
            title=title,
            summary=summary,
            body_markdown=body_markdown,
            details_markdown=details_markdown,
            dedupe_key=dedupe_key,
            blocking=blocking,
            context=extra_context or None,
            progress=progress,
            ack_required=ack_required,
            pause_policy=pause_policy,
        )

    def info(
        self,
        title: str,
        *,
        body_markdown: str | None = None,
        source: str,
        summary: str | None = None,
        details_markdown: str | None = None,
        scope_key: str | None = None,
        dedupe_key: str | None = None,
        priority: str = "action",
        semantic_type: str = "required_action",
        image: str | None = None,
        progress: dict[str, Any] | None = None,
        answer_placeholder: str | None = None,
        prompt_id: str | None = None,
    ) -> Any:
        ui = self._ui
        if ui is None or not getattr(ui, "enabled", False) or not hasattr(ui, "prompt_info"):
            return None
        communication = self._prompt_communication(
            title=title,
            summary=summary,
            body_markdown=body_markdown,
            details_markdown=details_markdown,
            priority=priority,
            semantic_type=semantic_type,
            dedupe_key=dedupe_key,
            scope_key=scope_key,
            blocking=True,
            progress=progress,
            prompt_key=prompt_id,
        )
        return ui.prompt_info(
            title,
            prompt_long=body_markdown,
            source=source,
            image=image,
            communication=communication,
            scope_key=scope_key,
            dedupe_key=dedupe_key,
            priority=priority,
            summary=summary,
            details_markdown=details_markdown,
            answer_placeholder=answer_placeholder,
            prompt_id=prompt_id,
        )

    def choice(
        self,
        title: str,
        *,
        choices: list[str],
        source: str,
        subtitle: str | None = None,
        body_markdown: str | None = None,
        details_markdown: str | None = None,
        choice_meta: list[dict[str, Any]] | None = None,
        scope_key: str | None = None,
        dedupe_key: str | None = None,
        layout: str = "dialog",
        priority: str = "action",
        semantic_type: str = "required_action",
        prompt_id: str | None = None,
    ) -> Any:
        ui = self._ui
        if ui is None or not getattr(ui, "enabled", False) or not hasattr(ui, "prompt_choice"):
            return None
        body = body_markdown if body_markdown is not None else subtitle
        communication = self._prompt_communication(
            title=title,
            summary=subtitle,
            body_markdown=body,
            details_markdown=details_markdown,
            priority=priority,
            semantic_type=semantic_type,
            dedupe_key=dedupe_key,
            scope_key=scope_key,
            prompt_key=prompt_id,
        )
        return ui.prompt_choice(
            title,
            choices=list(choices or []),
            source=source,
            subtitle=subtitle,
            title=title,
            prompt_long=body,
            details_markdown=details_markdown,
            layout=layout,
            choice_meta=list(choice_meta or []),
            communication=communication,
            scope_key=scope_key,
            dedupe_key=dedupe_key,
            priority=priority,
            prompt_id=prompt_id,
        )

    def roll(
        self,
        prompt: str,
        *,
        source: str,
        scope_key: str | None = None,
        dedupe_key: str | None = None,
        layout: str = "test",
        answer_placeholder: str | None = None,
        roll_stack: dict[str, Any] | None = None,
        modifiers: dict[str, Any] | None = None,
        return_meta: bool = False,
        prompt_id: str | None = None,
    ) -> Any:
        ui = self._ui
        if ui is None or not getattr(ui, "enabled", False) or not hasattr(ui, "prompt_roll"):
            return None
        return ui.prompt_roll(
            prompt,
            source=source,
            scope_key=scope_key,
            dedupe_key=dedupe_key,
            layout=layout,
            answer_placeholder=answer_placeholder,
            roll_stack=roll_stack,
            modifiers=modifiers,
            return_meta=return_meta,
            prompt_id=prompt_id,
        )

    def text(
        self,
        title: str,
        *,
        body_markdown: str | None = None,
        source: str,
        scope_key: str | None = None,
        dedupe_key: str | None = None,
        answer_placeholder: str | None = None,
        prompt_id: str | None = None,
    ) -> Any:
        return self.choice(
            title,
            choices=[],
            source=source,
            subtitle=body_markdown,
            scope_key=scope_key,
            dedupe_key=dedupe_key,
            layout="dialog",
            prompt_id=prompt_id,
        )

    def card(
        self,
        *,
        kind: str,
        title: str,
        body_markdown: str | None = None,
        summary: str | None = None,
        details_markdown: str | None = None,
        priority: str = "info",
        scope_key: str = "system",
        dedupe_key: str | None = None,
        prompt_id: str | None = None,
        ack_required: bool | None = None,
        pause_policy: str | None = None,
    ) -> bool:
        return bool(
            getattr(self.game, "ui_event", lambda *_args, **_kwargs: False)(
                "player_card",
                {
                    "kind": kind,
                    "title": title,
                    "summary": summary,
                    "body_markdown": body_markdown,
                    "details_markdown": details_markdown,
                    "priority": priority,
                    "scope_key": scope_key,
                    "dedupe_key": dedupe_key,
                    "prompt_id": prompt_id,
                    "ack_required": ack_required,
                    "pause_policy": pause_policy,
                },
            )
        )

    def result(self, title: str, body_markdown: str, *, summary: str | None = None, dedupe_key: str | None = None) -> bool:
        return self.card(
            kind="result",
            title=title,
            summary=summary,
            body_markdown=body_markdown,
            priority="result",
            scope_key="hero_turn:resolution",
            dedupe_key=dedupe_key,
        )

    def idle(self, title: str, text: str | None = None, *, scope_key: str = "system", dedupe_key: str | None = None) -> bool:
        return self.card(
            kind="idle",
            title=title,
            summary=text,
            body_markdown=text,
            priority="info",
            scope_key=scope_key,
            dedupe_key=dedupe_key,
        )

    def cancel_scope(self, scope_key: str) -> bool:
        return bool(
            getattr(self.game, "ui_event", lambda *_args, **_kwargs: False)(
                "prompt_scope_cancel",
                {"scope_key": scope_key},
            )
        )

    def answer(self, prompt_id: str, answer: Any) -> bool:
        return bool(
            getattr(self.game, "ui_event", lambda *_args, **_kwargs: False)(
                "prompt_answer",
                {"prompt_id": prompt_id, "answer": answer},
            )
        )
