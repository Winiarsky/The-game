import random
from GameObjects.base import GameObjectMeta
from typing import Optional

from GameObjects.interactions_mixin.base_interaction import InteractableMixin, Interaction
from GameObjects.interactions_mixin import HideInMixin, prompt_for_roll, RangeAttackAffectMixin
import logging
from board import consts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LockedChest(RangeAttackAffectMixin, InteractableMixin, HideInMixin):
    """Prosta skrzynia: otwórz, aby zebrać skarb."""
    cover_type = "minor"

    def __init__(
        self,
        loot: list[str],
        locked: bool,
        allow_same_cell_interact: bool,
        blocks_movement: bool,
        thievery_dc: int,
        force_open_dc: int,
        push_dc: int,
        ac: int,
        hp: int,
        hardness: int,
        working_keys: Optional[list[str]],
        inspection_msg: Optional[str],
        max_crit_failures: int,
        max_failures: int,
        ):
        super().__init__(position=None, allow_same_cell_interact=allow_same_cell_interact)
        # pozwala stać na tym samym polu po wskoczeniu, ale domyślnie blokuje ruch zwykły
        self.allow_same_cell_interact = allow_same_cell_interact
        self.blocks_movement = blocks_movement
        self.locked = locked
        self.interactable = True
        self.loot = list(loot)
        self.thievery_dc = thievery_dc  # trudność otwarcia skrzyni
        self.force_open_dc = force_open_dc
        self.ac = ac  # klasa pancerza skrzyni dla ataków
        self.hp = hp
        self.hardness = hardness
        self.working_keys = list(working_keys) if working_keys is not None else ["master_key"]
        self.is_open = False
        self.destroyed = False
        self.register_default_actions()
        self.inspection_msg = inspection_msg
        self.max_crit_failures = max_crit_failures
        self.max_failures = max_failures
        self.crit_failures = 0
        self.failures = 0
        self.push_dc = push_dc  # trudność przesunięcia skrzyni
        self.someone_inside = None  # przechowuje postać, która wskoczyła do skrzyni
        HideInMixin.__init__(self, hide_stealth_bonus=2)

    def can_interact(self, actor, game) -> bool:
        return self.interactable

    # --- Narzędzia ---
    def _skill_check(self, dc: int, roll_msg: str) -> tuple[str, int]:
        roll = prompt_for_roll(roll_msg)
        if roll >= dc + 10:
            outcome = "critical_success"
        elif roll >= dc:
            outcome = "success"
        elif roll <= dc - 10:
            outcome = "critical_failure"
        else:
            outcome = "failure"
        return outcome, roll

    def _describe_loot(self) -> str:
        msg = ", ".join(self.loot) if self.loot else "Tu nic nie ma!"
        return msg

    # --- Akcje ---
    def register_default_actions(self) -> None:
        """Rejestruje zestaw domyślnych akcji skrzyni."""
        self.register_action(
            Interaction(
                id="inspect",
                label="Obejrzyj",
                description="Sprawdź stan skrzyni.",
                tags=["interact", "manipulate"],
                handler=LockedChest.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="open",
                label="Otwórz",
                description="Spróbuj otworzyć (jeśli odblokowana).",
                tags=["interact", "manipulate"],
                handler=LockedChest.action_open,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="close",
                label="Zamknij",
                description="Zamknij wieko otwartej skrzyni.",
                tags=["interact", "manipulate"],
                handler=LockedChest.action_close,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="use_key",
                label="Użyj klucza",
                description="Włóż klucz i spróbuj odblokować.",
                tags=["interact", "manipulate"],
                handler=LockedChest.action_use_key,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="unlock_thievery",
                label="Wytrych",
                description="Test Złodziejstwa vs DC.",
                tags=["interact", "manipulate", "thievery"],
                handler=LockedChest.action_unlock_thievery,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="force_open",
                label="Wyrwij/wyważ",
                description="Athletics vs DC, próba sforsowania.",
                tags=["interact", "manipulate", "athletics"],
                handler=LockedChest.action_force_open,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="attack",
                label="Atakuj",
                description="Uderz w skrzynię bronią.",
                tags=["attack_melee"],
                handler=LockedChest.action_attack,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="push",
                label="Przesuń",
                description="Spróbuj przesunąć skrzynię na sąsiednie pole.",
                tags=["interact", "manipulate", "athletics", "move"],
                handler=LockedChest.action_push,
            )
        )
        self.register_action(
            Interaction(
                id="jump_on",
                label="Wskocz do skrzynię",
                description="Wskocz do skrzyni aby otrzymac bonus do ukrywania i zaslone. (Tylko dla postaci o maym lub mniejszym rozmiarze)",
                tags=["interact", "move"],
                handler=LockedChest.action_jump_in,
            )
        )
        self.register_action(
            Interaction(
                id="loot",
                label="Zbierz łup",
                description="Weź wszystko ze środka (jeśli otwarte).",
                tags=["interact", "manipulate"],
                handler=LockedChest.action_loot,
            )
        )
        self.register_action(
            Interaction(
                id="leave",
                label="Zrezygnuj",
                description="Zakończ interakcję.",
                tags=["interaction_end"],
                handler=lambda _self, _actor, _game, _payload=None: "Koniec akcji.",
            )
        )

    def action_inspect(self, actor, game, _payload: Optional[dict] = None) -> str:
        if self.inspection_msg:
            return self.inspection_msg
        state = "otwarta" if self.is_open else "zamknięta"
        lock_state = "odblokowana" if not self.locked else "zakluczona"
        destroyed = " (rozbita)" if self.destroyed else ""
        loot_info = f" W środku: {self._describe_loot()}." if self.is_open or self.destroyed else ""
        return f"Skrzynia jest {state}, {lock_state}{destroyed}.{loot_info}"

    def action_open(self, actor, game, _payload: Optional[dict] = None) -> str:
        if self.destroyed:
            self.is_open = True
            return "Skrzynia jest zniszczona."
        if self.locked:
            return "Skrzynia jest zakluczona, użyj klucza lub innej metody, by ją odblokować."
        if self.is_open and not self.loot:
            return "Skrzynia zostala juz wyeksplorowana."
        self.is_open = True
        return f"Otwierasz skrzynię. Widzisz: {self._describe_loot()}."

    def action_close(self, actor, game, _payload: Optional[dict] = None) -> str:
        if self.destroyed:
            return "Nie da się zamknąć rozbitej skrzyni."
        if self.locked:
            return "Skrzynia jest juz zamknieta i zakluczona."
        if not self.is_open:
            return "Wieko już jest zamknięte."
        self.is_open = False
        return "Zamykasz wieko skrzyni."

    def action_use_key(self, actor, game, _payload: Optional[dict] = None) -> str:
        if not self.locked:
            return "Zamek już odblokowany."
        if self.destroyed:
            return "Skrzynia jest rozwalona, zaden klucz juz tu nie pomoze."
        if self.is_open:
            return "Skrzynia jest juz otwarta."
        ui = getattr(game, "ui", None)
        key_name = None
        if ui and ui.enabled:
            key_name = ui.prompt_choice("Podaj nazwę klucza, którego używasz:", source="interaction")
        if not key_name:
            key_name = input("Podaj nazwę klucza, którego używasz: ").strip()
        if not key_name:
            return "Nie użyto klucza."
        if key_name in self.working_keys:
            self.locked = False
            self.is_open = True
            return f"Używasz {key_name}. Zamek klika i luzuje się."
        return f"{key_name} nie pasuje do zamka."

    def action_unlock_thievery(self, actor, game, _payload: Optional[dict] = None) -> str:
        if not self.locked:
            return "Zamek już odblokowany."
        if self.destroyed:
            return "Skrzynia jest rozwalona, nic juz nie da sie z tym zrobic."
        if self.is_open:
            return "Skrzynia jest juz otwarta."
        if self.failures >= self.max_failures or self.crit_failures >= self.max_crit_failures:
            return "Zamek jest zbyt uszkodzony od poprzednich prób, by kontynuować."
        outcome, total = self._skill_check(self.thievery_dc, "Rzuć na Thievery (podaj ostateczny wynik): ")
        match outcome:
            case "critical_success":
                self.locked = False
                self.is_open = True
                return f"Kryt! ({total}) Cicho otwierasz zamek i uchylasz wieko. Łup: {self._describe_loot()}."
            case "success":
                self.locked = False
                return f"Sukces ({total}). Zamek ustępuje."
            case "failure":
                self.failures += 1
                return f"Porażka ({total}). Zamek nadal zamknięty."
            case "critical_failure":
                self.crit_failures += 1
                self.thievery_dc += 2
                return f"Krytyczna porażka ({total})! Zamek się klinuje; kolejne próby będą trudniejsze."
        return "Nieoczekiwany wynik testu."

    def action_force_open(self, actor, game, _payload: Optional[dict] = None) -> str:
        if not self.locked:
            return "Zamek już odblokowany - nie ma czego wyważać."
        if self.destroyed:
            return "Skrzynia jest rozwalona, nic juz nie da sie z tym zrobic."
        if self.is_open:
            return "Skrzynia jest juz otwarta."
        outcome, total = self._skill_check(self.force_open_dc, "Rzuć na Athletics (podaj ostateczny wynik): ")
        match outcome:
            case "critical_success":
                self.locked = False
                self.is_open = True
                return f"Krytyk siłowy ({total})! Zawiasy pękają, wieko odskakuje. Łup: {self._describe_loot()}."
            case "success":
                self.locked = False
                return f"Udało się wyważyć ({total}). Skrzynia jest odblokowana."
            case "failure":
                self.failures += 1
                return f"Porażka ({total}). Zamek wciąż trzyma."
            case "critical_failure":
                self.crit_failures += 1
                self.locked = True
                self.force_open_dc += 2
                return f"Fatalne pudło ({total})! Zamek się klinuje, następne próby mogą być trudniejsze."
        return "Nieoczekiwany wynik testu."

    def action_attack(self, actor, game, _payload: Optional[dict] = None) -> str:
        if self.destroyed:
            return "Skrzynia już rozbita."
        attack_roll = prompt_for_roll("Rzuć na atak (podaj ostateczny wynik): ") # po zaimplementowaniu walki, to powinno korzystać z mechaniki walki
        if attack_roll < self.ac:
            return f"Atak ({attack_roll}) nie trafia skrzyni (AC {self.ac})."
        damage = prompt_for_roll("Podaj zadaną ilość obrażeń: ")
        effective_damage = max(0, damage - self.hardness)
        self.hp -= effective_damage
        if self.hp <= 0:
            self.destroyed = True
            self.locked = False
            self.is_open = True
            return f"Skrzynia pęka pod uderzeniem! Łup wypada: {self._describe_loot()}."
        return f"Trafienie ({attack_roll}). Zadajesz {effective_damage} obrażeń (po Hardness {self.hardness}). HP skrzyni: {self.hp}."

    def action_push(self, actor, game, _payload: Optional[dict] = None) -> str:
        if self.destroyed:
            return "To już kupa desek, przesuwanie nie ma sensu."
        if self.position is None:
            return "Skrzynia nie jest na planszy."
        outcome, total = self._skill_check(self.push_dc, "Rzuć na Athletics (podaj ostateczny wynik): ")
        if outcome == "failure":
            return f"Nie udaje się przesunąć skrzyni ({total})."
        if outcome == "critical_failure":
            return f"Krytyczna porażka ({total})! Potykasz się i upadasz, nie przesuwając skrzyni otrzymujesz {random.randint(1, 3)} obrażeń."

        board = game.board
        current_pos = self.position
        passenger = None
        if self.someone_inside:
            occupant = board.occupant_at(current_pos)
            if occupant is self.someone_inside:
                passenger = occupant
            else:
                # pasażer wyszedł ze skrzyni – wyczyść znacznik
                self.someone_inside = None

        neighbors = board.get_neighbors(current_pos)
        valid_targets = [
            pos for pos in neighbors
            if pos != current_pos and board.can_traverse(current_pos, pos, allow_occupied=False)
        ]

        if not valid_targets:
            return f"Sukces testu ({total}), ale brak dostępnych pól do przesunięcia skrzyni."

        game.conn.set_leds(valid_targets, consts.MOVE_FIELD_RGB)
        while True:
            try:
                target = game.conn.scan_board(valid_targets)
                if target not in valid_targets:
                    logger.info("Wybrano nieprawidłowe pole.")
                    continue
                game.conn.leds_off()
                break
            except Exception as e:
                continue

        if passenger is not None:
            try:
                board.move(current_pos, target)
            except ValueError as exc:
                return f"Nie da się przesunąć skrzyni z pasażerem: {exc}"

        board.remove_interactable(self, current_pos)
        board.add_interactable(self, target)
        return f"Przesuwasz skrzynię na {target} (test {total})."

    def _hide_in_precheck(self, actor, game) -> Optional[str]:
        if self.destroyed:
            return "Skrzynia jest rozwalona, nie da sie juz do niej wskoczyc."
        if self.locked:
            return "Musisz najpierw otworzyc skrzynie."
        if not self.is_open:
            return "Musisz najpierw otworzyc skrzynie."
        return None

    def action_jump_in(self, actor, game, _payload: Optional[dict] = None) -> str:
        msg = self.hide_in(actor, game)
        if msg.startswith("Ukrywasz się"):
            bonus = self.hide_stealth_bonus
            return f"Wskakujesz do skrzyni, otrzymujesz bonus do ukrywania się +{bonus} oraz połowiczną zasłonę."
        return msg
    
    def action_loot(self, actor, game, _payload: Optional[dict] = None) -> str:
        if self.locked and not self.destroyed:
            return "Najpierw odblokuj skrzynię."
        if not self.is_open and not self.destroyed:
            return "Otwórz skrzynię, by sięgnąć do środka."
        if not self.loot:
            return "W środku jest pusto."
        loot_items = self.loot[:]
        self.loot = []
        return f"Zabierasz: {', '.join(loot_items)}."


META = GameObjectMeta(
    object_id="locked_chest",
    label="Zamknięta skrzynia",
    color="#c58f22",
    category="Interactables",
    placement="cell",
    description="Skrzynia ze skarbem, interakcja: otwórz i zabierz łup.",
    logic_cls=LockedChest,
    default_config={
        "loot": [],
        "locked": True,
        "allow_same_cell_interact": True,
        "blocks_movement": True,
        "thievery_dc": 12,
        "force_open_dc": 15,
        "push_dc": 13,
        "ac": 20,
        "hp": 10,
        "hardness": 5,
        "working_keys": ["12345"],
        "inspection_msg": None,
        "max_crit_failures": 3,
        "max_failures": 5,
    },
)
