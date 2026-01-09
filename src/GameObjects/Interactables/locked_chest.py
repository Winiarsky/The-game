from GameObjects.base import GameObjectMeta
from interactable import Interactable


class LockedChest(Interactable):
    """Prosta skrzynia: otwórz, aby zebrać skarb."""

    def __init__(self, loot: list[str] | None = None, locked: bool = True):
        super().__init__(position=None)
        self.allow_same_cell_interact = False
        self.blocks_movement = True
        self.locked = locked
        self.opened = False
        self.loot = loot or ["gold_coin", "gem"]
        self.dc = 12  # trudność otwarcia skrzyni
        self.ac = 20  # klasa pancerza skrzyni dla ataków
        self.hp = 10
        self.hardness = 5
        self.allowed_actions = ['thievery', 'attack', 'key']

    def can_interact(self, actor, game) -> bool:
        return not self.opened

    def interact(self, actor, game):
        if not self.locked:
            return "Skrzynia jest już odblokowana."
        action = input("wybierz akcje ktora chesz wykonac")
        if action not in self.allowed_actions:
            return f"Akcja '{action}' nie jest dozwolona dla tej skrzyni."
        match action:
            case 'key':
                self.locked = False
                return "Używasz klucza, aby odblokować skrzynię."
            case 'thievery':
                return self.attempt_unlock(actor, game)
            case 'attack':
                return self.attempt_attack(actor, game)
            
    def attempt_unlock(self, actor, game) -> str:
        if not self.locked:
            return "Skrzynia jest już odblokowana."
        # Tutaj można dodać logikę rzutu kością i porównania z DC
        self.locked = False
        return "Udało ci się otworzyć skrzynię metodą włamywania!"
    
    def attempt_attack(self, actor, game) -> str:
        # Tutaj można dodać logikę ataku na skrzynię
        self.hp -= 5  # przykładowe obrażenia
        if self.hp <= 0:
            self.locked = False
            return "Skrzynia została zniszczona i otwarta!"
        return f"Skrzynia została trafiona! Pozostało jej {self.hp} punktów życia."
    


META = GameObjectMeta(
    object_id="locked_chest",
    label="Zamknięta skrzynia",
    color="#c58f22",
    category="Interactables",
    placement="cell",
    description="Skrzynia ze skarbem, interakcja: otwórz i zabierz łup.",
    logic_cls=LockedChest,
    default_config={"locked": True, "loot": ["gold_coin", "gem"]},
)
