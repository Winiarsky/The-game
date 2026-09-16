"""Finite-deck economy experiments. This layer does not approximate combat DPS."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from random import Random
from statistics import median

from dnd_board_game.rules.pooled_mana import (
    COLORS, PooledMana, attack_mana, confirm_shuffle, deck_copies, new_mana,
    pay_pool, report_removed, reveal, start_turn, take, finish_burn, recover,
)
from dnd_board_game.rules.pooled_mana_catalog import PoolAbility

POLICIES = ("basic_only", "spend_early", "save_ultimate", "adaptive", "cooperative", "overburn", "sustain")


def available_abilities(catalog: dict[str, object], hero: str, hand: tuple[str, ...]) -> list[PoolAbility]:
    result = []
    for key, a in catalog["abilities"].items():
        if a["hero"] != hero or a["free"]:
            continue
        ability = PoolAbility(key, hero, a["minimum"], tuple(a["required"].items()), a["free"])
        try:
            ability.validate(hand, catalog["heroes"][hero]["values"])
        except ValueError:
            continue
        result.append(ability)
    return result


def prepare(state: PooledMana, rng: Random, metrics: Counter[str]) -> PooledMana:
    while state.phase in {"burn", "prison", "expire"}:
        metrics["expired_cards" if state.phase == "expire" else "removed_cards"] += 1
        state = report_removed(state, state.deck[0])
    if state.phase in {"setup", "drain"}:
        if state.phase == "drain":
            metrics["drains"] += 1
            metrics["cards_lost"] += sum(len(hand) for _, hand in state.pools)
            metrics["points_lost"] += sum(state.points(h) for h in state.heroes)
        cards = list(COLORS) * state.copies
        rng.shuffle(cards)
        state = confirm_shuffle(state, tuple(cards))
    while state.phase == "reveal":
        state = reveal(state, state.deck[0])
        metrics["revealed"] += 1
    return state


def choose_index(state: PooledMana, catalog: dict[str, object], policy: str, next_hero: str) -> int:
    """Uses only the public offer, hands and per-hero values, never deck order."""
    values = catalog["heroes"][state.actor]["values"]
    next_values = catalog["heroes"][next_hero]["values"]
    def rank(index: int) -> tuple[int, int]:
        color = state.offer[index]
        hand = (*state.hand(state.actor), color)
        choices = available_abilities(catalog, state.actor, hand)
        best = max((a.minimum for a in choices), default=0)
        leave = state.offer[1 - index] if len(state.offer) == 2 else color
        cooperation = next_values[leave] if policy == "cooperative" and next_hero != state.actor else 0
        return best + cooperation, values[color]
    return max(range(len(state.offer)), key=rank)


def run_trial(catalog: dict[str, object], heroes: tuple[str, ...], policy: str,
              copies: int, rounds: int, pressure: str, seed: int) -> dict[str, object]:
    rng = Random(seed)
    metrics: Counter[str] = Counter()
    state = new_mana(heroes, heroes[0], copies=copies, values={h: catalog["heroes"][h]["values"] for h in heroes})
    reached: dict[str, int] = {}
    uses: Counter[str] = Counter()
    for round_index in range(rounds):
        for index, hero in enumerate(heroes):
            if round_index or index:
                state = prepare(state, rng, metrics)
                state = start_turn(state, hero, round_end=index == 0 and round_index > 0)
            state = prepare(state, rng, metrics)
            if state.phase == "choose":
                state = take(state, choose_index(state, catalog, policy, heroes[(index + 1) % len(heroes)]))
            elif state.phase != "ready":
                raise ValueError("Nieukończony dobór w symulacji.")
            if state.points(hero) >= 21:
                metrics["fully_charged_turns"] += 1
            metrics["hero_turns"] += 1
            metrics["held_card_turns"] += sum(len(hand) for _, hand in state.pools)
            options = available_abilities(catalog, hero, state.hand(hero))
            ultimates = [a for a in options if a.minimum >= 21]
            if ultimates:
                reached.setdefault(hero, round_index + 1)
                metrics["ultimate_available_turns"] += 1
            candidate = None
            if policy == "spend_early" and options:
                candidate = min(options, key=lambda a: (a.minimum, a.id))
            elif policy != "basic_only" and ultimates:
                candidate = max(ultimates, key=lambda a: (a.minimum, a.id))
            elif policy in {"adaptive", "cooperative", "overburn", "sustain"} and options:
                if len(state.deck) <= len(heroes) + 2 or max(a.minimum for a in options) >= 12:
                    candidate = max(options, key=lambda a: (a.minimum, a.id))
            if policy == "sustain" and len(state.deck) < len(heroes) * 2 + 3:
                candidate = next((a for a in options if a.id in {"mana_recovery", "mana_great_tuning"} and state.burned), None)
            if candidate:
                hand = state.hand(hero)
                metrics["ability_uses"] += 1
                metrics["overspend_points"] += sum(catalog["heroes"][hero]["values"][c] for c in hand) - candidate.minimum
                uses[candidate.id] += 1
                cost = catalog["abilities"][candidate.id]["burn"]
                if candidate.id in {"mana_recovery", "mana_great_tuning"}:
                    amount = 3 if candidate.id == "mana_great_tuning" else 2
                    cards = state.burned[:amount]
                    state = recover(state, cards, top=candidate.id == "mana_great_tuning")
                    metrics["recovered_cards"] += len(cards)
                elif policy == "overburn":
                    cost += 2
                    metrics["boosted_uses"] += 1
                if hero == "lorian" and "F" in hand and cost:
                    cost = max(1, cost - 1)
                state = replace(pay_pool(state, hero, free=cost == 0), burn_due=cost)
                metrics["spent_cards"] += cost
                state = finish_burn(state)
                state = prepare(state, rng, metrics)
            else:
                metrics["basic_attacks"] += 1
        if pressure != "none":
            state = start_turn(state, "enemy")
            source = "offer" if pressure == "offer" else "deck"
            state = attack_mana(state, source, 1 if source == "offer" else 2,
                                captor="enemy" if pressure == "prison" else "")
            while state.phase in {"burn", "prison"}:
                state = report_removed(state, state.deck[0])
                metrics["removed_cards"] += 1
            state = prepare(state, rng, metrics)
    return dict(metrics=metrics, reached=reached, uses=uses, points_lost=metrics["points_lost"],
                not_reached=len(heroes) - len(reached))


def compare(catalog: dict[str, object], samples: int, rounds: int, seed: int,
            sizes: tuple[int, ...] = (1, 3, 5, 7)) -> list[dict[str, object]]:
    heroes = tuple(catalog["heroes"])
    rows = []
    for size in sizes:
        for copies in sorted({5, max(5, size + 1), deck_copies(size), max(5, 2 * size + 1)}):
            for pressure in ("none", "deck", "offer", "prison"):
                for policy in POLICIES:
                    sums: Counter[str] = Counter()
                    uses: Counter[str] = Counter()
                    reached = []
                    per_hero: dict[str, Counter[str]] = {h: Counter() for h in heroes}
                    for sample in range(samples):
                        party = tuple(heroes[(sample + i) % len(heroes)] for i in range(size))
                        trial = run_trial(catalog, party, policy, copies, rounds, pressure, seed + sample * 1009)
                        sums.update(trial["metrics"])
                        uses.update(trial["uses"])
                        sums["not_reached"] += trial["not_reached"]
                        reached.extend(trial["reached"].values())
                        for h in party:
                            per_hero[h]["trials"] += 1
                            per_hero[h]["reached"] += h in trial["reached"]
                    rows.append(dict(players=size, cards=copies * 5, pressure=pressure, policy=policy,
                        trials=samples, rounds=rounds, metrics=dict(sums), uses=dict(uses),
                        hero_coverage={h: dict(v) for h, v in per_hero.items()},
                        ultimate_median_when_reached=median(reached) if reached else None,
                        ultimate_unreached_fraction=sums["not_reached"] / (size * samples),
                        drains_per_trial=sums["drains"] / samples,
                        basic_attack_fraction=sums["basic_attacks"] / sums["hero_turns"],
                        fully_charged_fraction=sums["fully_charged_turns"] / sums["hero_turns"],
                        ability_uses_per_hero=sums["ability_uses"] / (samples * size),
                        held_cards_mean=sums["held_card_turns"] / sums["hero_turns"],
                        overspend_mean_when_paid=sums["overspend_points"] / sum(uses.values()) if uses else None,
                        points_lost_per_drain=sums["points_lost"] / sums["drains"] if sums["drains"] else None))
    return rows
