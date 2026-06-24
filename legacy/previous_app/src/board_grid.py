from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import List, Optional, Protocol, Tuple

from GameObjects.interactions_mixin import StatusMixin
from GameObjects.interactions_mixin.base_interaction import InteractableMixin
from GameObjects.Obstacles.basic_obstacle import Obstacle
from GameObjects.Terrains.basic_terrain import BasicTerrain
from GameObjects.Walls.basic_wall import Wall
from statuses import COVERED_STATUS, HIDE_STATUS


class Occupant(Protocol):
    position: Optional[Tuple[int, int]]

    def set_position(self, position: Optional[Tuple[int, int]]) -> None: ...


@dataclass(slots=True)
class GridCell:
    field: BasicTerrain = dataclass_field(default_factory=BasicTerrain)
    occupant: Optional[Occupant] = None
    interactables: list[InteractableMixin] = dataclass_field(default_factory=list)
    rooms: set[str] = dataclass_field(default_factory=set)


class BoardGrid:
    """Dwuwymiarowa siatka pól gry (pozycje przekazujemy jako krotki (col, row))."""

    def __init__(self, rows: int, cols: int):
        if rows <= 0 or cols <= 0:
            raise ValueError("Wymiary planszy muszą być dodatnie.")
        self.rows = rows  # liczba rzędów (drugi element w krotce pozycji)
        self.cols = cols  # liczba kolumn (pierwszy element w krotce pozycji)
        self._grid: List[List[GridCell]] = [
            [GridCell() for _ in range(cols)] for _ in range(rows)
        ]
        # Interactables na krawędziach (np. drzwi między polami).
        self.edge_interactables: dict[frozenset[Tuple[int, int]], list[Interactable]] = {}
        self.walls: dict[frozenset[Tuple[int, int]], Wall] = {}
        self.room_positions: dict[str, set[Tuple[int, int]]] = {}
        self.rooms_meta: dict[str, dict[str, object]] = {}
        self.room_seek_locked: set[str] = set()
        self.room_seek_fail_counts: dict[str, int] = {}

    def in_bounds(self, position: Tuple[int, int] | None) -> bool:
        if position is None:
            return False
        col, row = position
        return 0 <= row < self.rows and 0 <= col < self.cols

    def cell_at(self, position: Tuple[int, int]) -> GridCell:
        if not self.in_bounds(position):
            raise ValueError(f"Pozycja {position} znajduje się poza planszą.")
        col, row = position
        return self._grid[row][col]

    def set_field(self, position: Tuple[int, int], terrain: BasicTerrain) -> None:
        """Ustaw typ pola (np. teren nieprzechodni)."""
        cell = self.cell_at(position)
        cell.field = terrain

    def rooms_at(self, position: Tuple[int, int]) -> set[str]:
        """Zwróć zestaw identyfikatorów pokoi przypisanych do pola."""
        if not self.in_bounds(position):
            raise ValueError(f"Pozycja {position} znajduje się poza planszą.")
        return set(self.cell_at(position).rooms)

    def positions_in_rooms(self, room_ids: set[str] | list[str]) -> set[Tuple[int, int]]:
        """Zwróć wszystkie pola należące do wskazanych pokoi."""
        result: set[Tuple[int, int]] = set()
        for room_id in room_ids:
            result.update(self.room_positions.get(room_id, set()))
        return result

    def apply_rooms(self, rooms: list[dict[str, object]]) -> None:
        """Zastąp informacje o pokojach na planszy (wspiera wiele pokoi na jednym polu)."""
        self.room_positions.clear()
        self.rooms_meta.clear()
        self.room_seek_locked.clear()
        self.room_seek_fail_counts.clear()
        for grid_row in self._grid:
            for cell in grid_row:
                cell.rooms.clear()

        for room in rooms or []:
            room_id = str(room.get("id") or room.get("name") or "").strip()
            if not room_id:
                continue
            room_name = room.get("name") or room_id
            room_color = room.get("color")
            self.rooms_meta[room_id] = {"name": room_name, "color": room_color}

            positions = room.get("positions") or []
            for raw_pos in positions:
                try:
                    col, row_idx = raw_pos
                    pos = (int(col), int(row_idx))
                except Exception:
                    continue
                if not self.in_bounds(pos):
                    continue
                cell = self.cell_at(pos)
                cell.rooms.add(room_id)
                self.room_positions.setdefault(room_id, set()).add(pos)

    # --- Seek state ---
    def is_room_seek_locked(self, room_id: str) -> bool:
        return room_id in self.room_seek_locked

    def lock_room_seek(self, room_id: str) -> None:
        self.room_seek_locked.add(room_id)

    def room_seek_failures(self, room_id: str) -> int:
        return self.room_seek_fail_counts.get(room_id, 0)

    def increment_room_seek_fail(self, room_id: str) -> int:
        current = self.room_seek_fail_counts.get(room_id, 0) + 1
        self.room_seek_fail_counts[room_id] = current
        return current

    def occupant_at(self, position: Tuple[int, int] | None) -> Optional[Occupant]:
        if position is None:
            return None
        return self.cell_at(position).occupant

    def interactables_at(self, position: Tuple[int, int]) -> list[InteractableMixin]:
        """Obiekty interaktywne na polu + krawędziach stykających się z polem."""
        cell_objs = list(self.cell_at(position).interactables)
        edge_objs: list[InteractableMixin] = []
        for key, objects in self.edge_interactables.items():
            if position in key:
                edge_objs.extend(objects)
        seen: set[int] = set()
        result: list[Interactable] = []
        for obj in cell_objs + edge_objs:
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            result.append(obj)
        return result

    def get_neighbors(self, position: Tuple[int, int], include_position: bool = True, diagonal: bool = True) -> list[Tuple[int, int]]:
        """Zwróć pola sąsiadujące w obrębie planszy.

        diagonal=False – tylko ortogonalne (góra/dół/lewo/prawo).
        """
        if not self.in_bounds(position):
            raise ValueError(f"Pozycja {position} znajduje się poza planszą.")
        col, row = position
        offsets = (-1, 0, 1)
        result: list[Tuple[int, int]] = []
        if diagonal:
            for dr in offsets:
                for dc in offsets:
                    if dr == 0 and dc == 0:
                        continue
                    neighbor = (col + dc, row + dr)
                    if self.in_bounds(neighbor):
                        result.append(neighbor)
        else:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor = (col + dc, row + dr)
                if self.in_bounds(neighbor):
                    result.append(neighbor)
        if include_position:
            result.append(position)
        return result

    def add_wall(
        self,
        a: Tuple[int, int],
        b: Tuple[int, int],
        *,
        hardness: int | None = None,
        features: Optional[dict[str, object]] = None,
        wall_cls: type[Wall] = Wall,
    ) -> Wall:
        """Dodaj ścianę blokującą przejście między polami."""
        if a == b:
            raise ValueError("Ściana musi łączyć dwa różne pola.")
        if not (self.in_bounds(a) and self.in_bounds(b)):
            raise ValueError("Ściana poza planszą.")
        wall = wall_cls(a=a, b=b, hardness=hardness, features=features or {})
        self.walls[wall.key] = wall
        return wall

    def get_wall(self, a: Tuple[int, int], b: Tuple[int, int]) -> Optional[Wall]:
        return self.walls.get(frozenset((a, b)))

    def is_blocked(self, a: Tuple[int, int], b: Tuple[int, int]) -> bool:
        return frozenset((a, b)) in self.walls

    def _is_obstacle(self, occupant: Optional[Occupant]) -> bool:
        return isinstance(occupant, Obstacle)

    @staticmethod
    def _is_diagonal_step(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
        return abs(int(a[0]) - int(b[0])) == 1 and abs(int(a[1]) - int(b[1])) == 1

    def _can_step_direct(self, a: Tuple[int, int], b: Tuple[int, int], *, allow_occupied: bool = False) -> bool:
        if not (self.in_bounds(a) and self.in_bounds(b)):
            return False
        if self.is_blocked(a, b):
            return False
        for edge_obj in self.edge_interactables_between(a, b):
            blocks_passage = getattr(edge_obj, "blocks_passage", None)
            if callable(blocks_passage) and blocks_passage(a, b):
                return False
        return self.can_enter(b, allow_occupied=allow_occupied)

    def can_enter(self, position: Tuple[int, int], allow_occupied: bool = False) -> bool:
        """Sprawdź czy pole można zająć/przejść (teren przechodni, brak ściany i brak przeszkody)."""
        cell = self.cell_at(position)
        if not cell.field.walkable:
            return False
        # Interactables mogą blokować wejście (np. drzwi do otwarcia z boku).
        if any(getattr(obj, "blocks_movement", False) or not getattr(obj, "allow_same_cell_interact", True) for obj in cell.interactables):
            return False
        if cell.occupant is None:
            return True
        occupant = cell.occupant
        # blokada ruchu dla przeszkód i przeciwników (blocks_movement)
        if self._is_obstacle(occupant):
            return False
        if getattr(occupant, "blocks_movement", False):
            return False
        return allow_occupied

    def can_traverse(self, a: Tuple[int, int], b: Tuple[int, int], allow_occupied: bool = False) -> bool:
        """Czy z pola a można przejść na b (brak ściany, teren przechodni, brak przeszkody)."""
        if not (self.in_bounds(a) and self.in_bounds(b)):
            return False
        if self._is_diagonal_step(a, b):
            mid_a = (int(b[0]), int(a[1]))
            mid_b = (int(a[0]), int(b[1]))
            route_a = self._can_step_direct(a, mid_a, allow_occupied=False) and self._can_step_direct(
                mid_a,
                b,
                allow_occupied=allow_occupied,
            )
            route_b = self._can_step_direct(a, mid_b, allow_occupied=False) and self._can_step_direct(
                mid_b,
                b,
                allow_occupied=allow_occupied,
            )
            return bool(route_a or route_b)
        return self._can_step_direct(a, b, allow_occupied=allow_occupied)

    def place(self, occupant: Occupant, position: Tuple[int, int]) -> None:
        cell = self.cell_at(position)
        if cell.occupant is not None:
            raise ValueError(f"Pole {position} jest już zajęte.")
        cell.occupant = occupant
        occupant.set_position(position)

    def remove(self, position: Tuple[int, int]) -> Optional[Occupant]:
        cell = self.cell_at(position)
        occupant = cell.occupant
        if occupant is not None:
            # jeśli obiekt interaktywny śledzi pasażera (np. skrzynia), wyczyść go przy opuszczaniu pola
            for interactable in cell.interactables:
                if getattr(interactable, "someone_inside", None) is occupant:
                    interactable.someone_inside = None
            if isinstance(occupant, StatusMixin):
                occupant.remove_status(HIDE_STATUS)
                occupant.remove_status(COVERED_STATUS)
            else:
                statuses = getattr(occupant, "statuses", None)
                if isinstance(statuses, list):
                    try:
                        statuses.remove("hide")
                    except ValueError:
                        pass
                    try:
                        statuses.remove("covered")
                    except ValueError:
                        pass
            if hasattr(occupant, "hide_stealth_bonus"):
                try:
                    occupant.hide_stealth_bonus = 0  # type: ignore[attr-defined]
                except Exception:
                    pass
            # zdejmij premie z akcji take cover
            remover = getattr(occupant, "remove_bonuses_with_prefix", None)
            if callable(remover):
                try:
                    remover("take_cover:")
                except Exception:
                    pass
            cell.occupant = None
            occupant.set_position(None)
        return occupant

    def add_interactable(self, interactable: Interactable, position: Tuple[int, int]) -> None:
        cell = self.cell_at(position)
        cell.interactables.append(interactable)
        interactable.set_position(position)

    def add_edge_interactable(self, interactable: Interactable, a: Tuple[int, int], b: Tuple[int, int]) -> None:
        """Dodaj obiekt interaktywny między dwoma polami (np. drzwi)."""
        if a == b:
            raise ValueError("Obiekt krawędziowy wymaga dwóch różnych pól.")
        if not (self.in_bounds(a) and self.in_bounds(b)):
            raise ValueError("Krawędź poza planszą.")
        key = frozenset((a, b))
        self.edge_interactables.setdefault(key, []).append(interactable)
        if hasattr(interactable, "edge"):
            try:
                interactable.edge = (a, b)  # type: ignore[attr-defined]
            except Exception:
                pass
        interactable.set_position(None)

    def edge_interactables_between(self, a: Tuple[int, int], b: Tuple[int, int]) -> list[Interactable]:
        return list(self.edge_interactables.get(frozenset((a, b)), []))

    def remove_interactable(self, interactable: Interactable, position: Tuple[int, int]) -> None:
        cell = self.cell_at(position)
        if interactable in cell.interactables:
            cell.interactables.remove(interactable)
            interactable.set_position(None)

    def get_interactables_in_range(
        self,
        position: Tuple[int, int],
        *,
        include_position: bool = True,
        diagonal: bool = True,
        include_hidden: bool = False,
    ) -> list[tuple[Tuple[int, int], list[Interactable]]]:
        """Zwróć pozycje z obiektami interaktywnymi w zasięgu sąsiadów (1 pole)."""

        def _eligible(objs: list[Interactable]) -> list[Interactable]:
            """Uwzględnia filtr ukrycia."""
            result: list[Interactable] = []
            for obj in objs:
                if getattr(obj, "hidden", False) and not getattr(obj, "revealed", False):
                    if not include_hidden or not getattr(obj, "allow_hidden_interaction", False):
                        continue
                result.append(obj)
            return result

        def _filter_by_reach(objs: list[Interactable], candidate_pos: Tuple[int, int]) -> list[Interactable]:
            """Uwzględnij ograniczenia interakcji względem pozycji bohatera."""
            filtered: list[Interactable] = []
            for obj in objs:
                if candidate_pos == position and not getattr(obj, "allow_same_cell_interact", True):
                    continue
                if candidate_pos != position and getattr(obj, "require_same_cell_interact", False):
                    continue
                filtered.append(obj)
            return filtered

        result: list[tuple[Tuple[int, int], list[Interactable]]] = []
        for candidate in self.get_neighbors(position, include_position=include_position, diagonal=diagonal):
            interactables = _filter_by_reach(_eligible(self.interactables_at(candidate)), candidate)
            if not interactables:
                continue
            result.append((candidate, interactables))
        # Obiekty krawędziowe między polem a sąsiadami wybieramy klikając sąsiada.
        for neighbor in self.get_neighbors(position, include_position=False, diagonal=diagonal):
            edge_objs = _filter_by_reach(_eligible(self.edge_interactables_between(position, neighbor)), neighbor)
            if edge_objs:
                result.append((neighbor, edge_objs))
        return result
    
    def move(self, source: Tuple[int, int], target: Tuple[int, int]) -> None:
        occupant = self.occupant_at(source)
        if occupant is None:
            raise ValueError(f"Brak obiektu do przeniesienia z pola {source}.")
        self.remove(source)
        self.place(occupant, target)
        self._cleanup_shared_tower_shield_cover()

    def _iter_occupants(self):
        for row in self._grid:
            for cell in row:
                occupant = cell.occupant
                if occupant is not None:
                    yield occupant

    @staticmethod
    def _adjacent(a: Tuple[int, int] | None, b: Tuple[int, int] | None) -> bool:
        if a is None or b is None:
            return False
        dx = abs(int(a[0]) - int(b[0]))
        dy = abs(int(a[1]) - int(b[1]))
        return max(dx, dy) <= 1

    def _drop_covered_if_no_take_cover(self, actor) -> None:
        bonuses = list(getattr(actor, "bonuses", []) or [])
        if any(str(getattr(effect, "source", "") or "").startswith("take_cover:") for effect in bonuses):
            return
        if isinstance(actor, StatusMixin):
            try:
                actor.remove_status(COVERED_STATUS)
                return
            except Exception:
                pass
        statuses = getattr(actor, "statuses", None)
        if not isinstance(statuses, list):
            return
        filtered = []
        for status in statuses:
            sid = str(getattr(status, "id", status) or "").strip().lower()
            if sid == "covered":
                continue
            filtered.append(status)
        try:
            actor.statuses = filtered
        except Exception:
            pass

    def _cleanup_shared_tower_shield_cover(self) -> None:
        """Usuń pożyczony Take Cover z tower shield, jeśli beneficjent nie stoi już obok właściciela."""
        try:
            from GameObjects.items.shield import has_raised_tower_shield_cover, tower_shield_cover_owner_key
        except Exception:
            return

        owners_by_key: dict[str, object] = {}
        for actor in self._iter_occupants():
            if not has_raised_tower_shield_cover(actor):
                continue
            try:
                key = tower_shield_cover_owner_key(actor)
            except Exception:
                continue
            owners_by_key[str(key)] = actor

        shared_prefix = "take_cover:tower_shield_from:"
        for actor in self._iter_occupants():
            bonuses = list(getattr(actor, "bonuses", []) or [])
            if not bonuses:
                continue
            kept = []
            removed_any = False
            actor_pos = getattr(actor, "position", None)
            for effect in bonuses:
                source = str(getattr(effect, "source", "") or "")
                if not source.startswith(shared_prefix):
                    kept.append(effect)
                    continue
                owner_key = source[len(shared_prefix) :].strip()
                owner = owners_by_key.get(owner_key)
                owner_pos = getattr(owner, "position", None) if owner is not None else None
                if owner is not None and self._adjacent(actor_pos, owner_pos):
                    kept.append(effect)
                    continue
                removed_any = True
            if not removed_any:
                continue
            try:
                actor.bonuses = kept
            except Exception:
                continue
            self._drop_covered_if_no_take_cover(actor)
