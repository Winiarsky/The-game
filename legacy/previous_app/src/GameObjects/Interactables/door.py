import logging
from typing import Optional

from board import consts
from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin import (
    DestructibleMixin,
    HiddenMixin,
    LockableMixin,
    TrappableMixin,
    RangeAttackAffectMixin,
    resolve_skill_check,
    resolve_skill_check_with_sources,
)
from ui_client import get_ui_client

logger = logging.getLogger(__name__)


class Door(RangeAttackAffectMixin, LockableMixin, TrappableMixin, HiddenMixin, DestructibleMixin, InteractableMixin):
    """Drzwi z obsługą zamka, pułapki, ukrycia i niszczenia."""
    cover_type = "greater"

    def __init__(
        self,
        *,
        locked: bool = True,
        allow_same_cell_interact: bool = True,
        allow_hidden_interaction: bool = True,
        require_same_cell_interact: bool = True,
        thievery_dc: int = 16,
        force_open_dc: int = 18,
        working_keys: Optional[list[str]] = None,
        trap_armed: bool = False,
        trap_detection_dc: int = 16,
        trap_disable_dc: int = 18,
        trap_effect: str = "Pułapka zadaje obrażenia lub uruchamia alarm.",
        hidden: bool = False,
        reveal_dc: int = 18,
        seekable: bool = True,
        reveal_tags: Optional[list[str]] = None,
        ac: int = 18,
        hp: int = 10,
        hardness: int = 5,
        auto_reveal_on_enter: bool = False,
        auto_trigger_on_enter: bool = False,
    ):
        InteractableMixin.__init__(
            self,
            position=None,
            blocks_movement=False,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
            allow_hidden_interaction=allow_hidden_interaction,
        )
        # atrybuty zamka
        self.locked = locked
        self.working_keys = working_keys or ["door_key"]
        self.thievery_dc = thievery_dc
        self.force_open_dc = force_open_dc
        self.jammed = False

        # pułapka
        self.trap_armed = trap_armed
        self.trap_detected = False
        self.trap_detection_dc = trap_detection_dc
        self.trap_disable_dc = trap_disable_dc
        self.trap_effect = trap_effect

        # ukrycie
        self.hidden = hidden
        self.revealed = not hidden
        self.reveal_dc = reveal_dc
        self.seekable = seekable
        self.reveal_tags = tuple(reveal_tags or [])
        self.auto_reveal_on_enter = auto_reveal_on_enter
        self.auto_trigger_on_enter = auto_trigger_on_enter

        # niszczenie
        self.ac = ac
        self.hp = hp
        self.hardness = hardness
        self.destroyed = False
        self.seek_color = list(consts.SEEK_DOOR_RGB)
        self.seek_color_name = "brązowe"
        self.seek_label = "drzwi"

        self.is_open = False
        self.edge: tuple[tuple[int, int], tuple[int, int]] | None = None  # para pól, między którymi stoją drzwi
        self.register_default_actions()
        self._sync_block_state()

    # --- narzędzia ---
    def _sync_block_state(self) -> None:
        """Aktualizuje blokowanie ruchu na podstawie stanu drzwi."""
        self.blocks_movement = not self.is_open and not self.destroyed

    def blocks_passage(self, a, b) -> bool:
        """Używane przez BoardGrid do blokowania przejścia między polami a-b."""
        return not self.is_open and not self.destroyed

    def can_interact(self, actor, game) -> bool:
        return True  # pozwalamy na ślepe próby nawet dla ukrytych drzwi

    def _neighboring_positions(self) -> list[tuple[int, int]]:
        """Zwróć pola sąsiadujące z krawędzią drzwi (a,b)."""
        if not self.edge:
            return []
        a, b = self.edge
        return [a, b]

    # --- akcje ---
    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="inspect",
                label="Obejrzyj",
                description="Sprawdź stan drzwi.",
                handler=Door.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="listen",
                label="Nasłuchuj",
                description="Przykładasz ucho do drzwi.",
                handler=Door.action_listen,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="open",
                label="Otwórz",
                description="Otwórz, jeśli się da.",
                handler=Door.action_open,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="close",
                label="Zamknij",
                description="Zamknij otwarte drzwi.",
                handler=Door.action_close,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="use_key",
                label="Klucz",
                description="Użyj właściwego klucza.",
                handler=Door.action_use_key,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="pick_lock",
                label="Wytrych",
                description="Test Złodziejstwa vs DC zamka.",
                handler=Door.action_pick_lock,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="force_open",
                label="Wyważ",
                description="Athletics vs DC zamka.",
                handler=Door.action_force_open,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="attack",
                label="Atakuj",
                description="Próbuj zniszczyć drzwi.",
                handler=Door.action_attack,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="search_trap",
                label="Szukaj pułapki",
                description="Perception vs DC wykrycia.",
                handler=Door.action_search_trap,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="disable_trap",
                label="Rozbrój pułapkę",
                description="Thievery vs DC rozbrojenia.",
                handler=Door.action_disable_trap,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="search_secret",
                label="Przeszukaj",
                description="Próba wykrycia ukrytych drzwi.",
                handler=Door.action_search_secret,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="blind_probe",
                label="Ślepy strzał",
                description="Macanie bez podpowiedzi (dla ukrytych elementów).",
                handler=Door.action_blind_probe,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="leave",
                label="Zakończ",
                description="Zakończ interakcję.",
                handler=lambda _self, _actor, _game, _payload=None: "Koniec interakcji.",
                end_interaction=True,
            )
        )

    def action_inspect(self, actor, game, _payload=None) -> str:
        state = "otwarte" if self.is_open else "zamknięte"
        lock = "odblokowane" if not self.locked else "zakluczone"
        jam = " (zaklinowane)" if self.jammed else ""
        destroyed = " (zniszczone)" if self.destroyed else ""
        trap = ""
        if self.trap_armed and self.trap_detected:
            trap = " Pułapka wykryta."
        if self.hidden and not self.revealed:
            return "Nie dostrzegasz tu drzwi."
        return f"Drzwi są {state}, {lock}{jam}{destroyed}.{trap}"

    def action_listen(self, actor, game, _payload=None) -> str:
        return "Nasłuchujesz za drzwiami. Nic wyraźnego nie słychać."

    def action_open(self, actor, game, _payload=None) -> str:
        if self.destroyed:
            self.is_open = True
            self._sync_block_state()
            return "Tu już nie ma czego otwierać."
        if self.hidden and not self.revealed:
            return "Nie znajdujesz uchwytu ani szczeliny."
        if self.locked or self.jammed:
            return "Drzwi są zablokowane."
        if self.is_open:
            return "Drzwi już są otwarte."
        if self.trap_armed:
            effect = self.trigger_trap()
            self.is_open = True
            self._sync_block_state()
            return f"Pułapka odpala przy otwieraniu! {effect}"
        self.is_open = True
        self._sync_block_state()
        return "Otwierasz drzwi."

    def action_close(self, actor, game, _payload=None) -> str:
        if self.destroyed:
            return "Zniszczonych drzwi nie zamkniesz."
        if self.hidden and not self.revealed:
            return "Nie wiesz, co zamykać."
        if not self.is_open:
            return "Drzwi już są zamknięte."
        self.is_open = False
        self._sync_block_state()
        return "Zamykasz drzwi."

    def action_use_key(self, actor, game, _payload=None) -> str:
        if self.destroyed:
            return "Nie ma zamka do otwarcia."
        ui = getattr(game, "ui", None)
        key_name = None
        if ui and ui.enabled:
            key_name = ui.prompt_choice("Podaj nazwę klucza:", source="interaction")
        elif ui and not getattr(ui, "allow_cli_fallback", False):
            return "UI-only mode: brak aktywnego promptu do podania nazwy klucza."
        if not key_name:
            if ui and not getattr(ui, "allow_cli_fallback", False):
                return "Nie podano nazwy klucza."
            key_name = input("Podaj nazwę klucza: ").strip()
        if not key_name:
            return "Nie użyto klucza."
        success, msg = self.try_key(key_name)
        if success:
            self.is_open = True
            self._sync_block_state()
        return msg

    def action_pick_lock(self, actor, game, _payload=None) -> str:
        if self.destroyed:
            return "Zamek zniszczony, wytrych niepotrzebny."
        roll = get_ui_client().prompt_roll(
            "Rzuć na Thievery (wynik końcowy): ",
            source="game",
            layout="test",
            answer_placeholder="Wynik Thievery",
        )
        outcome, msg = self.pick_lock(roll)
        if outcome in ("critical_success",):
            self.is_open = True
        self._sync_block_state()
        return msg

    def action_force_open(self, actor, game, _payload=None) -> str:
        if self.destroyed:
            return "Zamek i zawiasy już zniszczone."
        roll = get_ui_client().prompt_roll(
            "Rzuć na Athletics (wyważanie): ",
            source="game",
            layout="test",
            answer_placeholder="Wynik Athletics",
        )
        outcome, msg = self.force_lock(roll)
        if outcome in ("critical_success", "success"):
            self.is_open = True
        self._sync_block_state()
        return msg

    def action_attack(self, actor, game, _payload=None) -> str:
        attack_roll = get_ui_client().prompt_roll(
            "Rzut na atak: ",
            source="game",
            layout="test",
            answer_placeholder="Wynik ataku",
        )
        damage = get_ui_client().prompt_roll(
            "Zadane obrażenia: ",
            source="game",
            layout="damage",
            answer_placeholder="Obrażenia",
        )
        hit, dealt, msg = self.apply_damage(attack_roll, damage)
        if hit and self.destroyed:
            self.is_open = True
            self.locked = False
            self._sync_block_state()
            return msg + " Przejście jest otwarte."
        self._sync_block_state()
        return msg

    def action_search_trap(self, actor, game, _payload=None) -> str:
        roll = get_ui_client().prompt_roll(
            "Rzuć na Perception (szukanie pułapki): ",
            source="game",
            layout="test",
            answer_placeholder="Wynik Perception",
        )
        outcome, msg = self.detect_trap(roll)
        return f"{msg} (wynik: {outcome})"

    def action_disable_trap(self, actor, game, _payload=None) -> str:
        roll = get_ui_client().prompt_roll(
            "Rzuć na Thievery (rozbrajanie): ",
            source="game",
            layout="test",
            answer_placeholder="Wynik Thievery",
        )
        outcome, msg = self.disable_trap(roll, actor=actor, game=game)
        return f"{msg} (wynik: {outcome})"

    def action_search_secret(self, actor, game, _payload=None) -> str:
        tags = ["seek", "secret", "door", "perception"]
        tags.extend([t for t in self.reveal_tags if t not in tags])
        result = resolve_skill_check_with_sources(
            skill_id="perception",
            dc=self.reveal_dc,
            actor=actor,
            target=None,
            tags=tags,
            game=game,
            apply_modifiers=True,
        )
        outcome, msg = self.try_reveal(result.total)
        return f"{msg} (wynik: {outcome})"

    def action_blind_probe(self, actor, game, _payload=None) -> str:
        if not self.hidden:
            return "Tu nic nie jest ukryte – ślepy strzał nic nie da."
        if self.revealed:
            return "Sekret już odkryty."
        tags = ["seek", "secret", "door", "perception", "blind_probe"]
        tags.extend([t for t in self.reveal_tags if t not in tags])
        result = resolve_skill_check_with_sources(
            skill_id="perception",
            dc=self.reveal_dc + 2,
            actor=actor,
            target=None,
            tags=tags,
            game=game,
            apply_modifiers=True,
        )
        if result.outcome in ("success", "critical_success"):
            self.revealed = True
            return "Udaje się namacać ukryte drzwi."
        return "Nie znajdujesz niczego konkretnego."

    def on_enter(self, actor, game) -> str | None:
        """Wejście na pola sąsiadujące z krawędzią drzwi."""
        if not self.edge:
            return None
        if actor.position not in self._neighboring_positions():
            return None
        messages: list[str] = []
        if self.auto_trigger_on_enter and self.trap_armed:
            effect = self.trigger_trap()
            messages.append(f"Pułapka przy drzwiach odpala! {effect}")
        if self.auto_reveal_on_enter and self.hidden and not self.revealed:
            tags = ["seek", "secret", "door", "perception", "auto"]
            tags.extend([t for t in self.reveal_tags if t not in tags])
            result = resolve_skill_check_with_sources(
                skill_id="perception",
                dc=self.reveal_dc,
                actor=actor,
                target=None,
                tags=tags,
                game=game,
                apply_modifiers=True,
            )
            outcome, msg = self.try_reveal(result.total)
            messages.append(f"{msg} (wynik: {outcome})")
        return " ".join(messages) if messages else None


META = GameObjectMeta(
    object_id="door",
    label="Drzwi",
    color="#8b5",
    category="Interactables",
    placement="edge",
    description="Drzwi z obsługą zamka, pułapki i sekretów.",
    logic_cls=Door,
    default_config={
        "locked": True,
        "allow_same_cell_interact": True,
        "allow_hidden_interaction": True,
        "require_same_cell_interact": True,
        "thievery_dc": 16,
        "force_open_dc": 18,
        "working_keys": ["door_key"],
        "trap_armed": False,
        "trap_detection_dc": 16,
        "trap_disable_dc": 18,
        "trap_effect": "Pułapka zadaje 2k6 obrażeń.",
        "hidden": False,
        "reveal_dc": 18,
        "seekable": True,
        "reveal_tags": [],
        "auto_reveal_on_enter": False,
        "auto_trigger_on_enter": False,
        "ac": 18,
        "hp": 10,
        "hardness": 5,
    },
)
