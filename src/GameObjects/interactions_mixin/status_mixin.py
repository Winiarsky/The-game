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
        if data.get("ui_choice_kind") == "general_training":
            try:
                self._handle_general_training_choice(status, data)
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

    def _druid_order_choice(self) -> str | None:
        setup = self._druid_setup_data()
        value = setup.get("order")
        if value is None:
            value = getattr(self, "druid_order", None)
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
            if not self._is_druid_actor():
                self._ui_log(f"{self._labelize_choice(status_id)}: wymaga klasy Druid.")
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

    def _drop_reactions_for_status(self, status_id: str) -> None:
        reactions = getattr(self, "reactions", None)
        if not isinstance(reactions, list):
            return
        if status_id == "shield_block":
            self.reactions = [item for item in reactions if getattr(item, "id", None) != "shield_block"]

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

    def add_status(self, status: str | "Status") -> bool:
        """Dodaj status – wymagany obiekt Status (nie string)."""
        from statuses import Status  # lokalny import by unikać cykli
        if not isinstance(status, Status):
            raise TypeError("add_status oczekuje instancji Status.")
        self._ensure_status_objects()
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
