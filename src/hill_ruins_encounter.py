from __future__ import annotations

from typing import Any


STATE_KEY = "_hill_ruins_state"
RITUAL_REQUIRED = 4

MIRA_POS = (9, 8)
MEMORY_CIRCLE_POS = (9, 8)
CRYPT_DESCENT_POS = (17, 5)
ECHO_POS = (5, 6)
FALSE_ASH_POS = (13, 11)
ASH_STORM_PATH = ((8, 6), (10, 6), (12, 7), (11, 9), (8, 10), (6, 9))
HAZARD_POSITIONS = ((7, 7), (8, 7), (10, 9), (11, 9), (14, 8), (15, 8))
ARCH_POS = (12, 5)
ANCHOR_POSITIONS = {
    "oath": (4, 5),
    "ash": (14, 5),
    "blood": (5, 12),
    "relic": (15, 12),
}
ANCHOR_LABELS = {
    "oath": "Anchor Przysięgi",
    "ash": "Anchor Popiołu",
    "blood": "Anchor Krwi",
    "relic": "Anchor Relikwiarza",
}


def ensure_state(game: Any) -> dict[str, Any]:
    state = getattr(game, STATE_KEY, None)
    if not isinstance(state, dict):
        state = {
            "ritual_started": False,
            "ritual_stability": 0,
            "ritual_required": RITUAL_REQUIRED,
            "last_stability_round": None,
            "mira_focus": 3,
            "mira_in_danger": False,
            "memory_shards_revealed": [],
            "anchors_completed": [],
            "ash_storm_index": 0,
            "ash_storm_position": ASH_STORM_PATH[0],
            "crypt_descent_unsealed": False,
            "odran_warning_active": False,
            "truth_reconstructed": False,
            "false_ash_exposed": False,
            "ash_storm_suppressed_round": None,
            "hallowed_ash_vial_used": False,
            "fallen_arch_supported": False,
            "overview_seen": False,
        }
        setattr(game, STATE_KEY, state)
    if flag_enabled(game, "odran_warned"):
        state["odran_warning_active"] = True
    return state


def combat_round(game: Any) -> int:
    try:
        return int(getattr(getattr(game, "state", None), "round_index", 0) or 0)
    except Exception:
        return 0


def session_flags(game: Any) -> dict[str, Any]:
    session = getattr(game, "scenario_session", None)
    flags = getattr(session, "global_flags", None)
    if isinstance(flags, dict):
        return flags
    flags = getattr(game, "global_flags", None)
    if isinstance(flags, dict):
        return flags
    setattr(game, "global_flags", {})
    return getattr(game, "global_flags")


def set_flag(game: Any, flag: str, value: bool = True) -> None:
    key = str(flag or "").strip()
    if key:
        session_flags(game)[key] = bool(value)


def flag_enabled(game: Any, flag: str) -> bool:
    return bool(session_flags(game).get(str(flag or "").strip()))


def save_checkpoint(game: Any, reason: str) -> None:
    session = getattr(game, "scenario_session", None)
    saver = getattr(session, "save_checkpoint", None)
    if callable(saver):
        try:
            saver(reason=str(reason))
        except Exception:
            pass


def prompt_info(game: Any, title: str, body: str, *, source: str) -> None:
    text = str(body or "").strip()
    if not text:
        return
    player_prompt = getattr(game, "player_prompt", None)
    if player_prompt is not None and hasattr(player_prompt, "info"):
        try:
            player_prompt.info(
                title,
                body_markdown=text,
                source=f"hill_ruins:{source}",
                summary="Ruiny na wzgórzu",
                scope_key="hill_ruins_encounter",
                dedupe_key=f"hill_ruins:{source}",
                semantic_type="required_action",
            )
            return
        except Exception:
            pass
    try:
        game.ui_narration(text, summary=title, source=f"hill_ruins:{source}")
    except Exception:
        try:
            game.ui_log(text)
        except Exception:
            pass


def update_leds(game: Any, mode: str = "idle") -> None:
    conn = getattr(game, "conn", None)
    if conn is None or not hasattr(conn, "set_leds"):
        return
    state = ensure_state(game)
    updates: dict[tuple[int, int], list[int]] = {
        MIRA_POS: [190, 220, 255],
        CRYPT_DESCENT_POS: [15, 20, 15],
        ECHO_POS: [210, 185, 80],
        FALSE_ASH_POS: [150, 150, 145],
        ARCH_POS: [120, 90, 55],
    }
    for anchor_id, pos in ANCHOR_POSITIONS.items():
        updates[pos] = [35, 65, 110]
        if anchor_id in set(state.get("anchors_completed") or []):
            updates[pos] = [185, 225, 255]
    if mode == "active_anchor":
        for anchor_id, pos in ANCHOR_POSITIONS.items():
            if anchor_id not in set(state.get("anchors_completed") or []):
                updates[pos] = [255, 205, 60]
                break
    if bool(state.get("ritual_started")):
        updates[MEMORY_CIRCLE_POS] = [215, 220, 230]
    if bool(state.get("mira_in_danger")):
        updates[MIRA_POS] = [255, 55, 55]
    storm_pos = tuple(state.get("ash_storm_position") or ASH_STORM_PATH[0])
    updates[storm_pos] = [205, 205, 210]
    for pos in HAZARD_POSITIONS:
        updates[pos] = [160, 50, 140] if mode != "hazard_clear" else [40, 40, 45]
    if bool(state.get("crypt_descent_unsealed")):
        updates[CRYPT_DESCENT_POS] = [45, 220, 95]
    if mode == "truth":
        updates[MEMORY_CIRCLE_POS] = [240, 245, 255]
        updates[CRYPT_DESCENT_POS] = [45, 220, 95]
    try:
        conn.set_leds(list(updates.keys()), list(updates.values()))
    except Exception:
        for pos, color in updates.items():
            try:
                conn.set_leds([pos], color)
            except Exception:
                continue


def present_overview(game: Any) -> str:
    state = ensure_state(game)
    state["overview_seen"] = True
    start_ritual(game, announce=False)
    text = (
        "Ruiny na wzgórzu nie są zwykłą areną. Zimne światło przy Mirze oznacza krąg wspomnienia. "
        "Cztery niebieskie punkty to anchory rytuału; trzeba je stabilizować, żeby prawda przetrwała. "
        "Szary punkt wiru popiołu będzie zmieniał presję na mapie, a zielone zejście do krypty pozostaje zamknięte, "
        "dopóki wspomnienie nie pokaże kradzieży relikwiarza."
    )
    if flag_enabled(game, "hidden_mill_route_found"):
        text += " Wejście traktem z młyna daje wam flankę i bliższy dostęp do południowych anchorów."
    if flag_enabled(game, "odran_warned"):
        text += " Odran został ostrzeżony; duchy zaczynają bliżej zejścia do krypty."
    prompt_info(game, "Ruiny na wzgórzu", text, source="overview")
    update_leds(game, "active_anchor")
    return text


def start_ritual(game: Any, *, announce: bool = True) -> None:
    state = ensure_state(game)
    if bool(state.get("ritual_started")):
        return
    state["ritual_started"] = True
    set_flag(game, "hill_ruins_entered")
    if flag_enabled(game, "odran_warned"):
        state["odran_warning_active"] = True
    if announce:
        prompt_info(
            game,
            "Rytuał Miry",
            "Popielny krąg odpowiada na waszą obecność. Mira utrzymuje wspomnienie, ale duchy próbują rozerwać jego krawędzie.",
            source="ritual_started",
        )
    update_leds(game, "active_anchor")


def can_gain_stability_this_round(game: Any) -> bool:
    state = ensure_state(game)
    if bool(state.get("truth_reconstructed")):
        return False
    return state.get("last_stability_round") != combat_round(game)


def round_gate_message(game: Any) -> str:
    msg = "Popielne wspomnienie przyjęło już jedną stabilizację w tej rundzie. Kolejny anchor musi poczekać, aż krąg złapie oddech."
    prompt_info(game, "Rytuał odrzuca pośpiech", msg, source="round_gate")
    return msg


def add_ritual_stability(game: Any, *, anchor_id: str | None = None, method: str = "ritual") -> tuple[bool, str]:
    start_ritual(game)
    if not can_gain_stability_this_round(game):
        return False, round_gate_message(game)
    state = ensure_state(game)
    completed = set(state.get("anchors_completed") or [])
    anchor_key = str(anchor_id or "").strip()
    if anchor_key and anchor_key in completed:
        return False, f"{ANCHOR_LABELS.get(anchor_key, 'Anchor')} jest już ustabilizowany."
    if anchor_key:
        completed.add(anchor_key)
        state["anchors_completed"] = sorted(completed)
    state["last_stability_round"] = combat_round(game)
    state["ritual_stability"] = min(
        int(state.get("ritual_required", RITUAL_REQUIRED) or RITUAL_REQUIRED),
        int(state.get("ritual_stability", 0) or 0) + 1,
    )
    progress = int(state.get("ritual_stability", 0) or 0)
    required = int(state.get("ritual_required", RITUAL_REQUIRED) or RITUAL_REQUIRED)
    if progress >= required:
        reconstruct_truth(game, method=method)
        return True, "Ostatni anchor milknie. Wspomnienie układa się w pełną scenę kradzieży relikwiarza."
    update_leds(game, "active_anchor")
    return True, f"Rytuał stabilizuje się: {progress}/{required}."


def reconstruct_truth(game: Any, *, method: str = "ritual") -> str:
    state = ensure_state(game)
    if bool(state.get("truth_reconstructed")):
        return "Prawda została już odtworzona."
    state["truth_reconstructed"] = True
    state["crypt_descent_unsealed"] = True
    state["mira_in_danger"] = False
    set_flag(game, "ritual_anchors_completed")
    set_flag(game, "mira_memory_stabilized")
    set_flag(game, "mira_truth_learned")
    set_flag(game, "mira_allied")
    set_flag(game, "crypt_descent_unsealed")
    set_flag(game, "odran_relic_theft_proven")
    save_checkpoint(game, "mira_truth_learned")
    save_checkpoint(game, "crypt_descent_unsealed")
    session = getattr(game, "scenario_session", None)
    revealer = getattr(session, "reveal_object", None)
    if callable(revealer):
        try:
            revealer("hill_ruins", "to_oath_crypt", state_updates={"hidden": False, "revealed": True})
        except Exception:
            pass
    prompt_info(
        game,
        "Prawda w popiele",
        "Popiół pokazuje kaplicę sprzed pożaru: Odran Vale stoi przy ołtarzu, jego ludzie wynoszą relikwiarz, a fałszywy pył ma skierować winę na Mirę. Zejście do Krypty Przysięgi otwiera się zimnym światłem.",
        source=f"truth_reconstructed:{method}",
    )
    update_leds(game, "truth")
    return "Prawda zostaje odtworzona, a zejście do krypty jest odblokowane."


def backlash(game: Any, *, reason: str = "ritual_failure") -> str:
    state = ensure_state(game)
    focus = max(0, int(state.get("mira_focus", 3) or 0) - 1)
    state["mira_focus"] = focus
    if focus <= 1:
        state["mira_in_danger"] = True
    move_ash_storm(game, announce=False)
    msg = "Popiół szarpie krąg i przesuwa wir przez ruiny. Mira traci część skupienia."
    if state["mira_in_danger"]:
        msg += " Biało-czerwony LED przy Mirze oznacza, że trzeba odciążyć rytuał."
    prompt_info(game, "Odrzut rytuału", msg, source=f"backlash:{reason}")
    update_leds(game, "failed_anchor")
    return msg


def move_ash_storm(game: Any, *, announce: bool = True) -> tuple[int, int]:
    state = ensure_state(game)
    index = (int(state.get("ash_storm_index", 0) or 0) + 1) % len(ASH_STORM_PATH)
    state["ash_storm_index"] = index
    state["ash_storm_position"] = ASH_STORM_PATH[index]
    if announce:
        prompt_info(game, "Wir popiołu", f"Wir popiołu przesuwa się na pole {ASH_STORM_PATH[index]}.", source=f"ash_storm:{index}")
    update_leds(game, "ash_storm")
    return ASH_STORM_PATH[index]


def expose_false_ash(game: Any) -> str:
    state = ensure_state(game)
    if bool(state.get("false_ash_exposed")):
        return "Fałszywy popiół został już porównany ze śladem ruin."
    state["false_ash_exposed"] = True
    shards = set(state.get("memory_shards_revealed") or [])
    shards.add("false_ash")
    state["memory_shards_revealed"] = sorted(shards)
    set_flag(game, "false_ash_exposed")
    msg = "Próbka z młyna nie pasuje do popiołu przysięgi. To spreparowany pył, którym ktoś próbował obciążyć Mirę."
    prompt_info(game, "Fałszywy popiół", msg, source="false_ash_exposed")
    update_leds(game, "active_anchor")
    return msg


def consume_hallowed_ash_vial(game: Any, actor: Any = None) -> tuple[bool, str]:
    state = ensure_state(game)
    if bool(state.get("hallowed_ash_vial_used")):
        return False, "Fiolka uświęconego popiołu została już zużyta."

    def _norm(value: Any) -> str:
        return str(value or "").strip().lower().replace("_", " ").replace("-", " ")

    names = {"hallowed ash vial", "fiolka uświęconego popiołu", "fiolka uswieconego popiolu", "hallowed ash"}
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
                state["hallowed_ash_vial_used"] = True
                state["ash_storm_suppressed_round"] = combat_round(game)
                return True, "Zużywacie fiolkę uświęconego popiołu. Wir cichnie na tę rundę."
    return False, "Nie macie fiolki uświęconego popiołu."


def support_fallen_arch(game: Any) -> str:
    state = ensure_state(game)
    if bool(state.get("fallen_arch_supported")):
        return "Zawalony łuk jest już podparty."
    state["fallen_arch_supported"] = True
    set_flag(game, "hill_ruins_arch_supported")
    update_leds(game, "hazard_clear")
    return "Łuk zostaje podparty. Otwiera się krótsze przejście do północnego anchora."


def anchor_bonus(game: Any, anchor_id: str) -> int:
    key = str(anchor_id or "").strip()
    if key == "oath" and (flag_enabled(game, "warden_medallion_recovered") or flag_enabled(game, "relic_theft_discovered")):
        return 2
    if key == "ash" and (flag_enabled(game, "false_ash_secured") or flag_enabled(game, "false_ash_hint")):
        return 2
    if key == "relic" and flag_enabled(game, "mill_ledger_secured"):
        return 2
    if key == "blood" and (flag_enabled(game, "chapel_confession_silence") or flag_enabled(game, "charred_deacon_defeated")):
        return 2
    return 0
