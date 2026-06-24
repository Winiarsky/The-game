from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from GameObjects.base import GameObjectMeta

logger = logging.getLogger(__name__)


@dataclass
class GameObjectDefinition:
    meta: GameObjectMeta
    logic_cls: object | None
    module_name: str
    path: Path


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Brak spec dla {module_name}")
    module = importlib.util.module_from_spec(spec)
    # wpychamy moduł do sys.modules przed exec_module, by dataclasses miały prawidłowy __module__
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def scan_game_objects(base_dir: Path, *, ensure_src_on_path: bool = True) -> list[GameObjectDefinition]:
    """Zeskanuj katalog GameObjects i zwróć listę definicji (meta + klasa logiki)."""
    definitions: list[GameObjectDefinition] = []
    if ensure_src_on_path:
        src_root = base_dir.parent
        if str(src_root) not in sys.path:
            sys.path.insert(0, str(src_root))

    # Skanujemy tylko katalogi z obiektami planszy/scenariusza.
    # Pomijamy moduły pomocnicze (events/items/companions), które nie mają META
    # i potrafią wywoływać skutki uboczne przy imporcie.
    skip_categories = {"interactions_mixin", "dialogs", "events", "items", "companions"}
    for category_dir in base_dir.iterdir():
        if not category_dir.is_dir():
            continue
        if category_dir.name in skip_categories:
            continue
        category = category_dir.name
        base_skip = {"basic_obstacle", "basic_terrain", "basic_wall", "basic_enemy", "base_npc"}
        for module_file in category_dir.glob("*.py"):
            if module_file.stem == "__init__":
                continue
            # Bazowe klasy wspólne, nie obiekty do rejestru.
            if module_file.stem in base_skip:
                continue
            module_name = f"GameObjects.{category}.{module_file.stem}"
            try:
                module = _load_module(module_name, module_file)
                meta = getattr(module, "META", None)
                if not isinstance(meta, GameObjectMeta):
                    logger.debug("Pomijam %s - brak META typu GameObjectMeta", module_name)
                    continue
                logic_cls = getattr(meta, "logic_cls", None) or getattr(module, "LOGIC_CLS", None)
                definitions.append(
                    GameObjectDefinition(
                        meta=meta,
                        logic_cls=logic_cls,
                        module_name=module_name,
                        path=module_file,
                    )
                )
            except Exception as exc:  # pragma: no cover - bezpieczne logowanie
                logger.exception("Nie udało się wczytać obiektu %s: %s", module_name, exc)
                continue
    return definitions


def serialize_meta(definitions: Iterable[GameObjectDefinition]) -> list[dict[str, object]]:
    """Przygotuj dane do frontu (bez klasy logiki)."""
    result: list[dict[str, object]] = []
    for definition in definitions:
        meta = definition.meta
        result.append(
            {
                "category": meta.category,
                "object_id": meta.object_id,
                "label": meta.label,
                "color": meta.color,
                "placement": meta.placement,
                "description": meta.description,
                "default_config": meta.default_config,
            }
        )
    return result
