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
                del self.statuses[idx]
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
                removed += 1
                continue
            remaining.append(replace(status, duration=turns))
        self.statuses = remaining
        return removed
