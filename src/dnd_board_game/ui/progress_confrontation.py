"""Mission transport for the one-round, reputation-backed confrontation rules."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, TYPE_CHECKING

from dnd_board_game.application import reputation
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL
from dnd_board_game.inventory.magic_items import effective_ability_modifier
from dnd_board_game.rules import progress_confrontation as rules
from dnd_board_game.rules.reputation import BOOSTS
from dnd_board_game.scenarios.mission_pack import asset_url

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor
    from .exploration_app import ExplorationUiSession

ENGINE = "progress_v1"
TIER_LABELS = {"worsened": "Pogorszenie", "unchanged": "Bez dodatkowej korzyści", "complication": "Sukces z komplikacją",
               "success": "Sukces", "bonus": "Sukces +", "full": "Pełny sukces"}
BOOST_LABELS = {"plus_one": "+1 do testu · 1 reputacji", "plus_five": "+5 do testu · 3 reputacji",
                "extra_die": "Dodatkowa k20, zachowaj wyższą · 5 reputacji"}


def build(actors: tuple[Actor, ...], scene: dict[str, Any]) -> rules.Confrontation:
    participants = tuple(rules.Participant(str(actor.id), actor.name, tuple(
        rules.Approach(option["id"], option["name"], option["description"], ABILITY_LABELS_PL[option["ability"]],
                       effective_ability_modifier(actor, option["ability"]),
                       option.get("progress_dc", scene.get("progress_dc", 14)), option.get("repeatable", False))
        for option in scene["approaches"])) for actor in actors)
    return rules.Confrontation(participants, social=scene["kind"] == "npc",
                              first_test_bonus=scene.get("first_test_bonus", 0),
                              first_test_label=scene.get("first_test_label", ""))


def command(s: ExplorationUiSession, store: dict[str, Any], data: dict[str, Any]) -> dict[str, object]:
    from . import confrontation as adapter, mission_zero as mission
    current = store["current"]
    if not store["active"]:
        raise ValueError("Konfrontacja jest już zamknięta.")
    state = rules.Confrontation.from_data(current["state"])
    action = str(data.get("action", ""))
    legal = {choice["action"] for choice in payload(s, store)["board_choices"]}
    if action not in legal and not (action == "roll" and state.stage in {"check", "extra_check"}):
        raise ValueError("To działanie nie jest teraz dostępne.")
    old = state
    cost = 0
    if action == "next":
        store["active"] = False
        apply_result = not current.get("committed")
        current["committed"] = True
        adapter.write(s, store)
        if apply_result:
            mission.finish_confrontation(s, current)
            mission.autosave(s)
        return s.state_payload()
    if action == "leave":
        store["active"] = False
    elif action == "acknowledge":
        state = rules.begin(state)
    elif action == "approach":
        state = rules.choose(state, str(data.get("approach", "")))
    elif action == "roll":
        rolls = data.get("rolls")
        if not isinstance(rolls, list) or len(rolls) != 1:
            raise ValueError("Podaj jeden naturalny wynik k20.")
        state = rules.roll(state, rolls[0])
    elif action == "reputation":
        state = rules.select_boost(state, str(data.get("option", "")), reputation.read(s.state.flags).points)
    elif action == "cancel":
        state = rules.cancel(state)
    elif action == "confirm":
        state, cost = rules.confirm(state, reputation.read(s.state.flags).points)
        if cost:
            event = f"confrontation:{current['token']}:{old.actor.id}:reputation"
            s.state = replace(s.state, flags=reputation.apply(s.state.flags, event, -cost))
    elif action == "pass":
        state = rules.pass_turn(state)
    elif action == "advance":
        state = rules.advance(state)
    elif action == "cart_preview":
        current["cart_preview"] = True
    elif action == "cart_cancel":
        current["cart_preview"] = False
    elif action == "cart_exchange":
        m = mission.read(s)
        mission.exchange_cart(s, m)
        current["cart_preview"] = False
        current["committed"] = True
        store["active"] = False
        state = replace(state, stage="result", outcome="success", tier="full", last="Wóz zamieniony. Reputacja −3; bez testu i zmęczenia.")
        mission.write(s, m)
    else:
        raise ValueError("Nieznane działanie konfrontacji.")
    current["state"] = state.to_data()
    adapter.write(s, store)
    s._record("progress_confrontation_action", dict(action=action, actor=old.actor.id, previous_stage=old.stage,
              stage=state.stage, progress_before=old.progress, progress=state.progress, outcome=state.outcome,
              reputation=reputation.read(s.state.flags).points, reputation_spent=cost, input=dict(data)))
    mission.autosave(s)
    return s.state_payload()


def _result(s: ExplorationUiSession, current: dict[str, Any], state: rules.Confrontation, scene: dict[str, Any]) -> str:
    if not state.outcome:
        return ""
    name = current["mission_scene"]
    if name == "cart":
        return {"worsened": "Wóz trzeba wydobyć awaryjnie. Zmęczenie potrwa k4 + 1 rund walki.",
                "unchanged": "Wóz wydobyto awaryjnie. Rzut k4 określi liczbę rund zmęczenia.",
                "complication": "Wóz jest wolny. Wysiłek kosztuje drużynę jedną rundę zmęczenia.",
                "success": "Wóz jest wolny bez zmęczenia.", "bonus": "Wóz jest wolny bez zmęczenia. Ładunek został bezpiecznie zabezpieczony.",
                "full": "Wóz jest wolny bez zmęczenia. Cały ładunek i mocowanie osi są zabezpieczone."}.get(state.tier, scene.get(state.outcome, ""))
    result = scene.get(state.outcome, "")
    if name in {"armory", "quarters"}:
        from .mission_zero_recovery import confrontation_result
        result = confrontation_result(s, current, result)
    return f"{TIER_LABELS.get(state.tier, '')}. {result}".strip(". ")


def payload(s: ExplorationUiSession, store: dict[str, Any]) -> dict[str, Any]:
    from . import mission_zero as mission
    from .exploration_mana_board import choice
    from .board_panel_symbols import panel_icon
    current = store["current"]
    state = rules.Confrontation.from_data(current["state"])
    scene = mission.scene(s, current["mission_scene"])
    balance = reputation.read(s.state.flags).points
    options: list[dict[str, Any]] = []
    trade = bool(current.get("cart_preview"))
    if trade:
        if balance >= 20: options.append(choice(28, "cart_exchange", "Zamień wóz · koszt 3 reputacji"))
        options.append(choice(29, "cart_cancel", "Anuluj bez kosztu"))
    elif state.stage == "introduction":
        options.extend((choice(28, "acknowledge", "Wybierz podejście"), choice(29, "leave", "Wróć do misji")))
    elif state.stage == "approach":
        available = rules.available_approaches(state)
        options.extend(choice(5 + i, "approach", option.name, approach=option.id) for i, option in enumerate(state.actor.options) if option in available)
        options.extend((choice(3, "pass", "Pas · zakończ swoją kolej"), choice(29, "leave", "Wróć do misji")))
        if current["mission_scene"] == "cart" and balance >= 20:
            options.append(choice(17, "cart_preview", "Zażądaj zamiany wozu · reputacja ≥20 · koszt 3"))
    elif state.stage == "check":
        options.append(choice(29, "cancel", "Wróć do podejść"))
    elif state.stage == "summary":
        options.extend({**choice(5+i, "reputation", BOOST_LABELS[key], option=key), "selected": state.boost == key}
                       for i, (key, _, _) in enumerate(BOOSTS) if key in rules.available_boosts(state, balance))
        options.append(choice(28, "confirm", "Zapłać 5 i rzuć dodatkową k20" if state.boost == "extra_die" and not state.paid else "Zatwierdź rezultat"))
        if not state.paid: options.append(choice(29, "cancel", "Usuń wybór premii"))
    elif state.stage == "after_action":
        options.extend((choice(28, "advance", "Następny bohater"), choice(29, "leave", "Wróć do misji")))
    elif state.stage == "result":
        options.append(choice(28, "next", "Zastosuj wynik i wróć do misji"))
    rolling = state.stage in {"check", "extra_check"} and not trade
    if not rolling:
        options.extend((choice(26, "scroll", "Przewiń w dół", direction=1), choice(27, "scroll", "Przewiń w górę", direction=-1)))
    root = mission.root(s)
    approach = state.approach
    result = rules.preview(state)
    cost = 0 if state.paid else next((cost for key, cost, _ in BOOSTS if key == state.boost), 0)
    party = [dict(id=p.id, name=p.name, portrait_url=asset_url(root, f"assets/images/{p.id}.png"),
                  acted=p.id in dict(state.choices), method=dict(state.choices).get(p.id, "")) for p in state.participants]
    return dict(model="party_confrontation", engine=ENGINE, active=True, revision=store["revision"],
                phase="cart_preview" if trade else state.stage, scene=scene, actor=state.actor.id, actor_name=state.actor.name,
                image_url=asset_url(root, scene["image"]) if scene.get("image") else "", party=party,
                method=approach.name if approach else "Wybierz podejście", dc=approach.dc if approach else 14,
                round=1, approach_index=state.turn + 1, progress=state.progress, maximum=state.maximum,
                track=[dict(value=value, label="Początek" if value == 0 else TIER_LABELS[rules.tier(value, state.maximum)]) for value in range(-1, state.maximum+1)],
                approaches=[dict(id=a.id, name=a.name, description=a.description, ability=a.ability, modifier=a.modifier,
                                 dc=a.dc, repeatable=a.repeatable, slot=5+i, icon=panel_icon(5+i),
                                 available=a in rules.available_approaches(state)) for i, a in enumerate(state.actor.options)],
                reputation=dict(points=balance, social=state.social, selected=state.boost, cost=cost, paid=state.paid,
                                options=[dict(id=key, label=BOOST_LABELS[key], cost=price, bonus=bonus, slot=5+i,
                                              icon=panel_icon(5+i), available=key in rules.available_boosts(state, balance), selected=state.boost == key)
                                         for i, (key, price, bonus) in enumerate(BOOSTS)]),
                original_roll=state.original_roll, extra_roll=state.extra_roll, preview=result,
                check_modifier=state.check_modifier, last=state.last, last_total=state.last_total, last_impact=state.last_impact,
                critical=state.last_critical, outcome=state.outcome, tier=state.tier, result=_result(s, current, state, scene),
                board_choices=options, needs_resume=False, choosing_approach=state.stage=="approach", run_mode="mission",
                mana={}, setup=dict(position=scene.get("party_position", [])),
                attempt=dict(phase="roll", actor=state.actor.name, method=approach.name, dice_count=1, die=20,
                             modifier_total=state.check_modifier, modifiers=[dict(label=approach.ability, value=state.check_modifier)]) if rolling and approach else {})
