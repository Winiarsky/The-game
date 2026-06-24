from __future__ import annotations

import random
from typing import Any


ALTAR_POS = (6, 5)
DEACON_SPAWN_POS = (6, 6)
SEAL_REQUIRED = 3
STATUE_SEQUENCE = ("watcher", "bellbearer", "flamekeeper", "ash_saint")
MAX_CINDERS = 6

CONFESSIONAL_POS = (2, 6)
STATUE_POSITIONS = {
    "watcher": (3, 6),
    "bellbearer": (9, 6),
    "flamekeeper": (4, 9),
    "ash_saint": (8, 9),
}
FALLEN_BEAM_POS = (9, 8)
ASH_VENT_POSITIONS = ((5, 6), (7, 6))
CINDER_SPAWN_CANDIDATES = ((5, 7), (7, 7), (4, 8), (8, 8), (6, 9), (3, 8))


def ensure_state(game: Any) -> dict[str, Any]:
    state = getattr(game, "_burned_chapel_state", None)
    if not isinstance(state, dict):
        state = {
            "altar_triggered": False,
            "seal_progress": 0,
            "seal_required": SEAL_REQUIRED,
            "last_seal_round": None,
            "altar_sealed": False,
            "confessional_resolved": False,
            "saint_symbol_found": False,
            "statue_sequence_progress": 0,
            "deacon_sustained_message_shown": False,
            "boss_defeated": False,
            "final_sermon_used": False,
            "bell_rung_round": None,
            "holy_water_used": False,
            "fallen_beam_moved": False,
            "overview_seen": False,
        }
        setattr(game, "_burned_chapel_state", state)
    return state


def combat_round(game: Any) -> int:
    try:
        return int(getattr(getattr(game, "state", None), "round_index", 0) or 0)
    except Exception:
        return 0


def altar_is_sealed(game: Any) -> bool:
    state = ensure_state(game)
    return bool(state.get("altar_sealed")) or int(state.get("seal_progress", 0) or 0) >= int(
        state.get("seal_required", SEAL_REQUIRED) or SEAL_REQUIRED
    )


def can_attempt_seal_this_round(game: Any) -> bool:
    state = ensure_state(game)
    if altar_is_sealed(game):
        return False
    return state.get("last_seal_round") != combat_round(game)


def seal_round_gate_message(game: Any) -> str:
    msg = "Ołtarz odrzuca kolejny rytuał w tej rundzie. Popiół musi na chwilę opaść."
    prompt_info(game, "Ołtarz odrzuca rytuał", msg, source="seal_round_gate")
    return msg


def prompt_info(game: Any, title: str, text: str, *, source: str) -> None:
    player_prompt = getattr(game, "player_prompt", None)
    if player_prompt is not None and hasattr(player_prompt, "info"):
        try:
            player_prompt.info(title, body_markdown=text, source=source, prompt_id=f"burned_chapel.{source}")
            return
        except Exception:
            pass
    ui = getattr(game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
        try:
            ui.prompt_info(title, prompt_long=text, source=source, prompt_id=f"burned_chapel.{source}")
        except Exception:
            pass


def set_flag(game: Any, flag: str, value: bool = True) -> None:
    key = str(flag or "").strip()
    if not key:
        return
    session = getattr(game, "scenario_session", None)
    flags = getattr(session, "global_flags", None)
    if isinstance(flags, dict):
        flags[key] = value
    flags = getattr(game, "global_flags", None)
    if isinstance(flags, dict):
        flags[key] = value


def save_checkpoint(game: Any, reason: str) -> None:
    session = getattr(game, "scenario_session", None)
    saver = getattr(session, "save_checkpoint", None)
    if callable(saver):
        try:
            saver(reason=reason)
        except Exception:
            pass


def update_leds(game: Any, mode: str = "idle") -> None:
    conn = getattr(game, "conn", None)
    if conn is None or not hasattr(conn, "set_leds"):
        return
    state = ensure_state(game)
    updates: dict[tuple[int, int], list[int]] = {}
    altar = ALTAR_POS
    progress = int(state.get("seal_progress", 0) or 0)
    if mode == "sealed" or altar_is_sealed(game):
        updates[altar] = [180, 220, 255]
    elif bool(state.get("altar_triggered")):
        updates[altar] = [220, 20, 8]
    else:
        updates[altar] = [80, 8, 5]
    if mode in {"overview", "idle"}:
        updates[CONFESSIONAL_POS] = [190, 215, 255]
        for pos in STATUE_POSITIONS.values():
            updates[pos] = [95, 65, 25]
        for pos in ASH_VENT_POSITIONS:
            updates[pos] = [220, 90, 15]
        if not bool(state.get("fallen_beam_moved")):
            updates[FALLEN_BEAM_POS] = [120, 70, 20]
    for pos in STATUE_POSITIONS.values():
        updates[pos] = [24, 18, 12]
    if mode == "overview":
        updates[CONFESSIONAL_POS] = [190, 215, 255]
        updates[ALTAR_POS] = [120, 12, 8]
        for pos in STATUE_POSITIONS.values():
            updates[pos] = [255, 190, 40]
        for pos in ASH_VENT_POSITIONS:
            updates[pos] = [220, 90, 15]
        if not bool(state.get("fallen_beam_moved")):
            updates[FALLEN_BEAM_POS] = [120, 70, 20]
    if bool(state.get("confessional_resolved")):
        idx = min(int(state.get("statue_sequence_progress", 0) or 0), len(STATUE_SEQUENCE) - 1)
        updates[STATUE_POSITIONS[STATUE_SEQUENCE[idx]]] = [255, 190, 40]
    if progress >= 1:
        updates[(5, 5)] = [140, 190, 255]
    if progress >= 2:
        updates[(6, 5)] = [160, 210, 255]
    if progress >= 3:
        updates[(7, 5)] = [180, 220, 255]
    if not bool(state.get("fallen_beam_moved")):
        updates[FALLEN_BEAM_POS] = [120, 70, 20]
    elif mode == "fallen_beam":
        updates[FALLEN_BEAM_POS] = [40, 180, 80]
    try:
        conn.set_leds(list(updates.keys()), list(updates.values()))
    except Exception:
        pass


def update_token_leds(game: Any, positions: list[tuple[int, int]], color: list[int]) -> None:
    conn = getattr(game, "conn", None)
    if conn is None or not hasattr(conn, "set_leds") or not positions:
        return
    try:
        conn.set_leds(positions, [color for _ in positions])
    except Exception:
        pass


def present_chapel_overview(game: Any) -> str:
    state = ensure_state(game)
    state["overview_seen"] = True
    text = (
        "Kaplica nie jest zwykłym polem walki. Czerwony LED wskazuje spalony ołtarz na polu "
        f"{ALTAR_POS}; zimne białe światło pokazuje nienaruszony konfesjonał na polu {CONFESSIONAL_POS}. "
        "Złote punkty to cztery posągi-seale: Obserwator, Dzwonnik, Strażnik Płomienia i Popielny Święty. "
        f"Brązowy LED przy polu {FALLEN_BEAM_POS} oznacza fizyczną belkę, którą można przesunąć po teście Atletyki. "
        "Pomarańczowe LED-y przy ołtarzu oznaczają popielne wyziewy. Walka zacznie się dopiero, gdy ktoś podejdzie do ołtarza; "
        "wcześniej warto sprawdzić konfesjonał i tropy przy progu."
    )
    prompt_info(game, "Spalona Kaplica", text, source="chapel_overview")
    update_leds(game, "overview")
    return text


def trigger_altar(game: Any) -> str:
    state = ensure_state(game)
    if bool(state.get("altar_triggered")):
        update_leds(game, "triggered")
        return "Ołtarz już płonie ciemnym żarem."
    deacon = spawn_deacon(game)
    state["altar_triggered"] = True
    prompt_info(
        game,
        "Spalony Diakon",
        "Popiół przy ołtarzu unosi się w kształt spalonego duchownego. Pastorał uderza o kamień, a czerwony żar rozlewa się po posadzce.",
        source="altar_triggered",
    )
    update_leds(game, "triggered")
    try:
        game.start_combat(trigger=deacon or find_deacon(game))
    except Exception:
        pass
    return "Ołtarz budzi Spalonego Diakona."


def spawn_deacon(game: Any) -> Any | None:
    existing = find_deacon(game)
    if existing is not None:
        return existing
    builder = getattr(game, "_encounter_build_object_instance", None)
    if not callable(builder):
        return None
    deacon = builder("Enemies", "charred_deacon", {})
    if deacon is None:
        return None
    board = getattr(game, "board", None)
    if board is None:
        return None
    candidates = [DEACON_SPAWN_POS, (6, 7), (5, 6), (7, 6), (5, 7), (7, 7)]
    for pos in candidates:
        try:
            if not board.can_enter(pos, allow_occupied=False):
                continue
            board.place(deacon, pos)
            deacon.position = pos
            getattr(game, "enemies", []).append(deacon)
            prompt_info(
                game,
                "Postaw figurkę",
                f"Postaw figurkę Spalonego Diakona na polu {pos}. Czerwone światło ołtarza wskazuje miejsce wejścia bossa.",
                source="deacon_spawn_board",
            )
            return deacon
        except Exception:
            continue
    return None


def altar_zone(enemy: Any) -> str:
    pos = getattr(enemy, "position", None)
    if not isinstance(pos, tuple):
        return "outer"
    dist = abs(int(pos[0]) - ALTAR_POS[0]) + abs(int(pos[1]) - ALTAR_POS[1])
    if dist <= 2:
        return "inner"
    if dist <= 5:
        return "middle"
    return "outer"


def zone_values(zone: str) -> tuple[int, int]:
    if zone == "inner":
        return 3, 5
    if zone == "middle":
        return 2, 3
    return 1, 1


def add_seal_progress(game: Any, *, actor: Any = None, method: str = "rite", backlash: bool = False) -> tuple[bool, str]:
    state = ensure_state(game)
    if altar_is_sealed(game):
        return False, "Ołtarz jest już zablokowany."
    current_round = combat_round(game)
    if state.get("last_seal_round") == current_round:
        msg = seal_round_gate_message(game)
        return False, msg
    state["last_seal_round"] = current_round
    state["seal_progress"] = min(
        int(state.get("seal_required", SEAL_REQUIRED) or SEAL_REQUIRED),
        int(state.get("seal_progress", 0) or 0) + 1,
    )
    progress = int(state.get("seal_progress", 0) or 0)
    if backlash:
        apply_backlash(game, actor=actor, reason=method)
    if progress >= int(state.get("seal_required", SEAL_REQUIRED) or SEAL_REQUIRED):
        state["altar_sealed"] = True
        remove_cinders(game)
        prompt_info(
            game,
            "Ołtarz zgasł",
            "Czerwony żar pod kamieniem pęka i przechodzi w zimne światło. Spalony Diakon traci kotwicę, która trzymała go przy życiu.",
            source="altar_sealed",
        )
        update_leds(game, "sealed")
        return True, "Ołtarz został zablokowany. Spalony Diakon może teraz zginąć."
    update_leds(game, f"seal_{progress}")
    return True, f"Postęp sealu: {progress}/{state.get('seal_required', SEAL_REQUIRED)}."


def apply_backlash(game: Any, *, actor: Any = None, reason: str = "failure") -> str:
    roll = random.randint(1, 3)
    deacon = find_deacon(game)
    if roll == 1:
        if actor is not None and hasattr(actor, "apply_damage"):
            try:
                actor.apply_damage(2, "shadow")
            except Exception:
                pass
        msg = "Ciemny płomień odbija się od ołtarza i rani tego, kto naruszył rytuał."
    elif roll == 2:
        spawned = spawn_cinder(game)
        msg = "Z popiołu podnosi się Popielna Iskra." if spawned else "Popiół drży, ale nie znajduje miejsca, by uformować kolejny cień."
    else:
        if deacon is not None:
            try:
                deacon.heal(3)
            except Exception:
                pass
            try:
                deacon.ai_memory["fed_by_altar_round"] = combat_round(game)
            except Exception:
                pass
        msg = "Ołtarz karmi Deacona ciemnym żarem."
    prompt_info(game, "Odrzut ołtarza", msg, source=f"altar_backlash:{reason}")
    update_leds(game, "backlash")
    return msg


def consume_holy_water(game: Any, actor: Any = None) -> tuple[bool, str]:
    state = ensure_state(game)
    if bool(state.get("holy_water_used")):
        return False, "Woda święcona została już zużyta przy tym ołtarzu."

    def _norm(value: Any) -> str:
        return str(value or "").strip().lower().replace("_", " ").replace("-", " ")

    names = {"holy water", "woda swiecona", "woda święcona", "lesser holy water"}
    containers = []
    if actor is not None:
        containers.append(getattr(actor, "inventory", None))
    containers.append(getattr(game, "party_stash", None))
    for container in containers:
        if not isinstance(container, list):
            continue
        for item in list(container):
            item_id = _norm(getattr(item, "item_id", "") or getattr(item, "id", ""))
            name = _norm(getattr(item, "name", "") or item)
            if item_id in names or name in names:
                quantity = getattr(item, "quantity", None)
                if isinstance(quantity, int) and quantity > 1:
                    try:
                        item.quantity = quantity - 1
                    except Exception:
                        container.remove(item)
                else:
                    try:
                        container.remove(item)
                    except Exception:
                        pass
                state["holy_water_used"] = True
                return True, "Zużywacie jedną fiolkę wody święconej."

    return False, "Nie macie wody święconej, którą można spalić na ołtarzu."


def find_deacon(game: Any) -> Any | None:
    for enemy in list(getattr(game, "enemies", []) or []):
        if str(getattr(enemy, "encounter_role", "") or "") == "charred_deacon":
            return enemy
        if enemy.__class__.__name__ == "CharredDeacon":
            return enemy
    return None


def active_cinders(game: Any) -> list[Any]:
    return [
        enemy
        for enemy in list(getattr(game, "enemies", []) or [])
        if str(getattr(enemy, "encounter_role", "") or "") == "ash_cinder" and getattr(enemy, "position", None) is not None
    ]


def spawn_cinder(game: Any) -> bool:
    if len(active_cinders(game)) >= MAX_CINDERS:
        return False
    builder = getattr(game, "_encounter_build_object_instance", None)
    if not callable(builder):
        return False
    cinder = builder("Enemies", "ash_cinder", {})
    if cinder is None:
        return False
    board = getattr(game, "board", None)
    if board is None:
        return False
    candidates = list(CINDER_SPAWN_CANDIDATES)
    for pos in candidates:
        try:
            if not board.can_enter(pos, allow_occupied=False):
                continue
            board.place(cinder, pos)
            cinder.position = pos
            getattr(game, "enemies", []).append(cinder)
            combat = getattr(game, "state", None)
            adder = getattr(combat, "add_revealed_enemy", None)
            if callable(adder):
                adder(cinder, join_current_round=True)
            return True
        except Exception:
            continue
    return False


def summon_cinders(game: Any, count: int | None = None) -> int:
    total = count if count is not None else random.randint(1, 4)
    spawned = 0
    for _ in range(max(0, int(total or 0))):
        if spawn_cinder(game):
            spawned += 1
    if spawned:
        positions = [getattr(cinder, "position", None) for cinder in active_cinders(game)[-spawned:]]
        shown_positions = [pos for pos in positions if isinstance(pos, tuple)]
        if shown_positions:
            update_token_leds(game, shown_positions, [120, 120, 135])
        noun = "cień" if spawned == 1 else "cienie" if 2 <= spawned <= 4 else "cieni"
        positions_text = f" na polach {', '.join(str(pos) for pos in shown_positions)}" if shown_positions else ""
        prompt_info(
            game,
            "Popielne cienie",
            f"Spalony Diakon uderza pastorałem w posadzkę. Z popiołu podnosi się {spawned} popielny {noun}{positions_text}. "
            "Połóż odpowiednie tokeny na wskazanych szarych LED-ach.",
            source="call_from_ashes",
        )
    return spawned


def remove_cinders(game: Any) -> int:
    removed = 0
    board = getattr(game, "board", None)
    enemies = getattr(game, "enemies", None)
    for cinder in list(active_cinders(game)):
        pos = getattr(cinder, "position", None)
        if board is not None and isinstance(pos, tuple):
            try:
                board.remove(pos)
            except Exception:
                pass
        if isinstance(enemies, list) and cinder in enemies:
            enemies.remove(cinder)
        try:
            cinder.position = None
        except Exception:
            pass
        removed += 1
    return removed


def handle_deacon_defeat(game: Any, deacon: Any, *, source: str = "damage") -> bool:
    state = ensure_state(game)
    if altar_is_sealed(game):
        state["boss_defeated"] = True
        set_flag(game, "charred_deacon_defeated", True)
        set_flag(game, "chapel_investigated", True)
        set_flag(game, "relic_theft_discovered", True)
        set_flag(game, "warden_medallion_recovered", True)
        save_checkpoint(game, "charred_deacon_defeated")
        prompt_info(
            game,
            "Spalony Diakon pokonany",
            "Spalony Diakon rozpada się bez powrotu. Pod ołtarzem zostaje medalion Serai, pęknięta pieczęć Vale'a i fiolka jasnego popiołu.",
            source="deacon_defeated",
        )
        update_leds(game, "defeated")
        return False
    zone = altar_zone(deacon)
    _regen, revive_hp = zone_values(zone)
    try:
        deacon.hp = revive_hp
    except Exception:
        pass
    if not bool(state.get("deacon_sustained_message_shown")):
        state["deacon_sustained_message_shown"] = True
        prompt_info(
                game,
                "Ołtarz podtrzymuje Deacona",
            "Spalony Diakon rozpada się w popiół, ale ołtarz rozbłyskuje czerwienią. Coś pod kamieniem ściąga go z powrotem. Nie da się go zniszczyć, dopóki ołtarz płonie.",
            source="deacon_sustained",
        )
    else:
        prompt_info(
            game,
            "Diakon wraca z popiołu",
            f"Ołtarz ściąga popiół z powrotem w spaloną sylwetkę. Diakon wraca z {revive_hp} HP.",
            source="deacon_revive",
        )
    update_leds(game, "revive")
    return True


def deacon_turn_start(game: Any, deacon: Any) -> None:
    if altar_is_sealed(game):
        state = ensure_state(game)
        if not bool(state.get("final_sermon_used")):
            state["final_sermon_used"] = True
            prompt_info(
                game,
                "Ostatnie kazanie",
                "Bez kotwicy ołtarza Diakon wyrzuca ostatnią falę popiołu. Każdy bohater w kaplicy otrzymuje 1 obrażenie od cienia.",
                source="final_sermon",
            )
            for hero in list(getattr(game, "heroes", []) or []):
                if hasattr(hero, "apply_damage"):
                    try:
                        hero.apply_damage(1, "shadow")
                    except Exception:
                        pass
        return
    zone = altar_zone(deacon)
    regen, _revive = zone_values(zone)
    try:
        if int(getattr(deacon, "hp", 0) or 0) > 0:
            deacon.heal(regen)
    except Exception:
        pass
    ensure_state(game)["altar_triggered"] = True
    update_leds(game, f"zone_{zone}")


def move_fallen_beam(game: Any) -> str:
    state = ensure_state(game)
    if bool(state.get("fallen_beam_moved")):
        return "Belka jest już przesunięta. Zostawcie fizyczny znacznik poza przejściem."
    state["fallen_beam_moved"] = True
    set_flag(game, "fallen_beam_moved", True)
    update_leds(game, "fallen_beam")
    msg = (
        "Belka odsuwa się z hukiem. Przesuńcie fizyczny znacznik belki z pola 9,8 poza główne przejście; "
        "zielone światło pokazuje oczyszczony fragment trasy między posągami."
    )
    prompt_info(game, "Spalona belka", msg, source="fallen_beam_moved")
    return msg


def complete_confessional(game: Any) -> str:
    state = ensure_state(game)
    state["confessional_resolved"] = True
    state["saint_symbol_found"] = True
    set_flag(game, "chapel_confession_silence", True)
    update_leds(game, "confessional")
    return (
        "Konfesjonał odpowiada ciszą. W ukrytej szczelinie znajdujecie pęknięty symbol świętego. "
        "Cztery posągi układają historię: Obserwator, Dzwonnik, Strażnik Płomienia, Popielny Święty."
    )


def activate_statue(game: Any, statue_id: str, *, actor: Any = None) -> str:
    state = ensure_state(game)
    if not bool(state.get("altar_triggered")):
        return (
            "Posąg jest zimny. Możecie odczytać scenę, ale rytuał posągów odpowie dopiero wtedy, "
            "gdy ołtarz się przebudzi."
        )
    expected_idx = int(state.get("statue_sequence_progress", 0) or 0)
    expected = STATUE_SEQUENCE[min(expected_idx, len(STATUE_SEQUENCE) - 1)]
    normalized = str(statue_id or "").strip().lower()
    if normalized != expected:
        apply_backlash(game, actor=actor, reason="wrong_statue")
        return f"Zły posąg. Ołtarz oczekiwał sceny: {expected}."
    expected_idx += 1
    state["statue_sequence_progress"] = expected_idx
    update_leds(game, "statue")
    if expected_idx >= len(STATUE_SEQUENCE):
        ok, msg = add_seal_progress(game, actor=actor, method="statue_sequence", backlash=False)
        return f"Sekwencja posągów zamyka jedną warstwę rytuału. {msg}" if ok else msg
    return f"Posąg {normalized} gaśnie. Następna scena czeka."
