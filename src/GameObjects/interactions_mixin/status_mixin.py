from __future__ import annotations

from dataclasses import dataclass, field, replace
import logging
from typing import TYPE_CHECKING

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
        prompt = data.get("ui_prompt")
        if not prompt:
            return
        prompt_long = data.get("ui_prompt_long")
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
        return str(value or "").replace("_", " ").strip().title()

    @staticmethod
    def _prompt_choice(prompt: str, choices: list[str], *, source: str) -> str | None:
        try:
            from ui_client import get_ui_client

            ui_client = get_ui_client()
            if ui_client.enabled:
                return ui_client.prompt_choice(prompt, choices=choices, source=source)
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
        label_map = {self._labelize_choice(item): item for item in choices}
        labels = list(label_map.keys())
        chosen_label = self._prompt_choice(prompt, labels, source=source)
        if not chosen_label:
            return None
        chosen = label_map.get(chosen_label)
        if chosen:
            return chosen
        raw = str(chosen_label).strip().lower().replace(" ", "_")
        return raw if raw in choices else None

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
            "adopted_ancestry": ("statuses.general.adopted_ancestry", "ADOPTED_ANCESTRY_STATUS"),
            "armor_proficiency": ("statuses.general.armor_proficiency", "ARMOR_PROFICIENCY_STATUS"),
            "assurance": ("statuses.general.assurance", "ASSURANCE_STATUS"),
            "breath_control": ("statuses.general.breath_control", "BREATH_CONTROL_STATUS"),
            "canny_acumen": ("statuses.general.canny_acumen", "CANNY_ACUMEN_STATUS"),
            "diehard": ("statuses.general.diehard", "DIEHARD_STATUS"),
            "dubious_knowledge": ("statuses.general.dubious_knowledge", "DUBIOUS_KNOWLEDGE_STATUS"),
            "fleet": ("statuses.general.fleet", "FLEET_STATUS"),
            "incredible_initiative": ("statuses.general.incredible_initiative", "INCREDIBLE_INITIATIVE_STATUS"),
            "recognize_spell": ("statuses.general.recognize_spell", "RECOGNIZE_SPELL_STATUS"),
            "shield_block": ("statuses.general.shield_block", "SHIELD_BLOCK_STATUS"),
            "skill_training": ("statuses.general.skill_training", "SKILL_TRAINING_STATUS"),
            "toughness": ("statuses.general.toughness", "TOUGHNESS_STATUS"),
            "trick_magic_item": ("statuses.general.trick_magic_item", "TRICK_MAGIC_ITEM_STATUS"),
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
                "deific_weapon": ("statuses.classes.champion.feats.deific_weapon", "DEIFIC_WEAPON_STATUS"),
                "raise_shield_allow": (
                    "statuses.classes.champion.feats.raise_shield_allow",
                    "CHAMPION_RAISE_SHIELD_ALLOW_FEAT",
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
        if status_id in {"deadly_simplicity", "domain_initiate", "harming_hands", "healing_hands", "holy_castigation"}:
            if not self._is_cleric_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Cleric.")
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
            "sudden_charge",
        }:
            if not self._is_fighter_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Fighter.")
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
        chosen_tradition = self._pick_choice_id(
            "Adapted Cantrip: wybierz tradycje",
            traditions,
            source="status",
        )
        if not chosen_tradition:
            return

        cantrip_map = dict(data.get("adapted_cantrip_choices") or {})
        cantrip_choices = list(cantrip_map.get(chosen_tradition, [])) or list(cantrip_map.get("all", []))
        if not cantrip_choices:
            cantrip_choices = ["detect_magic", "daze", "ray_of_frost", "light", "guidance"]
        chosen_cantrip = self._pick_choice_id(
            f"Adapted Cantrip ({self._labelize_choice(chosen_tradition)}): wybierz cantrip",
            cantrip_choices,
            source="status",
        )
        if not chosen_cantrip:
            return

        replaced_choices = list(data.get("replaced_cantrip_choices") or cantrip_choices)
        chosen_replaced = self._pick_choice_id(
            "Adapted Cantrip: wybierz cantrip do zastapienia",
            replaced_choices,
            source="status",
        )
        if not chosen_replaced:
            return

        self._replace_status_data(
            status,
            {
                "adapted_tradition": chosen_tradition,
                "adapted_cantrip": chosen_cantrip,
                "replaced_cantrip": chosen_replaced,
            },
        )
        self._ui_log(
            "Adapted Cantrip: "
            f"{self._labelize_choice(chosen_tradition)} -> {self._labelize_choice(chosen_cantrip)} "
            f"(zastapiony: {self._labelize_choice(chosen_replaced)})."
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
        if not choices:
            self._ui_log(f"Natural Ambition: brak listy featów dla klasy {class_id}.")
            return

        chosen_feat = self._pick_choice_id(
            f"Natural Ambition ({self._labelize_choice(class_id)}): wybierz class feat",
            choices,
            source="status",
        )
        if not chosen_feat:
            return

        self._replace_status_data(
            status,
            {
                "class_name": class_id,
                "class_feat": chosen_feat,
            },
        )

        registry = self._class_feat_registry().get(class_id, {})
        feat_status = self._resolve_status_from_registry(chosen_feat, registry)
        if feat_status is None:
            self._ui_log(
                f"Natural Ambition: nie znaleziono statusu feata {chosen_feat} dla klasy {class_id}."
            )
            return
        self.add_status(feat_status)
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
        field_labels = [self._labelize_choice(f) for f in fields]
        field_label_to_id = {self._labelize_choice(f): f for f in fields}
        chosen_label = self._prompt_choice(
            "Research Field: wybierz specjalizację",
            field_labels,
            source="status",
        )
        if not chosen_label:
            return
        chosen_field = field_label_to_id.get(chosen_label, None)
        if not chosen_field:
            chosen_field = str(chosen_label).strip().lower().replace(" ", "_")

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
        label_map = {self._labelize_choice(key): key for key in choices}
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
        label_map = {self._labelize_choice(key): key for key in choices}
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

    def _handle_bard_muse_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("bard_muse_choices") or [])
        if not choices:
            choices = ["enigma", "maestro", "polymath"]
        muse_effects = data.get("bard_muse_effects") or {}

        label_to_key: dict[str, str] = {}
        labels: list[str] = []
        for key in choices:
            effect_data = muse_effects.get(key) or {}
            effect = str(effect_data.get("effect") or "").strip()
            feat_label = str(effect_data.get("feat_label") or "").strip()
            spell_label = str(effect_data.get("spell_label") or "").strip()
            detail_parts = [part for part in [effect, f"Feat: {feat_label}" if feat_label else "", f"Czar: {spell_label}" if spell_label else ""] if part]
            details = "; ".join(detail_parts)
            base_label = self._labelize_choice(key)
            label = f"{base_label} - {details}" if details else base_label
            label_to_key[label] = key
            labels.append(label)

        chosen_label = self._prompt_choice(
            "Bard Muse: wybierz inspiracje",
            labels,
            source="status",
        )
        if not chosen_label:
            return

        chosen_key = label_to_key.get(chosen_label)
        if not chosen_key:
            chosen_key = str(chosen_label).split("-", 1)[0].strip().lower().replace(" ", "_")

        default_map = {
            "enigma": {"feat": "bardic_lore", "spell": "true_strike", "spell_label": "True Strike"},
            "maestro": {"feat": "lingering_composition", "spell": "soothe", "spell_label": "Soothe"},
            "polymath": {"feat": "versatile_performance", "spell": "unseen_servant", "spell_label": "Unseen Servant"},
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
            self._ui_log(
                f"Dopisz do listy znanych czarow: {chosen_spell_label}."
            )

    def _handle_druid_setup_choice(self, status: "Status", data: dict) -> None:
        order_choices = list(data.get("druid_order_choices") or ["animal", "leaf", "storm", "wild"])
        order_skills = dict(data.get("druid_order_skills") or {})
        order_start_feats = dict(data.get("druid_order_start_feats") or {})
        order_spells = dict(data.get("druid_order_spells") or {})
        order_focus_bonus = dict(data.get("druid_order_focus_bonus") or {})

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
            except Exception:
                pass

        self._ui_log(
            "Druid setup: "
            f"order={self._labelize_choice(chosen_order)}, "
            f"skill={self._labelize_choice(chosen_skill)}, "
            f"order spell={self._labelize_choice(chosen_order_spell)}."
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

        def _pick(prompt: str, choices: list[str]) -> str | None:
            if not choices:
                return None
            label_map = {self._labelize_choice(item): item for item in choices}
            labels = list(label_map.keys())
            chosen_label = self._prompt_choice(prompt, labels, source="status")
            if not chosen_label:
                return None
            chosen = label_map.get(chosen_label)
            if chosen:
                return chosen
            raw = str(chosen_label).strip().lower().replace(" ", "_")
            return raw if raw in choices else None

        chosen_key_ability = _pick("Champion: wybierz key ability", key_ability_choices)
        if not chosen_key_ability:
            return
        chosen_cause = _pick("Champion: wybierz cause", cause_choices)
        if not chosen_cause:
            return
        chosen_deity = _pick("Champion: wybierz deity", deity_choices)
        if not chosen_deity:
            return

        available_deity_skills = list(deity_skill_choices.get(chosen_deity, [])) or list(
            deity_skill_choices.get("custom", [])
        )
        if not available_deity_skills:
            available_deity_skills = ["religion"]
        chosen_deity_skill = _pick(
            f"Champion ({self._labelize_choice(chosen_deity)}): wybierz skill od deity",
            available_deity_skills,
        )
        if not chosen_deity_skill:
            return

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["champion_setup"] = {
                        "key_ability": chosen_key_ability,
                        "cause": chosen_cause,
                        "deity": chosen_deity,
                        "deity_skill": chosen_deity_skill,
                    }
                    new_data["champion_key_ability"] = chosen_key_ability
                    new_data["champion_cause"] = chosen_cause
                    new_data["champion_deity"] = chosen_deity
                    new_data["champion_deity_skill"] = chosen_deity_skill
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

        if chosen_cause == "paladin":
            try:
                from statuses.classes.champion.feats.deific_weapon import DEIFIC_WEAPON_STATUS

                self.add_status(DEIFIC_WEAPON_STATUS)
            except Exception:
                self._ui_log("Nie udalo sie dodac feata Deific Weapon.")

        self._ui_log(
            "Champion setup: "
            f"key ability={self._labelize_choice(chosen_key_ability)}, "
            f"cause={self._labelize_choice(chosen_cause)}, "
            f"deity={self._labelize_choice(chosen_deity)}, "
            f"skill={self._labelize_choice(chosen_deity_skill)}."
        )

    def _handle_fighter_setup_choice(self, status: "Status", data: dict) -> None:
        key_ability_choices = list(data.get("fighter_key_ability_choices") or ["strength", "dexterity"])
        chosen_key_ability = self._pick_choice_id(
            "Fighter: wybierz key ability",
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
            "Monk: wybierz key ability",
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
            "Ranger: wybierz key ability",
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
                "Sorcerer: wybierz key ability",
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
            chosen_elemental_type = self._pick_choice_id(
                "Sorcerer (Elemental): wybierz elemental type",
                elemental_type_choices,
                source="status",
            )
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

        setup_payload = {
            "key_ability": chosen_key_ability,
            "bloodline": chosen_bloodline,
            "spell_tradition": chosen_tradition,
            "class_feat": chosen_feat,
            "trained_skills": list(bloodline_skills),
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

        known_cantrips = list(getattr(self, "sorcerer_known_cantrips", []) or [])
        if bloodline_cantrip and bloodline_cantrip not in known_cantrips:
            known_cantrips.append(bloodline_cantrip)
        known_rank_1 = list(getattr(self, "sorcerer_known_rank_1_spells", []) or [])
        if bloodline_rank_1_spell and bloodline_rank_1_spell not in known_rank_1:
            known_rank_1.append(bloodline_rank_1_spell)
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
                "Wizard: wybierz key ability",
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

        available_feat_choices = list(feat_choices)
        if chosen_arcane_study != "universalist":
            available_feat_choices = [feat for feat in available_feat_choices if feat != "hand_of_the_apprentice"]
        chosen_feat = self._pick_choice_id(
            "Wizard: wybierz 1. poziomowy class feat",
            available_feat_choices,
            source="status",
        )
        if not chosen_feat:
            return

        chosen_bonus_feat: str | None = None
        if chosen_arcane_study == "universalist" and bool(data.get("wizard_universalist_bonus_feat", True)):
            bonus_pool = [feat for feat in feat_choices if feat != chosen_feat]
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
            "bond_source": bond_source,
            "bonded_item": chosen_bonded_item,
            "drain_action": drain_action,
            "spellbook_start_cantrips": spellbook_start_cantrips,
            "spellbook_start_rank1_spells": spellbook_start_rank1_spells,
            "spellbook_auto_add_per_level": spellbook_auto_add_per_level,
            "prepared_cantrips": total_prepared_cantrips,
            "prepared_rank1_slots": total_prepared_rank1_slots,
            "specialist_bonus_cantrip": specialist_bonus_cantrip if specialist else 0,
            "specialist_bonus_rank1_slot": 1 if specialist else 0,
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
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        wizard_spellbook = dict(getattr(self, "wizard_spellbook", {}) or {})
        wizard_spellbook.update(
            {
                "cantrips_count": spellbook_start_cantrips,
                "rank1_spells_count": spellbook_start_rank1_spells,
                "auto_add_spells_per_level": spellbook_auto_add_per_level,
                "spell_tradition": "arcane",
            }
        )
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
        try:
            setattr(self, "wizard_school_spells", known_school_spells)
            setattr(self, "wizard_focus_spells", known_focus_spells)
            setattr(self, "wizard_prepared_cantrips", total_prepared_cantrips)
            setattr(self, "wizard_prepared_rank1_slots", total_prepared_rank1_slots)
        except Exception:
            pass

        if school_focus_spell:
            try:
                current_focus = int(getattr(self, "focus_point", 0) or 0)
            except Exception:
                current_focus = 0
            try:
                setattr(self, "focus_point", max(1, current_focus))
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

        if "hand_of_the_apprentice" in applied_feats:
            known_focus_spells = list(getattr(self, "wizard_focus_spells", []) or [])
            if "hand_of_the_apprentice" not in known_focus_spells:
                known_focus_spells.append("hand_of_the_apprentice")
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
        if chosen_metamagic_feat:
            self._ui_log(
                "Wizard thesis (Metamagical Experimentation): "
                f"aktywny feat={self._labelize_choice(chosen_metamagic_feat)}."
            )
        if chosen_thesis == "spell_blending":
            self._ui_log(
                "Wizard thesis (Spell Blending): "
                "wymiana slotów jest obsługiwana manualnie podczas daily preparations (prompt reminder)."
            )
        if chosen_thesis == "spell_substitution":
            self._ui_log(
                "Wizard thesis (Spell Substitution): "
                "podmiana przygotowanego czaru po 10 minutach jest obsługiwana manualnie (prompt reminder)."
            )
        if school_bonus_spell or school_focus_spell:
            self._ui_log(
                "Wizard school bonusy: "
                f"spell={self._labelize_choice(school_bonus_spell)}, "
                f"focus spell={self._labelize_choice(school_focus_spell)}."
            )
        self._ui_log(
            "Wizard spellbook: "
            f"{spellbook_start_cantrips} cantrips, {spellbook_start_rank1_spells} rank-1 spells, "
            f"+{spellbook_auto_add_per_level} spells/level."
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
                f"Rogue ({self._labelize_choice(chosen_racket)}): wybierz key ability",
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
        favored_weapon_choices = list(data.get("cleric_favored_weapon_choices") or ["sword", "dagger", "longbow", "unarmed"])
        font_choices = list(data.get("cleric_font_choices") or ["heal", "harm"])
        weapon_groups = dict(data.get("cleric_weapon_groups") or {})
        domain_spell_placeholders = dict(data.get("cleric_domain_spell_placeholders") or {})

        def _pick(prompt: str, choices: list[str]) -> str | None:
            if not choices:
                return None
            label_map = {self._labelize_choice(item): item for item in choices}
            labels = list(label_map.keys())
            chosen_label = self._prompt_choice(prompt, labels, source="status")
            if not chosen_label:
                return None
            chosen = label_map.get(chosen_label)
            if chosen:
                return chosen
            raw = str(chosen_label).strip().lower().replace(" ", "_")
            return raw if raw in choices else None

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

        chosen_deity = _pick("Cleric: wybierz deity", deity_choices)
        if not chosen_deity:
            return
        chosen_doctrine = _pick("Cleric: wybierz doctrine", doctrine_choices)
        if not chosen_doctrine:
            return

        deity_data = dict(deity_options.get(chosen_deity, {}) or {})
        chosen_favored_weapon = _normalize_weapon(deity_data.get("favored_weapon"))
        if not chosen_favored_weapon:
            chosen_favored_weapon = _pick("Cleric: wybierz favored weapon", favored_weapon_choices)
        if not chosen_favored_weapon:
            return
        favored_weapon_group = _normalize_weapon(deity_data.get("favored_weapon_group")) or _weapon_group_for(
            chosen_favored_weapon
        )

        allowed_fonts = list(deity_data.get("font_options") or font_choices)
        if not allowed_fonts:
            allowed_fonts = ["heal"]
        chosen_font = allowed_fonts[0] if len(allowed_fonts) == 1 else _pick("Cleric: wybierz divine font", allowed_fonts)
        if not chosen_font:
            return

        domain_choices = list(deity_data.get("domain_choices") or [])
        if not domain_choices:
            domain_choices = ["custom_domain_a", "custom_domain_b", "custom_domain_c"]

        setup_payload = {
            "deity": chosen_deity,
            "doctrine": chosen_doctrine,
            "favored_weapon": chosen_favored_weapon,
            "favored_weapon_group": favored_weapon_group,
            "font": chosen_font,
            "domain_choices": list(domain_choices),
        }
        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["cleric_setup"] = dict(setup_payload)
                    new_data["cleric_deity"] = chosen_deity
                    new_data["cleric_doctrine"] = chosen_doctrine
                    new_data["cleric_favored_weapon"] = chosen_favored_weapon
                    new_data["cleric_favored_weapon_group"] = favored_weapon_group
                    new_data["cleric_font"] = chosen_font
                    new_data["cleric_domain_choices"] = list(domain_choices)
                    new_data["cleric_domain_spell_placeholders"] = dict(domain_spell_placeholders)
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Cleric setup: nie udalo sie zapisac wyborow.")
            return

        for attr, value in (
            ("cleric_deity", chosen_deity),
            ("cleric_doctrine", chosen_doctrine),
            ("cleric_favored_weapon", chosen_favored_weapon),
            ("cleric_favored_weapon_group", favored_weapon_group),
            ("cleric_font", chosen_font),
            ("cleric_domain_choices", list(domain_choices)),
            ("cleric_domain_spell_placeholders", dict(domain_spell_placeholders)),
        ):
            try:
                setattr(self, attr, value)
            except Exception:
                pass

        self._ui_log(
            "Cleric setup: "
            f"deity={self._labelize_choice(chosen_deity)}, "
            f"doctrine={self._labelize_choice(chosen_doctrine)}, "
            f"favored weapon={self._labelize_choice(chosen_favored_weapon)}, "
            f"font={self._labelize_choice(chosen_font)}."
        )
        self._ui_log(
            "Divine Font: przygotowanie listy czarow i pilnowanie slotow pozostaje po stronie gracza."
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

    def _handle_deific_weapon_choice(self, status: "Status", data: dict) -> None:
        choices = list(data.get("deific_weapon_choices") or [])
        if not choices:
            return
        label_map = {self._labelize_choice(item): item for item in choices}
        labels = list(label_map.keys())
        chosen_label = self._prompt_choice(
            "Deific Weapon: wybierz typ broni",
            labels,
            source="status",
        )
        if not chosen_label:
            return
        chosen_weapon = label_map.get(chosen_label)
        if not chosen_weapon:
            raw = str(chosen_label).strip().lower().replace(" ", "_").replace("-", "_")
            chosen_weapon = raw if raw in choices else None
        if not chosen_weapon:
            self._ui_log("Deific Weapon: nie wybrano poprawnego typu broni.")
            return

        try:
            for idx, item in enumerate(self.statuses):
                if item is status:
                    new_data = dict(data)
                    new_data["deific_weapon_type"] = chosen_weapon
                    self.statuses[idx] = replace(status, data=new_data)
                    break
        except Exception:
            self._ui_log("Deific Weapon: nie udalo sie zapisac wyboru broni.")
            return

        try:
            setattr(self, "deific_weapon_type", chosen_weapon)
        except Exception:
            pass
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
                    choice = self._prompt_choice(
                        "Shield Block: wybierz tarcze",
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
        for key, value in attrs.items():
            name = str(key or "").strip()
            if not name:
                continue
            if hasattr(self, name):
                continue
            try:
                setattr(self, name, value)
            except Exception:
                continue

        additive = data.get("add_actor_attrs") or {}
        if not isinstance(additive, dict):
            return
        for key, value in additive.items():
            name = str(key or "").strip()
            if not name:
                continue
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

    def tick_statuses_turn(self) -> int:
        """Zdekrementuj duration statusów; usuń wygasłe."""
        self._ensure_status_objects()
        if not self.statuses:
            return 0
        try:
            from statuses.race.dwarf.feats.vengeful_hatred import tick_vengeful_hatred_rounds

            tick_vengeful_hatred_rounds(self)
        except Exception:
            pass
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
