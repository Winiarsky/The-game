"""Count-only physical mana, with atomic payments and explicit table acknowledgements.

Colours stay on the table. Every transition conserves the 25 physical cards;
no intermediate draw or payment can refresh the deck during an ability.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Mapping
from .pooled_mana import PooledMana
from .runes import RunePool


class ManaPhase(StrEnum):
    POOLED = "pooled"
    READY = "ready"
    RESOLVING = "resolving"
    END_TURN = "end_turn"
    DISCARD = "discard"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class SharedMana:
    deck: int = 20
    market: int = 5
    discard: int = 0
    cycle: int = 1
    exhausted: bool = False
    phase: ManaPhase = ManaPhase.READY
    revision: int = 0
    turn_actor: str = ""
    spent_this_turn: int = 0
    pending_ability: str = ""
    pending_actor: str = ""
    pending_boosts: tuple[tuple[str, int], ...] = ()
    echo_spell: str = ""
    echo_count: int = 0
    end_turn_pending: bool = False
    end_effects_applied: bool = False
    hymn_sources: tuple[str, ...] = ()
    bastion_sources: tuple[str, ...] = ()
    bastion_anchors: tuple[tuple[str, int, int, int], ...] = ()
    command_step: int = 0
    command_ally: str = ""
    command_stage: str = ""
    command_skipped: bool = False
    technique_movement: int = 0
    smoke_movement: int = 0
    attack_targets: tuple[str, ...] = ()

    pooled: PooledMana | None = None
    runes: RunePool | None = None
    rune_upkeep_actor: str = ""
    rune_upkeep_selected: str = ""
    rune_flaw_paid: bool = False
    rune_payment: tuple[str, ...] = ()
    rune_exchange: str = ""
    rune_recovery: tuple[str, ...] = ()
    rune_recovery_available: tuple[str, ...] = ()
    rune_ally_actor: str = ""
    rune_ally_payment: str = ""

    def __post_init__(self) -> None:
        for name in ("deck", "market", "discard", "cycle", "revision", "spent_this_turn", "echo_count", "command_step", "technique_movement", "smoke_movement"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"Nieprawidłowy licznik many: {name}.")
        if self.pooled is None and self.runes is None and (self.deck + self.market + self.discard != 25 or self.market > 5 or self.cycle < 1):
            raise ValueError("Wspólna mana wymaga 25 kart i najwyżej pięciu na rynku.")
        if not isinstance(self.phase, ManaPhase):
            raise ValueError("Nieznany etap wspólnej many.")
        if self.phase == ManaPhase.RESOLVING and not self.pending_ability:
            raise ValueError("Brak opłaconej zdolności.")

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["phase"] = self.phase.value
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> SharedMana:
        data = dict(payload)
        if data.get("pooled") is not None:
            data["pooled"] = PooledMana.from_payload(data["pooled"])
        if data.get("runes") is not None:
            data["runes"] = RunePool.from_payload(data["runes"])
        data["phase"] = ManaPhase(str(data.get("phase", "ready")))
        data["pending_boosts"] = tuple((str(k), int(v)) for k, v in data.get("pending_boosts", ()))
        data["attack_targets"] = tuple(data.get("attack_targets", ()))
        data["hymn_sources"] = tuple(data.get("hymn_sources", ()))
        data["bastion_sources"] = tuple(data.get("bastion_sources", ()))
        data["bastion_anchors"] = tuple(tuple(item) for item in data.get("bastion_anchors", ()))
        for name in ("rune_payment", "rune_recovery", "rune_recovery_available"):
            data[name] = tuple(data.get(name, ()))
        return cls(**data)


def _expect(state: SharedMana, revision: int, *phases: ManaPhase) -> None:
    if type(revision) is not int or revision != state.revision:
        raise ValueError("Ten wybór został już rozliczony. Odśwież widok many.")
    if state.phase not in phases:
        raise ValueError("Najpierw dokończ bieżącą operację many.")


def sync_pool(state: SharedMana, pooled: PooledMana) -> SharedMana:
    """Compatibility envelope for existing action resolvers and old saves."""
    return replace(state, pooled=pooled, deck=len(pooled.deck), market=len(pooled.hand(pooled.actor)),
                   discard=len(pooled.burned), cycle=pooled.cycle,
                   phase=ManaPhase.READY if pooled.phase == "ready" else ManaPhase.POOLED,
                   revision=state.revision + 1)


def sync_runes(state: SharedMana, runes: RunePool) -> SharedMana:
    return replace(state, runes=runes, deck=len(runes.deck), market=len(runes.offer),
                   discard=len(runes.discard), phase=ManaPhase.READY if runes.phase == "ready" else ManaPhase.POOLED,
                   revision=state.revision + 1)


def begin_mana_turn(state: SharedMana, actor_id: str, *, round_end: bool = False) -> SharedMana:
    if state.phase != ManaPhase.READY:
        raise ValueError("Przed następną turą potwierdź operację kart.")
    if state.pooled is not None:
        from .pooled_mana import start_turn
        return sync_pool(replace(state, turn_actor=actor_id, spent_this_turn=0, smoke_movement=0,
                         end_turn_pending=False, end_effects_applied=False), start_turn(state.pooled, actor_id, round_end=round_end))
    return replace(state, turn_actor=actor_id, spent_this_turn=0, smoke_movement=0,
                   end_turn_pending=False, end_effects_applied=False, revision=state.revision + 1)


def pay_mana(state: SharedMana, *, revision: int, actor_id: str,
             ability_id: str, count: int, boosts: tuple[tuple[str, int], ...] = (),
             echo_spell: bool = False, rune_payment: tuple[str, ...] | None = None,
             rune_exchange: str = "", rune_recovery: tuple[str, ...] = (),
             rune_ally_actor: str = "", rune_ally_payment: str = "", rune_surcharge: int = 0) -> SharedMana:
    _expect(state, revision, ManaPhase.READY)
    if state.runes is not None:
        from collections import Counter
        from .runes import spend_runes, validate_card_payment
        from dnd_board_game.scenarios.rune_catalog import rune_card
        card = rune_card(actor_id, ability_id)
        if card is None:
            raise ValueError("Nieznana moc runiczna.")
        free_first = card.free_first and (actor_id, ability_id + ":free") not in state.runes.used_once
        if type(rune_surcharge) is not int or not 0 <= rune_surcharge <= 2:
            raise ValueError("Nieprawidłowa dopłata runiczna skazy.")
        if actor_id == "nimra" and rune_surcharge != (min(2, state.echo_count) if state.echo_spell == ability_id else 0):
            raise ValueError("Dopłata Echa nie zgadza się z ostatnią opłaconą mocą.")
        costs = validate_card_payment(state.runes.hand(actor_id),
            card.payment(dict(boosts), free_base=free_first) + ("*",) * rune_surcharge, rune_payment)
        if count != len(costs):
            raise ValueError("Koszt runiczny nie zgadza się z kartą.")
        remaining = list(state.runes.hand(actor_id))
        for rune in costs:
            remaining.remove(rune)
        if ability_id == "mana_tuning" and (rune_exchange not in remaining or not state.runes.deck):
            raise ValueError("Wybierz dodatkową runę pozostałą po zapłacie do wymiany.")
        recovery_available = state.runes.discard if ability_id == "mana_recovery" else ()
        if ability_id == "mana_recovery":
            maximum = min(3 if dict(boosts).get("recover_more") else 2, 7-len(remaining))
            if (not rune_recovery or len(rune_recovery) > maximum
                    or Counter(rune_recovery) - Counter(recovery_available)):
                raise ValueError("Wybierz runy ze stosu sprzed zapłaty, mieszczące się na ręce.")
        if ability_id == "counterattack_command" and (rune_ally_actor == actor_id
                or rune_ally_payment not in state.runes.hand(rune_ally_actor)):
            raise ValueError("Sojusznik musi wybrać własną runę na Kontratak.")
        once = ability_id if card.once else ability_id + ":free" if free_first else ""
        runes = spend_runes(state.runes, actor_id, costs, once=once)
        return replace(sync_runes(state, runes), phase=ManaPhase.RESOLVING, pending_actor=actor_id,
                       pending_ability=ability_id, pending_boosts=boosts,
                       echo_spell=ability_id if actor_id == "nimra" else state.echo_spell,
                       echo_count=min(2, state.echo_count + 1) if actor_id == "nimra" and state.echo_spell == ability_id else 1 if actor_id == "nimra" else state.echo_count,
                       rune_flaw_paid=bool(rune_surcharge), rune_payment=costs, rune_exchange=rune_exchange, rune_recovery=rune_recovery,
                       rune_recovery_available=recovery_available, rune_ally_actor=rune_ally_actor,
                       rune_ally_payment=rune_ally_payment,
                       technique_movement={"unstoppable": 20, "blade_dance": 15}.get(ability_id, 0), attack_targets=())
    if state.pooled is not None:
        from .pooled_mana import pay_pool
        hand = state.pooled.hand(actor_id)
        if type(count) is not int or count < 0:
            raise ValueError("Nieprawidłowy koszt spalania.")
        updated = sync_pool(state, replace(pay_pool(state.pooled, actor_id, free=count == 0), burn_due=count))
        return replace(updated, phase=ManaPhase.RESOLVING, pending_actor=actor_id,
                       pending_ability=ability_id, pending_boosts=boosts,
                       spent_this_turn=state.spent_this_turn + count,
                       echo_spell=ability_id if echo_spell else state.echo_spell,
                       echo_count=(state.echo_count + 1 if state.echo_spell == ability_id else 1) if echo_spell else state.echo_count,
                       technique_movement={"unstoppable": 20, "blade_dance": 15}.get(ability_id, 0), attack_targets=())
    if type(count) is not int or not 0 <= count <= min(5, state.market):
        raise ValueError("Na rynku brakuje kart na cały koszt (maksymalnie pięć).")
    if not actor_id or not ability_id:
        raise ValueError("Wskaż autora i zdolność płatności.")
    return replace(
        state, market=state.market-count, discard=state.discard+count,
        phase=ManaPhase.RESOLVING, revision=state.revision+1,
        pending_actor=actor_id, pending_ability=ability_id, pending_boosts=boosts,
        technique_movement={"unstoppable": 20, "blade_dance": 15}.get(ability_id, 0), attack_targets=(),
        spent_this_turn=state.spent_this_turn + (count if actor_id == state.turn_actor else 0),
        echo_spell=ability_id if echo_spell else state.echo_spell,
        echo_count=(state.echo_count+1 if state.echo_spell == ability_id else 1) if echo_spell else state.echo_count,
    )


def validate_card_operation(state: SharedMana, ability_id: str, cost: int) -> None:
    """Preflight BEFORE payment, including a separate sacrifice for tuning."""
    if state.pooled is not None or state.runes is not None:
        return
    if ability_id == "mana_tuning" and (state.deck < 2 or state.market-cost < 1):
        raise ValueError("Strojenie wymaga dwóch kart talii i jednej karty rynku poza kosztem.")


def finish_mana_action(state: SharedMana, *, revision: int) -> SharedMana:
    """Acknowledge the whole ability; recoveries can use its paid cost."""
    _expect(state, revision, ManaPhase.RESOLVING)
    if state.runes is not None:
        return replace(state, phase=ManaPhase.READY, pending_ability="", pending_actor="",
                       pending_boosts=(), technique_movement=0, attack_targets=(), rune_payment=(), rune_flaw_paid=False,
                       rune_exchange="", rune_recovery=(), rune_recovery_available=(),
                       rune_ally_actor="", rune_ally_payment="", revision=state.revision + 1)
    if state.pooled is not None:
        from .pooled_mana import finish_burn
        state = sync_pool(state, finish_burn(state.pooled))
        return replace(state, pending_ability="", pending_actor="",
                       pending_boosts=(), technique_movement=0, attack_targets=(), revision=state.revision + 1)
    deck, market, discard = state.deck, state.market, state.discard
    boosts = dict(state.pending_boosts)
    if state.pending_ability == "mana_tuning":
        if deck < 2 or market < 1:
            raise ValueError("Brak kart do Strojenia rynku.")
        # Extra market discard, draw two, one to market, one to deck bottom.
        deck -= 1
        discard += 1
    elif state.pending_ability == "mana_recovery":
        amount = 2 + boosts.get("recover", 0)
        if discard < amount:
            raise ValueError("Brak kart na stosie odrzuconych.")
        discard -= amount
        deck += amount
    elif state.pending_ability == "mana_great_tuning":
        if discard < 3 or market > 2:
            raise ValueError("Brak trzech kart lub miejsc na rynku.")
        discard -= 3
        market += 3
    exhausted = state.exhausted or deck == 0
    return replace(state, deck=deck, market=market, discard=discard,
                   exhausted=exhausted,
                   phase=ManaPhase.REFRESH if deck == market == 0 else ManaPhase.READY,
                   pending_ability="", pending_actor="", pending_boosts=(), technique_movement=0, attack_targets=(),
                   revision=state.revision+1)


def request_mana_end_turn(state: SharedMana, *, revision: int) -> SharedMana:
    _expect(state, revision, ManaPhase.READY)
    return replace(state, phase=ManaPhase.END_TURN, end_turn_pending=True,
                   revision=state.revision+1)


def confirm_mana_refill(state: SharedMana, *, revision: int) -> SharedMana:
    _expect(state, revision, ManaPhase.END_TURN)
    if state.runes is not None:
        raise ValueError("Runy dobiera się wyłącznie na początku walki.")
    drawn = min(5-state.market, state.deck)
    deck, market = state.deck-drawn, state.market+drawn
    exhausted = state.exhausted or deck == 0
    phase = (ManaPhase.REFRESH if deck == market == 0 else
             ManaPhase.DISCARD if exhausted and state.spent_this_turn == 0 else ManaPhase.READY)
    return replace(state, deck=deck, market=market, exhausted=exhausted,
                   phase=phase, revision=state.revision+1)


def confirm_mana_discard(state: SharedMana, *, revision: int) -> SharedMana:
    _expect(state, revision, ManaPhase.DISCARD)
    if state.market == 0:
        raise ValueError("Rynek jest pusty.")
    return replace(state, market=state.market-1, discard=state.discard+1,
                   phase=ManaPhase.REFRESH if state.deck == 0 and state.market == 1 else ManaPhase.READY,
                   revision=state.revision+1)


def request_mana_refresh(state: SharedMana, *, revision: int) -> SharedMana:
    _expect(state, revision, ManaPhase.READY, ManaPhase.DISCARD, ManaPhase.END_TURN)
    if state.runes is not None:
        raise ValueError("Puli run nie odświeża się w trakcie walki.")
    return replace(state, phase=ManaPhase.REFRESH, revision=state.revision+1)


def confirm_mana_refresh(state: SharedMana, *, revision: int) -> SharedMana:
    _expect(state, revision, ManaPhase.REFRESH)
    return replace(state, deck=20, market=5, discard=0, cycle=state.cycle+1,
                   exhausted=False, phase=ManaPhase.READY, revision=state.revision+1, hymn_sources=(), bastion_sources=(), bastion_anchors=())
