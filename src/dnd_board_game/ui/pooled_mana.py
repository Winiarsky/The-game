"""Board-first physical card reporting for the personal-pool combat profile."""
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from dnd_board_game.rules.pooled_mana import COLORS, confirm_shuffle, reveal, take, report_removed, recover, tune, release
from dnd_board_game.rules.shared_mana import sync_pool, finish_mana_action
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
from .board_panel_symbols import panel_icon, SYMBOLS
from .party_ethos import deck_instruction, deck_preparation

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession, BoardScanTarget
    from dnd_board_game.world import Coordinate

NAMES = dict(zip(COLORS, ("Czerwona", "Biała", "Zielona", "Czarna", "Niebieska")))


def view(session: ExplorationUiSession) -> dict[str, object] | None:
    state = session.combat_state
    if state is None or state.shared_mana is None or state.shared_mana.pooled is None:
        return None
    pool = state.shared_mana.pooled
    definition = session.shared_mana_declaration
    bard = definition is not None and definition.stage == "cards"
    phase = "bard" if bard else pool.phase
    choices = []
    instruction = "Pula: maks. 6 kart. Każda karta daje +1 do testów, także ataków i obron. Do odblokowania zdolności atut liczy się jako 2, inne kolory jako 1: progi 2/4/6, ładunek maks. 6. Pasywy liczą fizyczne karty. Zdolności spalają wspólną talię; pula zostaje. Przy 6 kartach nie dobierasz."
    if phase in {"setup", "drain"}:
        instruction = ("Mana drain! " if phase == "drain" else "Nowa walka. ") + deck_instruction(pool) + " Zbierz także osobiste pule, ofertę, spalone, wygasłe i uwięzione karty tej talii. Premie ładunku i efekty O wygasają; odzyskane PW zostają. Potwierdź ✓."
        choices = [dict(slot=28, command="pool_shuffle", label="Komplet przetasowany")]
        if phase == "setup":
            from .training_walkthrough import enabled
            if enabled(session):
                from .pooled_mana_training import preparation
                instruction += " " + preparation(session)
    elif phase == "release":
        cards = dict(pool.prisons).get(pool.captor, ())
        instruction = "Przeciwnik pokonany. Oddaj jego uwięzione karty na spód talii w kolejności uwięzienia: " + ", ".join(NAMES[c] for c in cards) + "."
        choices = [dict(slot=28, command="pool_release", label="Uwięziona mana oddana")]
    elif phase in {"reveal", "burn", "prison", "expire", "bard"}:
        instruction = {"reveal": "Odkryj jedną kartę z wierzchu i zgłoś jej kolor runą.",
                       "burn": f"Spal z wierzchu jeszcze {pool.pending_count} kart. Zgłaszaj kolory pojedynczo.",
                       "expire": "Koniec rundy: odłóż jedną kartę z wierzchu do wygasłych i zgłoś kolor. Nie można jej odzyskać przed mana drainem.",
                       "prison": f"Uwięź przy przeciwniku jeszcze {pool.pending_count} kart z wierzchu. Zgłaszaj kolory.",
                       "bard": "Wskaż kolory kart zgodnie z instrukcją zdolności; ✓ kończy operację."}[phase]
        if bard:
            buffer = definition.resume_arguments.get("pool_buffer", [])
            tuning = definition.ability_id == "mana_tuning"
            maximum = min(2, len(pool.deck)) if tuning else (3 if definition.ability_id == "mana_great_tuning" else 2 + definition.boosts.get("recover", 0))
            instruction = (f"Podejrzyj do dwóch wierzchnich kart i zgłoś je w wybranej kolejności (pierwsza będzie na wierzchu). {len(buffer)}/{maximum}."
                           if tuning else f"Wybierz do {maximum} spalonych kart; wrócą {'na wierzch' if definition.ability_id == 'mana_great_tuning' else 'na spód'} w zgłoszonej kolejności. Wybrano: {len(buffer)}.")
            allowed = [c for c in COLORS if len(buffer) < maximum and (tuning or pool.burned.count(c) > buffer.count(c))]
            if not tuning or len(buffer) == maximum:
                choices.append(dict(slot=28, command="pool_bard_done", label="Karty ułożone"))
            if buffer:
                choices.append(dict(slot=29, command="pool_bard_back", label="Popraw ostatni kolor"))
        else:
            known = (*pool.deck, *pool.offer, *pool.burned, *pool.expired,
                     *(c for _, cards in (*pool.pools, *pool.prisons) for c in cards))
            allowed = [c for c in COLORS if pool.deck and (pool.deck[0] == c or
                       (pool.deck[0] is None and known.count(c) < pool.composition[c]))]
        choices += [dict(slot=6 + COLORS.index(c), command="pool_color", color=c, label=NAMES[c]) for c in allowed]
    elif phase == "choose":
        instruction = "Wybierz jedną kartę do swojej puli. Druga pozostanie dla następnego bohatera."
        choices = [dict(slot=24 + i, command="pool_take", index=i, label=NAMES[c], color=c) for i, c in enumerate(pool.offer)]
    if phase == "ready" and not choices:
        from .pooled_mana_training import controls
        choices = controls(session)
    actors = {str(a.id): a.name for a in state.actors}
    hands = []
    from dnd_board_game.actors.mana_passives import color_passive_status
    for hero in pool.heroes:
        profile = hero_profile(hero)
        cards = pool.hand(hero)
        actor = next(a for a in state.actors if str(a.id) == hero)
        color_passives = {c: {**p, 'status': color_passive_status(actor, p)}
                          for c, p in profile['color_passives'].items()}
        hands.append(dict(hero=hero, name=actors.get(hero, hero), cards=list(cards),
                          total=pool.points(hero), card_count=len(cards), limit=6, trump_color=profile["trump_color"], roll_bonus=0 if pool.phase in {"setup", "drain"} else pool.roll_bonus(hero), values=pool.point_values(hero),
                          passive=profile["passive"], flaw=profile["flaw"], color_passives=color_passives, charged=pool.full(hero), legacy_overflow=len(cards)>6))
    return dict(phase=phase, copies=pool.copies, total=pool.total, composition=pool.composition, excluded=list(pool.excluded), deck=len(pool.deck),
                offer=list(pool.offer), burned=list(pool.burned), expired=list(pool.expired), prisons=dict(pool.prisons),
                hands=hands, actor=pool.actor, instruction=instruction,
                deck_preparation=deck_preparation(pool) if phase in {'setup', 'drain'} else None,
                choices=[dict(c, icon=panel_icon(c["slot"]), rune=SYMBOLS[c["slot"]][0] if c["slot"] < 26 else "✓" if c["slot"] == 28 else "↩") for c in choices])


def command(session: ExplorationUiSession, data: dict[str, object]) -> dict[str, object]:
    state = session.combat_state
    mana = state.shared_mana
    if data.get("revision") != mana.revision:
        raise ValueError("Nieaktualny wybór many.")
    pool = mana.pooled
    action = data.get("command")
    declaration = session.shared_mana_declaration
    bard = declaration is not None and declaration.stage == "cards"
    if action == "pool_shuffle":
        was_drain = pool.phase == "drain"
        if was_drain:
            from dnd_board_game.combat.shared_mana import expire_deck_effects
            state, session.active_combat_effects = expire_deck_effects(state, session.active_combat_effects)
            session.combat_state = state
        pool = confirm_shuffle(pool)
        from .pooled_mana_training import after_shuffle
        pool = after_shuffle(session, pool, was_drain=was_drain)
    elif action == "pool_release" and pool.phase == "release":
        pool = release(pool, pool.captor)
    elif action in {"pool_lesson_attack", "pool_lesson_release"}:
        from .pooled_mana_training import lesson_command
        pool = lesson_command(session, pool, action)
    elif action == "pool_take":
        pool = take(pool, data.get("index"))
        from dnd_board_game.combat.mana_charge import picked_color
        passive = hero_profile(pool.actor)["color_passives"][pool.hand(pool.actor)[-1]]
        session.combat_state = replace(session.combat_state, actors=picked_color(session.combat_state.actors, pool.actor, passive))
    elif action == "pool_color" and bard:
        color = str(data.get("color"))
        if not any(c.get("color") == color for c in view(session)["choices"]):
            raise ValueError("Ten kolor nie jest dostępny.")
        declaration.resume_arguments.setdefault("pool_buffer", []).append(color)
    elif action == "pool_color":
        color = str(data.get("color"))
        pool = reveal(pool, color) if pool.phase == "reveal" else report_removed(pool, color)
    elif action == "pool_bard_back" and bard:
        buffer = declaration.resume_arguments.get("pool_buffer", [])
        if not buffer:
            raise ValueError("Nie ma koloru do poprawienia.")
        buffer.pop()
    elif action == "pool_bard_done" and bard:
        cards = tuple(declaration.resume_arguments.get("pool_buffer", ()))
        if declaration.ability_id == "mana_tuning":
            pool = tune(pool, cards)
        else:
            limit = 3 if declaration.ability_id == "mana_great_tuning" else 2 + declaration.boosts.get("recover", 0)
            if len(cards) > limit:
                raise ValueError("Przekroczono limit odzysku.")
            pool = recover(pool, cards, top=declaration.ability_id == "mana_great_tuning")
        mana = replace(mana, pooled=pool)
        mana = finish_mana_action(mana, revision=mana.revision)
        pool = mana.pooled
        session.shared_mana_declaration = None
        from .training_tutorial import record_ability
        session.combat_state = replace(state, shared_mana=sync_pool(mana, pool))
        record_ability(session, declaration.ability_id, declaration.actor_id)
    else:
        raise ValueError("Nieznana operacja puli many.")
    updated = sync_pool(mana, pool)
    if bard and session.shared_mana_declaration is not None:
        updated = replace(updated, phase=mana.phase)
    session.combat_state = replace(session.combat_state, shared_mana=updated)
    from dnd_board_game.combat.shared_mana import synchronize_shared_effects
    session.combat_state, session.active_combat_effects = synchronize_shared_effects(session.combat_state, session.active_combat_effects)
    session.board_panel_context = None
    session._record("pooled_mana_operation", {"command": action, "phase": pool.phase, "deck": len(pool.deck),
        "actor": pool.actor, "color": data.get("color"), "choice_index": data.get("index"),
        "offer": list(pool.offer), "hand": list(pool.hand(pool.actor)), "burned": len(pool.burned),
        "imprisoned": sum(len(cards) for _, cards in pool.prisons), "cycle": pool.cycle})
    session._sync_board_leds()
    return session.state_payload()


def scan_target(session: ExplorationUiSession) -> BoardScanTarget | None:
    from .exploration_app import BoardScanTarget
    from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
    from .exploration_mana_board import MANA_LED_COLORS
    payload = view(session)
    if payload is None or not payload["choices"]:
        return None
    slots = tuple(c["slot"] for c in payload["choices"])
    colors = {c['slot']: MANA_LED_COLORS[c['color']] for c in payload['choices'] if c.get('color') in MANA_LED_COLORS}
    return BoardScanTarget(positions=tuple(panel_position(s) for s in slots),
                           feedback=panel_feedback(tuple(s for s in slots if s < 26), control_slots=tuple(s for s in slots if s >= 26), action_colors=colors),
                           empty_message=payload["instruction"])


def select_position(session: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    from dnd_board_game.hardware.board_panel import panel_position
    payload = view(session)
    choice = next((c for c in payload["choices"] if panel_position(c["slot"]) == position), None)
    if choice is None:
        raise ValueError("Wybierz podświetloną runę many.")
    return command(session, dict(choice, revision=session.combat_state.shared_mana.revision))
