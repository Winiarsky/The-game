from dataclasses import dataclass
from typing import Any, Literal, Optional


PlacementType = Literal["cell", "edge"]


@dataclass(slots=True)
class GameObjectMeta:
    """Minimalne metadane potrzebne edytorowi."""

    object_id: str
    label: str
    color: str
    category: str
    placement: PlacementType = "cell"
    description: Optional[str] = None
    logic_cls: Optional[type[Any]] = None  # wskaźnik na klasę używaną w logice gry (nieserializowany)
    default_config: Optional[dict[str, Any]] = None
