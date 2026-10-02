"""Server-owned charge combat UI, physical controls and transactional commands."""
from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any, TYPE_CHECKING

from dnd_board_game.actors import Faction
from dnd_board_game.application.resonance_combat import encounter_engine, charge_weapon
from dnd_board_game.combat.charge_encounter import ChargeEncounter, hymn_source, point
from dnd_board_game.combat.stealth import HiddenState
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.resonance_feedback import ResonanceBoardView, resonance_feedback
from dnd_board_game.rules.resonance import bonus_summary, cards_for
from dnd_board_game.world import Coordinate
from dnd_board_game.world.charge_movement import distance, playable
from .board_panel_symbols import SYMBOLS, rune_slot, panel_icon

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession, BoardScanTarget

LABELS = {"move": "Ruch", "attack": "Atak bronią", "item": "Mikstura", "focus": "Skupienie", "end": "Koniec tury"}
STATUS_NAMES = {"rage": "Runiczny szał", "prone": "Powalony", "fear": "Najbliższy atak z utrudnieniem", "slow": "Połowa ruchu",
                "root": "Brak zwykłego ruchu", "round_root": "Więzy mroku · brak zwykłego ruchu w następnej rundzie", "bless": "Pieczęć łaski · +1 atak / obrona",
                "arcane": "Tarcza arkanów · +2 KP", "broken": "Przełamana obrona · −2 KP"}


def _relations(e: ChargeEncounter) -> bool:
    """An active legacy encounter keeps its original controls and summaries."""
    return e.is_relations


def _card_details(e: ChargeEncounter, card: Any) -> list[str]:
    if not _relations(e):
        return [card.target, card.requirements]
    details = [f"Koszt karty: {card.cost} ładunków · {card.budget}", card.target, card.requirements]
    if card.requires_resonance:
        details.append("Wyładowanie: " + " + ".join(card.requires_resonance) + "; wymaga zgodnego przejścia i kończy Rezonans.")
    details.extend(" + ".join(bonus["requires"]) + ": " + bonus["text"] for bonus in card.resonance_bonuses)
    return [line for line in details if line]


def _status_deadline(e: ChargeEncounter, status: dict[str, Any]) -> str:
    if status.get("until_start"):
        return f" · do początku tury: {e.actor(status['until_start']).name}"
    if status.get("until_end"):
        return f" · do końca tury: {e.actor(status['until_end']).name}"
    if "remaining" in status:
        return f" · {status['remaining']} tur"
    return ""


def _status_text(e: ChargeEncounter, status: dict[str, Any]) -> str:
    kind, value = status["type"], status.get("value", 0)
    if kind == "round_root":
        movement = "zwykłego ruchu" if _relations(e) else "ruchu"
        return f"Więzy mroku · brak {movement} w rundzie {status['round']}"
    if kind.startswith("ward:"):
        name = f"Ochrona · +{value} KP"
    elif kind == "arcane" and _relations(e):
        name = f"Tarcza arkanów · +{status.get('value', 2)} KP"
    elif kind == "bless" and _relations(e):
        name = f"Pieczęć łaski · +{status.get('value', 1)} atak / obrona"
    elif kind == "root" and not _relations(e):
        name = "Unieruchomiony"
    elif kind == "move_penalty":
        name = f"Spowolnienie · −{value} ruchu"
    elif kind == "next_attack":
        name = "Najbliższy atak z przewagą"
    elif kind in {"temporary", "prevention", "hymn"}:
        return ""  # The current pool or Hymn die is shown once below.
    else:
        name = status.get("name") or STATUS_NAMES.get(kind, kind)
    return name + _status_deadline(e, status)


def active(session: ExplorationUiSession) -> bool:
    return bool(session.combat_state and session.combat_state.resonance)


def engine(session: ExplorationUiSession) -> ChargeEncounter:
    encounter = session._active_encounter()
    if not active(session) or encounter is None:
        raise ValueError("Brak aktywnej walki z Rezonansem.")
    e = encounter_engine(session.combat_state, encounter, effects=tuple(effect for effect in session.active_combat_effects if effect.kind == "scenario_fatigue"))
    from .mission_zero import enabled, available_potions, root
    if enabled(session):
        from dnd_board_game.scenarios.mission_pack import read_json
        definitions = read_json(root(session), "mechanics/items.json")
        mission_items = tuple(dict(id=item.id, owner=str(owner.id) if owner else "", name=item.name,
                                   count=definitions[item.id.removeprefix("mission_")]["dice"],
                                   sides=definitions[item.id.removeprefix("mission_")]["sides"],
                                   modifier=definitions[item.id.removeprefix("mission_")]["bonus"])
                              for owner, item in available_potions(session))
        e.items = (*mission_items, *(item for item in e.items if item["id"] not in {"mission_potion", "mission_weak_potion"}))
    return e


def controls(e: ChargeEncounter) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    def add(slot: int, label: str, command: str, **extra: Any) -> None:
        result[slot] = dict(slot=slot, label=label, command=command, **extra)
    s, task = e.s, e.s.task
    if s.inspected:
        add(26, "Następna strona", "page", delta=1)
        add(27, "Poprzednia strona", "page", delta=-1)
        add(29, "Wróć do walki", "back")
        return result
    if s.phase == "idle":
        if e.active.faction == Faction.ENEMY:
            add(28, "Tura przeciwnika", "accept")
        else:
            for slot, action_id in ((0, "move"), (1, "attack"), (2, "item"), (rune_slot("Spirala"), "focus")):
                if not e.unavailable(action_id):
                    add(slot, LABELS[action_id], "choose", id=action_id)
            for card in e.cards():
                if not e.unavailable(card.id):
                    add(rune_slot(card.rune), card.name, "choose", id=card.id)
            add(3, "Koniec tury", "end")
    elif s.phase == "preview":
        card = e.card(s.preview["id"])
        if card and not _relations(e):
            add(26, f"Wzmocniona · {e.price(card, 'enhanced', s.preview['targets'])}", "mode", mode="enhanced")
            add(27, f"Podstawowa · {e.price(card, 'base', s.preview['targets'])}", "mode", mode="base")
        if s.preview["id"] == "item" and len(e.items) > 1:
            add(26, "Następna mikstura", "item", delta=1)
            add(27, "Poprzednia mikstura", "item", delta=-1)
        if s.preview["id"] in {"force_wave", "flame_fan"} and s.preview["center"] is not None and not s.preview["exclude_chosen"]:
            add(28, "Nie wyłączaj żadnego pola", "exclude", actor=None)
        elif e.ready() and not p_rejected(e):
            add(28, "Zatwierdź", "accept")
        add(29, "Wróć", "back")
    elif task:
        kind = task["type"]
        if kind == "roll":
            if e.actor(task["actor"]).faction == Faction.ENEMY:
                add(28, "Rozstrzygnij rzut przeciwnika", "accept")
            else:
                add(26, "Zwiększ wynik", "adjust", delta=1)
                add(27, "Zmniejsz wynik", "adjust", delta=-1)
                add(28, "Zatwierdź kość", "accept")
        elif kind in {"enemy-result", "enemy-move", "correction"}:
            add(28, "Dalej" if kind == "enemy-result" else "Figurka ustawiona", "accept")
        elif kind in {"recover", "hymn", "opportunity"}:
            hymn_label = f"Dodaj 1k{e.hymn_sides(task['actor'])}" if _relations(e) and kind == "hymn" else "Dodaj 1k6"
            add(28, {"recover": "Odzyskaj 1k4", "hymn": hymn_label, "opportunity": "Wykonaj atak"}[kind], "accept")
            add(29, "Pomiń", "back")
        elif kind == "bonus_target":
            if task.get("target"):
                add(28, "Potwierdź sojusznika", "accept")
            add(29, "Pomiń dodatkowe leczenie", "back")
        elif kind == "relocate":
            if task.get("destination") is not None:
                add(28, "Potwierdź przestawienie", "accept")
                add(29, "Zmień pole", "back")
    elif s.phase in {"result", "end-preview", "finished"}:
        add(28, "Zakończ walkę" if s.phase == "finished" else "Zakończ turę" if s.phase == "end-preview" else "Dalej", "accept")
        if s.phase == "end-preview":
            add(29, "Wróć", "back")
    add(25, "Informacje o postaci", "info")
    return result


def actor_view(e: ChargeEncounter, actor_id: str) -> dict[str, Any]:
    from dnd_board_game.combat.conditions import condition_definition
    from dnd_board_game.inventory.magic_items import effective_ability_score
    a, f = e.actor(actor_id), e.fighter(actor_id)
    statuses = [text for status in f.statuses if (text := _status_text(e, status))]
    for source, fighter in e.s.fighters.items():
        if fighter.mark == actor_id:
            statuses.append(f"Piętno łowcy · {e.actor(source).name}")
    for condition in e.original.condition_states:
        if condition.actor_id == actor_id:
            label = condition_definition(condition.condition).label
            source = e.actors.get(str(condition.source_actor_id))
            statuses.append(label + (f" · {source.name}" if source else ""))
    if e.shielded(actor_id):
        statuses.append("Żywa osłona · +1 KP")
    cover = e.cover(actor_id)
    if cover.cover_bonus:
        statuses.append(f"Osłona terenu · +{cover.cover_bonus} KP · {', '.join(cover.cover_sources)}")
    if actor_id in e.original.enemy_ai.escaped_actor_ids:
        statuses.append("Uciekł z walki")
    if f.move_locked:
        statuses.append("Zwykły ruch niedostępny" if _relations(e) else "Ruch wykorzystany")
    if f.hidden:
        statuses.append("Ukrycie przed: "+", ".join(e.actor(key).name for key in f.hidden))
    if hymn_source(a):
        statuses.append(f"Hymn odwagi · 1k{e.hymn_sides(actor_id) if _relations(e) else 6} do wykorzystania")
    temporary_hp = max(f.cup, a.temp_hp) if _relations(e) else f.cup
    if temporary_hp:
        deadline = _status_deadline(e, e.status(actor_id, "temporary") or {}) if f.cup >= a.temp_hp else ""
        statuses.append(f"Tymczasowe PW: {temporary_hp}{deadline}" if _relations(e) else f"Kielich {f.cup}/{2*e.bonus(actor_id, 'Kielich')}")
    if f.shield:
        deadline = _status_deadline(e, e.status(actor_id, "prevention") or {})
        statuses.append(f"Osłona obrażeń: {f.shield} · bez psychicznych{deadline}" if _relations(e) else f"Osłona {f.shield}/{2*e.bonus(actor_id, 'Klepsydra')}")
    if a.hp <= 0:
        statuses.append("Martwy" if a.death_saves.dead else "Nieprzytomny")
    weapon = e.weapons.get(actor_id)
    traits = [weapon.name, f"Zasięg broni: {weapon.range} pól"] if weapon else []
    return dict(id=actor_id, name=a.name, hp=a.hp, max_hp=a.max_hp, ac=e.ac(actor_id), charges=f.charges,
                cover_bonus=cover.cover_bonus, cover_sources=list(cover.cover_sources),
                ability_scores={key: effective_ability_score(a, key) for key in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")},
                traits=traits,
                hero=a.faction == Faction.ALLY, position=list(a.position), statuses=statuses, active=actor_id == str(e.active.id),
                member=False if _relations(e) else e.member(actor_id), portrait_url="", movement=e.movement(actor_id),
                ordinary=f.ordinary, special=f.special, reaction=f.reaction)


def p_rejected(e: ChargeEncounter) -> dict[str, str] | None:
    return (e.s.preview or {}).get("rejected_target")


def decision(e: ChargeEncounter) -> dict[str, Any]:
    s, task, p = e.s, e.s.task, e.s.preview
    result: dict[str, Any] = dict(title="Wybierz akcję", body="", details=[])
    if s.inspected:
        actor_id = str(e.active.id) if s.inspected == "active" else s.inspected
        hero = e.catalog["heroes"].get(actor_id, {})
        a = actor_view(e, actor_id)
        pages = [dict(title=a["name"], body=" · ".join(a["statuses"][i:i+3]) or "Brak dodatkowych stanów.", details=[])
                 for i in range(0, max(1, len(a["statuses"])), 3)]
        for key in ("passive", "flaw"):
            if key in hero:
                pages.append(dict(title=hero[key]["name"], body=hero[key]["description"], details=[]))
        if hero:
            pages.append(dict(title="Odzysk klasowy · 1k4", body="Raz na rundę, gdy:", details=hero["regeneration"]))
            for card in cards_for(e.catalog, actor_id):
                details = _card_details(e, card)
                pages.extend(dict(title=card.name, body=card.effect if i == 0 else "Warunki i premie tej mocy.", details=details[i:i+3])
                             for i in range(0, max(1, len(details)), 3))
        inventory = e.actor(actor_id).inventory
        for i in range(0, len(inventory), 6):
            pages.append(dict(title="Ekwipunek", body="", details=[f"{item.name} ×{item.quantity}" for item in inventory[i:i+6]]))
        page = s.info_page % len(pages)
        return dict(pages[page], page=page+1, pages=len(pages), inspected=actor_id, actor=actor_id)
    if s.phase == "preview":
        card = e.card(p["id"])
        result.update(title=card.name if card else LABELS.get(p["id"], p["id"]), body=card.effect if card else "Wybierz podświetlone pole i potwierdź.")
        if card:
            if _relations(e):
                result.update(cost=e.price(card, targets=p["targets"]), budget=card.budget, rune=card.rune,
                              warning=e.unavailable(card.id), resonance=e.resonance_preview(card, p["targets"]))
            else:
                result.update(mode=p["mode"], base_cost=e.price(card, "base", p["targets"]), enhanced_cost=e.price(card, "enhanced", p["targets"]), budget=card.budget,
                              warning=e.unavailable(card.id, p["mode"]), rune=card.rune)
        if p["id"] == "focus":
            result["body"] = "Wykorzystaj akcję specjalną i odzyskaj 1k20 ładunków, do 20. Skupienie kończy Rezonans."
        if p["id"] == "item":
            item = p["item"]
            result.update(title=item["name"], body=f"Leczenie {item['count']}k{item['sides']} + {item['modifier']}. Zużywa miksturę i akcję ataku / przedmiotu. Możesz wskazać siebie albo sąsiadującego sojusznika.", item_choices=len(e.items))
        if p["id"] in {"rage", "second_wind", "hide", "focus"}:
            result["prompt"] = (f"Działa na postać: {e.active.name}. Potwierdź ✓." if e.ready()
                                else "Wskaż własne podświetlone pole, aby poprawić wybór, albo wróć ↩.")
        elif p["id"] in {"flame_fan", "force_wave"} and p["center"] is not None and not p["exclude_chosen"]:
            result["prompt"] = "Precyzyjny splot: wskaż podświetloną postać do wyłączenia albo wybierz „Nie wyłączaj żadnego pola”."
        elif p["id"] == "guard_vault":
            result["prompt"] = "Wybierz wolne pole przy wybranym wrogu." if p["targets"] else "Wybierz podświetlonego wroga."
        elif p["destination"]:
            result["prompt"] = "Niebieskie pola: zasięg, żółte: trasa, zielone: cel. Możesz wybrać inne pole; ✓ potwierdza ruch."
        else:
            result["prompt"] = "Wybierz cel na planszy." if not e.ready() else "Wybór gotowy do zatwierdzenia."
        if p["targets"]:
            result["targets"] = [e.actor(t).name for t in p["targets"]]
        result["target_ids"] = list(p["targets"])
        if rejected := p_rejected(e):
            result.update(warning=rejected["reason"], target_ids=[rejected["target"]], rejected_target=True,
                          targets=[], prompt="Wybierz legalny, podświetlony cel. Akcja nie została zużyta.")
    elif task:
        kind = task["type"]
        result.update(title=task.get("label", "Rozpatrywanie akcji"), body="", actor=task.get("actor"))
        if kind == "roll":
            enemy = e.actor(task["actor"]).faction == Faction.ENEMY
            result.update(enemy=enemy, title="Atak okazyjny przeciwnika" if enemy and task.get("power") == "opportunity" else task["label"])
            if enemy:
                result["body"] = f"{e.actor(task['actor']).name} wykonuje rzut automatycznie po zatwierdzeniu."
            else:
                dice = e.roll_dice()
                index = len(task.get("dice_results", []))
                result.update(die=dict(index=index, total=len(dice), sides=dice[index]["sides"], value=s.die_value, label=dice[index]["label"], accepted=task.get("dice_results", [])))
                result["body"] = "Rzuć jedną kością i ustaw jej wynik."
            result.update(modifier=task.get("modifier", 0), modifier_components=task.get("modifier_components", []),
                          dc=task.get("dc") if task["parts"][0]["sides"] == 20 else None, mode=task.get("mode", "normal"))
            if task.get("cover_bonus", 0):
                benefit = "KP celu" if task.get("outcome") == "attack" else "do obrony"
                result["cover_text"] = f"Osłona: +{task['cover_bonus']} {benefit} · " + ", ".join(task.get("cover_sources", []))
        elif kind == "enemy-result":
            result.update(title="Wynik przeciwnika", rolls=task["rolls"])
        elif kind in {"enemy-move", "correction"}:
            result.update(body=task["label"], title="Ruch przeciwnika" if kind == "enemy-move" else "Ruch przerwany")
        elif kind == "recover":
            result.update(title=f"{e.actor(task['actor']).name} · odzysk klasowy", body=e.fighter(task["actor"]).regeneration_reason)
        elif kind == "hymn":
            sides = e.hymn_sides(task["actor"]) if _relations(e) else 6
            result.update(title="Dodać kość Hymnu odwagi?", body=f"Wynik {task['total']} · {'sukces' if task['success'] else 'porażka'}. Możesz dodać 1k{sides} albo zachować kość.")
        elif kind == "opportunity":
            result.update(title="Twój atak okazyjny", body=f"{e.actor(task['actor']).name} może zaatakować {e.actor(task['target']).name}.")
        elif kind == "relocate":
            result["body"] = f"{e.actor(task['target']).name}: wybierz podświetlone pole, przestaw figurkę i potwierdź."
        elif kind == "bonus_target":
            result.update(title="Żar odnowy · dodatkowe leczenie", actor=task["source"],
                          body="Wybierz podświetlonego sojusznika przy Garranie i potwierdź, aby wykonać dodatkowy rzut leczenia.")
            if task.get("target"):
                result["targets"] = [e.actor(task["target"]).name]
    elif s.phase == "result":
        result.update(title="Podsumowanie akcji", body="", details=(s.action or {}).get("results", []))
    elif s.phase == "end-preview":
        end_reason = "mocy runicznej" if _relations(e) else "mocy wzmocnionej"
        result.update(title="Zakończyć turę?", body="Niewykorzystane akcje przepadną." + (f" Rezonans zakończy się: w tej turze nie użyto {end_reason}." if e.active.hp > 0 and not e.fighter().continued and s.chain else ""))
    elif s.phase == "finished":
        result.update(title="Koniec walki", body="Zatwierdź, aby przejść do wyniku starcia.")
    elif e.active.faction == Faction.ENEMY:
        result.update(title=f"Tura: {e.active.name}", body="Zatwierdź zamiar przeciwnika. Aplikacja wykona jego rzuty.")
    if task or s.phase == "result":
        result["target_ids"] = list(dict.fromkeys([task["target"]] if task and task.get("target")
                                                  else (s.action or {}).get("targets", [])))
    return result


def presentation(e: ChargeEncounter) -> tuple[dict[str, Any], ResonanceBoardView]:
    control = controls(e)
    p, task = e.s.preview, e.s.task
    fields = [a.position for a in e.board_actors()] if e.s.inspected else e.available_fields()
    selected = tuple(e.actor(t).position for t in p["targets"]) if p else ((e.actor(task["target"]).position,) if task and task["type"] == "bonus_target" and task.get("target") else ())
    path = tuple(point(pos) for pos in (p or task or {}).get("path", {}).get("cells", ())) if (p or task or {}).get("path") else ()
    destination = point((p or task)["destination"]) if (p or task or {}).get("destination") is not None else None
    area: tuple[Coordinate, ...] = ()
    if p and p["center"] is not None:
        radius = 1 if p["id"] == "flame_fan" else 2
        center = point(p["center"])
        area = tuple(Coordinate(x, y) for y in range(center.row-radius, center.row+radius+1) for x in range(center.col-radius, center.col+radius+1)
                     if playable(e.board, Coordinate(x, y)))
    focus_id = (task or {}).get("actor") or (task or {}).get("target")
    focus = e.actor(focus_id).position if focus_id in e.actors else None
    enemy = bool(focus_id in e.actors and e.actor(focus_id).faction == Faction.ENEMY)
    outcome = task["rolls"][0]["success"] if task and task["type"] == "enemy-result" else None
    actor_id = str(e.active.id)
    relations = _relations(e)
    chain = dict(entries=[asdict(entry) for entry in e.s.chain.entries], members=e.s.chain.members,
                 bonuses=[] if relations else bonus_summary(e.counts())) if e.s.chain else None
    if chain and relations:
        chain["next_runes"] = e.next_runes()
    powers = []
    for card in e.cards():
        power = dict(asdict(card), slot=rune_slot(card.rune), disabled=e.unavailable(card.id))
        if relations:
            power.pop("base_cost")
            power.pop("enhanced_cost")
            power.update(cost=e.price(card), resonance=e.resonance_preview(card))
        powers.append(power)
    illegal_ids = [key for key in e.target_candidates() if key not in e.legal_targets()] if not e.s.inspected else []
    basic_actions = [dict(slot=slot, id=action, command="choose", label=LABELS[action], disabled=e.unavailable(action))
                     for slot, action in ((0, "move"), (1, "attack"), (2, "item"), (rune_slot("Spirala"), "focus"))]
    view = dict(revision=e.s.revision, phase=e.s.phase, round=e.s.round, active=actor_id,
                profile=e.catalog["profile"], relations=relations,
                actors=[actor_view(e, key) for key in e.s.order], decision=decision(e), controls=list(control.values()), icons={str(slot): panel_icon(slot) for slot in range(30)},
                legal_positions=[list(p) for p in fields], history=e.s.history[:30],
                chain=chain, powers=powers, basic_actions=basic_actions,
                illegal_positions=[list(e.actor(key).position) for key in illegal_ids],
                rune_icons={name: panel_icon(rune_slot(name)) for name in (*e.catalog["rules"]["starter_runes"], *e.catalog["rules"].get("reserved_runes", []))},
                reserved_runes=e.catalog["rules"].get("reserved_runes", []))
    selected_slot = None
    if p:
        selected_card = e.card(p["id"])
        selected_slot = rune_slot(selected_card.rune) if selected_card else {"move": 0, "attack": 1, "item": 2, "focus": rune_slot("Spirala")}.get(p["id"])
    board_view = ResonanceBoardView(active=e.active.position, legal=tuple(fields), selected=selected, path=path, destination=destination,
        illegal=tuple(e.actor(key).position for key in illegal_ids),
        area=area, excluded=e.actor(p["exclude"]).position if p and p["exclude"] else None, focus=focus, focus_result=outcome, enemy=enemy,
        action_slots=tuple(slot for slot in control if slot < 26), control_slots=tuple(slot for slot in control if slot >= 26),
        selected_slot=selected_slot,
        action_cues=tuple((power["slot"], "locked" if power["disabled"] else power["resonance"]["transition"])
                          for power in powers) if relations and e.s.phase == "idle" and not e.s.inspected else (),
        legal_kind="movement" if not e.s.inspected and ((task and task["type"] == "relocate") or
            (p and (p["id"] in {"move", "misty_step"} or p["id"] == "skirmish_shot" and not p["destination"] or
                    p["id"] == "guard_vault" and p["targets"]))) else "target")
    return view, board_view


def payload(session: ExplorationUiSession) -> dict[str, Any]:
    return presentation(engine(session))[0]


def scan_target(session: ExplorationUiSession) -> BoardScanTarget:
    from .exploration_app import BoardScanTarget
    view, board = presentation(engine(session))
    positions = (*board.legal, *board.illegal, *(panel_position(c["slot"]) for c in view["controls"]))
    return BoardScanTarget(positions=tuple(dict.fromkeys(positions)), feedback=resonance_feedback(board), empty_message=view["decision"]["title"])


def select_position(session: ExplorationUiSession, position: Coordinate) -> dict[str, Any]:
    e = engine(session)
    if position.col == 19:
        choice = controls(e).get(29-position.row)
        if not choice:
            raise ValueError("Ten przycisk nie jest teraz dostępny.")
        data = dict(choice)
    else:
        data = dict(command="select", position=list(position))
    return command(session, dict(data, revision=e.s.revision))


def _rejection_text(session: ExplorationUiSession, e: ChargeEncounter, target_id: str, reason: str) -> str:
    """Name a mapped obstacle only when it actually blocks the shot's line."""
    from dnd_board_game.world.line_of_sight import bresenham_line, line_of_sight_clear
    p = e.s.preview or {}
    origin = point(p["destination"]) if p.get("id") == "skirmish_shot" and p.get("destination") else e.active.position
    target = e.actor(target_id)
    encounter = session._active_encounter()
    if encounter and not line_of_sight_clear(e.board, origin, target.position) and ("widocz" in reason.lower() or "zasł" in reason.lower()):
        blocked = {cell for cell in bresenham_line(origin, target.position)[1:-1] if e.board.terrain_at(cell).blocks_movement}
        obstacles = list(dict.fromkeys(obj.name for obj in encounter.scene_objects if blocked.intersection(obj.positions)))
        if obstacles:
            reason += " Przeszkoda: " + ", ".join(obstacles) + "."
    return f"Cel nielegalny — {target.name}: {reason}"


def plan_enemy(session: ExplorationUiSession, e: ChargeEncounter) -> bool:
    encounter = session._active_encounter()
    state = e.combat_state()
    # Feed current sight relations and reduced movement into the existing AI.
    planner_actors = tuple(replace(a, speed_feet=e.movement(str(a.id))*5) if a.id == e.active.id else a for a in state.actors)
    planner = replace(state, actors=planner_actors, hidden_states=tuple(HiddenState(key, 0, tuple(f.hidden)) for key, f in e.s.fighters.items() if f.hidden))
    transition = session.enemy_turn_flow.plan(state=planner, board=encounter.board,
        attack_sources_by_actor=encounter.attack_sources_by_actor, attack_source_options_by_actor=encounter.attack_source_options_by_actor,
        multiattack_sources_by_actor=encounter.multiattack_sources_by_actor, scene_objects=encounter.scene_objects,
        ai_profile=encounter.enemy_ai_profile, ai_roles=dict(encounter.enemy_ai_roles), ai_zone_positions=dict(encounter.enemy_ai_zone_positions), active_effects=())
    intent = transition.intent
    e.original = replace(e.original, enemy_ai=intent.state.enemy_ai)
    options = encounter.attack_source_options_by_actor.get(e.active.id, ())
    source = next((s for s in options if s.id == intent.source_id), encounter.attack_sources_by_actor.get(e.active.id))
    sources = encounter.multiattack_sources_by_actor.get(e.active.id) or ((source,) if source else ())
    weapons = tuple(charge_weapon(e.active, s) for s in sources)
    if intent.pack_attack_bonus:
        weapons = tuple(replace(w, attack_bonus=w.attack_bonus+intent.pack_attack_bonus,
            components=tuple(dict(p, modifier=p.get("modifier", 0)+intent.pack_attack_bonus) for p in w.components)) for w in weapons)
    return e.prepare_enemy_turn(target_id=intent.target.id if intent.target else "", destination=intent.movement_path.destination if intent.movement_path else None,
                                weapons=weapons, intent=intent.intent, escape_target=intent.escape_target, heal_target=intent.pack_heal_target_id, life_drain=intent.life_drain)


def command(session: ExplorationUiSession, data: dict[str, Any]) -> dict[str, Any]:
    from .mission_zero import active_panel
    if active_panel(session):
        raise ValueError("Najpierw rozpatrz bieżący komunikat misji.")
    e = engine(session)
    if type(data.get("revision")) is not int or data["revision"] != e.s.revision:
        raise ValueError("Ten wybór jest już nieaktualny. Użyj bieżącego ekranu.")
    if e.s.inspected and data.get("command") not in {"back", "page", "info", "inspect", "select"}:
        raise ValueError("Zamknij informacje przed wykonaniem akcji.")
    action, accepted = data.get("command"), False
    if action == "choose":
        accepted = e.choose(str(data.get("id", ""))) if not e.s.inspected and e.active.faction == Faction.ALLY else False
    elif action == "select":
        pos = point(data["position"])
        if e.s.inspected:
            selected = next((str(a.id) for a in e.actors.values() if a.position == pos), None)
            if selected:
                e.s.inspected, e.s.info_page, accepted = selected, 0, True
        else:
            accepted = e.select(pos)
            if accepted and e.s.preview:
                e.s.preview.pop("rejected_target", None)
            elif e.s.preview:
                target_id = next((key for key in e.target_candidates() if e.actor(key).position == pos), None)
                if target_id and (reason := e.target_rejection(target_id)):
                    e.s.preview["rejected_target"] = dict(target=target_id, reason=_rejection_text(session, e, target_id, reason))
                    accepted = True
    elif action == "mode":
        accepted = not _relations(e) and e.mode(data.get("mode"))
    elif action == "item" and e.s.phase == "preview" and e.s.preview["id"] == "item" and e.items:
        current = next((i for i, item in enumerate(e.items) if item == e.s.preview["item"]), 0)
        e.s.preview["item"] = e.items[(current+(1 if data.get("delta", 1) > 0 else -1)) % len(e.items)]
        accepted = True
    elif action == "exclude":
        accepted = e.exclude(data.get("actor"))
    elif action in {"info", "inspect"}:
        key = str(data.get("actor", e.active.id))
        if key in e.actors:
            e.s.inspected, e.s.info_page, accepted = key, 0, True
    elif action == "page" and e.s.inspected:
        e.s.info_page += 1 if data.get("delta", 1) > 0 else -1
        accepted = True
    elif action == "adjust" and e.s.task and e.s.task["type"] == "roll" and e.actor(e.s.task["actor"]).faction == Faction.ALLY:
        dice = e.roll_dice()
        die = dice[len(e.s.task.get("dice_results", []))]
        e.s.die_value = max(1, min(die["sides"], e.s.die_value+(1 if data.get("delta", 1) > 0 else -1)))
        accepted = True
    elif action == "die":
        accepted = e.submit_die(data.get("value"), data.get("index"))
    elif action == "end" and e.s.phase == "idle" and not e.s.inspected:
        e.s.phase, accepted = "end-preview", True
    elif action == "back":
        if e.s.inspected:
            accepted = e.cancel()
        elif e.s.task and e.s.task["type"] == "bonus_target":
            accepted = e.skip_bonus_target()
        elif e.s.task and e.s.task["type"] in {"recover", "hymn", "opportunity"}:
            accepted = {"recover": e.recover, "hymn": e.decide_hymn, "opportunity": e.opportunity}[e.s.task["type"]](False)
        else:
            accepted = e.cancel()
    elif action == "accept" and not e.s.inspected:
        task = e.s.task
        if e.s.phase == "preview":
            if p_rejected(e):
                raise ValueError(p_rejected(e)["reason"])
            accepted = e.commit()
        elif e.s.phase == "end-preview":
            accepted = e.end_turn()
        elif e.s.phase == "idle" and e.active.faction == Faction.ENEMY:
            accepted = plan_enemy(session, e)
        elif task:
            if task["type"] == "roll":
                accepted = e.confirm_enemy_roll(lambda sides: session.encounter_rng.randint(1, sides)) if e.actor(task["actor"]).faction == Faction.ENEMY else e.submit_die(e.s.die_value, len(task.get("dice_results", [])))
            elif task["type"] in {"recover", "hymn", "opportunity"}:
                accepted = {"recover": e.recover, "hymn": e.decide_hymn, "opportunity": e.opportunity}[task["type"]](True)
            elif task["type"] == "relocate":
                accepted = e.confirm_relocation()
            elif task["type"] == "bonus_target":
                accepted = e.confirm_bonus_target()
            else:
                accepted = e.acknowledge()
        elif e.s.phase == "result":
            enemy = e.active.faction == Faction.ENEMY
            accepted = e.acknowledge()
            if accepted and enemy and e.s.phase != "finished":
                e.end_turn()
        elif e.s.phase == "finished":
            return session.resolve_active_combat()
    if not accepted:
        raise ValueError("Ten wybór nie jest teraz możliwy.")
    previous_action = session.combat_state.resonance.action
    if e.s.action and e.s.action.get("consumed_item") and (not previous_action or previous_action["serial"] != e.s.action["serial"]):
        item = e.s.action["consumed_item"]
        if not item["owner"]:
            stash = session.state.party_loot
            session.state = replace(session.state, party_loot=replace(stash, items=tuple(replace(i, quantity=i.quantity-1) if i.id == item["id"] else i for i in stash.items if i.id != item["id"] or i.quantity > 1)))
        from .mission_zero import enabled, read, write
        if enabled(session) and item["id"].startswith("mission_"):
            mission = read(session)
            mission["ledger"].append(dict(kind="item", id=item["id"].removeprefix("mission_"), name="Zużyta mikstura", amount=-1))
            write(session, mission)
    e.s.revision += 1
    if e.s.round != session.combat_state.resonance.round:
        from dnd_board_game.rules.effects import EffectEvent, EffectEventType, expire_active_effects
        session.active_combat_effects = expire_active_effects(session.active_combat_effects, EffectEvent(EffectEventType.ROUND_ENDED)).active_effects
    session.combat_state = e.combat_state()
    session.board_selection_revision += 1
    session.board_panel_context = None
    session._sync_board_leds()
    return session.state_payload()
