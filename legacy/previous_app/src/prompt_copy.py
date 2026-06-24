from __future__ import annotations

from typing import Any

from prompt_text_catalog import render_prompt_text


def render_prompt_copy(prompt_id: str | None, **context: Any) -> dict[str, Any]:
    key = str(prompt_id or "").strip()
    if not key:
        return {}
    return render_prompt_text(key, **context)


def prompt_value(prompt_id: str | None, field: str, fallback: Any = None, **context: Any) -> Any:
    rendered = render_prompt_copy(prompt_id, **context)
    value = rendered.get(str(field or "").strip())
    if value in (None, ""):
        return fallback
    return value


def merge_menu_prompt(
    prompt_id: str | None,
    *,
    title: str,
    subtitle: str,
    options: list[dict[str, Any]],
    **context: Any,
) -> tuple[str, str, list[dict[str, Any]]]:
    rendered = render_prompt_copy(prompt_id, **context)
    merged_title = str(rendered.get("title") or title or "").strip() or title
    merged_subtitle = str(rendered.get("subtitle") or subtitle or "").strip() or subtitle
    rendered_options = rendered.get("options")
    if not isinstance(rendered_options, dict):
        return merged_title, merged_subtitle, [dict(option) for option in options]

    merged_options: list[dict[str, Any]] = []
    for option in options:
        item = dict(option)
        key = str(item.get("id", "")).strip()
        option_copy = rendered_options.get(key)
        if not isinstance(option_copy, dict) and key:
            option_copy = rendered_options.get(key.lower())
        if isinstance(option_copy, dict):
            for field in ("label", "desc", "key", "icon", "category"):
                value = option_copy.get(field)
                if value not in (None, ""):
                    item[field] = value
        merged_options.append(item)
    return merged_title, merged_subtitle, merged_options


def resolve_ui_prompt_copy(
    *,
    kind: str,
    source: str | None,
    title: str,
    subtitle: str | None = None,
    prompt_long: str | None = None,
    choice_meta: list[dict[str, Any]] | None = None,
    prompt_id: str | None = None,
    **context: Any,
) -> dict[str, Any]:
    resolved_prompt_id = str(prompt_id or "").strip()
    if not resolved_prompt_id:
        source_key = str(source or "").strip()
        if source_key:
            resolved_prompt_id = f"ui.{str(kind or '').strip().lower()}.{source_key}"
    rendered = render_prompt_copy(
        resolved_prompt_id,
        source=source,
        title=title,
        subtitle=subtitle,
        prompt_long=prompt_long,
        **context,
    )
    resolved_title = str(rendered.get("title") or title or "").strip() or title
    resolved_subtitle = rendered.get("subtitle")
    if resolved_subtitle in (None, ""):
        resolved_subtitle = subtitle
    resolved_body = rendered.get("body_markdown")
    if resolved_body in (None, ""):
        resolved_body = prompt_long
    resolved_details = rendered.get("details_markdown")
    resolved_cta = rendered.get("cta")
    resolved_next_hint = rendered.get("next_hint")
    resolved_choice_meta = choice_meta
    rendered_options = rendered.get("options")
    if isinstance(choice_meta, list) and isinstance(rendered_options, dict):
        updated_choice_meta: list[dict[str, Any]] = []
        for entry in choice_meta:
            item = dict(entry)
            raw_key = str(item.get("raw", "")).strip()
            option_copy = rendered_options.get(raw_key)
            if not isinstance(option_copy, dict) and raw_key:
                option_copy = rendered_options.get(raw_key.lower())
            if isinstance(option_copy, dict):
                for field in ("label", "desc", "key", "icon", "category"):
                    value = option_copy.get(field)
                    if value not in (None, ""):
                        item[field] = value
            updated_choice_meta.append(item)
        resolved_choice_meta = updated_choice_meta
    return {
        "prompt_id": resolved_prompt_id or None,
        "title": resolved_title,
        "subtitle": resolved_subtitle,
        "prompt_long": resolved_body,
        "details_markdown": resolved_details,
        "cta": resolved_cta,
        "next_hint": resolved_next_hint,
        "choice_meta": resolved_choice_meta,
        "copy": rendered,
    }
