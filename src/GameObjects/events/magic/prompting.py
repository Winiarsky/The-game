from __future__ import annotations


def _merge_prompt_long(base: str | None, extra: str | None) -> str | None:
    base_text = str(base or "").strip()
    extra_text = str(extra or "").strip()
    if base_text and extra_text:
        return f"{base_text}\n{extra_text}"
    return base_text or extra_text or None


def spell_formula_prompt(
    spell_name: str,
    formula: str | None,
    *,
    subject: str = "wartosc",
    answer_placeholder: str | None = None,
    prompt_long: str | None = None,
) -> tuple[str, str | None, str | None]:
    spell_text = str(spell_name or "").strip() or "Czar"
    subject_text = str(subject or "").strip() or "wartosc"
    formula_text = str(formula or "").strip()

    prompt = f"{spell_text} - podaj {subject_text}"
    if formula_text:
        prompt += f" ({formula_text})"
    prompt += ":"

    details = None
    if formula_text:
        details = f"Rozlicz bazowa wartosc czaru: **{formula_text}**."

    placeholder = answer_placeholder
    if placeholder is None and formula_text:
        placeholder = formula_text

    return prompt, placeholder, _merge_prompt_long(details, prompt_long)
