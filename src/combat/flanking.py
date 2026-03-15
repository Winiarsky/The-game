from __future__ import annotations

import logging
from typing import Iterable, Sequence

from statuses import Status, FLAT_FOOTED_STATUS
from bonuses import BonusEffect, BonusType, compute_total_modifier

logger = logging.getLogger(__name__)


def _adjacent_reachable(board, a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Sprawdza, czy między sąsiadami nie ma ściany/blokera na krawędzi (ignoruje zajętość pól)."""
    if not (board.in_bounds(a) and board.in_bounds(b)):
        return False
    if board.is_blocked(a, b):
        return False
    for edge_obj in board.edge_interactables_between(a, b):
        blocks_passage = getattr(edge_obj, "blocks_passage", None)
        if callable(blocks_passage) and blocks_passage(a, b):
            return False
    return True


def _are_opposite(center: tuple[int, int], a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Czy a i b leżą po przeciwnych stronach względem center (uwzględnia diagonale)."""
    ax, ay = a[0] - center[0], a[1] - center[1]
    bx, by = b[0] - center[0], b[1] - center[1]
    return (ax, ay) != (0, 0) and (bx, by) != (0, 0) and ax == -bx and ay == -by


def _threat_positions(board, target_pos: tuple[int, int], actors: Iterable[object]) -> list[tuple[int, int]]:
    threats: list[tuple[int, int]] = []
    for actor in actors:
        pos = getattr(actor, "position", None)
        if pos is None:
            continue
        if pos not in board.get_neighbors(target_pos, include_position=False, diagonal=True):
            continue
        if not _adjacent_reachable(board, target_pos, pos):
            continue
        threats.append(pos)
    return threats


def flanking_positions(
    board,
    target_pos: tuple[int, int],
    ally_positions: Sequence[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Zwróć pola, na które można wejść by flankować target (ally po przeciwnej stronie)."""
    candidates: list[tuple[int, int]] = []
    for pos in board.get_neighbors(target_pos, include_position=False, diagonal=True):
        if not board.can_enter(pos, allow_occupied=False):
            continue
        if not _adjacent_reachable(board, target_pos, pos):
            continue
        for ally in ally_positions:
            if ally == pos:
                continue
            if ally not in board.get_neighbors(target_pos, include_position=False, diagonal=True):
                continue
            if not _adjacent_reachable(board, target_pos, ally):
                continue
            if _are_opposite(target_pos, pos, ally):
                candidates.append(pos)
                break
    return candidates


def is_flanked(board, target_pos: tuple[int, int] | None, threats: Iterable[object]) -> bool:
    """Czy target ma dwóch przeciwników po przeciwnych stronach?"""
    if target_pos is None:
        return False
    threat_positions = _threat_positions(board, target_pos, threats)
    for idx, first in enumerate(threat_positions):
        for other in threat_positions[idx + 1 :]:
            if _are_opposite(target_pos, first, other):
                return True
    return False


def _remove_flat_footed(target, *, source: str | None = None) -> None:
    removed = False
    remover = getattr(target, "remove_status", None)
    if callable(remover):
        if source is None:
            removed = remover(FLAT_FOOTED_STATUS) or remover("flat_footed")
        else:
            removed = False
    statuses = getattr(target, "statuses", None)
    if isinstance(statuses, list):
        new_statuses: list[Status | object] = []
        for status in statuses:
            sid = status.id if isinstance(status, Status) else status
            if sid == "flat_footed":
                data = getattr(status, "data", None) or {}
                if source is not None and data.get("flat_footed_source") != source:
                    new_statuses.append(status)
                    continue
                removed = True
                continue
            new_statuses.append(status)
        if removed:
            target.statuses = new_statuses  # type: ignore[attr-defined]
    if hasattr(target, "flat_footed_penalty"):
        try:
            target.flat_footed_penalty = 0  # type: ignore[attr-defined]
        except Exception:
            pass


def _apply_flat_footed(target, ac_penalty: int) -> None:
    _remove_flat_footed(target, source="flanking")
    status = Status(
        id="flat_footed",
        label=FLAT_FOOTED_STATUS.label,
        data={"ac_penalty": ac_penalty, "flat_footed_source": "flanking"},
    )
    adder = getattr(target, "add_status", None)
    if callable(adder):
        adder(status)
    else:
        statuses = getattr(target, "statuses", None)
        if isinstance(statuses, list):
            statuses.append(status)
    if hasattr(target, "flat_footed_penalty"):
        try:
            target.flat_footed_penalty = ac_penalty  # type: ignore[attr-defined]
        except Exception:
            pass


def refresh_flanking_statuses(game, ac_penalty: int = 2) -> None:
    """Zaktualizuj status flat_footed oraz karę do AC flankowanego celu."""
    board = getattr(game, "board", None)
    if board is None:
        return

    heroes = [h for h in getattr(game, "heroes", []) if getattr(h, "position", None) is not None]
    enemies = [e for e in getattr(game, "enemies", []) if getattr(e, "position", None) is not None]

    # Wyczyść stare efekty flankowania
    for actor in heroes + enemies:
        remover = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("flanked:")
            except Exception:
                pass

    for enemy in getattr(game, "enemies", []):
        pos = getattr(enemy, "position", None)
        flanked = is_flanked(board, pos, heroes)
        if flanked:
            _apply_flat_footed(enemy, ac_penalty)
            # kara do AC
            adder = getattr(enemy, "add_bonus", None)
            if callable(adder):
                try:
                    adder(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=ac_penalty,
                            tag="ac",
                            is_penalty=True,
                            source=f"flanked:{getattr(enemy, 'object_id', 'enemy')}",
                            label="flankowany",
                        )
                    )
                except Exception:
                    pass
        else:
            _remove_flat_footed(enemy, source="flanking")

    for hero in getattr(game, "heroes", []):
        pos = getattr(hero, "position", None)
        flanked = is_flanked(board, pos, enemies)
        if flanked:
            _apply_flat_footed(hero, ac_penalty)
            adder = getattr(hero, "add_bonus", None)
            if callable(adder):
                try:
                    adder(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=ac_penalty,
                            tag="ac",
                            is_penalty=True,
                            source=f"flanked:{getattr(hero, 'object_id', 'hero')}",
                            label="flankowany",
                        )
                    )
                except Exception:
                    pass
        else:
            _remove_flat_footed(hero, source="flanking")

    # Snagging Strike: flat-footed znika natychmiast, gdy cel nie jest już w reach ręki.
    try:
        from statuses.classes.fighter.feats.snagging_strike import cleanup_snagging_flat_footed

        cleanup_snagging_flat_footed(game)
    except Exception:
        logger.debug("Nie udało się odświeżyć statusu Snagging Strike.", exc_info=True)


def flat_footed_penalty(target) -> int:
    """Wyciągnij karę do AC ze statusu flat_footed."""
    penalty = getattr(target, "flat_footed_penalty", 0) or 0
    statuses = getattr(target, "statuses", None)
    if isinstance(statuses, list):
        for status in statuses:
            sid = status.id if isinstance(status, Status) else status
            if sid in ("flat_footed", "off_guard"):
                if isinstance(status, Status):
                    data_val = status.data.get("ac_penalty")
                    if isinstance(data_val, int):
                        penalty = max(penalty, data_val)
                else:
                    penalty = max(penalty, 0)
    return int(penalty)


def ac_with_bonuses(
    target,
    *,
    attacker=None,
    extra_bonuses: Iterable[BonusEffect] | None = None,
    include_magic: bool = False,
) -> tuple[int, int, int]:
    """Zwróć (target_ac, base_ac, modifier) z uwzględnieniem bazowego AC i bonusów runtime."""
    base_ac = getattr(target, "ac", None)
    try:
        base_ac_value = int(base_ac if base_ac is not None else 10)
    except Exception:
        base_ac_value = 10

    bonuses = list(getattr(target, "bonuses", [])) if hasattr(target, "bonuses") else []
    if extra_bonuses:
        bonuses.extend(list(extra_bonuses))

    try:
        from GameObjects.items.armor import armor_ac_bonus, get_equipped_armor

        equipped_armor = get_equipped_armor(target)
        armor_bonus = int(armor_ac_bonus(target) or 0)
        ac_includes_armor = bool(getattr(target, "ac_includes_armor_bonus", False))
        if equipped_armor is not None and armor_bonus > 0 and not ac_includes_armor:
            bonuses.append(
                BonusEffect(
                    type=BonusType.ITEM,
                    value=armor_bonus,
                    tag="ac",
                    source=f"armor:{getattr(equipped_armor, 'item_id', 'equipped')}",
                    label=str(getattr(equipped_armor, "name", "armor") or "armor"),
                )
            )
    except Exception:
        pass

    try:
        from statuses import ac_penalty_effect

        cond_eff = ac_penalty_effect(target)
        if cond_eff is not None:
            bonuses.append(cond_eff)
    except Exception:
        pass

    attacker_id = getattr(attacker, "object_id", None)
    modifier = compute_total_modifier(bonuses, "ac", attacker_id) if bonuses else 0
    if include_magic:
        modifier += compute_total_modifier(bonuses, "ac_magic", attacker_id) if bonuses else 0

    if not bonuses:
        modifier -= max(0, flat_footed_penalty(target))

    return int(base_ac_value + modifier), int(base_ac_value), int(modifier)


def effective_ac(target) -> int:
    return ac_with_bonuses(target)[0]
