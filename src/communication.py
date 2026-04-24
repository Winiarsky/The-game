from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any


_STRONG_RE = re.compile(r"\*\*(.*?)\*\*")
_EM_RE = re.compile(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)")
_CODE_RE = re.compile(r"`([^`]+)`")


@dataclass(slots=True)
class CommunicationEnvelope:
    channel: str = "log"
    priority: str = "info"
    semantic_type: str = "status_update"
    title: str | None = None
    summary: str | None = None
    body_markdown: str | None = None
    details_markdown: str | None = None
    cta: str | None = None
    context: dict[str, Any] | None = None
    dedupe_key: str | None = None
    blocking: bool = False
    debug_only: bool = False
    progress: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value not in (None, "", {}, [])}


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_multiline(text: str | None) -> str:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    return raw.strip()


def _strip_markdown(text: str | None) -> str:
    raw = _normalize_multiline(text)
    if not raw:
        return ""
    raw = _STRONG_RE.sub(r"\1", raw)
    raw = _EM_RE.sub(r"\1", raw)
    raw = _CODE_RE.sub(r"\1", raw)
    return raw.strip()


def _first_meaningful_line(text: str | None) -> str:
    for line in _normalize_multiline(text).splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _rest_after_first_line(text: str | None) -> str:
    lines = [line.rstrip() for line in _normalize_multiline(text).splitlines()]
    if len(lines) <= 1:
        return ""
    rest = "\n".join(line for line in lines[1:] if line.strip())
    return rest.strip()


def _looks_technical_dump(text: str | None) -> bool:
    raw = _normalize_multiline(text)
    if not raw:
        return False
    lowered = raw.lower()
    if lowered.startswith("krawędzie:") or lowered.startswith("krawedzie:"):
        return True
    if raw.count("{") >= 2 or raw.count("[") >= 4:
        return True
    if "payload" in lowered and "snapshot" in lowered:
        return True
    return False


def _default_priority(*, level: str = "", source: str = "", tag: str = "", debug_only: bool = False) -> str:
    level_l = _as_text(level).lower()
    source_l = _as_text(source).lower()
    tag_l = _as_text(tag).lower()
    if debug_only or tag_l == "debug" or source_l == "debug":
        return "debug"
    if level_l in {"error", "fatal"}:
        return "error"
    if level_l in {"warn", "warning"}:
        return "warning"
    if source_l.startswith("enemy_") or "result" in source_l:
        return "result"
    return "info"


def _default_semantic_type(*, prompt: bool, source: str = "", title: str = "", blocking: bool = False) -> str:
    source_l = _as_text(source).lower()
    title_l = _as_text(title).lower()
    if blocking:
        return "required_action"
    if "result" in source_l or "wynik" in title_l:
        return "result"
    if "setup" in source_l:
        return "confirmation" if prompt else "status_update"
    if "thinking" in source_l or "myśli" in title_l or "mysli" in title_l:
        return "status_update"
    if "analysis" in source_l or "analiza" in title_l or "rzut" in title_l:
        return "explanation"
    return "confirmation" if prompt else "status_update"


def _build_dedupe_key(*, channel: str, source: str = "", title: str = "", summary: str = "", payload: Any = None) -> str:
    explicit = ""
    if isinstance(payload, dict):
        explicit = _as_text(payload.get("dedupe_key"))
    if explicit:
        return explicit
    base = "|".join(
        part
        for part in (
            channel,
            _as_text(source).lower(),
            _strip_markdown(title).lower(),
            _strip_markdown(summary).lower(),
        )
        if part
    )
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:12] if base else ""
    return explicit or (f"{channel}:{digest}" if digest else "")


def make_communication(
    *,
    channel: str,
    priority: str = "info",
    semantic_type: str = "status_update",
    title: str | None = None,
    summary: str | None = None,
    body_markdown: str | None = None,
    details_markdown: str | None = None,
    cta: str | None = None,
    context: dict[str, Any] | None = None,
    dedupe_key: str | None = None,
    blocking: bool = False,
    debug_only: bool = False,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return CommunicationEnvelope(
        channel=channel,
        priority=priority,
        semantic_type=semantic_type,
        title=_as_text(title) or None,
        summary=_as_text(summary) or None,
        body_markdown=_normalize_multiline(body_markdown) or None,
        details_markdown=_normalize_multiline(details_markdown) or None,
        cta=_as_text(cta) or None,
        context=dict(context or {}) or None,
        dedupe_key=_as_text(dedupe_key) or None,
        blocking=bool(blocking),
        debug_only=bool(debug_only),
        progress=dict(progress or {}) or None,
    ).to_dict()


def make_setup_step_communication(
    *,
    title: str,
    body_markdown: str,
    progress: dict[str, Any] | None = None,
    details_markdown: str | None = None,
    blocking: bool = True,
) -> dict[str, Any]:
    summary = _strip_markdown(_first_meaningful_line(body_markdown) or title)
    return make_communication(
        channel="prompt" if blocking else "timeline",
        priority="action",
        semantic_type="required_action" if blocking else "status_update",
        title=title,
        summary=summary,
        body_markdown=body_markdown,
        details_markdown=details_markdown,
        cta="Potwierdź po ustawieniu elementów na planszy.",
        context={"next": "Kolejny etap setupu pojawi się automatycznie."},
        dedupe_key=f"setup:{progress.get('current')}/{progress.get('total')}" if isinstance(progress, dict) else None,
        blocking=blocking,
        progress=progress,
    )


def make_enemy_turn_communication(
    *,
    title: str,
    body_markdown: str,
    dedupe_key: str,
    blocking: bool,
    semantic_type: str,
    next_hint: str | None = None,
    continue_hint: str | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {}
    if next_hint:
        context["next"] = str(next_hint)
    if continue_hint:
        context["continue"] = str(continue_hint)
    return make_communication(
        channel="prompt" if blocking else "timeline",
        priority="result" if semantic_type == "result" else "info",
        semantic_type=semantic_type,
        title=title,
        summary=_strip_markdown(_first_meaningful_line(body_markdown) or title),
        body_markdown=body_markdown,
        details_markdown=_rest_after_first_line(body_markdown) or None,
        cta=continue_hint if blocking else None,
        context=context or None,
        dedupe_key=dedupe_key,
        blocking=blocking,
    )


def make_debug_communication(*, title: str, details_markdown: str, dedupe_key: str | None = None) -> dict[str, Any]:
    return make_communication(
        channel="details",
        priority="debug",
        semantic_type="debug",
        title=title,
        summary=title,
        details_markdown=details_markdown,
        dedupe_key=dedupe_key,
        debug_only=True,
    )


def normalize_communication(
    *,
    event_type: str,
    payload: dict[str, Any],
    prompt: bool = False,
) -> dict[str, Any]:
    raw = dict(payload.get("communication") or {}) if isinstance(payload.get("communication"), dict) else {}
    title = _as_text(raw.get("title") or payload.get("title") or (payload.get("prompt") if prompt else ""))
    source = _as_text(payload.get("source") or raw.get("source"))
    tag = _as_text(payload.get("tag"))
    level = _as_text(payload.get("level"))
    body = _normalize_multiline(
        raw.get("body_markdown")
        or payload.get("body_markdown")
        or payload.get("prompt_long")
        or payload.get("message")
        or payload.get("text")
    )
    details = _normalize_multiline(raw.get("details_markdown") or payload.get("details_markdown"))
    debug_only = bool(raw.get("debug_only") or payload.get("debug_only")) or tag.lower() == "debug"

    if not details and _looks_technical_dump(body):
        details = body
        body = ""
    if not body and prompt and _normalize_multiline(payload.get("prompt")):
        body = _normalize_multiline(payload.get("prompt"))

    summary = _as_text(raw.get("summary") or payload.get("summary")) or _strip_markdown(
        _first_meaningful_line(
            raw.get("summary")
            or payload.get("summary")
            or body
            or payload.get("message")
            or payload.get("prompt")
            or title
        )
    )
    if not details and body and _rest_after_first_line(body):
        details = _rest_after_first_line(body)
    blocking = bool(raw.get("blocking") or payload.get("blocking")) or (prompt and event_type == "prompt")
    priority = _as_text(raw.get("priority") or payload.get("priority")) or _default_priority(
        level=level,
        source=source,
        tag=tag,
        debug_only=debug_only,
    )
    semantic_type = _as_text(raw.get("semantic_type") or payload.get("semantic_type")) or _default_semantic_type(
        prompt=prompt,
        source=source,
        title=title,
        blocking=blocking,
    )
    channel = _as_text(raw.get("channel") or payload.get("channel")) or ("prompt" if prompt else "log")
    context = dict(raw.get("context") or payload.get("context") or {}) or None
    progress = dict(raw.get("progress") or payload.get("progress") or {}) or None
    cta = _as_text(raw.get("cta") or payload.get("cta"))
    if not cta and prompt:
        cta = "Potwierdź, gdy zakończysz ten krok."
    dedupe_key = _as_text(raw.get("dedupe_key")) or _build_dedupe_key(
        channel=channel,
        source=source,
        title=title,
        summary=summary,
        payload=payload,
    )

    envelope = CommunicationEnvelope(
        channel=channel,
        priority=priority,
        semantic_type=semantic_type,
        title=title or None,
        summary=summary or None,
        body_markdown=body or None,
        details_markdown=details or None,
        cta=cta or None,
        context=context,
        dedupe_key=dedupe_key or None,
        blocking=blocking,
        debug_only=debug_only,
        progress=progress,
    )
    return envelope.to_dict()
