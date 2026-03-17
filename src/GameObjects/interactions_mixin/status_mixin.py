from __future__ import annotations

from dataclasses import dataclass, field, replace
import logging
from typing import TYPE_CHECKING

from localization import localized_hint_pl, localize_term_pl

if TYPE_CHECKING:
    from statuses import Status

logger = logging.getLogger(__name__)


@dataclass
class StatusMixin:
    """
    Mixin do zarządzania statusami (unikalna lista Status, kompatybilna ze stringami).

    Kontrakt:
    - add_status przyjmuje wyłącznie instancje Status (stringi są odrzucane).
    - do odczytu danych statusów używaj helperów get_status / get_status_data,
      zamiast przechowywać duplikaty pól na aktorze.
    """

    statuses: list["Status"] = field(default_factory=list)

    def _ui_log(self, message: str) -> None:
        ui_log = getattr(self, "ui_log", None)
        if callable(ui_log):
            ui_log(message)
            return
        game = getattr(self, "game", None)
        if game is not None:
            game_ui_log = getattr(game, "ui_log", None)
            if callable(game_ui_log):
                game_ui_log(message)

    def _status_immunity_blocks(self, incoming: "Status") -> bool:
        incoming_id = incoming.id
        incoming_tags = set(getattr(incoming, "data", {}).get("effect_tags", []) or [])
        for s in self.statuses:
            data = getattr(s, "data", None) or {}
            immune_ids = set(data.get("immune_status_ids", []) or [])
            if incoming_id in immune_ids:
                return True
            immune_tags = set(data.get("immune_status_tags", []) or [])
            if incoming_tags and immune_tags.intersection(incoming_tags):
                return True
        return False

    def _maybe_prompt_status_info(self, status: "Status") -> None:
        data = getattr(status, "data", None) or {}
        if data.get("ui_choice_kind") == "adopted_ancestry":
            try:
                self._handle_adopted_ancestry_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "additional_lore":
            try:
                self._handle_additional_lore_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "armor_proficiency":
            try:
                self._handle_armor_proficiency_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "assurance":
            try:
                self._handle_assurance_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "canny_acumen":
            try:
                self._handle_canny_acumen_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "skill_training":
            try:
                self._handle_skill_training_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "terrain_stalker":
            try:
                self._handle_terrain_stalker_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "virtuosic_performer":
            try:
                self._handle_virtuosic_performer_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "weapon_proficiency":
            try:
                self._handle_weapon_proficiency_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "alchemist_research_field":
            try:
                self._handle_alchemist_research_field_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "animal_instinct":
            try:
                self._handle_animal_instinct_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "dragon_instinct":
            try:
                self._handle_dragon_instinct_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "fury_instinct":
            try:
                self._handle_fury_instinct_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "spirit_instinct":
            try:
                self._handle_spirit_instinct_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "bard_setup":
            try:
                self._handle_bard_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "bard_muse":
            try:
                self._handle_bard_muse_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "druid_setup":
            try:
                self._handle_druid_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "animal_companion_type":
            try:
                self._handle_animal_companion_type_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "champion_setup":
            try:
                self._handle_champion_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "fighter_setup":
            try:
                self._handle_fighter_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "monk_setup":
            try:
                self._handle_monk_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "ranger_setup":
            try:
                self._handle_ranger_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "sorcerer_setup":
            try:
                self._handle_sorcerer_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "wizard_setup":
            try:
                self._handle_wizard_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "rogue_setup":
            try:
                self._handle_rogue_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "cleric_setup":
            try:
                self._handle_cleric_setup_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "cleric_domain_initiate":
            try:
                self._handle_cleric_domain_initiate_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "champion_deitys_domain":
            try:
                self._handle_champion_deitys_domain_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "deific_weapon":
            try:
                self._handle_deific_weapon_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "adapted_cantrip":
            try:
                self._handle_adapted_cantrip_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "otherworldly_magic":
            try:
                self._handle_otherworldly_magic_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "fey_touched_gnome":
            try:
                self._handle_fey_touched_gnome_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "first_world_magic":
            try:
                self._handle_first_world_magic_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "gnome_obsession":
            try:
                self._handle_gnome_obsession_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "wellspring_gnome":
            try:
                self._handle_wellspring_gnome_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "ancestral_longevity":
            try:
                self._handle_ancestral_longevity_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "elven_lore":
            try:
                self._handle_elven_lore_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "goblin_lore":
            try:
                self._handle_goblin_lore_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "halfling_lore":
            try:
                self._handle_halfling_lore_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "skilled_heritage":
            try:
                self._handle_skilled_heritage_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "general_training":
            try:
                self._handle_general_training_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "natural_skill":
            try:
                self._handle_natural_skill_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "unconventional_weaponry":
            try:
                self._handle_unconventional_weaponry_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "elf_atavism":
            try:
                self._handle_elf_atavism_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "natural_ambition":
            try:
                self._handle_natural_ambition_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "versatile_heritage":
            try:
                self._handle_versatile_heritage_choice(status, data)
            except Exception:
                pass
        if data.get("ui_choice_kind") == "background_martial_disciple":
            try:
                self._handle_background_martial_disciple_choice(status, data)
            except Exception:
                pass
        prompt = data.get("ui_prompt")
        if not prompt:
            return
        prompt_long = data.get("ui_prompt_long")
        if self._in_character_creation_mode():
            self._ui_log(prompt)
            return
        try:
            from ui_client import get_ui_client  # lokalny import by unikać cykli

            ui_client = get_ui_client()
            if ui_client.enabled:
                try:
                    ui_client.prompt_info(prompt, prompt_long=prompt_long, source="status")
                    return
                except Exception:
                    pass
        except Exception:
            pass
        self._ui_log(prompt)
    
    @staticmethod
    def _labelize_choice(value: str) -> str:
        return localize_term_pl(value)

    def _in_character_creation_mode(self) -> bool:
        return bool(getattr(self, "character_creation_in_progress", False))

    def _key_ability_prompt(self, class_label: str) -> str:
        return (
            f"KROK 6A ({class_label}): wybierz Key Ability "
            "(mechanika: wybrana cecha dostaje klasowy boost +2)."
        )

    def _prompt_choice(
        self,
        prompt: str,
        choices: list[str],
        *,
        source: str,
        choice_meta: list[dict] | None = None,
    ) -> str | None:
        source_ui = str(source or "").strip() or "status"
        if source_ui == "status" and self._in_character_creation_mode():
            source_ui = "character_creation"
        prompt_image = None
        if source_ui == "character_creation":
            prompt_image = str(getattr(self, "image", "") or "").strip() or None
        try:
            from ui_client import get_ui_client

            ui_client = get_ui_client()
            if ui_client.enabled:
                return ui_client.prompt_choice(
                    prompt,
                    choices=choices,
                    source=source_ui,
                    layout="menu_numpad",
                    choice_meta=choice_meta,
                    image=prompt_image,
                )
            if not getattr(ui_client, "allow_cli_fallback", False):
                return None
        except Exception:
            return None
        try:
            return input(f"{prompt} {choices}: ").strip() or None
        except Exception:
            return None

    def _pick_choice_id(self, prompt: str, choices: list[str], *, source: str = "status") -> str | None:
        if not choices:
            return None
        entries: list[dict] = []
        for idx, item in enumerate(choices, start=1):
            raw = str(item or "").strip()
            label = self._labelize_choice(raw)
            desc = self._choice_description(raw)
            entries.append(
                {
                    "raw": raw,
                    "label": label,
                    "desc": desc,
                    "key": str(idx),
                }
            )

        labels = [entry["label"] for entry in entries]
        chosen_label = self._prompt_choice(prompt, labels, source=source, choice_meta=entries)
        if not chosen_label:
            return None

        by_raw = {str(entry["raw"]).strip().lower(): str(entry["raw"]).strip() for entry in entries}
        by_label = {str(entry["label"]).strip().lower(): str(entry["raw"]).strip() for entry in entries}

        text = str(chosen_label).strip()
        if text.lower() in by_raw:
            return by_raw[text.lower()]
        if text.lower() in by_label:
            return by_label[text.lower()]

        normalized = text.lower().replace("-", "_").replace(" ", "_")
        if normalized in by_raw:
            return by_raw[normalized]

        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(entries):
                return str(entries[idx]["raw"]).strip()
        return None

    @staticmethod
    def _status_ui_description(status: "Status" | None) -> str:
        if status is None:
            return ""
        data = getattr(status, "data", None) or {}
        return str(
            data.get("ui_prompt_long")
            or data.get("ui_description")
            or data.get("ui_prompt")
            or ""
        ).strip()

    @staticmethod
    def _first_line(text: str) -> str:
        raw = str(text or "").strip()
        if not raw:
            return ""
        for line in raw.splitlines():
            line = str(line).strip()
            if line:
                return line
        return ""

    @staticmethod
    def _structured_desc(name: str, fluff: str, mechanics: str, when: str | None = None) -> str:
        import re

        mechanics_raw = str(mechanics or "").strip()
        when_raw = str(when or "").strip()
        effect_raw = mechanics_raw
        if mechanics_raw:
            match_when = re.search(r"Kiedy:\s*(.*?)(?:\s*(?:\||;)\s*Efekt:|\s+Efekt:|$)", mechanics_raw, flags=re.IGNORECASE | re.DOTALL)
            match_effect = re.search(r"Efekt:\s*(.*)$", mechanics_raw, flags=re.IGNORECASE | re.DOTALL)
            mechanics_starts_with_meta = mechanics_raw.lstrip().lower().startswith("kiedy:") or mechanics_raw.lstrip().lower().startswith("efekt:")
            if mechanics_starts_with_meta:
                if match_when and not when_raw:
                    when_raw = str(match_when.group(1) or "").strip(" .;|")
                if match_effect:
                    effect_raw = str(match_effect.group(1) or "").strip()
        if not when_raw:
            when_raw = "Po wybraniu tej opcji."
        if not effect_raw:
            effect_raw = "Brak dodatkowego opisu mechaniki."
        when_lines = [line for line in re.split(r"\s*(?:\||\n)\s*", when_raw) if str(line or "").strip()]
        effect_lines = [line for line in re.split(r"\s*(?:\||\n)\s*", effect_raw) if str(line or "").strip()]
        if not when_lines:
            when_lines = ["Po wybraniu tej opcji."]
        if not effect_lines:
            effect_lines = ["Brak dodatkowego opisu mechaniki."]

        cleaned_when: list[str] = []
        cleaned_effect: list[str] = []
        for item in when_lines:
            text = str(item or "").strip().lstrip("-•").strip(" .;")
            if text:
                cleaned_when.append(text)
        for item in effect_lines:
            text = str(item or "").strip().lstrip("-•").strip()
            if text.lower().startswith("efekt:"):
                text = text.split(":", 1)[1].strip()
            if text:
                cleaned_effect.append(text)
        if not cleaned_when:
            cleaned_when = ["Po wybraniu tej opcji."]
        if not cleaned_effect:
            cleaned_effect = ["Brak dodatkowego opisu mechaniki."]

        lines = [
            f"Fluff: {str(fluff or '').strip() or '-'}",
            "Mechanika:",
            f"- Kiedy: {cleaned_when[0]}",
        ]
        for extra in cleaned_when[1:]:
            lines.append(f"  - {extra}")

        if len(cleaned_effect) == 1:
            lines.append(f"- Efekt: {cleaned_effect[0]}")
        else:
            lines.append("- Efekt:")
            for item in cleaned_effect:
                lines.append(f"  - {item}")
        return "\n".join(lines)

    @staticmethod
    def _is_structured_desc(text: str) -> bool:
        raw = str(text or "").lstrip().upper()
        return raw.startswith("NAZWA:") or raw.startswith("FLUFF:") or raw.startswith("MECHANIKA:") or raw.startswith("KIEDY:") or raw.startswith("EFEKT:")

    @staticmethod
    def _normalize_choice_id(value: object) -> str:
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _spell_id_alias(value: str) -> str:
        aliases = {
            "shield": "shield_cantrip",
            "detectmagic": "detect_magic",
            "acidsplash": "acid_splash",
        }
        return aliases.get(value, value)

    @staticmethod
    def _looks_like_spell_hint(text: str) -> bool:
        low = str(text or "").strip().lower()
        if not low:
            return False
        return low.startswith("cantrip:") or low.startswith("czar") or low.startswith("focus spell")

    @staticmethod
    def _spell_hint_has_concrete_mechanics(text: str) -> bool:
        low = str(text or "").strip().lower()
        if not low:
            return False
        mechanic_tokens = (
            "save",
            "rzut",
            "dc",
            "obra",
            "kryty",
            "stunned",
            "enfeebled",
            "immobilized",
            "ac",
            "speed",
            "predkos",
            "zasieg",
            "akcj",
            "tura",
            "+1",
            "-1",
        )
        return any(token in low for token in mechanic_tokens)

    @staticmethod
    def _event_fallback_hint(choice_id: str) -> str:
        normalized = StatusMixin._spell_id_alias(StatusMixin._normalize_choice_id(choice_id))
        if not normalized:
            return ""
        try:
            import GameObjects.events.all_events  # noqa: F401
            from GameObjects.events.registry import list_events
            from spell_management import classify_spell_tier
        except Exception:
            return ""

        events = dict(list_events() or {})
        event_cls = events.get(normalized)
        if event_cls is None:
            return ""

        tags: set[str] = set()
        for tag in list(getattr(event_cls, "spell_tags", []) or []):
            value = StatusMixin._normalize_choice_id(tag)
            if value:
                tags.add(value)
        for tag in list(getattr(event_cls, "default_tags", []) or []):
            value = StatusMixin._normalize_choice_id(tag)
            if value:
                tags.add(value)
        for tradition in list(getattr(event_cls, "magic_traditions", []) or []):
            value = StatusMixin._normalize_choice_id(getattr(tradition, "value", tradition))
            if value:
                tags.add(value)
        if "arcana" in tags:
            tags.add("arcane")
        if "arcane" in tags:
            tags.add("arcana")

        tier = str(classify_spell_tier(list(tags)) or "").strip().lower()
        if tier == "cantrip":
            tier_label = "Cantrip"
        elif tier == "focus":
            tier_label = "Focus"
        elif tier.startswith("rank_"):
            try:
                tier_label = f"Ranga {max(1, int(tier.split('_', 1)[1]))}"
            except Exception:
                tier_label = "Czar"
        else:
            tier_label = "Akcja"

        try:
            actions_cost = max(1, int(getattr(event_cls, "actions_cost", 1) or 1))
        except Exception:
            actions_cost = 1
        cost_label = f"Koszt: {actions_cost} akcja" if actions_cost == 1 else f"Koszt: {actions_cost} akcje"

        range_raw = getattr(event_cls, "range_feet", None)
        if isinstance(range_raw, int):
            range_label = f"Zasieg: {max(0, int(range_raw))} ft"
        elif "touch" in tags:
            range_label = "Zasieg: dotyk"
        else:
            range_label = "Zasieg: wg efektu"

        traditions = [item for item in ("arcane", "divine", "occult", "primal") if item in tags]
        if traditions:
            traditions_label = "Tradycja: " + ", ".join(localize_term_pl(item) for item in traditions)
        else:
            traditions_label = "Tradycja: -"

        prompt = str(getattr(event_cls, "prompt", "") or "").strip()
        if not prompt:
            prompt = str(getattr(event_cls, "__doc__", "") or "").strip()
        prompt_line = StatusMixin._first_line(prompt)
        meta_lines = [tier_label, cost_label, range_label, traditions_label]
        if prompt_line:
            return "\n".join([prompt_line] + [f"- {line}" for line in meta_lines]).strip()
        return "\n".join(f"- {line}" for line in meta_lines).strip()

    @staticmethod
    def _domain_spell_fallback_hint(spell_id: str) -> str:
        normalized = StatusMixin._spell_id_alias(StatusMixin._normalize_choice_id(spell_id))
        if not normalized:
            return ""
        try:
            from GameObjects.events.magic.focus_spells.cleric.domain_spell_events import DOMAIN_SPELL_SPECS
        except Exception:
            return ""

        spec = DOMAIN_SPELL_SPECS.get(normalized)
        if spec is None:
            return ""

        mode = str(getattr(spec, "mode", "") or "").strip().lower()
        mode_desc_map = {
            "enemy_damage": "Atak czarem w przeciwnika; obrazenia rozliczane przez event.",
            "enemy_status": "Naklada status na przeciwnika (zalezne od rzutu obronnego).",
            "ally_heal": "Leczenie sojusznika.",
            "ally_bonus": "Daje czasowy bonus sojusznikowi.",
            "ally_status": "Naklada czasowy efekt na sojusznika.",
            "self_bonus": "Daje czasowy bonus tobie.",
            "self_status": "Naklada czasowy efekt na ciebie.",
            "self_speed_bonus": "Zwieksza twoja predkosc na czas trwania.",
            "self_move": "Pozwala wykonac ruch specjalny.",
            "touch_of_undeath": "Dotyk: zywi otrzymuja negative damage, undead sa leczeni.",
            "utility": "Efekt uzytkowy, czesto rozliczany recznie.",
        }
        parts: list[str] = []
        mode_desc = mode_desc_map.get(mode)
        if mode_desc:
            parts.append(mode_desc)

        save_type = str(getattr(spec, "save_type", "") or "").strip().lower()
        if save_type:
            save_label = localize_term_pl(save_type)
            if bool(getattr(spec, "basic_save", False)):
                parts.append(f"Rzut obronny: basic {save_label}.")
            else:
                parts.append(f"Rzut obronny: {save_label}.")

        damage_type = str(getattr(spec, "damage_type", "") or "").strip()
        if damage_type and mode in {"enemy_damage", "touch_of_undeath"}:
            parts.append(f"Typ obrazen: {localize_term_pl(damage_type)}.")

        persistent_amount = int(getattr(spec, "persistent_damage_amount", 0) or 0)
        persistent_type = str(getattr(spec, "persistent_damage_type", "") or "").strip()
        if persistent_amount > 0 and persistent_type:
            parts.append(
                f"Dodatkowo {persistent_amount} persistent {localize_term_pl(persistent_type)}."
            )

        status_id = str(getattr(spec, "status_id", "") or "").strip()
        if status_id:
            parts.append(f"Status: {localize_term_pl(status_id)}.")

        bonus_tags = [str(item or "").strip() for item in list(getattr(spec, "bonus_tags", ()) or []) if str(item or "").strip()]
        bonus_value = int(getattr(spec, "bonus_value", 0) or 0)
        if bonus_tags and bonus_value:
            sign = "-" if bool(getattr(spec, "is_penalty", False)) else "+"
            tags_label = ", ".join(localize_term_pl(tag) for tag in bonus_tags)
            parts.append(f"{sign}{abs(bonus_value)} do: {tags_label}.")

        speed_bonus = int(getattr(spec, "add_speed_bonus_feet", 0) or 0)
        speed_penalty = int(getattr(spec, "add_speed_penalty_feet", 0) or 0)
        if speed_bonus:
            parts.append(f"Predkosc: +{abs(speed_bonus)} ft.")
        if speed_penalty:
            parts.append(f"Predkosc: -{abs(speed_penalty)} ft.")

        detail = StatusMixin._first_line(str(getattr(spec, "prompt_long", "") or ""))
        if detail:
            parts.append(detail)
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        return "\n".join([parts[0]] + [f"- {part}" for part in parts[1:]]).strip()

    @staticmethod
    def _hint_fluff_prefix(text: str) -> str:
        raw = str(text or "").strip()
        if not raw:
            return ""
        marker_idx = raw.lower().find("mechanika:")
        if marker_idx >= 0:
            raw = raw[:marker_idx].strip(" .;|-")
        return StatusMixin._first_line(raw).strip(" .;|-")

    @staticmethod
    def _compact_hint_summary(text: str, max_parts: int = 2) -> str:
        parts: list[str] = []
        for raw_line in str(text or "").splitlines():
            line = str(raw_line or "").strip().lstrip("-•").strip()
            if not line:
                continue
            parts.append(line.rstrip(" .;"))
            if len(parts) >= max_parts:
                break
        return "; ".join(parts).strip()

    @staticmethod
    def _cleric_deity_setup_hint(choice_id: str) -> str:
        normalized = StatusMixin._normalize_choice_id(choice_id)
        if not normalized:
            return ""

        try:
            from statuses.classes.cleric.cleric import (
                CLERIC_DEITY_DIVINE_SKILL_CHOICES,
                CLERIC_DEITY_FLAVOR_TEXT,
                CLERIC_DEITY_OPTIONS,
                CLERIC_DOMAIN_ADVANCED_SPELLS,
                CLERIC_DOMAIN_INITIAL_SPELLS,
            )
        except Exception:
            return ""

        deity_data = dict(CLERIC_DEITY_OPTIONS.get(normalized, {}) or {})
        if not deity_data:
            return ""

        favored_weapon = str(deity_data.get("favored_weapon") or "wybor gracza").strip()
        divine_skills = [
            str(item or "").strip()
            for item in list(CLERIC_DEITY_DIVINE_SKILL_CHOICES.get(normalized) or [])
            if str(item or "").strip()
        ]
        fonts = [
            str(item or "").strip()
            for item in list(deity_data.get("font_options") or [])
            if str(item or "").strip()
        ]
        domains = [
            str(item or "").strip()
            for item in list(deity_data.get("domain_choices") or [])
            if str(item or "").strip()
        ]

        skills_label = ", ".join(localize_term_pl(item) for item in divine_skills) if divine_skills else "-"
        fonts_label = ", ".join(localize_term_pl(item) for item in fonts) if fonts else "-"
        domains_label = ", ".join(localize_term_pl(item) for item in domains) if domains else "-"

        fluff = str(CLERIC_DEITY_FLAVOR_TEXT.get(normalized) or "").strip()
        if not fluff:
            fluff = StatusMixin._hint_fluff_prefix(localized_hint_pl(normalized))
        if not fluff:
            fluff = f"Bostwo {localize_term_pl(normalized)}."

        mechanics_lines = [
            f"Ulubiona bron: {localize_term_pl(favored_weapon)}.",
            f"Divine skill: {skills_label}.",
            f"Dozwolony divine font: {fonts_label}.",
            f"Domeny do wyboru: {domains_label}.",
        ]

        for domain_id in domains:
            spell_id = str(CLERIC_DOMAIN_INITIAL_SPELLS.get(domain_id) or "").strip()
            advanced_spell_id = str(CLERIC_DOMAIN_ADVANCED_SPELLS.get(domain_id) or "").strip()
            spell_summary = StatusMixin._compact_hint_summary(StatusMixin._domain_spell_fallback_hint(spell_id))

            domain_parts: list[str] = []
            if spell_id:
                domain_parts.append(f"czar domenowy: {localize_term_pl(spell_id)}")
            if advanced_spell_id:
                domain_parts.append(f"advanced domain spell: {localize_term_pl(advanced_spell_id)}")
            if spell_summary:
                domain_parts.append(f"mechanika czaru: {spell_summary}")

            if domain_parts:
                mechanics_lines.append(
                    f"Domena {localize_term_pl(domain_id)}: {'; '.join(domain_parts)}."
                )

        return StatusMixin._structured_desc(
            name=localize_term_pl(normalized),
            fluff=fluff,
            mechanics="\n".join(mechanics_lines),
            when="Po wybraniu tego bostwa dla kleryka.",
        )

    @staticmethod
    def _animal_companion_choice_hint(choice_id: str) -> str:
        normalized = StatusMixin._normalize_choice_id(choice_id)
        if not normalized:
            return ""

        try:
            from GameObjects.companions import animal_companion_type_ids, companion_type_data
        except Exception:
            return ""

        if normalized not in set(animal_companion_type_ids()):
            return ""

        data = dict(companion_type_data(normalized) or {})
        label = str(data.get("label") or normalized.title()).strip() or normalized.title()
        speed = max(5, int(data.get("land_speed_feet", 25) or 25))
        size = str(data.get("size", "small") or "small").strip()
        hp_ancestry = max(1, int(data.get("hp_ancestry", 6) or 6))
        support = str(data.get("support_benefit") or "").strip()
        special = str(data.get("special") or "").strip()
        attacks = list(data.get("attacks") or [])

        fluff_map = {
            "badger": "Uporczywy towarzysz do kontroli pola i blokowania ruchu wroga.",
            "bear": "Mocny drapieznik do dokladania dodatkowych obrazen po twoim trafieniu.",
            "bird": "Szybki nekacz, ktory pomaga nakladac bleed i trzymac dystans.",
            "cat": "Zwinny lowca do ustawiania off-guard i wykorzystywania luk w obronie.",
            "dromaeosaur": "Blyskawiczny raptor, dobry do flankowania i agresywnego wejscia w zwarcie.",
            "horse": "Mobilny mount do szybkiego przemieszczania sie i wzmacniania szarzy.",
            "snake": "Kontroler reakcji, ktory otwiera ci bezpieczne okna na akcje ofensywne.",
            "wolf": "Lowca scigajacy ofiare i spowalniajacy cel po twoich trafieniach.",
        }

        attack_parts: list[str] = []
        for attack in attacks:
            attack_label = str(attack.get("label") or attack.get("id") or "Strike").strip()
            damage = str(attack.get("damage") or "").strip()
            damage_type = str(attack.get("damage_type") or "").strip()
            traits = [str(item or "").strip() for item in list(attack.get("traits") or []) if str(item or "").strip()]
            trait_label = f" ({', '.join(localize_term_pl(item) for item in traits)})" if traits else ""
            if damage and damage_type:
                attack_parts.append(f"{attack_label} {damage} {localize_term_pl(damage_type)}{trait_label}")
            elif damage:
                attack_parts.append(f"{attack_label} {damage}{trait_label}")
            else:
                attack_parts.append(f"{attack_label}{trait_label}")

        mechanics_lines = [
            "Po wybraniu companion pojawia sie w walce jako osobny obiekt; 1 akcja na Command Animal Companion daje mu 2 akcje.",
            f"Rozmiar: {localize_term_pl(size)}.",
            f"Predkosc: {speed} ft.",
            f"Skalowanie: HP i AC rosna z poziomem wlasciciela; bazowe hp ancestry dla tego typu = {hp_ancestry}.",
        ]
        if attack_parts:
            mechanics_lines.append(f"Ataki: {'; '.join(attack_parts)}.")
        if support:
            mechanics_lines.append(f"Support: {support}")
        if special:
            mechanics_lines.append(f"Special: {special}")

        return StatusMixin._structured_desc(
            name=label,
            fluff=fluff_map.get(normalized, f"Wybierasz typ zwierzecego towarzysza: {label}."),
            mechanics="\n".join(mechanics_lines),
            when="Przy wyborze typu Animal Companion.",
        )

    @staticmethod
    def _class_setup_fallback_hint(choice_id: str) -> str:
        normalized = StatusMixin._normalize_choice_id(choice_id)
        if not normalized:
            return ""

        # Cleric setup: deity / doctrine / font / domain / favored weapon.
        try:
            from statuses.classes.cleric.cleric import (
                CLERIC_DEITY_OPTIONS,
                CLERIC_DOMAIN_ADVANCED_SPELLS,
                CLERIC_DOMAIN_DESCRIPTIONS,
                CLERIC_DEITY_DIVINE_SKILL_CHOICES,
                CLERIC_DOMAIN_INITIAL_SPELLS,
                CLERIC_FAVORED_WEAPON_CHOICES,
            )

            if normalized in {"cloistered_cleric", "warpriest"}:
                if normalized == "cloistered_cleric":
                    return (
                        "Doktryna kleryka skupiona na czarach. "
                        "Mechanika: automatycznie dodaje Domain Initiate i koncentruje rozwój na magii."
                    )
                return (
                    "Doktryna kleryka bojowego. "
                    "Mechanika: otrzymujesz Shield Block; dla ulubionej broni typu simple/unarmed "
                    "dostajesz tez Deadly Simplicity."
                )

            if normalized in {"heal", "harm"}:
                if normalized == "heal":
                    return (
                        "Boski font leczenia. "
                        "Mechanika: przygotowujesz dodatkowe ladunki czaru Heal (zarzadzanie slotami prowadzisz w UI/na karcie)."
                    )
                return (
                    "Boski font zadawania ran. "
                    "Mechanika: przygotowujesz dodatkowe ladunki czaru Harm (zarzadzanie slotami prowadzisz w UI/na karcie)."
                )

            if normalized in CLERIC_DEITY_OPTIONS:
                return StatusMixin._cleric_deity_setup_hint(normalized)

            if normalized in CLERIC_DOMAIN_INITIAL_SPELLS:
                domain_spell = str(CLERIC_DOMAIN_INITIAL_SPELLS.get(normalized) or "")
                advanced_spell = str(CLERIC_DOMAIN_ADVANCED_SPELLS.get(normalized) or "")
                domain_desc = str(CLERIC_DOMAIN_DESCRIPTIONS.get(normalized) or "").strip()
                domain_desc_first = StatusMixin._first_line(domain_desc)
                if domain_spell:
                    advanced_part = f"\n- advanced domain spell: {localize_term_pl(advanced_spell)}" if advanced_spell else ""
                    return (
                        f"Domena kleryka {localize_term_pl(normalized)}. "
                        f"{domain_desc_first}\n"
                        "Mechanika:\n"
                        f"- przy Domain Initiate dodajesz czar domenowy: {localize_term_pl(domain_spell)}"
                        f"{advanced_part}"
                    )
                return (
                    f"Domena kleryka {localize_term_pl(normalized)}.\n"
                    "Mechanika:\n"
                    "- odblokowuje czar domenowy przy Domain Initiate."
                )

            if normalized in set(CLERIC_FAVORED_WEAPON_CHOICES):
                return (
                    f"Ulubiona bron bostwa: {localize_term_pl(normalized)}. "
                    "Mechanika: zapisywana w setupie kleryka; moze odblokowac efekty doktryny Warpriest."
                )
        except Exception:
            pass

        # Druid setup.
        try:
            from statuses.classes.druid.druid import (
                DRUID_ORDER_CHOICES,
                DRUID_ORDER_FOCUS_BONUS,
                DRUID_ORDER_SKILLS,
                DRUID_ORDER_SPELLS,
                DRUID_ORDER_START_FEATS,
                DRUID_ORDER_UI_DETAILS,
            )

            if normalized in set(DRUID_ORDER_CHOICES):
                skill = str(DRUID_ORDER_SKILLS.get(normalized) or "")
                feat = str(DRUID_ORDER_START_FEATS.get(normalized) or "")
                spell = str(DRUID_ORDER_SPELLS.get(normalized) or "")
                focus_bonus = int(DRUID_ORDER_FOCUS_BONUS.get(normalized) or 0)
                details = dict(DRUID_ORDER_UI_DETAILS.get(normalized) or {})
                starting_focus = max(0, 1 + focus_bonus)
                focus_line = (
                    f"bonus Focus: +{focus_bonus} (łącznie {starting_focus} Focus Point na starcie)."
                )
                effect_lines = [
                    f"trained skill: {localize_term_pl(skill)}.",
                    focus_line,
                    f"feat startowy - {localize_term_pl(feat)}: {str(details.get('feat_summary') or 'Dodaje startowy feat tego kręgu.').strip()}",
                    f"order spell - {localize_term_pl(spell)}: {str(details.get('spell_summary') or 'Dodaje focus spell tego kręgu.').strip()}",
                ]
                return StatusMixin._structured_desc(
                    name=f"Krąg druida: {localize_term_pl(normalized)}",
                    fluff=str(details.get("fluff") or f"Krąg druida: {localize_term_pl(normalized)}."),
                    mechanics="\n".join(effect_lines),
                    when="Po wybraniu tego kręgu podczas setupu druida.",
                )
        except Exception:
            pass

        animal_companion_hint = StatusMixin._animal_companion_choice_hint(normalized)
        if animal_companion_hint:
            return animal_companion_hint

        # Ranger setup.
        if normalized == "flurry":
            return (
                "Hunter's Edge: Flurry. "
                "Mechanika: przeciw Hunt Prey zmniejsza MAP dla kolejnych Strike'ow "
                "(2. atak: -2 agile/-3 standard; 3+: -4 agile/-6 standard)."
            )
        if normalized == "precision":
            return (
                "Hunter's Edge: Precision. "
                "Mechanika: raz na ture przeciw Hunt Prey dodajesz dodatkowe precision damage."
            )
        if normalized == "outwit":
            return (
                "Hunter's Edge: Outwit. "
                "Mechanika: przeciw Hunt Prey zyskujesz premie taktyczne; w silniku m.in. +1 circumstance do AC "
                "oraz +2 do wybranych testow (Stealth/Recall Knowledge)."
            )

        # Rogue setup.
        if normalized == "ruffian":
            return (
                "Racket lotrzyka: Ruffian. "
                "Mechanika: Key Ability moze byc STR albo DEX; dostajesz trained w Intimidation, "
                "medium armor training oraz brutalniejszy setup pod walke wręcz. "
                "W tym buildzie medium armor training dziala, a krytyczna specjalizacja Ruffiana dla simple weapon "
                "jest jeszcze oznaczona jako TODO."
            )
        if normalized == "scoundrel":
            return (
                "Racket lotrzyka: Scoundrel. "
                "Mechanika: Key Ability moze byc CHA albo DEX; dostajesz trained w Deception i Diplomacy. "
                "Success na Feint daje celowi off-guard przeciw twoim melee atakom do konca twojej nastepnej tury, "
                "a critical success rozszerza to na wszystkie melee ataki do konca twojej nastepnej tury."
            )
        if normalized == "thief":
            return (
                "Racket lotrzyka: Thief. "
                "Mechanika: Key Ability jest tylko DEX i dostajesz trained w Thievery. "
                "Przy finesse melee Strike'ach gra uzywa DEX zamiast STR w promptcie obrazen, "
                "wiec ten racket najmocniej wspiera zrecznosciowego lotrzyka."
            )

        # Sorcerer setup: bloodline + variants.
        try:
            from statuses.classes.sorcerer.sorcerer import (
                SORCERER_BLOODLINE_BLOOD_MAGIC,
                SORCERER_BLOODLINE_CHOICES,
                SORCERER_BLOODLINE_GRANTED_SPELLS,
                SORCERER_BLOODLINE_INITIAL_FOCUS_SPELLS,
                SORCERER_BLOODLINE_SKILLS,
                SORCERER_BLOODLINE_TRADITIONS,
                SORCERER_DRACONIC_TYPE_DAMAGE,
                SORCERER_ELEMENTAL_TYPE_DAMAGE,
            )

            if normalized in set(SORCERER_BLOODLINE_CHOICES):
                tradition = str(SORCERER_BLOODLINE_TRADITIONS.get(normalized) or "")
                skills = list(SORCERER_BLOODLINE_SKILLS.get(normalized) or [])
                spells = dict(SORCERER_BLOODLINE_GRANTED_SPELLS.get(normalized) or {})
                focus_spell = str(SORCERER_BLOODLINE_INITIAL_FOCUS_SPELLS.get(normalized) or "")
                blood_magic = str(SORCERER_BLOODLINE_BLOOD_MAGIC.get(normalized) or "").strip()
                cantrip = str(spells.get("cantrip") or "")
                rank1 = str(spells.get("rank_1") or "")
                cantrip_summary = StatusMixin._compact_hint_summary(StatusMixin._event_fallback_hint(cantrip))
                rank1_summary = StatusMixin._compact_hint_summary(StatusMixin._event_fallback_hint(rank1))
                focus_summary = StatusMixin._compact_hint_summary(StatusMixin._event_fallback_hint(focus_spell))
                skill_label = ", ".join(localize_term_pl(item) for item in skills) if skills else "-"
                effect_lines = [
                    f"Tradycja: {localize_term_pl(tradition)}.",
                    f"Umiejetnosci linii krwi: {skill_label}.",
                    f"Cantrip linii krwi: {localize_term_pl(cantrip)}.",
                    f"Czar 1. rangi linii krwi: {localize_term_pl(rank1)}.",
                    f"Focus spell linii krwi: {localize_term_pl(focus_spell)}.",
                ]
                if cantrip_summary:
                    effect_lines.append(f"Cantrip - mechanika {localize_term_pl(cantrip)}: {cantrip_summary}.")
                if rank1_summary:
                    effect_lines.append(f"Czar 1. rangi - mechanika {localize_term_pl(rank1)}: {rank1_summary}.")
                if focus_summary:
                    effect_lines.append(f"Focus spell - mechanika {localize_term_pl(focus_spell)}: {focus_summary}.")
                if blood_magic:
                    effect_lines.append(f"Blood Magic: {blood_magic}")
                return StatusMixin._structured_desc(
                    name=f"Linia krwi czarownika: {localize_term_pl(normalized)}",
                    fluff=f"Linia krwi czarownika: {localize_term_pl(normalized)}.",
                    mechanics="\n".join(effect_lines),
                    when="Po wybraniu tej opcji",
                )

            if normalized in dict(SORCERER_DRACONIC_TYPE_DAMAGE):
                dmg = str(SORCERER_DRACONIC_TYPE_DAMAGE.get(normalized) or "")
                return (
                    f"Typ smoczej krwi: {localize_term_pl(normalized)}. "
                    f"Mechanika: ustawia damage type linii draconic na {localize_term_pl(dmg)}."
                )

            if normalized in dict(SORCERER_ELEMENTAL_TYPE_DAMAGE):
                dmg = str(SORCERER_ELEMENTAL_TYPE_DAMAGE.get(normalized) or "")
                return (
                    f"Typ zywiolu: {localize_term_pl(normalized)}. "
                    f"Mechanika: ustawia damage type linii elemental na {localize_term_pl(dmg)}."
                )
        except Exception:
            pass

        # Wizard setup.
        try:
            from statuses.classes.wizard.wizard import (
                WIZARD_ARCANE_STUDY_CHOICES,
                WIZARD_ARCANE_THESIS_CHOICES,
                WIZARD_BONDED_ITEM_CHOICES,
                WIZARD_SCHOOL_FOCUS_SPELLS,
                WIZARD_SCHOOL_INITIAL_SPELLS,
                WIZARD_UNIVERSALIST_FOCUS_SPELL,
            )

            if normalized in set(WIZARD_ARCANE_STUDY_CHOICES):
                if normalized == "universalist":
                    return (
                        "Arcane Study: Universalist. "
                        "Mechanika: nie wybierasz szkoly, ale dostajesz automatycznie focus spell "
                        f"{localize_term_pl(WIZARD_UNIVERSALIST_FOCUS_SPELL)} oraz dodatkowy class feat na starcie."
                    )
                school_spell = str(WIZARD_SCHOOL_INITIAL_SPELLS.get(normalized) or "")
                focus_spell = str(WIZARD_SCHOOL_FOCUS_SPELLS.get(normalized) or "")
                school_summary = StatusMixin._compact_hint_summary(StatusMixin._event_fallback_hint(school_spell))
                focus_summary = StatusMixin._compact_hint_summary(StatusMixin._event_fallback_hint(focus_spell))
                detail_parts = [
                    f"Arcane Study: szkola {localize_term_pl(normalized)}.",
                    f"Mechanika: specjalizacja szkolna; bonusowy czar={localize_term_pl(school_spell)}, "
                    f"focus spell={localize_term_pl(focus_spell)}, dodatkowy przygotowany cantrip i dodatkowy slot szkolny kazdej rangi.",
                ]
                if school_summary:
                    detail_parts.append(f"Czar szkoly - {localize_term_pl(school_spell)}: {school_summary}.")
                if focus_summary:
                    detail_parts.append(f"Focus spell - {localize_term_pl(focus_spell)}: {focus_summary}.")
                return " ".join(detail_parts)

            if normalized in set(WIZARD_ARCANE_THESIS_CHOICES):
                thesis_map = {
                    "improved_familiar_attunement": "Bond Source=familiar i akcja Drain Familiar.",
                    "metamagical_experimentation": "Wybierasz dodatkowy metamagic feat na setupie.",
                    "staff_nexus": "Bonded item staje sie kosturem. Wybierasz 1 cantrip i 1 czar 1. rangi do makeshift staffu; podczas daily preparations staff dostaje ladunki rowne najwyzszej randze slotu, a dodatkowe ladunki mozesz doladowac poświęcając przygotowane sloty.",
                    "spell_blending": "Na początku scenariusza (daily preparations) pozwala wymieniac sloty i zamieniac slot na +2 cantripy.",
                    "spell_substitution": "Poza walka odblokowuje akcje 10-minutowej podmiany przygotowanego czaru (1 raz na scenariusz).",
                }
                return (
                    f"Arcane Thesis: {localize_term_pl(normalized)}. "
                    f"Mechanika: {thesis_map.get(normalized, 'Wplywa na przygotowanie i zarzadzanie czarami czarodzieja.')}"
                )

            if normalized in set(WIZARD_BONDED_ITEM_CHOICES):
                return (
                    f"Arcane Bond: {localize_term_pl(normalized)}. "
                    "Mechanika: zapisuje typ bonded item i aktywuje Drain Bonded Item."
                )
        except Exception:
            pass

        return ""

    def _choice_description(self, choice_id: str) -> str:
        raw = str(choice_id or "").strip()
        if not raw:
            return ""
        normalized_raw = self._normalize_choice_id(raw)

        try:
            from character_creation.catalog import resolve_status

            status = resolve_status(raw)
        except Exception:
            status = None

        desc = self._status_ui_description(status)
        localized_hint = localized_hint_pl(raw)
        if not localized_hint:
            localized_hint = localized_hint_pl(normalized_raw)
        class_hint = self._class_setup_fallback_hint(raw)
        event_hint = self._event_fallback_hint(raw)

        is_deity_choice = False
        try:
            from statuses.classes.cleric.cleric import CLERIC_DEITY_OPTIONS

            is_deity_choice = normalized_raw in {
                str(item).strip().lower() for item in list(CLERIC_DEITY_OPTIONS.keys()) if str(item).strip()
            }
        except Exception:
            is_deity_choice = False

        if is_deity_choice and class_hint:
            hint = class_hint
        else:
            hint = localized_hint or class_hint or event_hint
            if (
                localized_hint
                and event_hint
                and self._looks_like_spell_hint(localized_hint)
                and not self._spell_hint_has_concrete_mechanics(localized_hint)
            ):
                hint = event_hint
            if (
                localized_hint
                and class_hint
                and (
                    "efekt zalezy od opcji:" in str(localized_hint).lower()
                    or "brak dodatkowego opisu mechaniki." in str(localized_hint).lower()
                )
            ):
                hint = class_hint
        structured_source = ""
        if self._is_structured_desc(desc):
            structured_source = str(desc or "")
        elif self._is_structured_desc(hint):
            structured_source = str(hint or "")

        if structured_source:
            name = self._labelize_choice(raw)
            fluff = "Opcja wyboru."
            mechanics = ""
            when = ""
            effect = ""
            current_section = ""
            for raw_line in str(structured_source).splitlines():
                line = str(raw_line or "").strip()
                if not line:
                    continue
                normalized_line = line.lstrip("-• ").strip()
                low = normalized_line.lower()
                if low.startswith("nazwa:"):
                    name = normalized_line.split(":", 1)[1].strip() or name
                    current_section = "name"
                elif low.startswith("fluff:"):
                    fluff = normalized_line.split(":", 1)[1].strip() or fluff
                    current_section = "fluff"
                elif low.startswith("mechanika:"):
                    mechanics = normalized_line.split(":", 1)[1].strip() or mechanics
                    current_section = "mechanics"
                elif low.startswith("kiedy:"):
                    payload = normalized_line.split(":", 1)[1].strip()
                    when = payload or when
                    current_section = "when"
                elif low.startswith("efekt:"):
                    payload = normalized_line.split(":", 1)[1].strip()
                    effect = payload or effect
                    current_section = "effect"
                elif current_section == "when":
                    when = f"{when}\n{normalized_line}".strip()
                elif current_section == "effect":
                    effect = f"{effect}\n{normalized_line}".strip()
                elif current_section == "mechanics":
                    mechanics = f"{mechanics}\n{normalized_line}".strip()
            if effect:
                mechanics = f"{mechanics}\nEfekt: {effect}".strip()
            return self._structured_desc(name=name, fluff=fluff, mechanics=mechanics or "Brak dodatkowego opisu mechaniki.", when=when or None)

        label = self._labelize_choice(raw)
        text = str(desc or hint or "").strip()
        fluff = self._first_line(desc) or self._first_line(hint) or f"Wybierasz: {label}."
        mechanics = text or f"Efekt zalezy od opcji: {label}."

        low = text.lower()
        marker = "mechanika:"
        marker_idx = low.find(marker)
        if marker_idx >= 0:
            prefix = str(text[:marker_idx]).strip(" .;|-")
            suffix = str(text[marker_idx + len(marker) :]).strip()
            if prefix:
                fluff = prefix
            if suffix:
                mechanics = suffix
        return self._structured_desc(label, fluff, mechanics)

    def _replace_status_data(self, status: "Status", data_updates: dict) -> bool:
        if not isinstance(data_updates, dict):
            return False
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(getattr(item, "data", None) or {})
                    new_data.update(data_updates)
                    self.statuses[idx] = replace(item, data=new_data)
                    return True
        except Exception:
            return False
        return False

    @staticmethod
    def _general_feat_registry() -> dict[str, tuple[str, str]]:
        return {
            "additional_lore": ("statuses.general.additional_skill_feats", "ADDITIONAL_LORE_STATUS"),
            "adopted_ancestry": ("statuses.general.adopted_ancestry", "ADOPTED_ANCESTRY_STATUS"),
            "alchemical_crafting": ("statuses.general.additional_skill_feats", "ALCHEMICAL_CRAFTING_STATUS"),
            "arcane_sense": ("statuses.general.additional_skill_feats", "ARCANE_SENSE_STATUS"),
            "armor_proficiency": ("statuses.general.armor_proficiency", "ARMOR_PROFICIENCY_STATUS"),
            "assurance": ("statuses.general.assurance", "ASSURANCE_STATUS"),
            "bargain_hunter": ("statuses.backgrounds.skill_feats", "BARGAIN_HUNTER_STATUS"),
            "battle_medicine": ("statuses.backgrounds.skill_feats", "BATTLE_MEDICINE_STATUS"),
            "breath_control": ("statuses.general.breath_control", "BREATH_CONTROL_STATUS"),
            "canny_acumen": ("statuses.general.canny_acumen", "CANNY_ACUMEN_STATUS"),
            "cat_fall": ("statuses.backgrounds.skill_feats", "CAT_FALL_STATUS"),
            "charming_liar": ("statuses.backgrounds.skill_feats", "CHARMING_LIAR_STATUS"),
            "combat_climber": ("statuses.general.additional_skill_feats", "COMBAT_CLIMBER_STATUS"),
            "courtly_graces": ("statuses.backgrounds.skill_feats", "COURTLY_GRACES_STATUS"),
            "diehard": ("statuses.general.diehard", "DIEHARD_STATUS"),
            "dubious_knowledge": ("statuses.general.dubious_knowledge", "DUBIOUS_KNOWLEDGE_STATUS"),
            "experienced_professional": ("statuses.general.additional_skill_feats", "EXPERIENCED_PROFESSIONAL_STATUS"),
            "experienced_smuggler": ("statuses.backgrounds.skill_feats", "EXPERIENCED_SMUGGLER_STATUS"),
            "experienced_tracker": ("statuses.backgrounds.skill_feats", "EXPERIENCED_TRACKER_STATUS"),
            "fascinating_performance": ("statuses.backgrounds.skill_feats", "FASCINATING_PERFORMANCE_STATUS"),
            "fast_recovery": ("statuses.general.additional_skill_feats", "FAST_RECOVERY_STATUS"),
            "feather_step": ("statuses.general.additional_skill_feats", "FEATHER_STEP_STATUS"),
            "fleet": ("statuses.general.fleet", "FLEET_STATUS"),
            "forager": ("statuses.backgrounds.skill_feats", "FORAGER_STATUS"),
            "group_coercion": ("statuses.general.additional_skill_feats", "GROUP_COERCION_STATUS"),
            "group_impression": ("statuses.backgrounds.skill_feats", "GROUP_IMPRESSION_STATUS"),
            "hefty_hauler": ("statuses.backgrounds.skill_feats", "HEFTY_HAULER_STATUS"),
            "hobnobber": ("statuses.backgrounds.skill_feats", "HOBNOBBER_STATUS"),
            "impressive_performance": ("statuses.backgrounds.skill_feats", "IMPRESSIVE_PERFORMANCE_STATUS"),
            "incredible_initiative": ("statuses.general.incredible_initiative", "INCREDIBLE_INITIATIVE_STATUS"),
            "intimidating_glare": ("statuses.backgrounds.skill_feats", "INTIMIDATING_GLARE_STATUS"),
            "lengthy_diversion": ("statuses.general.additional_skill_feats", "LENGTHY_DIVERSION_STATUS"),
            "multilingual": ("statuses.backgrounds.skill_feats", "MULTILINGUAL_STATUS"),
            "natural_medicine": ("statuses.backgrounds.skill_feats", "NATURAL_MEDICINE_STATUS"),
            "oddity_identification": ("statuses.backgrounds.skill_feats", "ODDITY_IDENTIFICATION_STATUS"),
            "pickpocket": ("statuses.backgrounds.skill_feats", "PICKPOCKET_STATUS"),
            "quick_coercion": ("statuses.backgrounds.skill_feats", "QUICK_COERCION_STATUS"),
            "quick_identification": ("statuses.general.additional_skill_feats", "QUICK_IDENTIFICATION_STATUS"),
            "quick_jump": ("statuses.backgrounds.skill_feats", "QUICK_JUMP_STATUS"),
            "quick_repair": ("statuses.general.additional_skill_feats", "QUICK_REPAIR_STATUS"),
            "quick_squeeze": ("statuses.general.additional_skill_feats", "QUICK_SQUEEZE_STATUS"),
            "read_lips": ("statuses.general.additional_skill_feats", "READ_LIPS_STATUS"),
            "recognize_spell": ("statuses.general.recognize_spell", "RECOGNIZE_SPELL_STATUS"),
            "ride": ("statuses.general.additional_skill_feats", "RIDE_STATUS"),
            "shield_block": ("statuses.general.shield_block", "SHIELD_BLOCK_STATUS"),
            "sign_language": ("statuses.general.additional_skill_feats", "SIGN_LANGUAGE_STATUS"),
            "skill_training": ("statuses.general.skill_training", "SKILL_TRAINING_STATUS"),
            "snare_crafting": ("statuses.general.additional_skill_feats", "SNARE_CRAFTING_STATUS"),
            "specialty_crafting": ("statuses.backgrounds.skill_feats", "SPECIALTY_CRAFTING_STATUS"),
            "subtle_theft": ("statuses.general.additional_skill_feats", "SUBTLE_THEFT_STATUS"),
            "survey_wildlife": ("statuses.backgrounds.skill_feats", "SURVEY_WILDLIFE_STATUS"),
            "terrain_expertise": ("statuses.backgrounds.skill_feats", "TERRAIN_EXPERTISE_STATUS"),
            "terrain_stalker": ("statuses.general.additional_skill_feats", "TERRAIN_STALKER_STATUS"),
            "titan_wrestler": ("statuses.general.additional_skill_feats", "TITAN_WRESTLER_STATUS"),
            "toughness": ("statuses.general.toughness", "TOUGHNESS_STATUS"),
            "train_animal": ("statuses.backgrounds.skill_feats", "TRAIN_ANIMAL_STATUS"),
            "trick_magic_item": ("statuses.general.trick_magic_item", "TRICK_MAGIC_ITEM_STATUS"),
            "underwater_marauder": ("statuses.backgrounds.skill_feats", "UNDERWATER_MARAUDER_STATUS"),
            "virtuosic_performer": ("statuses.general.additional_skill_feats", "VIRTUOSIC_PERFORMER_STATUS"),
            "weapon_proficiency": ("statuses.general.weapon_proficiency", "WEAPON_PROFICIENCY_STATUS"),
        }

    @staticmethod
    def _class_feat_registry() -> dict[str, dict[str, tuple[str, str]]]:
        return {
            "alchemist": {
                "advanced_alchemy": ("statuses.classes.alchemist.feats.advanced_alchemy", "ADVANCED_ALCHEMY_STATUS"),
                "alchemical_savant": ("statuses.classes.alchemist.feats.alchemical_savant", "ALCHEMICAL_SAVANT_STATUS"),
                "alchemist_familiar_guidance": (
                    "statuses.classes.alchemist.feats.alchemist_familiar_guidance",
                    "ALCHEMIST_FAMILIAR_GUIDANCE_STATUS",
                ),
                "far_lobber": ("statuses.classes.alchemist.feats.far_lobber", "FAR_LOBBER_STATUS"),
                "quick_alchemy_allow": ("statuses.classes.alchemist.feats.quick_alchemy_allow", "QUICK_ALCHEMY_ALLOW_STATUS"),
                "quick_bomber": ("statuses.classes.alchemist.feats.quick_bomber", "QUICK_BOMBER_STATUS"),
            },
            "barbarian": {
                "cute_vision": ("statuses.classes.barbarian.feats.cute_vision", "CUTE_VISION_STATUS"),
                "moment_of_clarity": ("statuses.classes.barbarian.feats.moment_of_clarity", "MomentOfClarityStatus"),
                "raging_thrower": ("statuses.classes.barbarian.feats.raging_thrower", "RAGING_THROWER_STATUS"),
                "sudden_charge": (
                    "statuses.classes.fighter.feats.sudden_charge",
                    "SUDDEN_CHARGE_STATUS",
                ),
            },
            "bard": {
                "bardic_lore": ("statuses.classes.bard.feats.bardic_lore", "BARDIC_LORE_STATUS"),
                "lingering_composition": (
                    "statuses.classes.bard.feats.lingering_composition",
                    "LINGERING_COMPOSITION_STATUS",
                ),
                "reach_spell": ("statuses.classes.bard.feats.reach_spell", "REACH_SPELL_STATUS"),
                "versatile_performance": (
                    "statuses.classes.bard.feats.versatile_performance",
                    "VERSATILE_PERFORMANCE_STATUS",
                ),
            },
            "champion": {
                "deitys_domain": (
                    "statuses.classes.champion.feats.deitys_domain",
                    "DEITYS_DOMAIN_STATUS",
                ),
                "ranged_reprisal": (
                    "statuses.classes.champion.feats.ranged_reprisal",
                    "RANGED_REPRISAL_STATUS",
                ),
                "unimpeded_step": (
                    "statuses.classes.champion.feats.unimpeded_step",
                    "UNIMPEDED_STEP_STATUS",
                ),
                "weight_of_guilt": (
                    "statuses.classes.champion.feats.weight_of_guilt",
                    "WEIGHT_OF_GUILT_STATUS",
                ),
            },
            "cleric": {
                "deadly_simplicity": (
                    "statuses.classes.cleric.feats.deadly_simplicity",
                    "DEADLY_SIMPLICITY_STATUS",
                ),
                "domain_initiate": (
                    "statuses.classes.cleric.feats.domain_initiate",
                    "DOMAIN_INITIATE_STATUS",
                ),
                "harming_hands": (
                    "statuses.classes.cleric.feats.harming_hands",
                    "HARMING_HANDS_STATUS",
                ),
                "healing_hands": (
                    "statuses.classes.cleric.feats.healing_hands",
                    "HEALING_HANDS_STATUS",
                ),
                "holy_castigation": (
                    "statuses.classes.cleric.feats.holy_castigation",
                    "HOLY_CASTIGATION_STATUS",
                ),
                "reach_spell": ("statuses.classes.bard.feats.reach_spell", "REACH_SPELL_STATUS"),
            },
            "druid": {
                "animal_companion": (
                    "statuses.classes.druid.feats.animal_companion",
                    "ANIMAL_COMPANION_STATUS",
                ),
                "leshy_familiar": (
                    "statuses.classes.druid.feats.leshy_familiar",
                    "LESHY_FAMILIAR_STATUS",
                ),
                "reach_spell": ("statuses.classes.bard.feats.reach_spell", "REACH_SPELL_STATUS"),
                "storm_born": ("statuses.classes.druid.feats.storm_born", "STORM_BORN_STATUS"),
                "widen_spell": ("statuses.classes.druid.feats.widen_spell", "WIDEN_SPELL_STATUS"),
                "wild_shape": ("statuses.classes.druid.feats.wild_shape", "WILD_SHAPE_STATUS"),
            },
            "fighter": {
                "double_slice": (
                    "statuses.classes.fighter.feats.double_slice",
                    "DOUBLE_SLICE_STATUS",
                ),
                "exacting_strike": (
                    "statuses.classes.fighter.feats.exacting_strike",
                    "EXACTING_STRIKE_STATUS",
                ),
                "point_blank_shot": (
                    "statuses.classes.fighter.feats.point_blank_shot",
                    "POINT_BLANK_SHOT_STATUS",
                ),
                "power_attack": (
                    "statuses.classes.fighter.feats.power_attack",
                    "POWER_ATTACK_STATUS",
                ),
                "reactive_shield": (
                    "statuses.classes.fighter.feats.reactive_shield",
                    "REACTIVE_SHIELD_STATUS",
                ),
                "snagging_strike": (
                    "statuses.classes.fighter.feats.snagging_strike",
                    "SNAGGING_STRIKE_STATUS",
                ),
                "sudden_charge": (
                    "statuses.classes.fighter.feats.sudden_charge",
                    "SUDDEN_CHARGE_STATUS",
                ),
            },
            "monk": {
                "crane_stance": (
                    "statuses.classes.monk.feats.crane_stance",
                    "CRANE_STANCE_STATUS",
                ),
                "dragon_stance": (
                    "statuses.classes.monk.feats.dragon_stance",
                    "DRAGON_STANCE_STATUS",
                ),
                "ki_rush": (
                    "statuses.classes.monk.feats.ki_rush",
                    "KI_RUSH_STATUS",
                ),
                "ki_strike": (
                    "statuses.classes.monk.feats.ki_strike",
                    "KI_STRIKE_STATUS",
                ),
                "monastic_weaponry": (
                    "statuses.classes.monk.feats.monastic_weaponry",
                    "MONASTIC_WEAPONRY_STATUS",
                ),
                "mountain_stance": (
                    "statuses.classes.monk.feats.mountain_stance",
                    "MOUNTAIN_STANCE_STATUS",
                ),
                "tiger_stance": (
                    "statuses.classes.monk.feats.tiger_stance",
                    "TIGER_STANCE_STATUS",
                ),
                "wolf_stance": (
                    "statuses.classes.monk.feats.wolf_stance",
                    "WOLF_STANCE_STATUS",
                ),
            },
            "ranger": {
                "animal_companion": (
                    "statuses.classes.ranger.feats.animal_companion",
                    "ANIMAL_COMPANION_STATUS",
                ),
                "crossbow_ace": (
                    "statuses.classes.ranger.feats.crossbow_ace",
                    "CROSSBOW_ACE_STATUS",
                ),
                "hunted_shot": (
                    "statuses.classes.ranger.feats.hunted_shot",
                    "HUNTED_SHOT_STATUS",
                ),
                "monster_hunter": (
                    "statuses.classes.ranger.feats.monster_hunter",
                    "MONSTER_HUNTER_STATUS",
                ),
                "twin_takedown": (
                    "statuses.classes.ranger.feats.twin_takedown",
                    "TWIN_TAKEDOWN_STATUS",
                ),
            },
            "rogue": {
                "nimble_dodge": (
                    "statuses.classes.rogue.feats.nimble_dodge",
                    "NIMBLE_DODGE_STATUS",
                ),
                "trap_finder": (
                    "statuses.classes.rogue.feats.trap_finder",
                    "TRAP_FINDER_STATUS",
                ),
                "twin_feint": (
                    "statuses.classes.rogue.feats.twin_feint",
                    "TWIN_FEINT_STATUS",
                ),
                "youre_next": (
                    "statuses.classes.rogue.feats.youre_next",
                    "YOURE_NEXT_STATUS",
                ),
            },
            "sorcerer": {
                "counterspell": (
                    "statuses.classes.sorcerer.feats.counterspell",
                    "COUNTERSPELL_STATUS",
                ),
                "dangerous_sorcery": (
                    "statuses.classes.sorcerer.feats.dangerous_sorcery",
                    "DANGEROUS_SORCERY_STATUS",
                ),
                "familiar": (
                    "statuses.classes.sorcerer.feats.familiar",
                    "FAMILIAR_STATUS",
                ),
                "reach_spell": (
                    "statuses.classes.sorcerer.feats.reach_spell",
                    "REACH_SPELL_STATUS",
                ),
                "widen_spell": (
                    "statuses.classes.sorcerer.feats.widen_spell",
                    "WIDEN_SPELL_STATUS",
                ),
            },
            "wizard": {
                "counterspell": (
                    "statuses.classes.wizard.feats.counterspell",
                    "COUNTERSPELL_STATUS",
                ),
                "eschew_materials": (
                    "statuses.classes.wizard.feats.eschew_materials",
                    "ESCHEW_MATERIALS_STATUS",
                ),
                "familiar": (
                    "statuses.classes.wizard.feats.familiar",
                    "FAMILIAR_STATUS",
                ),
                "hand_of_the_apprentice": (
                    "statuses.classes.wizard.feats.hand_of_the_apprentice",
                    "HAND_OF_THE_APPRENTICE_STATUS",
                ),
                "reach_spell": (
                    "statuses.classes.wizard.feats.reach_spell",
                    "REACH_SPELL_STATUS",
                ),
                "widen_spell": (
                    "statuses.classes.wizard.feats.widen_spell",
                    "WIDEN_SPELL_STATUS",
                ),
            },
        }

    @staticmethod
    def _resolve_status_from_registry(feat_id: str, registry: dict[str, tuple[str, str]]):
        if not feat_id:
            return None
        entry = registry.get(str(feat_id))
        if not entry:
            return None
        module_path, symbol = entry
        try:
            import importlib

            module = importlib.import_module(module_path)
            resolved = getattr(module, symbol, None)
        except Exception:
            return None
        if resolved is None:
            return None
        if hasattr(resolved, "id"):
            return resolved
        if callable(resolved):
            try:
                candidate = resolved()
            except Exception:
                return None
            if hasattr(candidate, "id"):
                return candidate
        return None

    def _actor_class_id(self) -> str | None:
        class_id = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_id == "alchemsit":
            class_id = "alchemist"
        if class_id in self._class_feat_registry():
            return class_id
        for candidate in self._class_feat_registry():
            try:
                if self.has_status(candidate):
                    return candidate
            except Exception:
                continue
        return None

    def _has_spellcasting_class_feature(self) -> bool:
        class_id = self._actor_class_id()
        return class_id in {"bard", "cleric", "druid", "sorcerer", "wizard"}

    def _actor_spellcasting_tradition(self) -> str | None:
        class_id = self._actor_class_id()
        if class_id == "bard":
            setup = self._bard_setup_data()
            value = setup.get("spell_tradition")
            if value is None:
                value = getattr(self, "bard_spell_tradition", None)
            raw = self._normalize_choice_id(value)
            return raw or "occult"
        if class_id == "cleric":
            setup = self._cleric_setup_data()
            value = setup.get("spell_tradition")
            if value is None:
                value = getattr(self, "cleric_spell_tradition", None)
            raw = self._normalize_choice_id(value)
            return raw or "divine"
        if class_id == "druid":
            setup = self._druid_setup_data()
            value = setup.get("spell_tradition")
            if value is None:
                value = getattr(self, "druid_spell_tradition", None)
            raw = self._normalize_choice_id(value)
            return raw or "primal"
        if class_id == "sorcerer":
            setup = self._sorcerer_setup_data()
            value = setup.get("spell_tradition")
            if value is None:
                value = getattr(self, "sorcerer_spell_tradition", None)
            raw = self._normalize_choice_id(value)
            return raw or None
        if class_id == "wizard":
            setup = self._wizard_setup_data()
            value = setup.get("spell_tradition")
            if value is None:
                value = getattr(self, "wizard_spell_tradition", None)
            raw = self._normalize_choice_id(value)
            return raw or "arcane"
        return None

    @staticmethod
    def _replace_spell_id_in_list(values: list[str], *, source: str, target: str) -> list[str]:
        source_id = StatusMixin._normalize_spell_id(source)
        target_id = StatusMixin._normalize_spell_id(target)
        if not source_id or not target_id or source_id == target_id:
            return []

        normalized = [
            StatusMixin._normalize_spell_id(item)
            for item in list(values or [])
            if StatusMixin._normalize_spell_id(item)
        ]
        if source_id not in normalized or target_id in normalized:
            return []

        out: list[str] = []
        replaced = False
        for spell_id in normalized:
            if not replaced and spell_id == source_id:
                out.append(target_id)
                replaced = True
                continue
            if spell_id not in out:
                out.append(spell_id)
        return out if replaced else []

    def _adapted_cantrip_replacement_choices(self) -> list[str]:
        class_id = self._actor_class_id()
        choices: list[str] = []

        if class_id == "bard":
            setup = self._bard_setup_data()
            choices = list(setup.get("known_cantrips") or getattr(self, "bard_known_cantrips", []) or [])
        elif class_id == "sorcerer":
            setup = self._sorcerer_setup_data()
            choices = list(setup.get("known_cantrips") or getattr(self, "sorcerer_known_cantrips", []) or [])
        elif class_id == "wizard":
            setup = self._wizard_setup_data()
            raw_spellbook = setup.get("spellbook")
            if not isinstance(raw_spellbook, dict):
                raw_spellbook = getattr(self, "wizard_spellbook", {}) or {}
            if isinstance(raw_spellbook, dict):
                choices = list(raw_spellbook.get("cantrip") or raw_spellbook.get("cantrips") or [])
        elif class_id in {"cleric", "druid"}:
            tradition = self._actor_spellcasting_tradition()
            if tradition:
                choices = self._collect_spell_choices_by_tier(traditions={tradition}, tier="cantrip")

        if not choices:
            tradition = self._actor_spellcasting_tradition()
            if tradition:
                choices = self._collect_spell_choices_by_tier(traditions={tradition}, tier="cantrip")

        out: list[str] = []
        for item in list(choices or []):
            normalized = self._normalize_spell_id(item)
            if normalized and normalized not in out:
                out.append(normalized)
        return out

    def _apply_adapted_cantrip_class_replacement(self, *, source_spell: str, target_spell: str) -> bool:
        class_id = self._actor_class_id()
        source_id = self._normalize_spell_id(source_spell)
        target_id = self._normalize_spell_id(target_spell)
        if not source_id or not target_id or source_id == target_id:
            return False

        if class_id == "bard":
            setup = self._bard_setup_data()
            current = list(setup.get("known_cantrips") or getattr(self, "bard_known_cantrips", []) or [])
            updated = self._replace_spell_id_in_list(current, source=source_id, target=target_id)
            if not updated:
                return False
            try:
                setattr(self, "bard_known_cantrips", list(updated))
            except Exception:
                pass
            for idx, status in enumerate(list(getattr(self, "statuses", []) or [])):
                if getattr(status, "id", None) != "bard":
                    continue
                data = dict(getattr(status, "data", None) or {})
                setup_payload = dict(data.get("bard_setup") or {})
                setup_payload["known_cantrips"] = list(updated)
                data["bard_setup"] = setup_payload
                data["bard_known_cantrips"] = list(updated)
                self.statuses[idx] = replace(status, data=data)
                break
            return True

        if class_id == "sorcerer":
            setup = self._sorcerer_setup_data()
            current = list(setup.get("known_cantrips") or getattr(self, "sorcerer_known_cantrips", []) or [])
            updated = self._replace_spell_id_in_list(current, source=source_id, target=target_id)
            if not updated:
                return False
            try:
                setattr(self, "sorcerer_known_cantrips", list(updated))
            except Exception:
                pass
            for idx, status in enumerate(list(getattr(self, "statuses", []) or [])):
                if getattr(status, "id", None) != "sorcerer":
                    continue
                data = dict(getattr(status, "data", None) or {})
                setup_payload = dict(data.get("sorcerer_setup") or {})
                setup_payload["known_cantrips"] = list(updated)
                data["sorcerer_setup"] = setup_payload
                data["sorcerer_known_cantrips"] = list(updated)
                self.statuses[idx] = replace(status, data=data)
                break
            return True

        if class_id == "wizard":
            setup = self._wizard_setup_data()
            raw_spellbook = setup.get("spellbook")
            if not isinstance(raw_spellbook, dict):
                raw_spellbook = getattr(self, "wizard_spellbook", {}) or {}
            if not isinstance(raw_spellbook, dict):
                return False
            spellbook = dict(raw_spellbook)
            current = list(spellbook.get("cantrip") or spellbook.get("cantrips") or [])
            updated = self._replace_spell_id_in_list(current, source=source_id, target=target_id)
            if not updated:
                return False
            spellbook["cantrip"] = list(updated)
            if "cantrips" in spellbook:
                spellbook["cantrips"] = list(updated)
            try:
                setattr(self, "wizard_spellbook", dict(spellbook))
            except Exception:
                pass
            for idx, status in enumerate(list(getattr(self, "statuses", []) or [])):
                if getattr(status, "id", None) != "wizard":
                    continue
                data = dict(getattr(status, "data", None) or {})
                setup_payload = dict(data.get("wizard_setup") or {})
                setup_payload["spellbook"] = dict(spellbook)
                data["wizard_setup"] = setup_payload
                data["wizard_spellbook"] = dict(spellbook)
                self.statuses[idx] = replace(status, data=data)
                break
            return True

        if class_id in {"cleric", "druid"}:
            return source_id in set(self._adapted_cantrip_replacement_choices())

        return False

    @staticmethod
    def _is_trained_rank(raw_rank: object) -> bool:
        raw = str(raw_rank or "").strip().lower()
        return raw in {"trained", "expert", "master", "legendary", "t", "e", "m", "l", "2", "4", "6", "8"}

    def _has_martial_weapon_training(self) -> bool:
        mapping = getattr(self, "weapon_proficiency_ranks", None)
        if isinstance(mapping, dict) and self._is_trained_rank(mapping.get("martial")):
            return True
        for status in getattr(self, "statuses", None) or []:
            data = getattr(status, "data", None) or {}
            status_mapping = data.get("weapon_proficiency_ranks")
            if isinstance(status_mapping, dict) and self._is_trained_rank(status_mapping.get("martial")):
                return True
        return False

    def _current_weapon_rank(self, category: str) -> str:
        key = str(category or "").strip().lower()
        raw = None
        mapping = getattr(self, "weapon_proficiency_ranks", None)
        if isinstance(mapping, dict):
            raw = mapping.get(key, raw)
        for status in getattr(self, "statuses", None) or []:
            data = getattr(status, "data", None) or {}
            status_mapping = data.get("weapon_proficiency_ranks")
            if isinstance(status_mapping, dict) and key in status_mapping:
                raw = status_mapping.get(key, raw)
        return str(raw or "untrained")

    def _current_defense_rank(self, category: str) -> str:
        key = str(category or "").strip().lower()
        raw = None
        mapping = getattr(self, "defense_proficiency_ranks", None)
        if isinstance(mapping, dict):
            raw = mapping.get(key, raw)
        for status in getattr(self, "statuses", None) or []:
            data = getattr(status, "data", None) or {}
            status_mapping = data.get("defense_proficiency_ranks")
            if isinstance(status_mapping, dict) and key in status_mapping:
                raw = status_mapping.get(key, raw)
        return str(raw or "untrained")

    @staticmethod
    def _base_skill_choices() -> list[str]:
        return [
            "athletics",
            "acrobatics",
            "arcana",
            "crafting",
            "deception",
            "diplomacy",
            "intimidation",
            "medicine",
            "nature",
            "occultism",
            "performance",
            "religion",
            "society",
            "stealth",
            "survival",
            "thievery",
        ]

    def _cleric_setup_data(self) -> dict:
        getter = getattr(self, "get_status_data", None)
        if callable(getter):
            try:
                raw = getter("cleric", "cleric_setup", {})
                if isinstance(raw, dict):
                    return dict(raw)
            except Exception:
                pass
        for status in getattr(self, "statuses", []) or []:
            if getattr(status, "id", None) != "cleric":
                continue
            data = getattr(status, "data", None) or {}
            setup = data.get("cleric_setup")
            if isinstance(setup, dict):
                return dict(setup)
        return {}

    def _bard_setup_data(self) -> dict:
        getter = getattr(self, "get_status_data", None)
        if callable(getter):
            try:
                raw = getter("bard", "bard_setup", {})
                if isinstance(raw, dict):
                    return dict(raw)
            except Exception:
                pass
        for status in getattr(self, "statuses", []) or []:
            if getattr(status, "id", None) != "bard":
                continue
            data = getattr(status, "data", None) or {}
            setup = data.get("bard_setup")
            if isinstance(setup, dict):
                return dict(setup)
        return {}

    def _champion_setup_data(self) -> dict:
        getter = getattr(self, "get_status_data", None)
        if callable(getter):
            try:
                raw = getter("champion", "champion_setup", {})
                if isinstance(raw, dict):
                    return dict(raw)
            except Exception:
                pass
        for status in getattr(self, "statuses", []) or []:
            if getattr(status, "id", None) != "champion":
                continue
            data = getattr(status, "data", None) or {}
            setup = data.get("champion_setup")
            if isinstance(setup, dict):
                return dict(setup)
        return {}

    def _sorcerer_setup_data(self) -> dict:
        getter = getattr(self, "get_status_data", None)
        if callable(getter):
            try:
                raw = getter("sorcerer", "sorcerer_setup", {})
                if isinstance(raw, dict):
                    return dict(raw)
            except Exception:
                pass
        for status in getattr(self, "statuses", []) or []:
            if getattr(status, "id", None) != "sorcerer":
                continue
            data = getattr(status, "data", None) or {}
            setup = data.get("sorcerer_setup")
            if isinstance(setup, dict):
                return dict(setup)
        return {}

    def _druid_setup_data(self) -> dict:
        getter = getattr(self, "get_status_data", None)
        if callable(getter):
            try:
                raw = getter("druid", "druid_setup", {})
                if isinstance(raw, dict):
                    return dict(raw)
            except Exception:
                pass
        for status in getattr(self, "statuses", []) or []:
            if getattr(status, "id", None) != "druid":
                continue
            data = getattr(status, "data", None) or {}
            setup = data.get("druid_setup")
            if isinstance(setup, dict):
                return dict(setup)
        return {}

    def _wizard_setup_data(self) -> dict:
        getter = getattr(self, "get_status_data", None)
        if callable(getter):
            try:
                raw = getter("wizard", "wizard_setup", {})
                if isinstance(raw, dict):
                    return dict(raw)
            except Exception:
                pass
        for status in getattr(self, "statuses", []) or []:
            if getattr(status, "id", None) != "wizard":
                continue
            data = getattr(status, "data", None) or {}
            setup = data.get("wizard_setup")
            if isinstance(setup, dict):
                return dict(setup)
        return {}

    def _druid_order_choice(self) -> str | None:
        setup = self._druid_setup_data()
        value = setup.get("order")
        if value is None:
            value = getattr(self, "druid_order", None)
        raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        return raw or None

    def _wizard_arcane_study_choice(self) -> str | None:
        setup = self._wizard_setup_data()
        value = setup.get("arcane_study")
        if value is None:
            value = getattr(self, "wizard_arcane_study", None)
        raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        return raw or None

    def _is_druid_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "druid":
            return True
        try:
            return bool(self.has_status("druid"))
        except Exception:
            return False

    def _cleric_font_choice(self) -> str | None:
        setup = self._cleric_setup_data()
        value = setup.get("font")
        if value is None:
            value = setup.get("font_choice")
        if value is None:
            value = getattr(self, "cleric_font", None)
        raw = str(value or "").strip().lower()
        return raw if raw in ("heal", "harm") else None

    def _cleric_favored_weapon_group(self) -> str | None:
        setup = self._cleric_setup_data()
        value = setup.get("favored_weapon_group")
        if value is None:
            value = getattr(self, "cleric_favored_weapon_group", None)
        raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        if raw in ("simple", "martial", "unarmed"):
            return raw
        return None

    def _is_cleric_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "cleric":
            return True
        try:
            return bool(self.has_status("cleric"))
        except Exception:
            return False

    def _is_fighter_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "fighter":
            return True
        try:
            return bool(self.has_status("fighter"))
        except Exception:
            return False

    def _is_barbarian_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "barbarian":
            return True
        try:
            return bool(self.has_status("barbarian"))
        except Exception:
            return False

    def _is_monk_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "monk":
            return True
        try:
            return bool(self.has_status("monk"))
        except Exception:
            return False

    def _is_ranger_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "ranger":
            return True
        try:
            return bool(self.has_status("ranger"))
        except Exception:
            return False

    def _is_rogue_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "rogue":
            return True
        try:
            return bool(self.has_status("rogue"))
        except Exception:
            return False

    def _is_sorcerer_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "sorcerer":
            return True
        try:
            return bool(self.has_status("sorcerer"))
        except Exception:
            return False

    def _is_wizard_actor(self) -> bool:
        class_name = str(getattr(self, "class_name", "") or "").strip().lower()
        if class_name == "wizard":
            return True
        try:
            return bool(self.has_status("wizard"))
        except Exception:
            return False

    def _trained_skill_ids(self) -> set[str]:
        trained: set[str] = set()

        def _normalize(raw: object) -> str | None:
            value = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
            return value or None

        for source in (getattr(self, "trained_skills", None), getattr(self, "rogue_trained_skills", None)):
            if isinstance(source, (list, tuple, set)):
                for item in source:
                    normalized = _normalize(item)
                    if normalized:
                        trained.add(normalized)

        statuses = getattr(self, "statuses", None)
        if isinstance(statuses, list):
            for status in statuses:
                data = getattr(status, "data", None) or {}
                for key in ("trained_skills", "skills_trained"):
                    value = data.get(key)
                    if isinstance(value, (list, tuple, set)):
                        for item in value:
                            normalized = _normalize(item)
                            if normalized:
                                trained.add(normalized)
                for setup_key in (
                    "rogue_setup",
                    "ranger_setup",
                    "monk_setup",
                    "fighter_setup",
                    "cleric_setup",
                    "champion_setup",
                    "druid_setup",
                    "sorcerer_setup",
                    "wizard_setup",
                ):
                    payload = data.get(setup_key)
                    if not isinstance(payload, dict):
                        continue
                    for item in list(payload.get("trained_skills") or []):
                        normalized = _normalize(item)
                        if normalized:
                            trained.add(normalized)
                    normalized = _normalize(payload.get("trained_skill"))
                    if normalized:
                        trained.add(normalized)

        for skill_name in (
            "athletics",
            "acrobatics",
            "arcana",
            "crafting",
            "deception",
            "diplomacy",
            "intimidation",
            "medicine",
            "nature",
            "occultism",
            "performance",
            "religion",
            "society",
            "stealth",
            "survival",
            "thievery",
            "perception",
            "fortitude",
            "reflex",
            "will",
        ):
            attr_name = f"{skill_name}_trained"
            try:
                if bool(getattr(self, attr_name, False)):
                    trained.add(skill_name)
            except Exception:
                continue

        return trained

    def _passes_status_prerequisites(self, status: "Status") -> bool:
        status_id = str(getattr(status, "id", "") or "").strip().lower()
        status_data = getattr(status, "data", None) or {}

        if bool(status_data.get("is_background")):
            for existing in getattr(self, "statuses", []) or []:
                if getattr(existing, "id", None) == status_id:
                    continue
                existing_data = getattr(existing, "data", None) or {}
                if bool(existing_data.get("is_background")):
                    existing_label = getattr(existing, "display_label", None) or getattr(existing, "label", None) or getattr(existing, "id", "background")
                    self._ui_log(
                        f"Background: masz juz wybrany {existing_label}. Mozesz miec tylko jeden background."
                    )
                    return False

        if status_id in {"deadly_simplicity", "domain_initiate", "harming_hands", "healing_hands", "holy_castigation"}:
            if not self._is_cleric_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Cleric.")
                return False

        if status_id in {"deitys_domain", "ranged_reprisal", "unimpeded_step", "weight_of_guilt"}:
            if self._actor_class_id() != "champion":
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Champion.")
                return False
            required_cause = str(status_data.get("requires_champion_cause", "") or "").strip().lower()
            if required_cause:
                setup = self._champion_setup_data()
                current_cause = str(
                    setup.get("cause")
                    or self.get_status_data("champion", "champion_cause", "")
                    or getattr(self, "champion_cause", "")
                    or ""
                ).strip().lower()
                if current_cause and current_cause != required_cause:
                    self._ui_log(
                        f"{self._labelize_choice(status_id)}: wymaga cause {self._labelize_choice(required_cause)}."
                    )
                    return False

        if status_id == "deadly_simplicity":
            favored_group = self._cleric_favored_weapon_group()
            if favored_group not in {"simple", "unarmed"}:
                self._ui_log("Deadly Simplicity: wymaga favored weapon typu simple lub unarmed.")
                return False

        if status_id in {"harming_hands", "healing_hands"}:
            required_font = "harm" if status_id == "harming_hands" else "heal"
            current_font = self._cleric_font_choice()
            if current_font != required_font:
                self._ui_log(
                    f"{self._labelize_choice(status_id)}: wymaga divine font '{required_font}'."
                )
                return False

        if status_id in {"animal_companion", "leshy_familiar", "storm_born", "widen_spell", "wild_shape"}:
            allowed_classes = {
                str(item).strip().lower()
                for item in list(status_data.get("allowed_classes") or [])
                if str(item).strip()
            }
            if not allowed_classes:
                allowed_classes = {"druid"}
            class_checks = {
                "druid": self._is_druid_actor,
                "ranger": self._is_ranger_actor,
                "sorcerer": self._is_sorcerer_actor,
                "wizard": self._is_wizard_actor,
            }
            if not any(class_checks.get(cid, lambda: False)() for cid in allowed_classes):
                if "ranger" in allowed_classes and "druid" not in allowed_classes:
                    self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Ranger.")
                else:
                    self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Druid.")
                return False

        if status_id in {
            "double_slice",
            "exacting_strike",
            "point_blank_shot",
            "power_attack",
            "reactive_shield",
            "snagging_strike",
        }:
            if not self._is_fighter_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Fighter.")
                return False

        if status_id == "sudden_charge":
            if not (self._is_fighter_actor() or self._is_barbarian_actor()):
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Fighter lub Barbarian.")
                return False

        if status_id in {
            "crane_stance",
            "dragon_stance",
            "ki_rush",
            "ki_strike",
            "monastic_weaponry",
            "mountain_stance",
            "tiger_stance",
            "wolf_stance",
        }:
            if not self._is_monk_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Monk.")
                return False

        if status_id in {
            "crossbow_ace",
            "hunted_shot",
            "hunt_prey",
            "monster_hunter",
            "twin_takedown",
        }:
            if not self._is_ranger_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Ranger.")
                return False

        if status_id in {
            "nimble_dodge",
            "sneak_attack",
            "surprise_attack",
            "trap_finder",
            "twin_feint",
            "youre_next",
        }:
            if not self._is_rogue_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Rogue.")
                return False

        if status_id in {"counterspell", "familiar"}:
            if not (self._is_sorcerer_actor() or self._is_wizard_actor()):
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Sorcerer lub Wizard.")
                return False

        if status_id in {"dangerous_sorcery"}:
            if not self._is_sorcerer_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Sorcerer.")
                return False

        if status_id in {"eschew_materials", "hand_of_the_apprentice"}:
            if not self._is_wizard_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Wizard.")
                return False

        if status_id == "ancestral_longevity":
            min_age = int(status_data.get("requires_min_age_years", 100) or 100)
            actor_age = None
            for age_attr in ("age_years", "age", "years_old"):
                raw_age = getattr(self, age_attr, None)
                if raw_age is None:
                    continue
                try:
                    actor_age = int(raw_age)
                    break
                except Exception:
                    continue
            if actor_age is not None and actor_age < min_age:
                self._ui_log(
                    f"{self._labelize_choice(status_id)}: wymaga wieku co najmniej {min_age} lat."
                )
                return False

        max_level = status_data.get("requires_level_max")
        if max_level is not None:
            try:
                limit = int(max_level)
                actor_level = int(getattr(self, "level", 1) or 1)
            except Exception:
                limit = None
                actor_level = 1
            if limit is not None and actor_level > limit:
                self._ui_log(
                    f"{self._labelize_choice(status_id)}: można wybrać maksymalnie na {limit}. poziomie."
                )
                return False

        if bool(status_data.get("requires_low_light_vision")):
            has_low_light = False
            try:
                has_low_light = bool(self.has_status("low_light_vision") or self.has_status("dim_light_vision"))
            except Exception:
                has_low_light = False
            if not has_low_light:
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga low-light vision.")
                return False

        if bool(status_data.get("requires_spellcasting_class_feature")) and not self._has_spellcasting_class_feature():
            self._ui_log(f"{self._labelize_choice(status_id)}: wymaga spellcasting class feature.")
            return False

        required_trained_skills = {
            str(item).strip().lower().replace("-", "_").replace(" ", "_")
            for item in list(status_data.get("requires_trained_skills") or [])
            if str(item).strip()
        }
        if required_trained_skills:
            trained = self._trained_skill_ids()
            if not required_trained_skills.issubset(trained):
                missing = sorted(required_trained_skills.difference(trained))
                self._ui_log(
                    f"{self._labelize_choice(status_id)}: wymaga trained w skillach: "
                    f"{', '.join(self._labelize_choice(item) for item in missing)}."
                )
                return False

        required_druid_order = str(status_data.get("requires_druid_order", "") or "").strip().lower()
        if required_druid_order:
            if not self._is_druid_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Druid.")
                return False
            chosen_order = self._druid_order_choice()
            if chosen_order != required_druid_order:
                self._ui_log(
                    f"{self._labelize_choice(status_id)}: wymaga druid order '{required_druid_order}'."
                )
                return False

        required_wizard_arcane_study = (
            str(status_data.get("requires_wizard_arcane_study", "") or "")
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
        if required_wizard_arcane_study:
            if not self._is_wizard_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Wizard.")
                return False
            chosen_study = self._wizard_arcane_study_choice()
            if chosen_study != required_wizard_arcane_study:
                self._ui_log(
                    f"{self._labelize_choice(status_id)}: wymaga wizard study '{required_wizard_arcane_study}'."
                )
                return False
        return True

    def _handle_adapted_cantrip_choice(self, status: "Status", data: dict) -> None:
        traditions = list(data.get("adapted_cantrip_traditions") or ["arcane", "divine", "occult", "primal"])
        if not traditions:
            return
        current_tradition = self._actor_spellcasting_tradition()
        if current_tradition:
            traditions = [item for item in traditions if self._normalize_choice_id(item) != current_tradition]
        if not traditions:
            self._ui_log("Adapted Cantrip: brak dostepnych tradycji innych niz tradycja klasy.")
            return

        replaceable_cantrips = self._adapted_cantrip_replacement_choices()
        replaceable_set = set(replaceable_cantrips)
        if not replaceable_cantrips:
            self._ui_log("Adapted Cantrip: brak cantripow klasy do podmiany.")
            return

        chosen_tradition = self._pick_choice_id(
            "Adapted Cantrip: wybierz tradycje",
            traditions,
            source="status",
        )
        if not chosen_tradition:
            return

        cantrip_map = dict(data.get("adapted_cantrip_choices") or {})
        cantrip_choices = self._collect_spell_choices_by_tier(
            traditions={chosen_tradition},
            tier="cantrip",
        )
        if replaceable_set:
            cantrip_choices = [item for item in cantrip_choices if self._normalize_spell_id(item) not in replaceable_set]
        if not cantrip_choices:
            cantrip_choices = list(cantrip_map.get(chosen_tradition, [])) or list(cantrip_map.get("all", []))
            cantrip_choices = [item for item in cantrip_choices if self._normalize_spell_id(item) not in replaceable_set]
        if not cantrip_choices:
            self._ui_log("Adapted Cantrip: brak dostepnych cantripow w wybranej tradycji po odfiltrowaniu obecnych czarow klasy.")
            return
        chosen_cantrip = self._pick_choice_id(
            f"Adapted Cantrip ({self._labelize_choice(chosen_tradition)}): wybierz cantrip",
            cantrip_choices,
            source="status",
        )
        if not chosen_cantrip:
            return

        replaced_choices = list(replaceable_cantrips) or list(data.get("replaced_cantrip_choices") or [])
        chosen_replaced = self._pick_choice_id(
            "Adapted Cantrip: wybierz cantrip do zastapienia",
            replaced_choices,
            source="status",
        )
        if not chosen_replaced:
            return

        normalized_cantrip = self._normalize_spell_id(chosen_cantrip)
        normalized_replaced = self._normalize_spell_id(chosen_replaced)
        if not normalized_cantrip or not normalized_replaced or normalized_cantrip == normalized_replaced:
            self._ui_log("Adapted Cantrip: nowy cantrip musi byc inny niz podmieniany.")
            return
        if not self._apply_adapted_cantrip_class_replacement(
            source_spell=normalized_replaced,
            target_spell=normalized_cantrip,
        ):
            self._ui_log("Adapted Cantrip: nie udalo sie podmienic cantripu w biezacej liscie klasy.")
            return

        self._replace_status_data(
            status,
            {
                "adapted_tradition": chosen_tradition,
                "adapted_cantrip": normalized_cantrip,
                "replaced_cantrip": normalized_replaced,
                "granted_cantrips": [normalized_cantrip],
                "innate_magic_tradition": chosen_tradition,
                "removed_cantrips": [normalized_replaced],
            },
        )
        self._ui_log(
            "Adapted Cantrip: "
            f"{self._labelize_choice(chosen_tradition)} -> {self._labelize_choice(normalized_cantrip)} "
            f"(zastapiony: {self._labelize_choice(normalized_replaced)})."
        )

    def _handle_otherworldly_magic_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("otherworldly_magic_choices") or [])
        if not choices:
            choices = ["detect_magic", "daze", "light", "mage_hand", "shield", "ray_of_frost"]
        chosen_cantrip = self._pick_choice_id(
            "Otherworldly Magic: wybierz arcane cantrip",
            choices,
            source="status",
        )
        if not chosen_cantrip:
            return
        self._replace_status_data(
            status,
            {
                "otherworldly_magic_cantrip": chosen_cantrip,
                "granted_cantrips": [chosen_cantrip],
                "innate_magic_tradition": "arcane",
            },
        )
        self._ui_log(f"Otherworldly Magic: wybrano cantrip {self._labelize_choice(chosen_cantrip)}.")

    def _selected_wellspring_tradition(self) -> str | None:
        for status in getattr(self, "statuses", []) or []:
            if getattr(status, "id", None) != "wellspring_gnome":
                continue
            data = getattr(status, "data", None) or {}
            value = str(data.get("wellspring_tradition", "") or "").strip().lower()
            if value in {"arcane", "divine", "occult"}:
                return value
        return None

    @staticmethod
    def _apply_gnome_primal_innate_override(data: dict, override_tradition: str | None) -> dict:
        if not override_tradition:
            return data
        if not bool(data.get("gnome_primal_innate_source")):
            return data
        updated = dict(data)
        updated["innate_magic_tradition"] = override_tradition
        updated["innate_magic_tradition_overridden_by_wellspring"] = True
        return updated

    def _handle_fey_touched_gnome_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("fey_touched_cantrip_choices") or [])
        if not choices:
            choices = ["detect_magic", "guidance", "ray_of_frost", "light", "produce_flame", "ghost_sound"]
        chosen_cantrip = self._pick_choice_id(
            "Fey-touched Gnome: wybierz primal cantrip",
            choices,
            source="status",
        )
        if not chosen_cantrip:
            return
        override_tradition = self._selected_wellspring_tradition()
        innate_tradition = override_tradition or "primal"
        updates = self._apply_gnome_primal_innate_override(
            {
                "fey_touched_cantrip": chosen_cantrip,
                "granted_cantrips": [chosen_cantrip],
                "innate_magic_tradition": innate_tradition,
                "gnome_primal_innate_source": True,
            },
            override_tradition,
        )
        self._replace_status_data(status, updates)
        self._ui_log(
            "Fey-touched Gnome: wybrano cantrip "
            f"{self._labelize_choice(chosen_cantrip)} ({self._labelize_choice(innate_tradition)})."
        )

    def _handle_first_world_magic_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("first_world_magic_choices") or [])
        if not choices:
            choices = ["detect_magic", "guidance", "ray_of_frost", "light", "produce_flame", "ghost_sound"]
        chosen_cantrip = self._pick_choice_id(
            "First World Magic: wybierz primal cantrip",
            choices,
            source="status",
        )
        if not chosen_cantrip:
            return
        override_tradition = self._selected_wellspring_tradition()
        innate_tradition = override_tradition or "primal"
        updates = self._apply_gnome_primal_innate_override(
            {
                "first_world_magic_cantrip": chosen_cantrip,
                "granted_cantrips": [chosen_cantrip],
                "innate_magic_tradition": innate_tradition,
                "gnome_primal_innate_source": True,
            },
            override_tradition,
        )
        self._replace_status_data(status, updates)
        self._ui_log(
            "First World Magic: wybrano cantrip "
            f"{self._labelize_choice(chosen_cantrip)} ({self._labelize_choice(innate_tradition)})."
        )

    def _handle_gnome_obsession_choice(self, status: "Status", data: dict) -> None:
        base_choices = list(data.get("gnome_obsession_lore_choices") or [])
        if not base_choices:
            base_choices = [
                "acrobatics_lore",
                "arcana_lore",
                "caves_lore",
                "engineering_lore",
                "forest_lore",
                "fey_lore",
                "herbalism_lore",
                "history_lore",
                "mountains_lore",
                "nature_lore",
                "occult_lore",
                "religion_lore",
                "society_lore",
                "underworld_lore",
                "warfare_lore",
            ]
        chosen_lore = self._pick_choice_id(
            "Gnome Obsession: wybierz Lore",
            base_choices,
            source="status",
        )
        if not chosen_lore:
            return
        self._replace_status_data(
            status,
            {
                "gnome_obsession_lore": chosen_lore,
                "trained_lore": [chosen_lore],
            },
        )
        self._ui_log(f"Gnome Obsession: wybrano {self._labelize_choice(chosen_lore)}.")

    def _handle_wellspring_gnome_choice(self, status: "Status", data: dict) -> None:
        tradition_choices = list(data.get("wellspring_tradition_choices") or ["arcane", "divine", "occult"])
        chosen_tradition = self._pick_choice_id(
            "Wellspring Gnome: wybierz tradycję",
            tradition_choices,
            source="status",
        )
        if not chosen_tradition:
            return

        cantrip_map = dict(data.get("wellspring_cantrip_choices") or {})
        cantrip_choices = list(cantrip_map.get(chosen_tradition, []))
        if not cantrip_choices:
            cantrip_choices = ["detect_magic", "daze", "light", "mage_hand", "guidance"]
        chosen_cantrip = self._pick_choice_id(
            f"Wellspring Gnome ({self._labelize_choice(chosen_tradition)}): wybierz cantrip",
            cantrip_choices,
            source="status",
        )
        if not chosen_cantrip:
            return

        self._replace_status_data(
            status,
            {
                "wellspring_tradition": chosen_tradition,
                "wellspring_cantrip": chosen_cantrip,
                "granted_cantrips": [chosen_cantrip],
                "innate_magic_tradition": chosen_tradition,
            },
        )

        # Wellspring zmienia tradycję wcześniejszych primal innate spelli z gnome ancestry.
        for idx, item in enumerate(list(getattr(self, "statuses", []) or [])):
            item_data = dict(getattr(item, "data", None) or {})
            if not bool(item_data.get("gnome_primal_innate_source")):
                continue
            updated = self._apply_gnome_primal_innate_override(item_data, chosen_tradition)
            self.statuses[idx] = replace(item, data=updated)

        self._ui_log(
            "Wellspring Gnome: "
            f"{self._labelize_choice(chosen_tradition)} -> {self._labelize_choice(chosen_cantrip)}."
        )

    def _handle_ancestral_longevity_choice(self, status: "Status", data: dict) -> None:
        choices = [
            "athletics",
            "acrobatics",
            "arcana",
            "crafting",
            "deception",
            "diplomacy",
            "intimidation",
            "medicine",
            "nature",
            "occultism",
            "performance",
            "religion",
            "society",
            "stealth",
            "survival",
            "thievery",
            "perception",
        ]
        chosen_skill = self._pick_choice_id(
            "Ancestral Longevity: wybierz skill (trained do następnych przygotowań)",
            choices,
            source="status",
        )
        if not chosen_skill:
            return
        self._replace_status_data(
            status,
            {
                "ancestral_longevity_skill": chosen_skill,
                "trained_skills": [chosen_skill],
            },
        )
        self._ui_log(f"Ancestral Longevity: wybrano skill {self._labelize_choice(chosen_skill)}.")

    def _handle_elven_lore_choice(self, status: "Status", data: dict) -> None:
        base_skills = [str(item).strip().lower() for item in list(data.get("trained_skills") or ["arcana", "nature"]) if str(item).strip()]
        pre_add_trained = {
            str(item).strip().lower()
            for item in list(data.get("_pre_add_trained_skills") or [])
            if str(item).strip()
        }
        overlaps = [skill_id for skill_id in base_skills if skill_id in pre_add_trained]
        if not overlaps:
            return
        replacement_choices = [
            str(item).strip().lower()
            for item in list(
                data.get("elven_lore_replacement_choices")
                or [
                    "athletics",
                    "acrobatics",
                    "arcana",
                    "crafting",
                    "deception",
                    "diplomacy",
                    "intimidation",
                    "medicine",
                    "nature",
                    "occultism",
                    "performance",
                    "religion",
                    "society",
                    "stealth",
                    "survival",
                    "thievery",
                ]
            )
            if str(item).strip()
        ]
        replacement_choices = [item for item in replacement_choices if item not in pre_add_trained]
        chosen_replacements: list[str] = []
        for index, _skill in enumerate(overlaps, start=1):
            available = [item for item in replacement_choices if item not in chosen_replacements]
            if not available:
                break
            chosen = self._pick_choice_id(
                f"Elven Lore: wybierz skill zastępczy ({index}/{len(overlaps)})",
                available,
                source="status",
            )
            if not chosen:
                continue
            chosen_replacements.append(chosen)
        if not chosen_replacements:
            return
        updated_base = [item for item in base_skills if item not in overlaps]
        final_skills = list(dict.fromkeys(updated_base + chosen_replacements))
        self._replace_status_data(
            status,
            {
                "trained_skills": final_skills,
                "elven_lore_replacements": chosen_replacements,
            },
        )
        self._ui_log(
            "Elven Lore: zastąpiono już posiadane trained skille -> "
            f"{', '.join(self._labelize_choice(item) for item in chosen_replacements)}."
        )

    def _handle_goblin_lore_choice(self, status: "Status", data: dict) -> None:
        base_skills = [
            str(item).strip().lower()
            for item in list(data.get("trained_skills") or ["nature", "stealth"])
            if str(item).strip()
        ]
        pre_add_trained = {
            str(item).strip().lower()
            for item in list(data.get("_pre_add_trained_skills") or [])
            if str(item).strip()
        }
        overlaps = [skill_id for skill_id in base_skills if skill_id in pre_add_trained]
        if not overlaps:
            return
        replacement_choices = [
            str(item).strip().lower()
            for item in list(
                data.get("goblin_lore_replacement_choices")
                or [
                    "athletics",
                    "acrobatics",
                    "arcana",
                    "crafting",
                    "deception",
                    "diplomacy",
                    "intimidation",
                    "medicine",
                    "nature",
                    "occultism",
                    "performance",
                    "religion",
                    "society",
                    "stealth",
                    "survival",
                    "thievery",
                ]
            )
            if str(item).strip()
        ]
        replacement_choices = [item for item in replacement_choices if item not in pre_add_trained]
        chosen_replacements: list[str] = []
        for index, _skill in enumerate(overlaps, start=1):
            available = [item for item in replacement_choices if item not in chosen_replacements]
            if not available:
                break
            chosen = self._pick_choice_id(
                f"Goblin Lore: wybierz skill zastępczy ({index}/{len(overlaps)})",
                available,
                source="status",
            )
            if not chosen:
                continue
            chosen_replacements.append(chosen)
        if not chosen_replacements:
            return
        updated_base = [item for item in base_skills if item not in overlaps]
        final_skills = list(dict.fromkeys(updated_base + chosen_replacements))
        self._replace_status_data(
            status,
            {
                "trained_skills": final_skills,
                "goblin_lore_replacements": chosen_replacements,
            },
        )
        self._ui_log(
            "Goblin Lore: zastąpiono już posiadane trained skille -> "
            f"{', '.join(self._labelize_choice(item) for item in chosen_replacements)}."
        )

    def _handle_halfling_lore_choice(self, status: "Status", data: dict) -> None:
        base_skills = [
            str(item).strip().lower()
            for item in list(data.get("trained_skills") or ["acrobatics", "stealth"])
            if str(item).strip()
        ]
        pre_add_trained = {
            str(item).strip().lower()
            for item in list(data.get("_pre_add_trained_skills") or [])
            if str(item).strip()
        }
        overlaps = [skill_id for skill_id in base_skills if skill_id in pre_add_trained]
        if not overlaps:
            return
        replacement_choices = [
            str(item).strip().lower()
            for item in list(
                data.get("halfling_lore_replacement_choices")
                or [
                    "athletics",
                    "acrobatics",
                    "arcana",
                    "crafting",
                    "deception",
                    "diplomacy",
                    "intimidation",
                    "medicine",
                    "nature",
                    "occultism",
                    "performance",
                    "religion",
                    "society",
                    "stealth",
                    "survival",
                    "thievery",
                ]
            )
            if str(item).strip()
        ]
        replacement_choices = [item for item in replacement_choices if item not in pre_add_trained]
        chosen_replacements: list[str] = []
        for index, _skill in enumerate(overlaps, start=1):
            available = [item for item in replacement_choices if item not in chosen_replacements]
            if not available:
                break
            chosen = self._pick_choice_id(
                f"Halfling Lore: wybierz skill zastępczy ({index}/{len(overlaps)})",
                available,
                source="status",
            )
            if not chosen:
                continue
            chosen_replacements.append(chosen)
        if not chosen_replacements:
            return
        updated_base = [item for item in base_skills if item not in overlaps]
        final_skills = list(dict.fromkeys(updated_base + chosen_replacements))
        self._replace_status_data(
            status,
            {
                "trained_skills": final_skills,
                "halfling_lore_replacements": chosen_replacements,
            },
        )
        self._ui_log(
            "Halfling Lore: zastąpiono już posiadane trained skille -> "
            f"{', '.join(self._labelize_choice(item) for item in chosen_replacements)}."
        )

    def _handle_additional_lore_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("additional_lore_choices") or [])
        if not choices:
            choices = ["academia", "legal", "underworld", "warfare"]
        chosen = self._pick_choice_id(
            "Additional Lore: wybierz specjalizacje Lore",
            choices,
            source="status",
        )
        if not chosen:
            return
        lore_name = f"{self._labelize_choice(chosen)} Lore"
        self._replace_status_data(
            status,
            {
                "additional_lore_choice": chosen,
                "trained_lore_skills": [lore_name],
            },
        )
        self._ui_log(f"Additional Lore: wybrano {lore_name}.")

    def _handle_assurance_choice(self, status: "Status", data: dict) -> None:
        trained = sorted(self._trained_skill_ids())
        choices = list(data.get("assurance_skill_choices") or [])
        if not choices:
            choices = trained or self._base_skill_choices()
        chosen = self._pick_choice_id(
            "Assurance: wybierz skill",
            choices,
            source="status",
        )
        if not chosen:
            return
        self._replace_status_data(
            status,
            {
                "assurance_skill": chosen,
                "assurance_skill_choices": list(dict.fromkeys(choices)),
            },
        )
        self._ui_log(f"Assurance: wybrano {self._labelize_choice(chosen)}.")

    def _handle_skill_training_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("skill_training_choices") or self._base_skill_choices())
        if not choices:
            return
        chosen = self._pick_choice_id(
            "Skill Training: wybierz skill",
            choices,
            source="status",
        )
        if not chosen:
            return
        existing = [str(item).strip().lower() for item in list(data.get("trained_skills") or []) if str(item).strip()]
        if chosen not in existing:
            existing.append(chosen)
        self._replace_status_data(
            status,
            {
                "skill_training_skill": chosen,
                "trained_skills": list(dict.fromkeys(existing)),
            },
        )
        self._ui_log(f"Skill Training: wybrano {self._labelize_choice(chosen)}.")

    def _handle_canny_acumen_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("canny_acumen_choices") or ["fortitude", "reflex", "will", "perception"])
        if not choices:
            return
        chosen = self._pick_choice_id(
            "Canny Acumen: wybierz rzut/percepcje",
            choices,
            source="status",
        )
        if not chosen:
            return
        self._replace_status_data(status, {"canny_acumen_choice": chosen})
        self._ui_log(f"Canny Acumen: wybrano {self._labelize_choice(chosen)}.")

    def _handle_terrain_stalker_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("terrain_stalker_choices") or ["rubble", "snow", "underbrush"])
        if not choices:
            return
        chosen = self._pick_choice_id(
            "Terrain Stalker: wybierz teren",
            choices,
            source="status",
        )
        if not chosen:
            return
        self._replace_status_data(status, {"terrain_stalker_choice": chosen})
        self._ui_log(f"Terrain Stalker: wybrano {self._labelize_choice(chosen)}.")

    def _handle_virtuosic_performer_choice(self, status: "Status", data: dict) -> None:
        choices = list(
            data.get("virtuosic_performer_choices")
            or ["acting", "comedy", "dance", "oratory", "singing", "strings"]
        )
        if not choices:
            return
        chosen = self._pick_choice_id(
            "Virtuosic Performer: wybierz specjalizacje",
            choices,
            source="status",
        )
        if not chosen:
            return
        self._replace_status_data(status, {"virtuosic_performer_choice": chosen})
        self._ui_log(f"Virtuosic Performer: wybrano {self._labelize_choice(chosen)}.")

    def _handle_weapon_proficiency_choice(self, status: "Status", data: dict) -> None:
        simple_trained = self._is_trained_rank(self._current_weapon_rank("simple"))
        martial_trained = self._is_trained_rank(self._current_weapon_rank("martial"))

        updates: dict[str, object] = {}
        if not simple_trained:
            updates = {
                "weapon_proficiency_grant": "simple",
                "weapon_proficiency_ranks": {"simple": "trained"},
            }
            self._ui_log("Weapon Proficiency: zyskujesz trained w simple weapons.")
        elif not martial_trained:
            updates = {
                "weapon_proficiency_grant": "martial",
                "weapon_proficiency_ranks": {"martial": "trained"},
            }
            self._ui_log("Weapon Proficiency: zyskujesz trained w martial weapons.")
        else:
            choices = list(data.get("weapon_proficiency_advanced_choices") or [])
            if not choices:
                choices = ["falcata", "falchion", "katana", "meteor_hammer"]
            chosen = self._pick_choice_id(
                "Weapon Proficiency: wybierz advanced weapon",
                choices,
                source="status",
            )
            if not chosen:
                return
            updates = {
                "weapon_proficiency_grant": "advanced",
                "weapon_proficiency_advanced_choice": chosen,
                "weapon_proficiency_overrides": {chosen: "trained"},
            }
            self._ui_log(
                "Weapon Proficiency: zyskujesz trained w "
                f"{self._labelize_choice(chosen)}."
            )

        if not updates:
            return
        self._replace_status_data(status, updates)

        rank_map = getattr(self, "weapon_proficiency_ranks", None)
        if isinstance(rank_map, dict):
            merged = dict(rank_map)
            merged.update(dict(updates.get("weapon_proficiency_ranks") or {}))
            setattr(self, "weapon_proficiency_ranks", merged)

    def _handle_armor_proficiency_choice(self, status: "Status", _data: dict) -> None:
        light_trained = self._is_trained_rank(self._current_defense_rank("light"))
        medium_trained = self._is_trained_rank(self._current_defense_rank("medium"))
        heavy_trained = self._is_trained_rank(self._current_defense_rank("heavy"))

        if not light_trained:
            grant = "light"
        elif not medium_trained:
            grant = "medium"
        elif not heavy_trained:
            grant = "heavy"
        else:
            grant = "heavy"

        updates = {
            "armor_proficiency_grant": grant,
            "defense_proficiency_ranks": {grant: "trained"},
        }
        self._replace_status_data(status, updates)

        rank_map = getattr(self, "defense_proficiency_ranks", None)
        if isinstance(rank_map, dict):
            merged = dict(rank_map)
            merged.update(dict(updates.get("defense_proficiency_ranks") or {}))
            setattr(self, "defense_proficiency_ranks", merged)

        self._ui_log(f"Armor Proficiency: zyskujesz trained w pancerzu {self._labelize_choice(grant)}.")

    def _handle_general_training_choice(self, status: "Status", data: dict) -> None:
        registry = self._general_feat_registry()
        choices = list(data.get("general_feat_choices") or list(registry.keys()))
        if not choices:
            return
        chosen_feat = self._pick_choice_id(
            "General Training: wybierz general feat",
            choices,
            source="status",
        )
        if not chosen_feat:
            return
        self._replace_status_data(status, {"general_feat": chosen_feat})

        feat_status = self._resolve_status_from_registry(chosen_feat, registry)
        if feat_status is None:
            self._ui_log(f"General Training: nie znaleziono statusu dla feata {chosen_feat}.")
            return
        self.add_status(feat_status)
        self._ui_log(f"General Training: wybrano {self._labelize_choice(chosen_feat)}.")

    def _handle_skilled_heritage_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("skilled_heritage_choices") or self._base_skill_choices())
        if not choices:
            return
        chosen_skill = self._pick_choice_id(
            "Skilled Heritage: wybierz skill",
            choices,
            source="status",
        )
        if not chosen_skill:
            return
        self._replace_status_data(
            status,
            {
                "skilled_heritage_skill": chosen_skill,
                "trained_skills": [chosen_skill],
            },
        )
        self._ui_log(f"Skilled Heritage: wybrano {self._labelize_choice(chosen_skill)}.")

    def _handle_natural_skill_choice(self, status: "Status", data: dict) -> None:
        count = int(data.get("natural_skill_choices_count", 2) or 2)
        choices = list(data.get("natural_skill_choices") or self._base_skill_choices())
        if count <= 0 or not choices:
            return

        picked: list[str] = []
        for index in range(count):
            available = [item for item in choices if item not in picked]
            if not available:
                break
            chosen_skill = self._pick_choice_id(
                f"Natural Skill: wybierz skill ({index + 1}/{count})",
                available,
                source="status",
            )
            if not chosen_skill:
                continue
            picked.append(chosen_skill)

        if not picked:
            return
        self._replace_status_data(
            status,
            {
                "trained_skills": picked,
                "natural_skill_selected_skills": picked,
            },
        )
        self._ui_log(
            "Natural Skill: wybrano "
            + ", ".join(self._labelize_choice(item) for item in picked)
            + "."
        )

    def _handle_unconventional_weaponry_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("unconventional_weaponry_choices") or [])
        if not choices:
            return
        chosen_weapon = self._pick_choice_id(
            "Unconventional Weaponry: wybierz broń",
            choices,
            source="status",
        )
        if not chosen_weapon:
            return

        advanced_choices = {
            str(item).strip().lower()
            for item in list(data.get("unconventional_weaponry_advanced_choices") or [])
            if str(item).strip()
        }
        chosen_is_advanced = chosen_weapon in advanced_choices
        if chosen_is_advanced and not self._has_martial_weapon_training():
            self._ui_log(
                "Unconventional Weaponry: advanced weapon wymaga trained we wszystkich martial weapons."
            )
            return

        counts_as = "martial" if chosen_is_advanced else "simple"
        category_from = "advanced" if chosen_is_advanced else "martial"
        category_to = counts_as

        self._replace_status_data(
            status,
            {
                "weapon_name": chosen_weapon,
                "counts_as": counts_as,
                "weapon_proficiency_overrides": {chosen_weapon: "trained"},
                "weapon_access_names": [chosen_weapon],
                "weapon_category_adjustments": [
                    {
                        "required_tag": chosen_weapon,
                        "from": category_from,
                        "to": category_to,
                    }
                ],
            },
        )
        self._ui_log(
            "Unconventional Weaponry: "
            f"{self._labelize_choice(chosen_weapon)} traktowana jako {self._labelize_choice(category_to)}."
        )

    def _handle_elf_atavism_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("elf_atavism_choices") or [])
        if not choices:
            return
        chosen_heritage = self._pick_choice_id(
            "Elf Atavism: wybierz elf heritage",
            choices,
            source="status",
        )
        if not chosen_heritage:
            return

        heritage_registry = {
            "arctic_elf": ("statuses.race.elfs.heritages.arctic_elf", "ARCTIC_ELF_STATUS"),
            "cavern_elf": ("statuses.race.elfs.heritages.cavern_elf", "CAVERN_ELF_STATUS"),
            "seer_elf": ("statuses.race.elfs.heritages.seer_elf", "SEER_ELF_STATUS"),
            "whisper_elf": ("statuses.race.elfs.heritages.whisper_elf", "WHISPER_ELF_STATUS"),
            "woodland_elf": ("statuses.race.elfs.heritages.woodland_elf", "WOODLAND_ELF_STATUS"),
        }
        heritage_status = self._resolve_status_from_registry(chosen_heritage, heritage_registry)
        self._replace_status_data(status, {"elf_atavism_choice": chosen_heritage})
        if heritage_status is None:
            self._ui_log(f"Elf Atavism: nie znaleziono heritage {chosen_heritage}.")
            return
        self.add_status(heritage_status)
        self._ui_log(f"Elf Atavism: wybrano {self._labelize_choice(chosen_heritage)}.")

    def _handle_natural_ambition_choice(self, status: "Status", data: dict) -> None:
        class_id = self._actor_class_id()
        if not class_id:
            self._ui_log("Natural Ambition: brak wspieranej klasy bohatera.")
            return

        fallback_choices_map = {
            key: list(value.keys())
            for key, value in self._class_feat_registry().items()
        }
        raw_choices_map = data.get("natural_ambition_class_feat_choices") or {}
        choices_map = {}
        if isinstance(raw_choices_map, dict):
            for key, value in raw_choices_map.items():
                if isinstance(value, list):
                    choices_map[str(key)] = list(value)
        choices = list(choices_map.get(class_id, [])) or list(fallback_choices_map.get(class_id, []))
        if class_id == "champion" and choices:
            cause = str(getattr(self, "champion_cause", "") or "").strip().lower()
            if not cause:
                cause = str(self.get_status_data("champion", "champion_cause", "") or "").strip().lower()
            if not cause:
                setup = self.get_status_data("champion", "champion_setup", {}) or {}
                if isinstance(setup, dict):
                    cause = str(setup.get("cause", "") or "").strip().lower()
            if not cause:
                fallback = [feat_id for feat_id in choices if str(feat_id).strip().lower() == "deitys_domain"]
                if fallback:
                    choices = fallback
            allowed_by_cause = {
                "paladin": {"deitys_domain", "ranged_reprisal"},
                "redeemer": {"deitys_domain", "weight_of_guilt"},
                "liberator": {"deitys_domain", "unimpeded_step"},
            }
            allowed = allowed_by_cause.get(cause)
            if allowed:
                filtered = [feat_id for feat_id in choices if str(feat_id).strip().lower() in allowed]
                if filtered:
                    choices = filtered
        if not choices:
            self._ui_log(f"Natural Ambition: brak listy featów dla klasy {class_id}.")
            return

        registry = self._class_feat_registry().get(class_id, {})
        remaining_choices = list(choices)
        chosen_feat: str | None = None

        while remaining_choices:
            picked = self._pick_choice_id(
                f"Natural Ambition ({self._labelize_choice(class_id)}): wybierz class feat",
                remaining_choices,
                source="status",
            )
            if not picked:
                return
            picked = str(picked).strip().lower()

            feat_status = self._resolve_status_from_registry(picked, registry)
            if feat_status is None:
                self._ui_log(
                    f"Natural Ambition: nie znaleziono statusu feata {picked} dla klasy {class_id}."
                )
                return

            added = bool(self.add_status(feat_status))
            if added:
                chosen_feat = picked
                break

            already_has = False
            try:
                already_has = bool(self.has_status(picked))
            except Exception:
                already_has = False
            if already_has:
                self._ui_log(
                    "Natural Ambition: "
                    f"{self._labelize_choice(picked)} jest juz na postaci. Wybierz inny feat."
                )
                remaining_choices = [item for item in remaining_choices if str(item).strip().lower() != picked]
                continue
            return

        if not chosen_feat:
            self._ui_log("Natural Ambition: brak dostepnych nowych featow do wyboru.")
            return

        self._replace_status_data(
            status,
            {
                "class_name": class_id,
                "class_feat": chosen_feat,
            },
        )
        self._ui_log(
            "Natural Ambition: "
            f"{self._labelize_choice(class_id)} -> {self._labelize_choice(chosen_feat)}."
        )

    def _handle_versatile_heritage_choice(self, status: "Status", data: dict) -> None:
        registry = self._general_feat_registry()
        choices = list(data.get("general_feat_choices") or list(registry.keys()))
        if not choices:
            return
        chosen_feat = self._pick_choice_id(
            "Versatile Heritage: wybierz general feat",
            choices,
            source="status",
        )
        if not chosen_feat:
            return

        self._replace_status_data(status, {"general_feat": chosen_feat})
        feat_status = self._resolve_status_from_registry(chosen_feat, registry)
        if feat_status is None:
            self._ui_log(f"Versatile Heritage: nie znaleziono statusu dla feata {chosen_feat}.")
            return
        self.add_status(feat_status)
        self._ui_log(f"Versatile Heritage: wybrano {self._labelize_choice(chosen_feat)}.")

    def _handle_background_martial_disciple_choice(self, status: "Status", data: dict) -> None:
        skill_choices = list(data.get("martial_disciple_skill_choices") or ["acrobatics", "athletics"])
        if not skill_choices:
            return
        chosen_skill = self._pick_choice_id(
            "Martial Disciple: wybierz trained skill",
            skill_choices,
            source="status",
        )
        if not chosen_skill:
            return

        feat_by_skill = dict(
            data.get("martial_disciple_feat_by_skill")
            or {
                "acrobatics": "cat_fall",
                "athletics": "quick_jump",
            }
        )
        chosen_feat = str(feat_by_skill.get(chosen_skill) or "").strip().lower()
        self._replace_status_data(
            status,
            {
                "martial_disciple_skill_choice": chosen_skill,
                "martial_disciple_feat_choice": chosen_feat,
            },
        )

        if not chosen_feat:
            self._ui_log("Martial Disciple: brak zdefiniowanego feata dla wybranego skilla.")
            return

        feat_registry = {
            "cat_fall": ("statuses.backgrounds.skill_feats", "CAT_FALL_STATUS"),
            "quick_jump": ("statuses.backgrounds.skill_feats", "QUICK_JUMP_STATUS"),
        }
        feat_status = self._resolve_status_from_registry(chosen_feat, feat_registry)
        if feat_status is None:
            self._ui_log(f"Martial Disciple: nie znaleziono statusu feata {chosen_feat}.")
            return
        self.add_status(feat_status)
        self._ui_log(
            "Martial Disciple: "
            f"skill={self._labelize_choice(chosen_skill)}, feat={self._labelize_choice(chosen_feat)}."
        )

    def _handle_adopted_ancestry_choice(self, status: "Status", data: dict) -> None:
        races = list(data.get("adopted_ancestry_races") or [])
        feats_map = data.get("adopted_ancestry_feats") or {}
        if not races or not feats_map:
            return
        race_labels = [self._labelize_choice(r) for r in races]
        race_label_to_id = {self._labelize_choice(r): r for r in races}
        chosen_race_label = self._prompt_choice(
            "Adopted Ancestry: wybierz ancestry",
            race_labels,
            source="status",
        )
        if not chosen_race_label:
            return
        chosen_race_id = race_label_to_id.get(chosen_race_label, None)
        if not chosen_race_id:
            chosen_race_id = str(chosen_race_label).strip().lower().replace(" ", "_")
        feats = list(feats_map.get(chosen_race_id, []) or [])
        if not feats:
            self._ui_log("Brak listy feats dla wybranej ancestry.")
            return
        feat_labels = [self._labelize_choice(f) for f in feats]
        feat_label_to_id = {self._labelize_choice(f): f for f in feats}
        chosen_feat_label = self._prompt_choice(
            f"Adopted Ancestry ({self._labelize_choice(chosen_race_id)}): wybierz feat",
            feat_labels,
            source="status",
        )
        if not chosen_feat_label:
            return
        chosen_feat_id = feat_label_to_id.get(chosen_feat_label, None)
        if not chosen_feat_id:
            chosen_feat_id = str(chosen_feat_label).strip().lower().replace(" ", "_")

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["adopted_ancestry_choice"] = {
                        "race": chosen_race_id,
                        "feat": chosen_feat_id,
                    }
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            pass

        self._ui_log(
            f"Adopted Ancestry: wybrano {self._labelize_choice(chosen_race_id)} -> "
            f"{self._labelize_choice(chosen_feat_id)}."
        )

        # Dodaj wybrany feat jako status, jeśli moduł istnieje.
        try:
            import importlib

            race_pkg = "elfs" if chosen_race_id == "elf" else chosen_race_id
            module_path = f"statuses.race.{race_pkg}.feats.{chosen_feat_id}"
            status_name = f"{chosen_feat_id.upper()}_STATUS"
            fallback = {
                "elven_weapon_familiarity": ("elfs", "elven_weapon_familiarity", "ELVEN_WEAPON_FAMILIARITY_STATUS"),
                "dwarven_weapon_familiarity": ("dwarf", "dwarven_weapon_familiarity", "DWARVEN_WEAPON_FAMILIARITY_STATUS"),
                "gnome_weapon_familiarity": ("gnome", "gnome_weapon_familiarity", "GNOME_WEAPON_FAMILIARITY_STATUS"),
                "goblin_weapon_familiarity": ("goblin", "goblin_weapon_familiarity", "GOBLIN_WEAPON_FAMILIARITY_STATUS"),
                "halfling_weapon_familiarity": ("halfling", "halfling_weapon_familiarity", "HALFLING_WEAPON_FAMILIARITY_STATUS"),
                "halfling_luck": ("halfling", "halfling_luck", "HALFLING_LUCK_STATUS"),
                "halfling_lore": ("halfling", "halfling_lore", "HALFLING_LORE_STATUS"),
                "goblin_song": ("goblin", "goblin_song", "GOBLIN_SONG_STATUS"),
                "gnome_obsession": ("gnome", "gnome_obsession", "GNOME_OBSESSION_STATUS"),
                "first_world_magic": ("gnome", "first_world_magic", "FIRST_WORLD_MAGIC_STATUS"),
                "otherworldly_magic": ("elfs", "otherworldly_magic", "OTHERWORLDLY_MAGIC_STATUS"),
                "ancestral_longevity": ("elfs", "ancestral_longevity", "ANCESTRAL_LONGEVITY_STATUS"),
                "unwavering_mien": ("elfs", "unwavering_mien", "UNWAVERING_MIEN_STATUS"),
                "nimble_elf": ("elfs", "nimble_elf", "NIMBLE_ELF_STATUS"),
            }
            module = importlib.import_module(module_path)
            feat_status = getattr(module, status_name, None)
            if feat_status is None and chosen_feat_id in fallback:
                pkg, mod, status_attr = fallback[chosen_feat_id]
                module = importlib.import_module(f"statuses.race.{pkg}.feats.{mod}")
                feat_status = getattr(module, status_attr, None)
            if feat_status is not None:
                self.add_status(feat_status)
            else:
                self._ui_log(f"Nie znaleziono statusu feata: {chosen_feat_id}.")
        except Exception:
            self._ui_log("Nie udalo sie dodac wybranego feata (brak modulu?).")

    def _handle_alchemist_research_field_choice(self, status: "Status", data: dict) -> None:
        fields = list(data.get("research_field_choices") or [])
        if not fields:
            fields = ["bomber", "chirurgeon", "mutagenist"]
        chosen_field = self._pick_choice_id(
            "Research Field: wybierz specjalizację",
            fields,
            source="status",
        )
        if not chosen_field:
            return
        chosen_field = str(chosen_field).strip().lower().replace(" ", "_")

        field_data: dict = {}
        if chosen_field == "bomber":
            field_data = {
                "bomb_splash_primary_only": True,
                "signature_items": ["acidflask", "alchemists_fire"],
            }
        elif chosen_field == "chirurgeon":
            field_data = {
                "signature_items": ["antidote", "antiplague"],
                "use_crafting_for_medicine": True,
            }
        elif chosen_field == "mutagenist":
            field_data = {
                "signature_items": ["quicksilver_mutagen", "juggernaut_mutagen"],
                "mutagen_consumed": [],
                "mutagenic_flashback_used": False,
            }

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["research_field"] = chosen_field
                    new_data.update(field_data)
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            pass

        self._ui_log(
            f"Research Field: wybrano {self._labelize_choice(chosen_field)}."
        )

    def _handle_animal_instinct_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("animal_instinct_choices") or [])
        if not choices:
            return
        label_map = {self._labelize_choice(key): key for key in choices}
        labels = list(label_map.keys())
        chosen_label = self._prompt_choice(
            "Animal Instinct: wybierz zwierzę",
            labels,
            source="status",
        )
        if not chosen_label:
            return
        chosen_key = label_map.get(chosen_label)
        if not chosen_key:
            chosen_key = str(chosen_label).strip().lower().replace(" ", "_")
        try:
            from statuses.classes.barbarian.instincts.animal_instinct import ANIMAL_INSTINCT_PROFILES
        except Exception:
            ANIMAL_INSTINCT_PROFILES = {}
        profile = dict(ANIMAL_INSTINCT_PROFILES.get(chosen_key, {}) or {})

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["animal_instinct"] = chosen_key
                    if profile:
                        new_data["animal_instinct_profile"] = profile
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Nie udalo sie ustawic Animal Instinct.")

    def _handle_dragon_instinct_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("dragon_instinct_choices") or [])
        if not choices:
            return
        # Dla stabilnosci promptow i testow zachowujemy canonical EN labels.
        label_map = {
            str(key).replace("_", " ").strip().title(): key
            for key in choices
        }
        labels = list(label_map.keys())
        chosen_label = self._prompt_choice(
            "Dragon Instinct: wybierz typ obrażeń",
            labels,
            source="status",
        )
        if not chosen_label:
            return
        chosen_key = label_map.get(chosen_label)
        if not chosen_key:
            chosen_key = str(chosen_label).strip().lower().replace(" ", "_")

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["dragon_instinct_type"] = chosen_key
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Nie udalo sie ustawic Dragon Instinct.")

    def _handle_fury_instinct_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("fury_instinct_feat_choices") or [])
        if not choices:
            return
        # Dla stabilnosci promptow i testow zachowujemy canonical EN labels.
        label_map = {
            str(key).replace("_", " ").strip().title(): key
            for key in choices
        }
        labels = list(label_map.keys())
        chosen_label = self._prompt_choice(
            "Fury Instinct: wybierz feat",
            labels,
            source="status",
        )
        if not chosen_label:
            return
        chosen_key = label_map.get(chosen_label)
        if not chosen_key:
            chosen_key = str(chosen_label).strip().lower().replace(" ", "_")

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["fury_instinct_feat"] = chosen_key
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Nie udalo sie ustawic Fury Instinct.")
            return

        try:
            from statuses.classes.barbarian.feats.cute_vision import CUTE_VISION_STATUS
            from statuses.classes.barbarian.feats.raging_thrower import RAGING_THROWER_STATUS

            feat_map = {
                "cute_vision": CUTE_VISION_STATUS,
                "raging_thrower": RAGING_THROWER_STATUS,
            }
            feat_status = feat_map.get(str(chosen_key))
            if feat_status is not None:
                self.add_status(feat_status)
            else:
                self._ui_log(f"Nie znaleziono feata: {chosen_key}.")
        except Exception:
            self._ui_log("Nie udalo sie dodac feata z Fury Instinct.")

    def _handle_spirit_instinct_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("spirit_instinct_choices") or [])
        if not choices:
            return
        label_map = {self._labelize_choice(key): key for key in choices}
        labels = list(label_map.keys())
        chosen_label = self._prompt_choice(
            "Spirit Instinct: wybierz typ obrażeń",
            labels,
            source="status",
        )
        if not chosen_label:
            return
        chosen_key = label_map.get(chosen_label)
        if not chosen_key:
            chosen_key = str(chosen_label).strip().lower().replace(" ", "_")

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["spirit_instinct_type"] = chosen_key
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Nie udalo sie ustawic Spirit Instinct.")

    @staticmethod
    def _normalize_spell_id(value: object) -> str:
        raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "shield": "shield_cantrip",
            "detectmagic": "detect_magic",
            "acidsplash": "acid_splash",
        }
        return aliases.get(raw, raw)

    def _collect_spell_choices_by_tier(
        self,
        *,
        traditions: set[str],
        tier: str,
    ) -> list[str]:
        normalized_tier = str(tier or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized_tier:
            return []
        wanted_traditions = {str(item or "").strip().lower().replace("-", "_").replace(" ", "_") for item in set(traditions or set()) if str(item or "").strip()}
        if "arcane" in wanted_traditions:
            wanted_traditions.add("arcana")
        if "arcana" in wanted_traditions:
            wanted_traditions.add("arcane")

        try:
            import GameObjects.events.all_events  # noqa: F401
            from GameObjects.events.registry import list_events
            from spell_management import classify_spell_tier
        except Exception:
            return []

        def _event_traditions(event_cls: type | None) -> set[str]:
            tags: set[str] = set()
            if event_cls is None:
                return tags
            for tag in list(getattr(event_cls, "spell_tags", []) or []):
                normalized = str(tag or "").strip().lower().replace("-", "_").replace(" ", "_")
                if normalized:
                    tags.add(normalized)
            for tag in list(getattr(event_cls, "default_tags", []) or []):
                normalized = str(tag or "").strip().lower().replace("-", "_").replace(" ", "_")
                if normalized:
                    tags.add(normalized)
            for tradition in list(getattr(event_cls, "magic_traditions", []) or []):
                normalized = str(getattr(tradition, "value", tradition) or "").strip().lower().replace("-", "_").replace(" ", "_")
                if normalized:
                    tags.add(normalized)
            if "arcane" in tags:
                tags.add("arcana")
            if "arcana" in tags:
                tags.add("arcane")
            return tags

        out: list[str] = []
        for event_name, event_cls in dict(list_events() or {}).items():
            spell_id = self._normalize_spell_id(event_name)
            if not spell_id:
                continue
            tags = _event_traditions(event_cls)
            event_tier = str(classify_spell_tier(list(tags or set())) or "").strip().lower()
            if event_tier != normalized_tier:
                continue
            if wanted_traditions and not tags.intersection(wanted_traditions):
                continue
            if spell_id not in out:
                out.append(spell_id)

        out.sort(key=lambda item: (self._labelize_choice(item).lower(), item))
        return out

    def _pick_many_choice_ids(
        self,
        *,
        prompt: str,
        choices: list[str],
        count: int,
        source: str = "status",
        preselected: list[str] | None = None,
        allow_prompt: bool = True,
    ) -> list[str]:
        selected: list[str] = []
        for item in list(preselected or []):
            normalized = str(item or "").strip().lower().replace("-", "_").replace(" ", "_")
            if normalized and normalized in choices and normalized not in selected:
                selected.append(normalized)

        limit = max(0, int(count or 0))
        if limit <= len(selected):
            return selected[:limit]
        available_seed = [str(item or "").strip().lower().replace("-", "_").replace(" ", "_") for item in list(choices or []) if str(item or "").strip()]
        available_seed = [item for item in available_seed if item]

        while len(selected) < limit:
            available = [item for item in available_seed if item not in selected]
            if not available:
                break
            chosen: str | None = None
            if allow_prompt and self._in_character_creation_mode():
                chosen = self._pick_choice_id(
                    f"{prompt} ({len(selected) + 1}/{limit})",
                    available,
                    source=source,
                )
                chosen = str(chosen or "").strip().lower().replace("-", "_").replace(" ", "_")
                if chosen not in available:
                    chosen = None
            if not chosen:
                chosen = available[0]
            selected.append(chosen)

        return selected[:limit]

    def _bard_muse_known_spell(self) -> str:
        getter = getattr(self, "get_status_data", None)
        if callable(getter):
            try:
                payload = getter("inspiration", "bard_muse_choice", {})
                if isinstance(payload, dict):
                    return self._normalize_spell_id(payload.get("known_spell"))
            except Exception:
                pass
        for status in list(getattr(self, "statuses", []) or []):
            if getattr(status, "id", None) != "inspiration":
                continue
            payload = dict((getattr(status, "data", None) or {}).get("bard_muse_choice") or {})
            return self._normalize_spell_id(payload.get("known_spell"))
        return ""

    def _handle_bard_setup_choice(self, status: "Status", data: dict) -> None:
        spell_tradition = str(data.get("bard_spell_tradition") or "occult").strip().lower()
        try:
            cantrip_count = int(data.get("bard_known_cantrips_at_level1") or 5)
        except Exception:
            cantrip_count = 5
        try:
            rank1_count = int(data.get("bard_known_rank_1_spells_at_level1") or 2)
        except Exception:
            rank1_count = 2
        try:
            rank1_slots_per_day = int(data.get("bard_rank_1_slots_per_day") or 2)
        except Exception:
            rank1_slots_per_day = 2

        bonus_cantrips = [
            self._normalize_spell_id(item)
            for item in list(data.get("bard_bonus_cantrips") or [])
            if self._normalize_spell_id(item)
        ]
        bonus_focus_spells = [
            self._normalize_spell_id(item)
            for item in list(data.get("bard_bonus_focus_spells") or [])
            if self._normalize_spell_id(item)
        ]
        muse_known_spell = self._bard_muse_known_spell()

        existing_setup = dict(data.get("bard_setup") or {})
        existing_cantrips = [
            self._normalize_spell_id(item)
            for item in list(existing_setup.get("known_cantrips") or data.get("bard_known_cantrips") or [])
            if self._normalize_spell_id(item)
        ]
        existing_rank1 = [
            self._normalize_spell_id(item)
            for item in list(existing_setup.get("known_rank_1_spells") or data.get("bard_known_rank_1_spells") or [])
            if self._normalize_spell_id(item)
        ]
        existing_focus = [
            self._normalize_spell_id(item)
            for item in list(existing_setup.get("known_focus_spells") or data.get("bard_focus_spells") or [])
            if self._normalize_spell_id(item)
        ]

        cantrip_choices = self._collect_spell_choices_by_tier(
            traditions={spell_tradition},
            tier="cantrip",
        )
        rank1_choices = self._collect_spell_choices_by_tier(
            traditions={spell_tradition},
            tier="rank_1",
        )

        allow_prompt = self._in_character_creation_mode()
        if existing_cantrips and existing_rank1 and not allow_prompt:
            chosen_cantrips = list(existing_cantrips)
            chosen_rank1 = list(existing_rank1)
        else:
            chosen_cantrips = self._pick_many_choice_ids(
                prompt=(
                    "Bard: wybierz cantrip z listy occult "
                    "(Inspire Courage i Counter Performance dostajesz automatycznie z klasy)"
                ),
                choices=cantrip_choices,
                count=max(0, cantrip_count),
                source="status",
                allow_prompt=allow_prompt,
            )
            preselected_rank1: list[str] = []
            if muse_known_spell and muse_known_spell in rank1_choices:
                preselected_rank1.append(muse_known_spell)
            chosen_rank1 = self._pick_many_choice_ids(
                prompt="Bard: wybierz czar 1. rangi",
                choices=rank1_choices,
                count=max(0, rank1_count),
                source="status",
                preselected=preselected_rank1,
                allow_prompt=allow_prompt,
            )

        for spell_id in bonus_cantrips:
            if spell_id not in chosen_cantrips:
                chosen_cantrips.append(spell_id)
        if muse_known_spell and muse_known_spell not in chosen_rank1 and muse_known_spell in rank1_choices and rank1_count > 0:
            if len(chosen_rank1) >= rank1_count:
                chosen_rank1[-1] = muse_known_spell
            else:
                chosen_rank1.append(muse_known_spell)

        chosen_focus = list(existing_focus)
        for spell_id in bonus_focus_spells:
            if spell_id not in chosen_focus:
                chosen_focus.append(spell_id)

        setup_payload = {
            "spell_tradition": spell_tradition,
            "known_cantrips": list(chosen_cantrips),
            "known_rank_1_spells": list(chosen_rank1[: max(0, rank1_count)]),
            "known_focus_spells": list(chosen_focus),
            "class_granted_cantrips": list(bonus_cantrips),
            "rank_1_slots_per_day": max(0, int(rank1_slots_per_day)),
            "muse_granted_rank_1_spell": muse_known_spell or "",
        }
        self._replace_status_data(
            status,
            {
                "bard_setup": dict(setup_payload),
                "bard_spell_tradition": spell_tradition,
                "bard_known_cantrips": list(setup_payload["known_cantrips"]),
                "bard_known_rank_1_spells": list(setup_payload["known_rank_1_spells"]),
                "bard_focus_spells": list(setup_payload["known_focus_spells"]),
                "bard_class_granted_cantrips": list(setup_payload["class_granted_cantrips"]),
                "bard_rank_1_slots_per_day": int(setup_payload["rank_1_slots_per_day"]),
            },
        )

        for attr, value in (
            ("bard_spell_tradition", spell_tradition),
            ("bard_known_cantrips", list(setup_payload["known_cantrips"])),
            ("bard_known_rank_1_spells", list(setup_payload["known_rank_1_spells"])),
            ("bard_focus_spells", list(setup_payload["known_focus_spells"])),
            ("bard_rank_1_slots_per_day", int(setup_payload["rank_1_slots_per_day"])),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        if allow_prompt:
            self._ui_log(
                "Bard setup: "
                f"cantripy={len(setup_payload['known_cantrips'])}, "
                f"czary 1. rangi={len(setup_payload['known_rank_1_spells'])}, "
                f"sloty 1. rangi/dzien={int(setup_payload['rank_1_slots_per_day'])}."
            )
            if bonus_cantrips:
                self._ui_log(
                    "Bard setup: cantripy klasowe dodane automatycznie "
                    "(nie zuzywaja puli 5 wyborow): "
                    + ", ".join(self._labelize_choice(item) for item in bonus_cantrips)
                    + "."
                )

    def _handle_bard_muse_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("bard_muse_choices") or [])
        if not choices:
            choices = ["enigma", "maestro", "polymath"]
        muse_effects = data.get("bard_muse_effects") or {}

        choice_entries: list[dict] = []
        labels: list[str] = []
        for idx, key in enumerate(choices, start=1):
            effect_data = muse_effects.get(key) or {}
            effect = str(effect_data.get("effect") or "").strip()
            feat_label = str(effect_data.get("feat_label") or "").strip()
            spell_label = str(effect_data.get("spell_label") or "").strip()
            detail_parts = [part for part in [effect, f"Feat: {feat_label}" if feat_label else "", f"Czar: {spell_label}" if spell_label else ""] if part]
            details = "; ".join(detail_parts)
            base_label = self._labelize_choice(key)
            label = f"{base_label} - {details}" if details else base_label
            feat_id = str(effect_data.get("feat") or "").strip().lower()
            spell_id = str(effect_data.get("spell") or "").strip().lower()
            spell_hint = localized_hint_pl(spell_id)
            mechanics_parts: list[str] = []
            if feat_label:
                mechanics_parts.append(f"Otrzymujesz feat: {feat_label}.")
            if spell_label:
                mechanics_parts.append(f"Dopisz do znanych czarow: {spell_label}.")
            if spell_hint:
                mechanics_parts.append(f"Mechanika czaru: {spell_hint}")
            mechanics_text = " ".join(part for part in mechanics_parts if part).strip() or "Wybierasz pakiet muzy barda."
            desc = self._structured_desc(
                name=base_label,
                fluff=effect or "Wybierasz inspiracje, ktora nadaje styl twojej muzyce i wiedzy.",
                mechanics=mechanics_text,
                when="Po zatwierdzeniu wyboru muzy barda podczas setupu klasy.",
            )
            choice_entries.append(
                {
                    "raw": key,
                    "label": label,
                    "desc": desc,
                    "key": str(idx),
                    "feat_id": feat_id,
                    "spell_id": spell_id,
                }
            )
            labels.append(label)

        chosen_label = self._prompt_choice(
            "Bard Muse: wybierz inspiracje",
            labels,
            source="status",
            choice_meta=choice_entries,
        )
        if not chosen_label:
            return

        by_raw = {str(item["raw"]).strip().lower(): str(item["raw"]).strip().lower() for item in choice_entries}
        by_label = {str(item["label"]).strip().lower(): str(item["raw"]).strip().lower() for item in choice_entries}
        raw_choice = str(chosen_label).strip().lower()
        chosen_key = by_raw.get(raw_choice) or by_label.get(raw_choice)
        if not chosen_key:
            normalized = raw_choice.replace("-", "_").replace(" ", "_")
            chosen_key = by_raw.get(normalized) or by_label.get(normalized)
        if not chosen_key and raw_choice.isdigit():
            idx = int(raw_choice) - 1
            if 0 <= idx < len(choice_entries):
                chosen_key = str(choice_entries[idx]["raw"]).strip().lower()
        if not chosen_key:
            chosen_key = str(chosen_label).split("-", 1)[0].strip().lower().replace(" ", "_")

        default_map = {
            "enigma": {"feat": "bardic_lore", "spell": "true_strike"},
            "maestro": {"feat": "lingering_composition", "spell": "soothe"},
            "polymath": {"feat": "versatile_performance", "spell": "unseen_servant"},
        }
        selected = dict(default_map.get(chosen_key, {}))
        selected.update(dict(muse_effects.get(chosen_key, {}) or {}))

        chosen_feat = str(selected.get("feat") or "").strip().lower()
        chosen_spell = str(selected.get("spell") or "").strip().lower()
        chosen_spell_label = str(selected.get("spell_label") or "").strip() or self._labelize_choice(chosen_spell)

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["bard_muse"] = chosen_key
                    new_data["bard_muse_choice"] = {
                        "muse": chosen_key,
                        "feat": chosen_feat,
                        "known_spell": chosen_spell,
                    }
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Nie udalo sie zapisac wyboru muse.")

        self._ui_log(f"Bard Muse: wybrano {self._labelize_choice(chosen_key)}.")

        try:
            from statuses.classes.bard.feats.bardic_lore import BARDIC_LORE_STATUS
            from statuses.classes.bard.feats.lingering_composition import LINGERING_COMPOSITION_STATUS
            from statuses.classes.bard.feats.versatile_performance import VERSATILE_PERFORMANCE_STATUS

            feat_map = {
                "bardic_lore": BARDIC_LORE_STATUS,
                "lingering_composition": LINGERING_COMPOSITION_STATUS,
                "versatile_performance": VERSATILE_PERFORMANCE_STATUS,
            }
            feat_status = feat_map.get(chosen_feat)
            if feat_status is not None:
                self.add_status(feat_status)
            elif chosen_feat:
                self._ui_log(f"Nie znaleziono feata: {chosen_feat}.")
        except Exception:
            self._ui_log("Nie udalo sie dodac feata z Bard Muse.")

        if chosen_spell_label:
            canonical_spell = str(chosen_spell or "").replace("_", " ").strip()
            if canonical_spell and canonical_spell.lower() not in str(chosen_spell_label).lower():
                spell_note = f"{chosen_spell_label} ({canonical_spell})"
            else:
                spell_note = chosen_spell_label
            self._ui_log(
                f"Dopisz do listy znanych czarow: {spell_note}."
            )

    def _handle_druid_setup_choice(self, status: "Status", data: dict) -> None:
        order_choices = list(data.get("druid_order_choices") or ["animal", "leaf", "storm", "wild"])
        order_skills = dict(data.get("druid_order_skills") or {})
        order_start_feats = dict(data.get("druid_order_start_feats") or {})
        order_spells = dict(data.get("druid_order_spells") or {})
        order_focus_bonus = dict(data.get("druid_order_focus_bonus") or {})
        spell_tradition = str(data.get("druid_spell_tradition") or "primal").strip().lower()
        try:
            prepared_cantrips = int(data.get("druid_prepared_cantrips_at_level1") or 5)
        except Exception:
            prepared_cantrips = 5
        try:
            prepared_rank1_slots = int(data.get("druid_prepared_rank_1_slots_at_level1") or 2)
        except Exception:
            prepared_rank1_slots = 2

        chosen_order = self._pick_choice_id(
            "Druid: wybierz order",
            order_choices,
            source="status",
        )
        if not chosen_order:
            return

        chosen_skill = str(order_skills.get(chosen_order) or "")
        chosen_feat = str(order_start_feats.get(chosen_order) or "")
        chosen_order_spell = str(order_spells.get(chosen_order) or "")
        try:
            chosen_focus_bonus = int(order_focus_bonus.get(chosen_order) or 0)
        except Exception:
            chosen_focus_bonus = 0

        setup_payload = {
            "order": chosen_order,
            "trained_skill": chosen_skill,
            "order_feat": chosen_feat,
            "order_spell": chosen_order_spell,
            "focus_bonus": chosen_focus_bonus,
            "spell_tradition": spell_tradition,
            "prepared_cantrips_at_level1": max(0, int(prepared_cantrips)),
            "prepared_rank_1_slots_at_level1": max(0, int(prepared_rank1_slots)),
        }
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["druid_setup"] = dict(setup_payload)
                    new_data["druid_order"] = chosen_order
                    new_data["druid_order_skill"] = chosen_skill
                    new_data["druid_order_feat"] = chosen_feat
                    new_data["druid_order_spell"] = chosen_order_spell
                    new_data["druid_order_focus_bonus"] = chosen_focus_bonus
                    new_data["druid_spell_tradition"] = spell_tradition
                    new_data["druid_prepared_cantrips_at_level1"] = max(0, int(prepared_cantrips))
                    new_data["druid_prepared_rank_1_slots_at_level1"] = max(0, int(prepared_rank1_slots))
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Druid setup: nie udalo sie zapisac wyborow.")
            return

        for attr, value in (
            ("druid_order", chosen_order),
            ("druid_order_skill", chosen_skill),
            ("druid_order_feat", chosen_feat),
            ("druid_order_spell", chosen_order_spell),
            ("druid_order_focus_bonus", chosen_focus_bonus),
            ("druid_spell_tradition", spell_tradition),
            ("druid_prepared_cantrips_at_level1", max(0, int(prepared_cantrips))),
            ("druid_prepared_rank_1_slots_at_level1", max(0, int(prepared_rank1_slots))),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        known_order_spells = list(getattr(self, "druid_order_spells", []) or [])
        if chosen_order_spell and chosen_order_spell not in known_order_spells:
            known_order_spells.append(chosen_order_spell)
        try:
            setattr(self, "druid_order_spells", known_order_spells)
        except Exception:
            pass

        if chosen_focus_bonus:
            try:
                current_focus = int(getattr(self, "focus_point", 0) or 0)
            except Exception:
                current_focus = 0
            try:
                setattr(self, "focus_point", max(0, current_focus + chosen_focus_bonus))
                self._sync_focus_pool_attrs()
            except Exception:
                pass

        self._ui_log(
            "Druid setup: "
            f"order={self._labelize_choice(chosen_order)}, "
            f"skill={self._labelize_choice(chosen_skill)}, "
            f"order spell={self._labelize_choice(chosen_order_spell)}."
        )
        self._ui_log(
            "Druid spellcasting: "
            f"tradycja={self._labelize_choice(spell_tradition)}, "
            f"przygotowanie startowe={max(0, int(prepared_cantrips))} cantripow i "
            f"{max(0, int(prepared_rank1_slots))} sloty rank 1."
        )
        self._ui_log(
            f"Druid order spell ({self._labelize_choice(chosen_order_spell)}): "
            "dodany do listy known focus spells."
        )

        if not chosen_feat:
            return
        registry = self._class_feat_registry().get("druid", {})
        feat_status = self._resolve_status_from_registry(chosen_feat, registry)
        if feat_status is None:
            self._ui_log(f"Druid setup: nie znaleziono feata startowego {chosen_feat}.")
            return
        self.add_status(feat_status)

    def _handle_animal_companion_type_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("animal_companion_type_choices") or [])
        if not choices:
            choices = ["wolf"]
        chosen_type = self._pick_choice_id(
            "Animal Companion: wybierz typ companions",
            choices,
            source="status",
        )
        if not chosen_type:
            chosen_type = str(data.get("animal_companion_type") or choices[0] or "wolf")
        chosen_type = str(chosen_type).strip().lower().replace("-", "_").replace(" ", "_")
        if chosen_type not in choices:
            chosen_type = str(choices[0]).strip().lower()

        self._replace_status_data(
            status,
            {
                "animal_companion_type": chosen_type,
                "animal_companion_pending": False,
            },
        )
        try:
            setattr(self, "animal_companion_type", chosen_type)
        except Exception:
            pass
        self._ui_log(f"Animal Companion: wybrano typ {self._labelize_choice(chosen_type)}.")

    def _handle_champion_setup_choice(self, status: "Status", data: dict) -> None:
        key_ability_choices = list(data.get("champion_key_ability_choices") or ["strength", "dexterity"])
        cause_choices = list(data.get("champion_cause_choices") or ["paladin", "redeemer", "liberator"])
        deity_choices = list(data.get("champion_deity_choices") or ["custom"])
        deity_skill_choices = dict(data.get("champion_deity_skill_choices") or {})

        chosen_key_ability = self._pick_choice_id(
            self._key_ability_prompt("Champion"),
            key_ability_choices,
            source="status",
        )
        if not chosen_key_ability:
            return
        chosen_cause = self._pick_choice_id(
            "Champion: wybierz cause",
            cause_choices,
            source="status",
        )
        if not chosen_cause:
            return
        chosen_deity = self._pick_choice_id(
            "Champion: wybierz deity",
            deity_choices,
            source="status",
        )
        if not chosen_deity:
            return

        available_deity_skills = list(deity_skill_choices.get(chosen_deity, [])) or list(
            deity_skill_choices.get("custom", [])
        )
        if not available_deity_skills:
            available_deity_skills = ["religion"]
        deity_label = self._labelize_choice(chosen_deity)
        chosen_deity_skill: str | None = None
        if len(available_deity_skills) == 1:
            chosen_deity_skill = str(available_deity_skills[0] or "").strip().lower()
        else:
            choice_entries: list[dict[str, str]] = []
            for idx, skill_id in enumerate(available_deity_skills, start=1):
                skill_raw = str(skill_id or "").strip()
                skill_label = self._labelize_choice(skill_raw)
                choice_entries.append(
                    {
                        "raw": skill_raw,
                        "label": skill_label,
                        "desc": self._structured_desc(
                            name=skill_label,
                            fluff=f"Umiejetnosc wynikajaca z kultu bóstwa {deity_label}.",
                            mechanics=(
                                f"Po wybraniu stajesz sie trained w {skill_label} "
                                "jako skill od bóstwa dla klasy Czempion."
                            ),
                            when="Na etapie setupu klasy Czempion.",
                        ),
                        "key": str(idx),
                    }
                )

            chosen_skill_label = self._prompt_choice(
                f"Champion ({deity_label}): wybierz skill od deity",
                [entry["label"] for entry in choice_entries],
                source="status",
                choice_meta=choice_entries,
            )
            if chosen_skill_label:
                by_raw = {str(entry["raw"]).strip().lower(): str(entry["raw"]).strip() for entry in choice_entries}
                by_label = {str(entry["label"]).strip().lower(): str(entry["raw"]).strip() for entry in choice_entries}
                text = str(chosen_skill_label).strip()
                if text.lower() in by_raw:
                    chosen_deity_skill = by_raw[text.lower()]
                elif text.lower() in by_label:
                    chosen_deity_skill = by_label[text.lower()]
                else:
                    normalized = text.lower().replace("-", "_").replace(" ", "_")
                    if normalized in by_raw:
                        chosen_deity_skill = by_raw[normalized]
                    elif text.isdigit():
                        idx = int(text) - 1
                        if 0 <= idx < len(choice_entries):
                            chosen_deity_skill = str(choice_entries[idx]["raw"]).strip()

        if not chosen_deity_skill:
            return
        trained_skills = list(
            dict.fromkeys(
                [
                    item
                    for item in ("religion", str(chosen_deity_skill).strip().lower())
                    if str(item).strip()
                ]
            )
        )

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["champion_setup"] = {
                        "key_ability": chosen_key_ability,
                        "cause": chosen_cause,
                        "deity": chosen_deity,
                        "deity_skill": chosen_deity_skill,
                        "trained_skill": chosen_deity_skill,
                        "trained_skills": list(trained_skills),
                    }
                    new_data["champion_key_ability"] = chosen_key_ability
                    new_data["champion_cause"] = chosen_cause
                    new_data["champion_deity"] = chosen_deity
                    new_data["champion_deity_skill"] = chosen_deity_skill
                    new_data["trained_skills"] = list(trained_skills)
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Nie udalo sie zapisac wyboru Champion.")
            return

        for attr, value in (
            ("champion_key_ability", chosen_key_ability),
            ("champion_cause", chosen_cause),
            ("champion_deity", chosen_deity),
            ("champion_deity_skill", chosen_deity_skill),
            ("champion_trained_skills", list(trained_skills)),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        try:
            from combat.reactions.champion_reaction import ChampionReaction

            reactions = getattr(self, "reactions", None)
            if isinstance(reactions, list):
                exists = any(getattr(item, "id", None) == "champion_reaction" for item in reactions)
                if not exists:
                    reactions.append(ChampionReaction())
        except Exception:
            self._ui_log("Nie udalo sie dodac reakcji Champion.")

        try:
            from statuses.classes.champion.feats.deific_weapon import DEIFIC_WEAPON_STATUS

            self.add_status(DEIFIC_WEAPON_STATUS)
        except Exception:
            self._ui_log("Nie udalo sie dodac cechy Deific Weapon.")

        self._ui_log(
            "Champion setup: "
            f"key ability={self._labelize_choice(chosen_key_ability)}, "
            f"cause={self._labelize_choice(chosen_cause)}, "
            f"deity={self._labelize_choice(chosen_deity)}, "
            f"skill={self._labelize_choice(chosen_deity_skill)}."
        )
        self._ui_log(
            "Champion setup (skills): "
            f"trained={', '.join(self._labelize_choice(skill_id) for skill_id in trained_skills)}."
        )

    def _handle_fighter_setup_choice(self, status: "Status", data: dict) -> None:
        key_ability_choices = list(data.get("fighter_key_ability_choices") or ["strength", "dexterity"])
        chosen_key_ability = self._pick_choice_id(
            self._key_ability_prompt("Wojownik"),
            key_ability_choices,
            source="status",
        )
        if not chosen_key_ability:
            return

        setup_payload = {"key_ability": chosen_key_ability}
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["fighter_setup"] = dict(setup_payload)
                    new_data["fighter_key_ability"] = chosen_key_ability
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Fighter setup: nie udalo sie zapisac wyboru key ability.")
            return

        for attr, value in (
            ("fighter_key_ability", chosen_key_ability),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        self._ui_log(
            "Fighter setup: "
            f"key ability={self._labelize_choice(chosen_key_ability)}."
        )
        self._ui_log("Fighter: skille prowadzisz ręcznie poza grą.")

    def _handle_monk_setup_choice(self, status: "Status", data: dict) -> None:
        key_ability_choices = list(data.get("monk_key_ability_choices") or ["strength", "dexterity"])
        feat_choices = list(data.get("monk_feat_choices") or [])

        chosen_key_ability = self._pick_choice_id(
            self._key_ability_prompt("Mnich"),
            key_ability_choices,
            source="status",
        )
        if not chosen_key_ability:
            return

        chosen_feat = self._pick_choice_id(
            "Monk: wybierz 1. poziomowy class feat",
            feat_choices,
            source="status",
        )
        if not chosen_feat:
            return

        setup_payload = {"key_ability": chosen_key_ability, "class_feat": chosen_feat}
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["monk_setup"] = dict(setup_payload)
                    new_data["monk_key_ability"] = chosen_key_ability
                    new_data["monk_class_feat"] = chosen_feat
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Monk setup: nie udalo sie zapisac wyborow.")
            return

        for attr, value in (
            ("monk_key_ability", chosen_key_ability),
            ("monk_class_feat", chosen_feat),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        registry = self._class_feat_registry().get("monk", {})
        feat_status = self._resolve_status_from_registry(chosen_feat, registry)
        if feat_status is None:
            self._ui_log(f"Monk setup: nie znaleziono statusu feata {chosen_feat}.")
            return
        self.add_status(feat_status)

        self._ui_log(
            "Monk setup: "
            f"key ability={self._labelize_choice(chosen_key_ability)}, "
            f"feat={self._labelize_choice(chosen_feat)}."
        )

    def _handle_ranger_setup_choice(self, status: "Status", data: dict) -> None:
        key_ability_choices = list(data.get("ranger_key_ability_choices") or ["strength", "dexterity"])
        hunter_edge_choices = list(data.get("ranger_hunters_edge_choices") or ["flurry", "precision", "outwit"])
        feat_choices = list(data.get("ranger_feat_choices") or [])

        chosen_key_ability = self._pick_choice_id(
            self._key_ability_prompt("Lowca"),
            key_ability_choices,
            source="status",
        )
        if not chosen_key_ability:
            return

        chosen_hunter_edge = self._pick_choice_id(
            "Ranger: wybierz hunter's edge",
            hunter_edge_choices,
            source="status",
        )
        if not chosen_hunter_edge:
            return

        chosen_feat = self._pick_choice_id(
            "Ranger: wybierz 1. poziomowy class feat",
            feat_choices,
            source="status",
        )
        if not chosen_feat:
            return

        setup_payload = {
            "key_ability": chosen_key_ability,
            "hunter_edge": chosen_hunter_edge,
            "class_feat": chosen_feat,
        }
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["ranger_setup"] = dict(setup_payload)
                    new_data["ranger_key_ability"] = chosen_key_ability
                    new_data["ranger_hunter_edge"] = chosen_hunter_edge
                    new_data["ranger_class_feat"] = chosen_feat
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Ranger setup: nie udalo sie zapisac wyborow.")
            return

        for attr, value in (
            ("ranger_key_ability", chosen_key_ability),
            ("ranger_hunter_edge", chosen_hunter_edge),
            ("ranger_class_feat", chosen_feat),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        registry = self._class_feat_registry().get("ranger", {})
        feat_status = self._resolve_status_from_registry(chosen_feat, registry)
        if feat_status is None:
            self._ui_log(f"Ranger setup: nie znaleziono statusu feata {chosen_feat}.")
            return
        self.add_status(feat_status)

        self._ui_log(
            "Ranger setup: "
            f"key ability={self._labelize_choice(chosen_key_ability)}, "
            f"hunter's edge={self._labelize_choice(chosen_hunter_edge)}, "
            f"feat={self._labelize_choice(chosen_feat)}."
        )

    def _handle_sorcerer_setup_choice(self, status: "Status", data: dict) -> None:
        key_ability_choices = list(data.get("sorcerer_key_ability_choices") or ["charisma"])
        bloodline_choices = list(data.get("sorcerer_bloodline_choices") or [])
        feat_choices = list(data.get("sorcerer_feat_choices") or [])
        try:
            cantrip_count = int(data.get("sorcerer_known_cantrips_at_level1") or 5)
        except Exception:
            cantrip_count = 5
        try:
            rank1_count = int(data.get("sorcerer_known_rank_1_spells_at_level1") or 2)
        except Exception:
            rank1_count = 2
        try:
            rank1_slots_per_day = int(data.get("sorcerer_rank_1_slots_per_day") or 3)
        except Exception:
            rank1_slots_per_day = 3
        bloodline_traditions = dict(data.get("sorcerer_bloodline_traditions") or {})
        bloodline_skills_map = dict(data.get("sorcerer_bloodline_skills") or {})
        bloodline_spells_map = dict(data.get("sorcerer_bloodline_granted_spells") or {})
        bloodline_focus_map = dict(data.get("sorcerer_bloodline_initial_focus_spells") or {})
        bloodline_magic_map = dict(data.get("sorcerer_bloodline_blood_magic") or {})
        draconic_type_choices = list(data.get("sorcerer_draconic_type_choices") or [])
        draconic_type_damage = dict(data.get("sorcerer_draconic_type_damage") or {})
        elemental_type_choices = list(data.get("sorcerer_elemental_type_choices") or ["air", "earth", "fire", "water"])
        elemental_type_damage = dict(data.get("sorcerer_elemental_type_damage") or {})

        chosen_key_ability = (
            key_ability_choices[0]
            if len(key_ability_choices) == 1
            else self._pick_choice_id(
                self._key_ability_prompt("Czarownik"),
                key_ability_choices,
                source="status",
            )
        )
        if not chosen_key_ability:
            return

        chosen_bloodline = self._pick_choice_id(
            "Sorcerer: wybierz bloodline",
            bloodline_choices,
            source="status",
        )
        if not chosen_bloodline:
            return

        chosen_dragon_type: str | None = None
        chosen_elemental_type: str | None = None
        if chosen_bloodline == "draconic":
            chosen_dragon_type = self._pick_choice_id(
                "Sorcerer (Draconic): wybierz dragon type",
                draconic_type_choices,
                source="status",
            )
            if not chosen_dragon_type:
                return
        if chosen_bloodline == "elemental":
            choice_entries: list[dict[str, str]] = []
            for idx, element_id in enumerate(elemental_type_choices, start=1):
                raw_id = str(element_id or "").strip().lower().replace("-", "_").replace(" ", "_")
                damage_type = str(elemental_type_damage.get(raw_id) or "").strip()
                label = self._labelize_choice(raw_id)
                choice_entries.append(
                    {
                        "raw": raw_id,
                        "label": label,
                        "desc": self._structured_desc(
                            name=label,
                            fluff=f"Element twojej linii krwi: {label}.",
                            mechanics=(
                                f"Po wybraniu bloodline Elemental ustawiasz wariant {label}; "
                                f"damage type efektow bloodline to {self._labelize_choice(damage_type)}."
                            ),
                            when="Podczas setupu Sorcerer (Elemental).",
                        ),
                        "key": str(idx),
                    }
                )
            chosen_label = self._prompt_choice(
                "Sorcerer (Elemental): wybierz elemental type",
                [entry["label"] for entry in choice_entries],
                source="status",
                choice_meta=choice_entries,
            )
            if chosen_label:
                by_raw = {str(entry["raw"]).strip().lower(): str(entry["raw"]).strip() for entry in choice_entries}
                by_label = {str(entry["label"]).strip().lower(): str(entry["raw"]).strip() for entry in choice_entries}
                text = str(chosen_label).strip()
                if text.lower() in by_raw:
                    chosen_elemental_type = by_raw[text.lower()]
                elif text.lower() in by_label:
                    chosen_elemental_type = by_label[text.lower()]
                else:
                    normalized = text.lower().replace("-", "_").replace(" ", "_")
                    if normalized in by_raw:
                        chosen_elemental_type = by_raw[normalized]
                    elif text.isdigit():
                        idx = int(text) - 1
                        if 0 <= idx < len(choice_entries):
                            chosen_elemental_type = str(choice_entries[idx]["raw"]).strip()
            if not chosen_elemental_type:
                return

        chosen_feat = self._pick_choice_id(
            "Sorcerer: wybierz 1. poziomowy class feat",
            feat_choices,
            source="status",
        )
        if not chosen_feat:
            return

        chosen_tradition = str(bloodline_traditions.get(chosen_bloodline) or "")
        bloodline_skills = list(bloodline_skills_map.get(chosen_bloodline) or [])
        bloodline_spells = dict(bloodline_spells_map.get(chosen_bloodline) or {})
        bloodline_cantrip = str(bloodline_spells.get("cantrip") or "")
        bloodline_rank_1_spell = str(bloodline_spells.get("rank_1") or "")
        bloodline_focus_spell = str(bloodline_focus_map.get(chosen_bloodline) or "")
        blood_magic = str(bloodline_magic_map.get(chosen_bloodline) or "")
        chosen_dragon_damage_type = (
            str(draconic_type_damage.get(chosen_dragon_type) or "") if chosen_dragon_type else None
        )
        chosen_elemental_damage_type = (
            str(elemental_type_damage.get(chosen_elemental_type) or "") if chosen_elemental_type else None
        )

        spell_traditions = {str(chosen_tradition).strip().lower()} if str(chosen_tradition).strip() else set()
        cantrip_choices = self._collect_spell_choices_by_tier(
            traditions=spell_traditions,
            tier="cantrip",
        )
        rank1_choices = self._collect_spell_choices_by_tier(
            traditions=spell_traditions,
            tier="rank_1",
        )
        if bloodline_rank_1_spell:
            filtered_rank1 = [spell_id for spell_id in list(rank1_choices or []) if spell_id != bloodline_rank_1_spell]
            if filtered_rank1:
                rank1_choices = filtered_rank1
        existing_setup = dict(data.get("sorcerer_setup") or {})
        existing_cantrips = [
            self._normalize_spell_id(item)
            for item in list(
                existing_setup.get("known_cantrips")
                or data.get("sorcerer_known_cantrips")
                or getattr(self, "sorcerer_known_cantrips", [])
                or []
            )
            if self._normalize_spell_id(item)
        ]
        existing_rank1 = [
            self._normalize_spell_id(item)
            for item in list(
                existing_setup.get("known_rank_1_spells")
                or data.get("sorcerer_known_rank_1_spells")
                or getattr(self, "sorcerer_known_rank_1_spells", [])
                or []
            )
            if self._normalize_spell_id(item)
        ]
        allow_prompt = self._in_character_creation_mode()
        if existing_cantrips and existing_rank1 and not allow_prompt:
            chosen_cantrips = list(existing_cantrips)
            chosen_rank1 = list(existing_rank1)
        else:
            preselected_cantrips = [bloodline_cantrip] if bloodline_cantrip and bloodline_cantrip in cantrip_choices else []
            chosen_cantrips = self._pick_many_choice_ids(
                prompt="Sorcerer: wybierz cantrip",
                choices=cantrip_choices,
                count=max(0, cantrip_count),
                source="status",
                preselected=preselected_cantrips,
                allow_prompt=allow_prompt,
            )
            chosen_rank1 = self._pick_many_choice_ids(
                prompt="Sorcerer: wybierz czar 1. rangi",
                choices=rank1_choices,
                count=max(0, rank1_count),
                source="status",
                allow_prompt=allow_prompt,
            )
        if bloodline_cantrip and bloodline_cantrip not in chosen_cantrips:
            chosen_cantrips.append(bloodline_cantrip)
        if bloodline_rank_1_spell and bloodline_rank_1_spell not in chosen_rank1:
            chosen_rank1.append(bloodline_rank_1_spell)
        chosen_cantrips = list(dict.fromkeys([item for item in chosen_cantrips if item]))
        chosen_rank1 = list(dict.fromkeys([item for item in chosen_rank1 if item]))

        setup_payload = {
            "key_ability": chosen_key_ability,
            "bloodline": chosen_bloodline,
            "spell_tradition": chosen_tradition,
            "class_feat": chosen_feat,
            "trained_skills": list(bloodline_skills),
            "known_cantrips": list(chosen_cantrips),
            "known_rank_1_spells": list(chosen_rank1),
            "rank_1_slots_per_day": max(0, int(rank1_slots_per_day)),
            "bloodline_cantrip": bloodline_cantrip,
            "bloodline_rank_1_spell": bloodline_rank_1_spell,
            "bloodline_initial_focus_spell": bloodline_focus_spell,
            "blood_magic": blood_magic,
        }
        if chosen_dragon_type:
            setup_payload["dragon_type"] = chosen_dragon_type
            setup_payload["dragon_damage_type"] = chosen_dragon_damage_type
        if chosen_elemental_type:
            setup_payload["elemental_type"] = chosen_elemental_type
            setup_payload["elemental_damage_type"] = chosen_elemental_damage_type

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["sorcerer_setup"] = dict(setup_payload)
                    new_data["sorcerer_key_ability"] = chosen_key_ability
                    new_data["sorcerer_bloodline"] = chosen_bloodline
                    new_data["sorcerer_spell_tradition"] = chosen_tradition
                    new_data["sorcerer_class_feat"] = chosen_feat
                    new_data["sorcerer_known_cantrips"] = list(chosen_cantrips)
                    new_data["sorcerer_known_rank_1_spells"] = list(chosen_rank1)
                    new_data["sorcerer_rank_1_slots_per_day"] = int(setup_payload["rank_1_slots_per_day"])
                    new_data["sorcerer_bloodline_skills"] = list(bloodline_skills)
                    new_data["sorcerer_bloodline_granted_spells"] = dict(bloodline_spells)
                    new_data["sorcerer_bloodline_initial_focus_spell"] = bloodline_focus_spell
                    new_data["sorcerer_blood_magic"] = blood_magic
                    if chosen_dragon_type:
                        new_data["sorcerer_dragon_type"] = chosen_dragon_type
                        new_data["sorcerer_dragon_damage_type"] = chosen_dragon_damage_type
                    if chosen_elemental_type:
                        new_data["sorcerer_elemental_type"] = chosen_elemental_type
                        new_data["sorcerer_elemental_damage_type"] = chosen_elemental_damage_type
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Sorcerer setup: nie udalo sie zapisac wyborow.")
            return

        for attr, value in (
            ("sorcerer_key_ability", chosen_key_ability),
            ("sorcerer_bloodline", chosen_bloodline),
            ("sorcerer_spell_tradition", chosen_tradition),
            ("sorcerer_class_feat", chosen_feat),
            ("sorcerer_known_cantrips", list(chosen_cantrips)),
            ("sorcerer_known_rank_1_spells", list(chosen_rank1)),
            ("sorcerer_rank_1_slots_per_day", int(setup_payload["rank_1_slots_per_day"])),
            ("sorcerer_bloodline_skills", list(bloodline_skills)),
            ("sorcerer_bloodline_granted_spells", dict(bloodline_spells)),
            ("sorcerer_bloodline_initial_focus_spell", bloodline_focus_spell),
            ("sorcerer_blood_magic", blood_magic),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass
        if chosen_dragon_type:
            try:
                setattr(self, "sorcerer_dragon_type", chosen_dragon_type)
                setattr(self, "sorcerer_dragon_damage_type", chosen_dragon_damage_type)
            except Exception:
                pass
        if chosen_elemental_type:
            try:
                setattr(self, "sorcerer_elemental_type", chosen_elemental_type)
                setattr(self, "sorcerer_elemental_damage_type", chosen_elemental_damage_type)
            except Exception:
                pass

        known_cantrips = list(dict.fromkeys([self._normalize_spell_id(item) for item in list(chosen_cantrips) if self._normalize_spell_id(item)]))
        known_rank_1 = list(dict.fromkeys([self._normalize_spell_id(item) for item in list(chosen_rank1) if self._normalize_spell_id(item)]))
        known_focus_spells = list(getattr(self, "sorcerer_focus_spells", []) or [])
        if bloodline_focus_spell and bloodline_focus_spell not in known_focus_spells:
            known_focus_spells.append(bloodline_focus_spell)
        try:
            setattr(self, "sorcerer_known_cantrips", known_cantrips)
            setattr(self, "sorcerer_known_rank_1_spells", known_rank_1)
            setattr(self, "sorcerer_focus_spells", known_focus_spells)
        except Exception:
            pass

        self._ui_log(
            "Sorcerer setup: "
            f"bloodline={self._labelize_choice(chosen_bloodline)}, "
            f"tradition={self._labelize_choice(chosen_tradition)}, "
            f"feat={self._labelize_choice(chosen_feat)}."
        )
        if chosen_dragon_type:
            self._ui_log(
                "Draconic bloodline: "
                f"dragon type={self._labelize_choice(chosen_dragon_type)} "
                f"({self._labelize_choice(chosen_dragon_damage_type)})."
            )
        if chosen_elemental_type:
            self._ui_log(
                "Elemental bloodline: "
                f"element={self._labelize_choice(chosen_elemental_type)} "
                f"({self._labelize_choice(chosen_elemental_damage_type)})."
            )
        if bloodline_cantrip or bloodline_rank_1_spell:
            self._ui_log(
                "Bloodline granted spells: "
                f"cantrip={self._labelize_choice(bloodline_cantrip)}, "
                f"rank 1={self._labelize_choice(bloodline_rank_1_spell)}."
            )
        self._ui_log(
            "Sorcerer spellcasting: "
            f"cantripy={len(known_cantrips)}, "
            f"czary 1. rangi={len(known_rank_1)}, "
            f"sloty 1. rangi/dzien={int(setup_payload['rank_1_slots_per_day'])}."
        )
        if bloodline_focus_spell:
            self._ui_log(
                "Bloodline focus spell: "
                f"{self._labelize_choice(bloodline_focus_spell)}."
            )
        if blood_magic:
            self._ui_log(f"Blood Magic ({self._labelize_choice(chosen_bloodline)}): {blood_magic}")

        registry = self._class_feat_registry().get("sorcerer", {})
        feat_status = self._resolve_status_from_registry(chosen_feat, registry)
        if feat_status is None:
            self._ui_log(f"Sorcerer setup: nie znaleziono statusu feata {chosen_feat}.")
            return
        self.add_status(feat_status)

    def _handle_wizard_setup_choice(self, status: "Status", data: dict) -> None:
        key_ability_choices = list(data.get("wizard_key_ability_choices") or ["intelligence"])
        arcane_study_choices = list(data.get("wizard_arcane_study_choices") or [])
        arcane_school_choices = list(data.get("wizard_arcane_school_choices") or [])
        thesis_choices = list(data.get("wizard_arcane_thesis_choices") or [])
        feat_choices = list(data.get("wizard_feat_choices") or [])
        metamagic_feat_choices = list(data.get("wizard_metamagic_feat_choices") or ["reach_spell", "widen_spell"])
        bonded_item_choices = list(data.get("wizard_bonded_item_choices") or ["wand", "ring", "staff", "weapon", "other_item"])
        school_initial_spells = dict(data.get("wizard_school_initial_spells") or {})
        school_focus_spells = dict(data.get("wizard_school_focus_spells") or {})
        universalist_focus_spell = str(data.get("wizard_universalist_focus_spell") or "hand_of_the_apprentice")

        try:
            prepared_cantrips_base = int(data.get("wizard_prepared_cantrips_per_day") or 5)
        except Exception:
            prepared_cantrips_base = 5
        try:
            prepared_rank1_base = int(data.get("wizard_prepared_rank1_spells_per_day") or 2)
        except Exception:
            prepared_rank1_base = 2
        try:
            specialist_bonus_cantrip = int(data.get("wizard_specialist_bonus_cantrip") or 1)
        except Exception:
            specialist_bonus_cantrip = 1

        chosen_key_ability = (
            key_ability_choices[0]
            if len(key_ability_choices) == 1
            else self._pick_choice_id(
                self._key_ability_prompt("Czarodziej"),
                key_ability_choices,
                source="status",
            )
        )
        if not chosen_key_ability:
            return

        if not arcane_study_choices:
            arcane_study_choices = list(arcane_school_choices)
            if "universalist" not in arcane_study_choices:
                arcane_study_choices.append("universalist")
        chosen_arcane_study = self._pick_choice_id(
            "Wizard: wybierz arcane school lub universalist",
            arcane_study_choices,
            source="status",
        )
        if not chosen_arcane_study:
            return
        chosen_school = None if chosen_arcane_study == "universalist" else chosen_arcane_study

        chosen_thesis = self._pick_choice_id(
            "Wizard: wybierz arcane thesis",
            thesis_choices,
            source="status",
        )
        if not chosen_thesis:
            return

        available_feat_choices = [feat for feat in list(feat_choices) if feat != "hand_of_the_apprentice"]
        chosen_feat = self._pick_choice_id(
            "Wizard: wybierz 1. poziomowy class feat",
            available_feat_choices,
            source="status",
        )
        if not chosen_feat:
            return

        chosen_bonus_feat: str | None = None
        if chosen_arcane_study == "universalist" and bool(data.get("wizard_universalist_bonus_feat", True)):
            bonus_pool = [feat for feat in available_feat_choices if feat != chosen_feat]
            if bonus_pool:
                chosen_bonus_feat = self._pick_choice_id(
                    "Wizard (Universalist): wybierz bonusowy class feat",
                    bonus_pool,
                    source="status",
                )
                if not chosen_bonus_feat:
                    return

        chosen_metamagic_feat: str | None = None
        if chosen_thesis == "metamagical_experimentation":
            chosen_metamagic_feat = self._pick_choice_id(
                "Wizard (Metamagical Experimentation): wybierz metamagic feat",
                metamagic_feat_choices,
                source="status",
            )
            if not chosen_metamagic_feat:
                return

        bond_source = "item"
        drain_action = "drain_bonded_item"
        chosen_bonded_item: str | None = None
        if chosen_thesis == "improved_familiar_attunement":
            bond_source = "familiar"
            drain_action = "drain_familiar"
        elif chosen_thesis == "staff_nexus":
            chosen_bonded_item = "staff"
        else:
            chosen_bonded_item = self._pick_choice_id(
                "Wizard: wybierz bonded item",
                bonded_item_choices,
                source="status",
            )
            if not chosen_bonded_item and bonded_item_choices:
                chosen_bonded_item = bonded_item_choices[0]
            if not chosen_bonded_item:
                chosen_bonded_item = "wand"

        school_bonus_spell = str(school_initial_spells.get(chosen_school) or "")
        school_focus_spell = str(school_focus_spells.get(chosen_school) or "")
        specialist = bool(chosen_school)

        total_prepared_cantrips = prepared_cantrips_base + (specialist_bonus_cantrip if specialist else 0)
        total_prepared_rank1_slots = prepared_rank1_base + (1 if specialist and bool(data.get("wizard_specialist_bonus_slot_per_rank", True)) else 0)

        try:
            spellbook_start_cantrips = int(data.get("wizard_spellbook_start_cantrips") or 10)
        except Exception:
            spellbook_start_cantrips = 10
        try:
            spellbook_start_rank1_spells = int(data.get("wizard_spellbook_start_rank1_spells") or 5)
        except Exception:
            spellbook_start_rank1_spells = 5
        try:
            spellbook_auto_add_per_level = int(data.get("wizard_spellbook_auto_add_spells_per_level") or 2)
        except Exception:
            spellbook_auto_add_per_level = 2

        spell_traditions = {"arcane"}
        cantrip_choices = self._collect_spell_choices_by_tier(
            traditions=spell_traditions,
            tier="cantrip",
        )
        rank1_choices = self._collect_spell_choices_by_tier(
            traditions=spell_traditions,
            tier="rank_1",
        )

        existing_setup = dict(data.get("wizard_setup") or {})
        raw_existing_spellbook = existing_setup.get("spellbook")
        if not isinstance(raw_existing_spellbook, dict):
            raw_existing_spellbook = getattr(self, "wizard_spellbook", {}) or {}
        existing_spellbook = dict(raw_existing_spellbook) if isinstance(raw_existing_spellbook, dict) else {}

        def _extract_spellbook_list(raw_book: dict, tier_key: str) -> list[str]:
            out: list[str] = []
            if not isinstance(raw_book, dict):
                return out
            candidates = [raw_book.get(tier_key)]
            if tier_key == "rank_1":
                candidates.append(raw_book.get("rank1"))
            if tier_key == "cantrip":
                candidates.append(raw_book.get("cantrips"))
            for raw in candidates:
                if isinstance(raw, str):
                    raw = [raw]
                if not isinstance(raw, (list, tuple, set)):
                    continue
                for item in raw:
                    normalized = self._normalize_spell_id(item)
                    if normalized and normalized not in out:
                        out.append(normalized)
            return out

        existing_spellbook_cantrips = _extract_spellbook_list(existing_spellbook, "cantrip")
        existing_spellbook_rank1 = _extract_spellbook_list(existing_spellbook, "rank_1")
        allow_prompt = self._in_character_creation_mode()
        if existing_spellbook_cantrips and existing_spellbook_rank1 and not allow_prompt:
            spellbook_cantrips = list(existing_spellbook_cantrips)
            spellbook_rank1 = list(existing_spellbook_rank1)
        else:
            spellbook_cantrips = self._pick_many_choice_ids(
                prompt="Wizard: wybierz cantripy do spellbooka",
                choices=cantrip_choices,
                count=max(0, int(spellbook_start_cantrips)),
                source="status",
                allow_prompt=allow_prompt,
            )
            spellbook_rank1 = self._pick_many_choice_ids(
                prompt="Wizard: wybierz czary 1. rangi do spellbooka",
                choices=rank1_choices,
                count=max(0, int(spellbook_start_rank1_spells)),
                source="status",
                allow_prompt=allow_prompt,
            )

        universalist_bonus_spell: str | None = None
        if chosen_arcane_study == "universalist" and rank1_choices:
            if allow_prompt:
                universalist_bonus_spell = self._pick_choice_id(
                    "Wizard (Universalist): wybierz dodatkowy czar 1. rangi do spellbooka",
                    rank1_choices,
                    source="status",
                )
            if universalist_bonus_spell and universalist_bonus_spell in spellbook_rank1:
                replacement = next((candidate for candidate in rank1_choices if candidate not in spellbook_rank1), None)
                if replacement:
                    universalist_bonus_spell = replacement
            if not universalist_bonus_spell:
                for candidate in rank1_choices:
                    if candidate not in spellbook_rank1:
                        universalist_bonus_spell = candidate
                        break
                if not universalist_bonus_spell:
                    universalist_bonus_spell = rank1_choices[0]
            if universalist_bonus_spell and universalist_bonus_spell not in spellbook_rank1:
                spellbook_rank1.append(universalist_bonus_spell)

        if school_bonus_spell and school_bonus_spell not in spellbook_rank1:
            spellbook_rank1.append(school_bonus_spell)

        spellbook_payload: dict[str, object] = {
            "spell_tradition": "arcane",
            "cantrip": list(dict.fromkeys([self._normalize_spell_id(item) for item in spellbook_cantrips if self._normalize_spell_id(item)])),
            "rank_1": list(dict.fromkeys([self._normalize_spell_id(item) for item in spellbook_rank1 if self._normalize_spell_id(item)])),
            "rank_2": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_2") or []) if self._normalize_spell_id(item)])),
            "rank_3": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_3") or []) if self._normalize_spell_id(item)])),
            "rank_4": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_4") or []) if self._normalize_spell_id(item)])),
            "rank_5": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_5") or []) if self._normalize_spell_id(item)])),
            "rank_6": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_6") or []) if self._normalize_spell_id(item)])),
            "rank_7": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_7") or []) if self._normalize_spell_id(item)])),
            "rank_8": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_8") or []) if self._normalize_spell_id(item)])),
            "rank_9": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_9") or []) if self._normalize_spell_id(item)])),
            "rank_10": list(dict.fromkeys([self._normalize_spell_id(item) for item in list(existing_spellbook.get("rank_10") or []) if self._normalize_spell_id(item)])),
            "cantrips_count": max(0, int(spellbook_start_cantrips)),
            "rank1_spells_count": max(0, int(spellbook_start_rank1_spells)),
            "auto_add_spells_per_level": max(0, int(spellbook_auto_add_per_level)),
        }

        staff_nexus_cantrip: str | None = None
        staff_nexus_rank1_spell: str | None = None
        if chosen_thesis == "staff_nexus":
            staff_cantrip_choices = list(spellbook_payload.get("cantrip") or [])
            staff_rank1_choices = list(spellbook_payload.get("rank_1") or [])
            if staff_cantrip_choices:
                staff_nexus_cantrip = self._pick_choice_id(
                    "Wizard (Staff Nexus): wybierz cantrip w makeshift staffie",
                    staff_cantrip_choices,
                    source="status",
                )
                if not staff_nexus_cantrip:
                    staff_nexus_cantrip = staff_cantrip_choices[0]
            if staff_rank1_choices:
                staff_nexus_rank1_spell = self._pick_choice_id(
                    "Wizard (Staff Nexus): wybierz czar 1. rangi w makeshift staffie",
                    staff_rank1_choices,
                    source="status",
                )
                if not staff_nexus_rank1_spell:
                    staff_nexus_rank1_spell = staff_rank1_choices[0]

        setup_payload = {
            "key_ability": chosen_key_ability,
            "arcane_study": chosen_arcane_study,
            "school": chosen_school,
            "thesis": chosen_thesis,
            "class_feat": chosen_feat,
            "bonus_class_feat": chosen_bonus_feat,
            "thesis_metamagic_feat": chosen_metamagic_feat,
            "spell_tradition": "arcane",
            "school_bonus_spell": school_bonus_spell,
            "school_focus_spell": school_focus_spell,
            "universalist_focus_spell": universalist_focus_spell if chosen_arcane_study == "universalist" else "",
            "bond_source": bond_source,
            "bonded_item": chosen_bonded_item,
            "drain_action": drain_action,
            "spellbook_start_cantrips": spellbook_start_cantrips,
            "spellbook_start_rank1_spells": spellbook_start_rank1_spells,
            "spellbook_auto_add_per_level": spellbook_auto_add_per_level,
            "spellbook": dict(spellbook_payload),
            "staff_nexus_cantrip": str(staff_nexus_cantrip or ""),
            "staff_nexus_rank_1_spell": str(staff_nexus_rank1_spell or ""),
            "universalist_bonus_spell": str(universalist_bonus_spell or ""),
            "prepared_cantrips": total_prepared_cantrips,
            "prepared_rank1_slots": total_prepared_rank1_slots,
            "specialist_bonus_cantrip": specialist_bonus_cantrip if specialist else 0,
            "specialist_bonus_rank1_slot": 1 if specialist else 0,
            "specialist_bonus_slot_per_rank": bool(data.get("wizard_specialist_bonus_slot_per_rank", True)),
        }
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["wizard_setup"] = dict(setup_payload)
                    new_data["wizard_key_ability"] = chosen_key_ability
                    new_data["wizard_arcane_study"] = chosen_arcane_study
                    new_data["wizard_school"] = chosen_school
                    new_data["wizard_thesis"] = chosen_thesis
                    new_data["wizard_class_feat"] = chosen_feat
                    new_data["wizard_bonus_class_feat"] = chosen_bonus_feat
                    new_data["wizard_thesis_metamagic_feat"] = chosen_metamagic_feat
                    new_data["wizard_spell_tradition"] = "arcane"
                    new_data["wizard_school_bonus_spell"] = school_bonus_spell
                    new_data["wizard_school_focus_spell"] = school_focus_spell
                    new_data["wizard_bond_source"] = bond_source
                    new_data["wizard_bonded_item"] = chosen_bonded_item
                    new_data["wizard_drain_action"] = drain_action
                    new_data["wizard_spellbook"] = dict(spellbook_payload)
                    new_data["wizard_staff_nexus_cantrip"] = str(staff_nexus_cantrip or "")
                    new_data["wizard_staff_nexus_rank_1_spell"] = str(staff_nexus_rank1_spell or "")
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Wizard setup: nie udalo sie zapisac wyborow.")
            return

        for attr, value in (
            ("wizard_key_ability", chosen_key_ability),
            ("wizard_arcane_study", chosen_arcane_study),
            ("wizard_school", chosen_school),
            ("wizard_thesis", chosen_thesis),
            ("wizard_class_feat", chosen_feat),
            ("wizard_bonus_class_feat", chosen_bonus_feat),
            ("wizard_thesis_metamagic_feat", chosen_metamagic_feat),
            ("wizard_spell_tradition", "arcane"),
            ("wizard_school_bonus_spell", school_bonus_spell),
            ("wizard_school_focus_spell", school_focus_spell),
            ("wizard_bond_source", bond_source),
            ("wizard_bonded_item", chosen_bonded_item),
            ("wizard_drain_action", drain_action),
            ("wizard_spellbook", dict(spellbook_payload)),
            ("wizard_staff_nexus_cantrip", str(staff_nexus_cantrip or "")),
            ("wizard_staff_nexus_rank_1_spell", str(staff_nexus_rank1_spell or "")),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        wizard_spellbook = dict(spellbook_payload)
        try:
            setattr(self, "wizard_spellbook", wizard_spellbook)
        except Exception:
            pass

        known_school_spells = list(getattr(self, "wizard_school_spells", []) or [])
        if school_bonus_spell and school_bonus_spell not in known_school_spells:
            known_school_spells.append(school_bonus_spell)
        known_focus_spells = list(getattr(self, "wizard_focus_spells", []) or [])
        if school_focus_spell and school_focus_spell not in known_focus_spells:
            known_focus_spells.append(school_focus_spell)
        if chosen_arcane_study == "universalist" and universalist_focus_spell and universalist_focus_spell not in known_focus_spells:
            known_focus_spells.append(universalist_focus_spell)
        try:
            setattr(self, "wizard_school_spells", known_school_spells)
            setattr(self, "wizard_focus_spells", known_focus_spells)
            setattr(self, "wizard_prepared_cantrips", total_prepared_cantrips)
            setattr(self, "wizard_prepared_rank1_slots", total_prepared_rank1_slots)
        except Exception:
            pass

        if school_focus_spell or (chosen_arcane_study == "universalist" and universalist_focus_spell):
            try:
                current_focus = int(getattr(self, "focus_point", 0) or 0)
            except Exception:
                current_focus = 0
            try:
                setattr(self, "focus_point", max(1, current_focus))
                self._sync_focus_pool_attrs(minimum_pool=1)
            except Exception:
                pass

        registry = self._class_feat_registry().get("wizard", {})
        feats_to_apply = [chosen_feat, chosen_bonus_feat, chosen_metamagic_feat]
        applied_feats: list[str] = []
        for feat_id in feats_to_apply:
            if not feat_id:
                continue
            if feat_id in applied_feats:
                continue
            feat_status = self._resolve_status_from_registry(feat_id, registry)
            if feat_status is None:
                self._ui_log(f"Wizard setup: nie znaleziono statusu feata {feat_id}.")
                continue
            self.add_status(feat_status)
            applied_feats.append(str(feat_id))

        if chosen_thesis == "improved_familiar_attunement" and "familiar" not in applied_feats:
            familiar_status = self._resolve_status_from_registry("familiar", registry)
            if familiar_status is not None:
                self.add_status(familiar_status)
                applied_feats.append("familiar")

        if chosen_arcane_study == "universalist":
            hand_status = self._resolve_status_from_registry("hand_of_the_apprentice", registry)
            if hand_status is not None and not self.has_status("hand_of_the_apprentice"):
                self.add_status(hand_status)
            known_focus_spells = list(getattr(self, "wizard_focus_spells", []) or [])
            if universalist_focus_spell and universalist_focus_spell not in known_focus_spells:
                known_focus_spells.append(universalist_focus_spell)
            try:
                setattr(self, "wizard_focus_spells", known_focus_spells)
            except Exception:
                pass

        self._ui_log(
            "Wizard setup: "
            f"study={self._labelize_choice(chosen_arcane_study)}, "
            f"thesis={self._labelize_choice(chosen_thesis)}, "
            f"feat={self._labelize_choice(chosen_feat)}."
        )
        if chosen_bonus_feat:
            self._ui_log(
                "Wizard setup (Universalist): "
                f"bonus feat={self._labelize_choice(chosen_bonus_feat)}."
            )
        if chosen_arcane_study == "universalist":
            self._ui_log(
                "Wizard setup (Universalist): "
                f"focus spell={self._labelize_choice(universalist_focus_spell)} dodany automatycznie."
            )
        if chosen_metamagic_feat:
            self._ui_log(
                "Wizard thesis (Metamagical Experimentation): "
                f"aktywny feat={self._labelize_choice(chosen_metamagic_feat)}."
            )
        if chosen_thesis == "staff_nexus":
            self._ui_log(
                "Wizard thesis (Staff Nexus): "
                f"bonded item=staff; makeshift staff: cantrip={self._labelize_choice(staff_nexus_cantrip)}, "
                f"rank1={self._labelize_choice(staff_nexus_rank1_spell)}."
            )
        if chosen_thesis == "spell_blending":
            self._ui_log(
                "Wizard thesis (Spell Blending): "
                "na początku scenariusza (daily preparations) możesz wymieniać sloty i zamieniać slot na +2 cantripy."
            )
        if chosen_thesis == "spell_substitution":
            self._ui_log(
                "Wizard thesis (Spell Substitution): "
                "poza walką odblokowuje akcję 10-minutowej podmiany przygotowanego czaru (1 raz na scenariusz)."
            )
        if school_bonus_spell or school_focus_spell:
            self._ui_log(
                "Wizard school bonusy: "
                f"spell={self._labelize_choice(school_bonus_spell)}, "
                f"focus spell={self._labelize_choice(school_focus_spell)}."
            )
        self._ui_log(
            "Wizard spellbook: "
            f"{len(list(wizard_spellbook.get('cantrip', []) or []))} cantrips, "
            f"{len(list(wizard_spellbook.get('rank_1', []) or []))} rank-1 spells, "
            f"+{spellbook_auto_add_per_level} spells/level."
        )
        if universalist_bonus_spell:
            self._ui_log(
                "Wizard (Universalist): "
                f"dodatkowy czar do spellbooka={self._labelize_choice(universalist_bonus_spell)}."
            )
        self._ui_log(
            "Wizard prepared today: "
            f"{total_prepared_cantrips} cantrips, {total_prepared_rank1_slots} rank-1 slots."
        )

    def _handle_rogue_setup_choice(self, status: "Status", data: dict) -> None:
        racket_choices = list(data.get("rogue_racket_choices") or ["ruffian", "scoundrel", "thief"])
        feat_choices = list(data.get("rogue_feat_choices") or [])
        key_by_racket = dict(
            data.get("rogue_key_ability_by_racket")
            or {
                "ruffian": ["dexterity", "strength"],
                "scoundrel": ["dexterity", "charisma"],
                "thief": ["dexterity"],
            }
        )
        trained_skills_by_racket = dict(
            data.get("rogue_trained_skills_by_racket")
            or {
                "ruffian": ["intimidation"],
                "scoundrel": ["deception", "diplomacy"],
                "thief": ["thievery"],
            }
        )

        chosen_racket = self._pick_choice_id(
            "Rogue: wybierz racket",
            racket_choices,
            source="status",
        )
        if not chosen_racket:
            return

        key_ability_choices = list(key_by_racket.get(chosen_racket) or ["dexterity"])
        chosen_key_ability = (
            key_ability_choices[0]
            if len(key_ability_choices) == 1
            else self._pick_choice_id(
                self._key_ability_prompt(f"Lotrzyk - {self._labelize_choice(chosen_racket)}"),
                key_ability_choices,
                source="status",
            )
        )
        if not chosen_key_ability:
            return

        chosen_feat = self._pick_choice_id(
            "Rogue: wybierz 1. poziomowy class feat",
            feat_choices,
            source="status",
        )
        if not chosen_feat:
            return

        trained_skills = list(trained_skills_by_racket.get(chosen_racket) or [])
        if chosen_racket == "ruffian" and "intimidation" not in trained_skills:
            trained_skills.append("intimidation")
        setup_payload = {
            "racket": chosen_racket,
            "key_ability": chosen_key_ability,
            "class_feat": chosen_feat,
            "trained_skills": list(trained_skills),
            "ruffian_medium_armor_trained": bool(chosen_racket == "ruffian"),
            "ruffian_crit_spec_todo": bool(chosen_racket == "ruffian"),
            "scoundrel_feint_upgrade": bool(chosen_racket == "scoundrel"),
        }
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["rogue_setup"] = dict(setup_payload)
                    new_data["rogue_racket"] = chosen_racket
                    new_data["rogue_key_ability"] = chosen_key_ability
                    new_data["rogue_class_feat"] = chosen_feat
                    new_data["trained_skills"] = list(trained_skills)
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Rogue setup: nie udalo sie zapisac wyborow.")
            return

        for attr, value in (
            ("rogue_racket", chosen_racket),
            ("rogue_key_ability", chosen_key_ability),
            ("rogue_class_feat", chosen_feat),
            ("rogue_trained_skills", list(trained_skills)),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass
        if chosen_racket == "ruffian":
            try:
                setattr(self, "rogue_medium_armor_trained", True)
            except Exception:
                pass

        registry = self._class_feat_registry().get("rogue", {})
        feat_status = self._resolve_status_from_registry(chosen_feat, registry)
        if feat_status is None:
            self._ui_log(f"Rogue setup: nie znaleziono statusu feata {chosen_feat}.")
            return
        self.add_status(feat_status)

        self._ui_log(
            "Rogue setup: "
            f"racket={self._labelize_choice(chosen_racket)}, "
            f"key ability={self._labelize_choice(chosen_key_ability)}, "
            f"feat={self._labelize_choice(chosen_feat)}."
        )
        if chosen_racket == "ruffian":
            self._ui_log(
                "Ruffian: critical specialization dla simple weapon -> TODO (placeholder do wspólnej implementacji broni)."
            )
        if chosen_racket == "scoundrel":
            self._ui_log(
                "Scoundrel: Feint daje dłuższy flat-footed (do końca następnej tury, a crit działa na wszystkie melee ataki)."
            )

    def _handle_cleric_setup_choice(self, status: "Status", data: dict) -> None:
        doctrine_choices = list(data.get("cleric_doctrine_choices") or ["cloistered_cleric", "warpriest"])
        deity_choices = list(data.get("cleric_deity_choices") or ["custom"])
        deity_options = dict(data.get("cleric_deity_options") or {})
        deity_skill_choices = dict(data.get("cleric_deity_skill_choices") or {})
        favored_weapon_choices = list(data.get("cleric_favored_weapon_choices") or ["sword", "dagger", "longbow", "unarmed"])
        font_choices = list(data.get("cleric_font_choices") or ["heal", "harm"])
        weapon_groups = dict(data.get("cleric_weapon_groups") or {})
        domain_spell_placeholders = dict(data.get("cleric_domain_spell_placeholders") or {})
        spell_tradition = str(data.get("cleric_spell_tradition") or "divine").strip().lower()
        try:
            prepared_cantrips = int(data.get("cleric_prepared_cantrips_at_level1") or 5)
        except Exception:
            prepared_cantrips = 5
        try:
            prepared_rank1_slots = int(data.get("cleric_prepared_rank_1_slots_at_level1") or 2)
        except Exception:
            prepared_rank1_slots = 2

        def _normalize_weapon(value: str | None) -> str | None:
            raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
            return raw if raw else None

        def _weapon_group_for(weapon_id: str | None) -> str | None:
            normalized = _normalize_weapon(weapon_id)
            if not normalized:
                return None
            mapped = str(weapon_groups.get(normalized, "") or "").strip().lower()
            if mapped in {"simple", "martial", "unarmed"}:
                return mapped
            return None

        chosen_deity = self._pick_choice_id(
            "Cleric: wybierz deity",
            deity_choices,
            source="status",
        )
        if not chosen_deity:
            return
        chosen_doctrine = self._pick_choice_id(
            "Cleric: wybierz doctrine",
            doctrine_choices,
            source="status",
        )
        if not chosen_doctrine:
            return

        deity_data = dict(deity_options.get(chosen_deity, {}) or {})
        available_deity_skills = list(deity_skill_choices.get(chosen_deity, [])) or list(
            deity_skill_choices.get("custom", [])
        )
        if not available_deity_skills:
            available_deity_skills = ["religion"]
        chosen_deity_skill: str | None = None
        if len(available_deity_skills) == 1:
            chosen_deity_skill = str(available_deity_skills[0] or "").strip().lower()
        else:
            deity_label = self._labelize_choice(chosen_deity)
            choice_entries: list[dict[str, str]] = []
            for idx, skill_id in enumerate(available_deity_skills, start=1):
                skill_raw = str(skill_id or "").strip()
                skill_label = self._labelize_choice(skill_raw)
                choice_entries.append(
                    {
                        "raw": skill_raw,
                        "label": skill_label,
                        "desc": self._structured_desc(
                            name=skill_label,
                            fluff=f"Umiejetnosc wynikajaca z kultu bóstwa {deity_label}.",
                            mechanics=(
                                f"Po wybraniu stajesz sie trained w {skill_label} "
                                "jako divine skill klasy Kleryk."
                            ),
                            when="Na etapie setupu klasy Kleryk.",
                        ),
                        "key": str(idx),
                    }
                )

            chosen_skill_label = self._prompt_choice(
                f"Cleric ({deity_label}): wybierz divine skill",
                [entry["label"] for entry in choice_entries],
                source="status",
                choice_meta=choice_entries,
            )
            if chosen_skill_label:
                by_raw = {str(entry["raw"]).strip().lower(): str(entry["raw"]).strip() for entry in choice_entries}
                by_label = {str(entry["label"]).strip().lower(): str(entry["raw"]).strip() for entry in choice_entries}
                text = str(chosen_skill_label).strip()
                if text.lower() in by_raw:
                    chosen_deity_skill = by_raw[text.lower()]
                elif text.lower() in by_label:
                    chosen_deity_skill = by_label[text.lower()]
                else:
                    normalized = text.lower().replace("-", "_").replace(" ", "_")
                    if normalized in by_raw:
                        chosen_deity_skill = by_raw[normalized]
                    elif text.isdigit():
                        idx = int(text) - 1
                        if 0 <= idx < len(choice_entries):
                            chosen_deity_skill = str(choice_entries[idx]["raw"]).strip()
        if not chosen_deity_skill:
            return
        trained_skills = list(
            dict.fromkeys(
                [
                    item
                    for item in ("religion", str(chosen_deity_skill).strip().lower())
                    if str(item).strip()
                ]
            )
        )

        chosen_favored_weapon = _normalize_weapon(deity_data.get("favored_weapon"))
        if not chosen_favored_weapon:
            chosen_favored_weapon = self._pick_choice_id(
                "Cleric: wybierz favored weapon",
                favored_weapon_choices,
                source="status",
            )
        if not chosen_favored_weapon:
            return
        favored_weapon_group = _normalize_weapon(deity_data.get("favored_weapon_group")) or _weapon_group_for(
            chosen_favored_weapon
        )

        allowed_fonts = list(deity_data.get("font_options") or font_choices)
        if not allowed_fonts:
            allowed_fonts = ["heal"]
        chosen_font = (
            allowed_fonts[0]
            if len(allowed_fonts) == 1
            else self._pick_choice_id(
                "Cleric: wybierz divine font",
                allowed_fonts,
                source="status",
            )
        )
        if not chosen_font:
            return

        domain_choices = list(deity_data.get("domain_choices") or [])
        if not domain_choices:
            domain_choices = ["custom_domain_a", "custom_domain_b", "custom_domain_c"]

        setup_payload = {
            "deity": chosen_deity,
            "deity_skill": chosen_deity_skill,
            "trained_skill": chosen_deity_skill,
            "trained_skills": list(trained_skills),
            "doctrine": chosen_doctrine,
            "favored_weapon": chosen_favored_weapon,
            "favored_weapon_group": favored_weapon_group,
            "font": chosen_font,
            "domain_choices": list(domain_choices),
            "spell_tradition": spell_tradition,
            "prepared_cantrips_at_level1": max(0, int(prepared_cantrips)),
            "prepared_rank_1_slots_at_level1": max(0, int(prepared_rank1_slots)),
        }
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["cleric_setup"] = dict(setup_payload)
                    new_data["cleric_deity"] = chosen_deity
                    new_data["cleric_deity_skill"] = chosen_deity_skill
                    new_data["cleric_doctrine"] = chosen_doctrine
                    new_data["cleric_favored_weapon"] = chosen_favored_weapon
                    new_data["cleric_favored_weapon_group"] = favored_weapon_group
                    new_data["cleric_font"] = chosen_font
                    new_data["cleric_domain_choices"] = list(domain_choices)
                    new_data["cleric_domain_spell_placeholders"] = dict(domain_spell_placeholders)
                    new_data["cleric_spell_tradition"] = spell_tradition
                    new_data["cleric_prepared_cantrips_at_level1"] = max(0, int(prepared_cantrips))
                    new_data["cleric_prepared_rank_1_slots_at_level1"] = max(0, int(prepared_rank1_slots))
                    new_data["trained_skills"] = list(trained_skills)
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Cleric setup: nie udalo sie zapisac wyborow.")
            return

        for attr, value in (
            ("cleric_deity", chosen_deity),
            ("cleric_deity_skill", chosen_deity_skill),
            ("cleric_doctrine", chosen_doctrine),
            ("cleric_favored_weapon", chosen_favored_weapon),
            ("cleric_favored_weapon_group", favored_weapon_group),
            ("cleric_font", chosen_font),
            ("cleric_domain_choices", list(domain_choices)),
            ("cleric_domain_spell_placeholders", dict(domain_spell_placeholders)),
            ("cleric_trained_skills", list(trained_skills)),
            ("cleric_spell_tradition", spell_tradition),
            ("cleric_prepared_cantrips_at_level1", max(0, int(prepared_cantrips))),
            ("cleric_prepared_rank_1_slots_at_level1", max(0, int(prepared_rank1_slots))),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        self._ui_log(
            "Cleric setup: "
            f"deity={self._labelize_choice(chosen_deity)}, "
            f"skill={self._labelize_choice(chosen_deity_skill)}, "
            f"doctrine={self._labelize_choice(chosen_doctrine)}, "
            f"favored weapon={self._labelize_choice(chosen_favored_weapon)}, "
            f"font={self._labelize_choice(chosen_font)}."
        )
        self._ui_log(
            "Cleric setup (skills): "
            f"trained={', '.join(self._labelize_choice(skill_id) for skill_id in trained_skills)}."
        )
        self._ui_log(
            "Cleric spellcasting: "
            f"tradycja={self._labelize_choice(spell_tradition)}, "
            f"przygotowanie startowe={max(0, int(prepared_cantrips))} cantripow i "
            f"{max(0, int(prepared_rank1_slots))} sloty rank 1 + Divine Font."
        )

        if chosen_doctrine == "cloistered_cleric":
            try:
                from statuses.classes.cleric.feats.domain_initiate import DOMAIN_INITIATE_STATUS

                self.add_status(DOMAIN_INITIATE_STATUS)
            except Exception:
                self._ui_log("Cleric setup: nie udalo sie dodac Domain Initiate.")

        if chosen_doctrine == "warpriest":
            try:
                from statuses.general.shield_block import SHIELD_BLOCK_STATUS

                self.add_status(SHIELD_BLOCK_STATUS)
            except Exception:
                self._ui_log("Cleric setup: nie udalo sie dodac Shield Block.")
            if favored_weapon_group in {"simple", "unarmed"}:
                try:
                    from statuses.classes.cleric.feats.deadly_simplicity import DEADLY_SIMPLICITY_STATUS

                    self.add_status(DEADLY_SIMPLICITY_STATUS)
                except Exception:
                    self._ui_log("Cleric setup: nie udalo sie dodac Deadly Simplicity.")

    def _handle_cleric_domain_initiate_choice(self, status: "Status", data: dict) -> None:
        setup = self._cleric_setup_data()
        domain_choices = list(data.get("domain_choices") or setup.get("domain_choices") or [])
        if not domain_choices:
            domain_choices = list(getattr(self, "cleric_domain_choices", []) or [])
        if not domain_choices:
            domain_choices = ["custom_domain_a", "custom_domain_b", "custom_domain_c"]
        placeholder_map = dict(
            data.get("domain_spell_placeholders")
            or setup.get("domain_spell_placeholders")
            or getattr(self, "cleric_domain_spell_placeholders", {})
            or {}
        )

        selected_already: set[str] = set()
        for item in getattr(self, "statuses", []) or []:
            if getattr(item, "id", None) != "domain_initiate":
                continue
            item_data = getattr(item, "data", None) or {}
            selected = str(item_data.get("selected_domain", "") or "").strip().lower()
            if selected:
                selected_already.add(selected)

        available_domains = [domain for domain in domain_choices if domain not in selected_already]
        if not available_domains:
            self._ui_log("Domain Initiate: brak nowych domen do wyboru.")
            return
        chosen_domain = self._pick_choice_id(
            "Domain Initiate: wybierz domene",
            available_domains,
            source="status",
        )
        if not chosen_domain:
            return

        chosen_spell = str(placeholder_map.get(chosen_domain) or f"domain_spell_{chosen_domain}")
        self._replace_status_data(
            status,
            {
                "selected_domain": chosen_domain,
                "domain_spell": chosen_spell,
            },
        )

        known_domains = list(getattr(self, "cleric_known_domains", []) or [])
        if chosen_domain not in known_domains:
            known_domains.append(chosen_domain)
        known_spells = list(getattr(self, "cleric_domain_spells", []) or [])
        if chosen_spell not in known_spells:
            known_spells.append(chosen_spell)
        try:
            setattr(self, "cleric_known_domains", known_domains)
            setattr(self, "cleric_domain_spells", known_spells)
        except Exception:
            pass

        self._ui_log(
            "Domain Initiate: "
            f"{self._labelize_choice(chosen_domain)} -> {self._labelize_choice(chosen_spell)}."
        )

    def _handle_champion_deitys_domain_choice(self, status: "Status", data: dict) -> None:
        setup = self._champion_setup_data()
        deity = str(
            setup.get("deity")
            or self.get_status_data("champion", "champion_deity", "")
            or getattr(self, "champion_deity", "")
        ).strip().lower()

        choices_by_deity = dict(data.get("domain_choices_by_deity") or {})
        if not deity or deity not in choices_by_deity:
            deity_choices = [str(item).strip().lower() for item in list(choices_by_deity.keys()) if str(item).strip()]
            if "custom" in deity_choices:
                deity_choices = [item for item in deity_choices if item != "custom"] + ["custom"]
            if deity_choices:
                chosen_deity = self._pick_choice_id(
                    "Deity's Domain: wybierz deity",
                    deity_choices,
                    source="status",
                )
                if not chosen_deity:
                    return
                deity = str(chosen_deity).strip().lower()
                try:
                    setattr(self, "champion_deity", deity)
                except Exception:
                    pass
                try:
                    for idx, item in enumerate(self.statuses):
                        if getattr(item, "id", None) != "champion":
                            continue
                        new_data = dict(getattr(item, "data", None) or {})
                        setup_data = dict(new_data.get("champion_setup") or {})
                        setup_data["deity"] = deity
                        new_data["champion_setup"] = setup_data
                        new_data["champion_deity"] = deity
                        self.statuses[idx] = replace(item, data=new_data)
                        break
                except Exception:
                    pass
            else:
                deity = "custom"

        raw_domain_choices = list(choices_by_deity.get(deity) or choices_by_deity.get("custom") or [])
        domain_choices = [str(item).strip().lower() for item in raw_domain_choices if str(item).strip()]
        if not domain_choices:
            domain_choices = ["custom_domain_a", "custom_domain_b", "custom_domain_c"]

        placeholder_map = dict(data.get("domain_spell_placeholders") or {})
        domain_desc_map = dict(data.get("domain_descriptions") or {})
        advanced_map = dict(data.get("domain_advanced_spell_placeholders") or {})
        entries: list[dict] = []
        for idx, domain_id in enumerate(domain_choices, start=1):
            raw_domain = str(domain_id or "").strip().lower()
            if not raw_domain:
                continue
            spell_id = str(placeholder_map.get(raw_domain) or f"domain_spell_{raw_domain}").strip().lower()
            advanced_spell_id = str(advanced_map.get(raw_domain) or "").strip().lower()
            domain_label = self._labelize_choice(raw_domain)
            spell_label = self._labelize_choice(spell_id)
            advanced_label = self._labelize_choice(advanced_spell_id) if advanced_spell_id else ""
            domain_desc = self._first_line(str(domain_desc_map.get(raw_domain) or ""))
            event_hint = self._event_fallback_hint(spell_id)
            spec_hint = self._domain_spell_fallback_hint(spell_id)
            mechanics_parts = [f"Czar domenowy: {spell_label}."]
            if advanced_label:
                mechanics_parts.append(f"Advanced domain spell: {advanced_label}.")
            if event_hint:
                mechanics_parts.append(f"Szczegoly eventu:\n{event_hint}")
            if spec_hint:
                mechanics_parts.append(f"Szczegoly mechaniki:\n{spec_hint}")
            entries.append(
                {
                    "raw": raw_domain,
                    "label": domain_label,
                    "desc": self._structured_desc(
                        name=domain_label,
                        fluff=domain_desc or f"Domena {domain_label} daje czar {spell_label}.",
                        mechanics="\n".join(part for part in mechanics_parts if part).strip()
                        or f"Otrzymujesz czar domenowy {spell_label}.",
                        when="Po wybraniu feata Deity's Domain.",
                    ),
                    "key": str(idx),
                }
            )
        if not entries:
            self._ui_log("Deity's Domain: brak domen do wyboru.")
            return
        labels = [str(entry.get("label") or "") for entry in entries]
        chosen_label = self._prompt_choice(
            f"Deity's Domain ({self._labelize_choice(deity)}): wybierz domene",
            labels,
            source="status",
            choice_meta=entries,
        )
        if not chosen_label:
            return
        by_raw = {str(entry["raw"]).strip().lower(): str(entry["raw"]).strip() for entry in entries}
        by_label = {str(entry["label"]).strip().lower(): str(entry["raw"]).strip() for entry in entries}
        text = str(chosen_label).strip()
        chosen_domain = None
        if text.lower() in by_raw:
            chosen_domain = by_raw[text.lower()]
        elif text.lower() in by_label:
            chosen_domain = by_label[text.lower()]
        else:
            normalized = text.lower().replace("-", "_").replace(" ", "_")
            if normalized in by_raw:
                chosen_domain = by_raw[normalized]
            elif text.isdigit():
                idx = int(text) - 1
                if 0 <= idx < len(entries):
                    chosen_domain = str(entries[idx]["raw"]).strip()
        if not chosen_domain:
            return

        chosen_spell = str(placeholder_map.get(chosen_domain) or f"domain_spell_{chosen_domain}")
        self._replace_status_data(
            status,
            {
                "selected_domain": chosen_domain,
                "domain_spell": chosen_spell,
            },
        )

        known_domains = list(getattr(self, "champion_known_domains", []) or [])
        if chosen_domain not in known_domains:
            known_domains.append(chosen_domain)
        known_spells = list(getattr(self, "champion_domain_spells", []) or [])
        if chosen_spell not in known_spells:
            known_spells.append(chosen_spell)
        try:
            setattr(self, "champion_known_domains", known_domains)
            setattr(self, "champion_domain_spells", known_spells)
        except Exception:
            pass

        self._ui_log(
            "Deity's Domain: "
            f"{self._labelize_choice(chosen_domain)} -> {self._labelize_choice(chosen_spell)}."
        )

    def _handle_deific_weapon_choice(self, status: "Status", data: dict) -> None:
        setup = self._champion_setup_data()
        deity = str(
            setup.get("deity")
            or self.get_status_data("champion", "champion_deity", "")
            or getattr(self, "champion_deity", "")
            or ""
        ).strip().lower()

        chosen_weapon = ""
        if deity:
            try:
                from statuses.classes.cleric.cleric import CLERIC_DEITY_OPTIONS

                deity_data = dict(CLERIC_DEITY_OPTIONS.get(deity, {}) or {})
                chosen_weapon = str(deity_data.get("favored_weapon") or "").strip().lower()
            except Exception:
                chosen_weapon = ""

        if not chosen_weapon:
            choices = list(data.get("deific_weapon_choices") or [])
            if not choices:
                return
            picked = self._pick_choice_id(
                "Deific Weapon: wybierz typ broni",
                choices,
                source="status",
            )
            if not picked:
                self._ui_log("Deific Weapon: nie wybrano poprawnego typu broni.")
                return
            chosen_weapon = str(picked).strip().lower()

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["deific_weapon_type"] = chosen_weapon
                    if deity:
                        new_data["deific_weapon_deity"] = deity
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Deific Weapon: nie udalo sie zapisac wyboru broni.")
            return

        try:
            setattr(self, "deific_weapon_type", chosen_weapon)
        except Exception:
            pass
        if deity and chosen_weapon:
            self._ui_log(
                "Deific Weapon: "
                f"{self._labelize_choice(deity)} -> {self._labelize_choice(chosen_weapon)} (favored weapon)."
            )
        else:
            self._ui_log(f"Deific Weapon: wybrano {self._labelize_choice(chosen_weapon)}.")

    def _sync_reactions_for_status(self, status: "Status") -> None:
        reactions = getattr(self, "reactions", None)
        if not isinstance(reactions, list):
            return
        status_id = str(getattr(status, "id", "") or "")
        if status_id == "shield_block":
            try:
                from combat.reactions.shield_block_reaction import ShieldBlockReaction
                from GameObjects.items.shield import StandardShield, get_equipped_shield

                if not any(getattr(item, "id", None) == "shield_block" for item in reactions):
                    reactions.append(ShieldBlockReaction())
                equipped = get_equipped_shield(self, create_default=False)
                if equipped is None:
                    if self._in_character_creation_mode():
                        self._ui_log(
                            "Shield Block: feat aktywny. Wyposaz tarcze w ekwipunku, aby uzyc reakcji w walce."
                        )
                        return
                    choice = self._prompt_choice(
                        "Shield Block: brak wyposazonej tarczy.\n"
                        "Czy wyposazyc domyslna Standard Shield (szybki setup)?",
                        ["standard", "brak"],
                        source="status",
                    )
                    normalized = str(choice or "").strip().lower()
                    if normalized.startswith("s"):
                        try:
                            setattr(self, "equipped_shield", StandardShield())
                            self._ui_log("Wyposazono tarcze: Standard Shield.")
                        except Exception:
                            self._ui_log("Nie udalo sie wyposazyc tarczy.")
                    elif normalized.startswith("b"):
                        self._ui_log("Brak wyposazonej tarczy.")
                    else:
                        self._ui_log("Nie wybrano tarczy (brak wyposazenia).")
            except Exception:
                self._ui_log("Nie udalo sie dodac reakcji Shield Block.")
        if status_id == "reactive_shield":
            try:
                from combat.reactions.reactive_shield_reaction import ReactiveShieldReaction

                if not any(getattr(item, "id", None) == "reactive_shield" for item in reactions):
                    reactions.append(ReactiveShieldReaction())
            except Exception:
                self._ui_log("Nie udalo sie dodac reakcji Reactive Shield.")
        if status_id == "nimble_dodge":
            try:
                from combat.reactions.nimble_dodge_reaction import NimbleDodgeReaction

                if not any(getattr(item, "id", None) == "nimble_dodge" for item in reactions):
                    reactions.append(NimbleDodgeReaction())
            except Exception:
                self._ui_log("Nie udalo sie dodac reakcji Nimble Dodge.")
        if status_id == "counterspell":
            try:
                from combat.reactions.counterspell_reaction import CounterspellReaction

                if not any(getattr(item, "id", None) == "counterspell_reaction" for item in reactions):
                    reactions.append(CounterspellReaction())
            except Exception:
                self._ui_log("Nie udalo sie dodac reakcji Counterspell.")

    def _drop_reactions_for_status(self, status_id: str) -> None:
        reactions = getattr(self, "reactions", None)
        if not isinstance(reactions, list):
            return
        if status_id == "shield_block":
            self.reactions = [item for item in reactions if getattr(item, "id", None) != "shield_block"]
        if status_id == "reactive_shield":
            self.reactions = [item for item in reactions if getattr(item, "id", None) != "reactive_shield"]
        if status_id == "nimble_dodge":
            self.reactions = [item for item in reactions if getattr(item, "id", None) != "nimble_dodge"]
        if status_id == "counterspell":
            self.reactions = [item for item in reactions if getattr(item, "id", None) != "counterspell_reaction"]

    def _ensure_status_objects(self) -> None:
        if not self.statuses:
            return
        from statuses import Status  # lokalny import by unikać cykli
        # Zachowawczo konwertuj ewentualne stare stringi na Status, aby utrzymać spójność.
        if not all(isinstance(s, Status) for s in self.statuses):
            self.statuses = [s if isinstance(s, Status) else Status(id=str(s)) for s in self.statuses]

    def has_status(self, status: str | "Status") -> bool:
        self._ensure_status_objects()
        from statuses import Status  # lokalny import by unikać cykli
        status_id = status.id if isinstance(status, Status) else str(status)
        return any(s.id == status_id for s in self.statuses)

    def _prepare_incoming_status(self, status: "Status") -> "Status":
        data = dict(getattr(status, "data", None) or {})
        status_id = str(getattr(status, "id", "") or "").strip().lower()
        changed = False

        if status_id in {"elven_lore", "goblin_lore", "halfling_lore"}:
            data["_pre_add_trained_skills"] = sorted(self._trained_skill_ids())
            changed = True

        if status_id == "city_scavenger":
            wants_bonus = 2 if self.has_status("irongut_goblin") else 1
            try:
                current_bonus = int(data.get("city_scavenger_bonus", 1) or 1)
            except Exception:
                current_bonus = 1
            if current_bonus != wants_bonus:
                try:
                    from statuses.race.goblin.feats.city_scavenger import CityScavengerStatus

                    status = CityScavengerStatus(bonus=wants_bonus)
                    data = dict(getattr(status, "data", None) or {})
                    changed = False
                except Exception:
                    pass

        if status_id == "irongut_goblin":
            try:
                from statuses.race.goblin.feats.city_scavenger import CityScavengerStatus
            except Exception:
                CityScavengerStatus = None  # type: ignore[assignment]
            if CityScavengerStatus is not None:
                for idx, existing in enumerate(list(self.statuses or [])):
                    if getattr(existing, "id", None) != "city_scavenger":
                        continue
                    existing_data = getattr(existing, "data", None) or {}
                    try:
                        existing_bonus = int(existing_data.get("city_scavenger_bonus", 1) or 1)
                    except Exception:
                        existing_bonus = 1
                    if existing_bonus >= 2:
                        continue
                    try:
                        self.statuses[idx] = CityScavengerStatus(bonus=2)
                    except Exception:
                        continue

        if status_id != "wellspring_gnome":
            wellspring_tradition = self._selected_wellspring_tradition()
            if wellspring_tradition and bool(data.get("gnome_primal_innate_source")):
                data = self._apply_gnome_primal_innate_override(data, wellspring_tradition)
                changed = True

        if status_id not in {"unwavering_mien"} and self.has_status("unwavering_mien"):
            tags = {
                str(item).strip().lower()
                for item in list(data.get("effect_tags") or [])
                if str(item).strip()
            }
            reduce_by = 0
            for existing in self.statuses:
                if getattr(existing, "id", None) != "unwavering_mien":
                    continue
                existing_data = getattr(existing, "data", None) or {}
                try:
                    reduce_by = max(
                        reduce_by,
                        int(existing_data.get("reduce_mental_effect_duration_rounds", 0) or 0),
                    )
                except Exception:
                    continue
            if reduce_by > 0 and "mental" in tags:
                duration = getattr(status, "duration", None)
                if duration is not None:
                    try:
                        turns = int(duration)
                    except Exception:
                        turns = None
                    if turns is not None and turns >= 2:
                        status = replace(status, duration=max(1, turns - reduce_by))

        if changed:
            status = replace(status, data=data)
        return status

    def add_status(self, status: str | "Status") -> bool:
        """Dodaj status – wymagany obiekt Status (nie string)."""
        from statuses import Status  # lokalny import by unikać cykli
        if not isinstance(status, Status):
            raise TypeError("add_status oczekuje instancji Status.")
        self._ensure_status_objects()
        status = self._prepare_incoming_status(status)
        if not self._passes_status_prerequisites(status):
            return False
        if self._status_immunity_blocks(status):
            msg = f"Status '{getattr(status, 'label', status.id)}' zablokowany przez immunitet."
            logger.info(msg)
            self._ui_log(msg)
            return False
        if not getattr(status, "stacks", False):
            if any(s.id == status.id for s in self.statuses):
                return False
        self.statuses.append(status)
        try:
            from statuses import normalize_condition_stacks

            normalize_condition_stacks(self, log_changes=True)
        except Exception:
            pass
        self._apply_status_actor_attrs(status)
        self._apply_removed_statuses(status)
        self._apply_granted_statuses(status)
        self._sync_reactions_for_status(status)
        self._ui_log(f"Otrzymujesz status: {status.display_label}.")
        self._maybe_prompt_status_info(status)
        return True

    def _apply_status_actor_attrs(self, status: "Status") -> None:
        data = getattr(status, "data", None) or {}
        attrs = data.get("set_actor_attrs") or {}
        if not isinstance(attrs, dict):
            attrs = {}
        touched_focus_attrs = False
        for key, value in attrs.items():
            name = str(key or "").strip()
            if not name:
                continue
            if name in {"focus_point", "focus_pool_max", "wizard_focus_pool_max", "focus_pool_size"}:
                touched_focus_attrs = True
            if hasattr(self, name):
                continue
            try:
                setattr(self, name, value)
            except Exception:
                continue

        additive = data.get("add_actor_attrs") or {}
        if not isinstance(additive, dict):
            if touched_focus_attrs:
                self._sync_focus_pool_attrs()
            return
        for key, value in additive.items():
            name = str(key or "").strip()
            if not name:
                continue
            if name in {"focus_point", "focus_pool_max", "wizard_focus_pool_max", "focus_pool_size"}:
                touched_focus_attrs = True
            try:
                current = getattr(self, name, 0)
            except Exception:
                current = 0
            try:
                new_value = int(current) + int(value)
            except Exception:
                continue
            try:
                setattr(self, name, new_value)
            except Exception:
                continue
        if touched_focus_attrs:
            self._sync_focus_pool_attrs()

    def _sync_focus_pool_attrs(self, *, minimum_pool: int = 0) -> None:
        try:
            from focus_pool import ensure_focus_pool

            ensure_focus_pool(self, minimum_pool=minimum_pool)
        except Exception:
            return

    def _apply_removed_statuses(self, status: "Status") -> None:
        data = getattr(status, "data", None) or {}
        removes = data.get("remove_statuses") or data.get("remove_status") or []
        if not removes:
            return
        from statuses import Status  # lokalny import by unikać cykli
        for removed in removes:
            if isinstance(removed, Status):
                if removed.id == status.id:
                    continue
                try:
                    self.remove_status(removed)
                except Exception:
                    continue
            elif isinstance(removed, str):
                if removed == status.id:
                    continue
                try:
                    self.remove_status(removed)
                except Exception:
                    continue

    def _apply_granted_statuses(self, status: "Status") -> None:
        data = getattr(status, "data", None) or {}
        grants = data.get("grants_statuses") or data.get("grants_status") or []
        if not grants:
            return
        from statuses import Status  # lokalny import by unikać cykli
        for granted in grants:
            if isinstance(granted, Status):
                if granted.id == status.id:
                    continue
                self.add_status(granted)
            elif isinstance(granted, str):
                if granted == status.id:
                    continue
                try:
                    self.add_status(Status(id=granted))
                except Exception:
                    continue

    def remove_status(self, status: str | "Status") -> bool:
        self._ensure_status_objects()
        from statuses import Status  # lokalny import by unikać cykli
        target_id = status.id if isinstance(status, Status) else str(status)
        for idx, item in enumerate(self.statuses):
            if getattr(item, "id", None) == target_id:
                self._clear_temp_hp_for_status(item)
                del self.statuses[idx]
                self._drop_reactions_for_status(target_id)
                try:
                    from statuses import normalize_condition_stacks

                    normalize_condition_stacks(self, log_changes=False)
                except Exception:
                    pass
                return True
        return False

    def get_status(self, status_id: str) -> Status | None:
        """Zwróć pierwszą instancję Status o podanym id albo None."""
        self._ensure_status_objects()
        for status in self.statuses:
            if getattr(status, "id", None) == status_id:
                return status
        return None

    def get_status_data(self, status_id: str, key: str, default=None):
        """Shortcut do pobrania danych z statusu."""
        status = self.get_status(status_id)
        if status is None:
            return default
        data = getattr(status, "data", None) or {}
        return data.get(key, default)

    def clear_statuses(self, *statuses: str | "Status") -> int:
        """Usuń podane statusy, zwróć liczbę usuniętych wpisów."""
        self._ensure_status_objects()
        from statuses import Status  # lokalny import by unikać cykli
        to_remove = {s.id if isinstance(s, Status) else str(s) for s in statuses} if statuses else {s.id for s in self.statuses}
        new_statuses: list[Status] = []
        removed = 0
        for status in self.statuses:
            if status.id in to_remove:
                self._clear_temp_hp_for_status(status)
                removed += 1
                continue
            new_statuses.append(status)
        self.statuses = new_statuses
        return removed

    def status_labels(self) -> list[str]:
        """Zwraca listę etykiet (label -> id) do logów/UI."""
        self._ensure_status_objects()
        return [s.display_label for s in self.statuses]

    def tick_statuses_turn(self, *, phase: str = "turn_start", log_changes: bool = False) -> int:
        """Zdekrementuj duration statusów dla wskazanej fazy; usuń wygasłe."""
        self._ensure_status_objects()
        if not self.statuses:
            return 0
        normalized_phase = str(phase or "turn_start").strip().lower()
        if normalized_phase in {"turn_start", "start_turn", "start"}:
            try:
                from statuses.race.dwarf.feats.vengeful_hatred import tick_vengeful_hatred_rounds

                tick_vengeful_hatred_rounds(self)
            except Exception:
                pass
        try:
            from statuses import tick_condition_durations, normalize_condition_stacks

            removed = int(tick_condition_durations(self, phase=normalized_phase, log_changes=log_changes) or 0)
            normalize_condition_stacks(self, log_changes=log_changes)
            return removed
        except Exception:
            pass

        # Fallback (legacy path): zachowuje poprzednie zachowanie dla kompatybilności.
        remaining: list[Status] = []
        removed = 0
        for status in self.statuses:
            duration = getattr(status, "duration", None)
            if duration is None:
                remaining.append(status)
                continue
            try:
                turns = int(duration) - 1
            except Exception:
                remaining.append(status)
                continue
            if turns <= 0:
                self._clear_temp_hp_for_status(status)
                removed += 1
                continue
            remaining.append(replace(status, duration=turns))
        self.statuses = remaining
        return removed

    def _clear_temp_hp_for_status(self, status: "Status") -> None:
        data = getattr(status, "data", None) or {}
        source = data.get("temp_hp_source")
        if not source:
            return
        try:
            from combat.hp_engine import clear_temp_hp

            clear_temp_hp(self, source=str(source))
        except Exception:
            pass
