from __future__ import annotations

from typing import Any


STATE_KEY = "_oath_crypt_state"
PROOF_REQUIRED = 4

SERAI_POS = (5, 15)
ODRAN_POS = (16, 15)
RELIQUARY_POS = (10, 15)
ODRAN_GATE_POS = (18, 15)
PROOF_PILLAR_POSITIONS = {
    "oath": (4, 5),
    "ash": (15, 5),
    "ledger": (4, 24),
    "witness": (15, 24),
}
PROOF_PILLAR_LABELS = {
    "oath": "Filar Przysięgi",
    "ash": "Filar Popiołu",
    "ledger": "Filar Księgi",
    "witness": "Filar Świadka",
}
HAZARD_POSITIONS = ((8, 10), (9, 10), (11, 20), (12, 20), (2, 14), (17, 14))
CHAIN_POSITIONS = ((9, 13), (11, 13), (9, 17), (11, 17))


def ensure_state(game: Any) -> dict[str, Any]:
    state = getattr(game, STATE_KEY, None)
    if not isinstance(state, dict):
        state = {
            "trial_started": False,
            "proof_score": 0,
            "proof_required": PROOF_REQUIRED,
            "oath_integrity": 4,
            "serai_trust": 0,
            "odran_pressure": 0,
            "odran_confronted": False,
            "odran_escape_started": False,
            "relic_stabilized": False,
            "restore_oath_unlocked": False,
            "bargain_unlocked": False,
            "final_choice_locked": False,
            "oath_restored": False,
            "odran_escaped": False,
            "costly_ending_triggered": False,
            "proofs_presented": [],
            "overview_seen": False,
        }
        setattr(game, STATE_KEY, state)
    if flag_enabled(game, "odran_warned"):
        state["odran_pressure"] = max(int(state.get("odran_pressure", 0) or 0), 1)
    return state


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
                source=f"oath_crypt:{source}",
                summary="Krypta Przysięgi",
                scope_key="oath_crypt_encounter",
                dedupe_key=f"oath_crypt:{source}",
                semantic_type="required_action",
            )
            return
        except Exception:
            pass
    try:
        game.ui_narration(text, summary=title, source=f"oath_crypt:{source}")
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
        SERAI_POS: [190, 220, 255],
        ODRAN_POS: [120, 15, 20],
        ODRAN_GATE_POS: [80, 10, 10],
        RELIQUARY_POS: [55, 55, 70],
    }
    completed = set(state.get("proofs_presented") or [])
    for proof_id, pos in PROOF_PILLAR_POSITIONS.items():
        updates[pos] = [45, 55, 95]
        if proof_id in completed:
            updates[pos] = [210, 235, 255]
    for index, pos in enumerate(CHAIN_POSITIONS, start=1):
        updates[pos] = [120, 120, 135] if int(state.get("proof_score", 0) or 0) < index else [25, 25, 30]
    for pos in HAZARD_POSITIONS:
        updates[pos] = [150, 45, 40]
    if mode == "trial_started":
        updates[RELIQUARY_POS] = [190, 210, 235]
    if mode == "active_proof":
        for proof_id, pos in PROOF_PILLAR_POSITIONS.items():
            if proof_id not in completed:
                updates[pos] = [255, 215, 85]
                break
    if bool(state.get("restore_oath_unlocked")):
        updates[RELIQUARY_POS] = [245, 250, 255]
    if bool(state.get("bargain_unlocked")):
        updates[ODRAN_GATE_POS] = [160, 20, 20]
    if bool(state.get("odran_escape_started")):
        updates[ODRAN_GATE_POS] = [180, 45, 20]
    if mode == "oath_restored":
        updates[RELIQUARY_POS] = [220, 255, 220]
        updates[SERAI_POS] = [220, 255, 240]
    if mode == "costly_ending":
        updates[ODRAN_GATE_POS] = [220, 20, 20]
        updates[RELIQUARY_POS] = [90, 15, 20]
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
    start_trial(game, announce=False)
    text = (
        "Krypta Przysięgi zajmuje całą planszę. Biały LED przy Serai to krąg sądu, "
        "ciemnoczerwony punkt po wschodniej stronie to Odran, a przygaszony relikwiarz w centrum "
        "odblokuje się dopiero po czterech przyjętych dowodach. Cztery filary w ćwiartkach planszy "
        "odpowiadają przysiędze, popiołowi, księdze młyna i świadkowi."
    )
    if flag_enabled(game, "odran_warned"):
        text += " Odran został ostrzeżony, więc jego presja na bramę zaczyna się szybciej."
    prompt_info(game, "Krypta Przysięgi", text, source="overview")
    update_leds(game, "active_proof")
    return text


def start_trial(game: Any, *, announce: bool = True) -> None:
    state = ensure_state(game)
    if bool(state.get("trial_started")):
        return
    state["trial_started"] = True
    set_flag(game, "oath_trial_started")
    save_checkpoint(game, "oath_trial_started")
    if announce:
        prompt_info(
            game,
            "Sąd Przysięgi",
            "Serai nie żąda walki. Żąda prawdy. Każdy filar może przyjąć jeden dowód, a relikwiarz pozostanie zimny, dopóki oskarżenie przeciw Odranowi nie zostanie domknięte.",
            source="trial_started",
        )
    update_leds(game, "trial_started")


def proof_bonus(game: Any, proof_id: str) -> int:
    key = str(proof_id or "").strip()
    if key == "oath" and any(flag_enabled(game, flag) for flag in ("warden_medallion_recovered", "odran_relic_theft_proven", "relic_theft_discovered")):
        return 3
    if key == "ash" and any(flag_enabled(game, flag) for flag in ("false_ash_secured", "false_ash_exposed", "chapel_tracks_read")):
        return 3
    if key == "ledger" and any(flag_enabled(game, flag) for flag in ("mill_ledger_secured", "relic_theft_discovered")):
        return 3
    if key == "witness" and any(flag_enabled(game, flag) for flag in ("tovin_rescued", "tovin_ready_to_testify", "mira_truth_learned", "mira_allied")):
        return 3
    return 0


def proof_flag(proof_id: str) -> str:
    return {
        "oath": "proof_of_oath_presented",
        "ash": "proof_of_false_ash_presented",
        "ledger": "proof_of_ledger_presented",
        "witness": "proof_of_witness_presented",
    }.get(str(proof_id or "").strip(), "proof_presented")


def present_proof(game: Any, proof_id: str, *, method: str = "test") -> tuple[bool, str]:
    start_trial(game)
    state = ensure_state(game)
    key = str(proof_id or "").strip()
    if key in set(state.get("proofs_presented") or []):
        return False, f"{PROOF_PILLAR_LABELS.get(key, 'Filar')} już przyjął dowód."
    presented = set(state.get("proofs_presented") or [])
    presented.add(key)
    state["proofs_presented"] = sorted(presented)
    state["proof_score"] = min(int(state.get("proof_required", PROOF_REQUIRED) or PROOF_REQUIRED), int(state.get("proof_score", 0) or 0) + 1)
    state["serai_trust"] = int(state.get("serai_trust", 0) or 0) + 1
    set_flag(game, proof_flag(key))
    progress = int(state.get("proof_score", 0) or 0)
    required = int(state.get("proof_required", PROOF_REQUIRED) or PROOF_REQUIRED)
    if progress >= 3:
        state["odran_escape_started"] = True
        set_flag(game, "odran_escape_started")
    if progress >= required:
        unlock_restore(game)
        return True, "Czwarty dowód zostaje przyjęty. Łańcuchy przy relikwiarzu gasną, a Odran nie ma już gdzie ukryć kłamstwa."
    update_leds(game, "active_proof")
    return True, f"Dowód przyjęty przez {PROOF_PILLAR_LABELS.get(key, 'filar')}: {progress}/{required}."


def reject_proof(game: Any, *, reason: str = "proof_failure") -> str:
    state = ensure_state(game)
    state["odran_pressure"] = int(state.get("odran_pressure", 0) or 0) + 1
    integrity = max(0, int(state.get("oath_integrity", 4) or 0) - 1)
    state["oath_integrity"] = integrity
    msg = "Krypta odrzuca niepełny dowód. Czerwony rozbłysk oznacza, że Odran zyskuje chwilę presji."
    if integrity <= 1:
        state["odran_escape_started"] = True
        set_flag(game, "odran_escape_started")
        msg += " Brama Odrana zaczyna pulsować; próbuje wymknąć się z relikwią."
    prompt_info(game, "Dowód odrzucony", msg, source=f"proof_rejected:{reason}")
    update_leds(game, "proof_rejected")
    return msg


def unlock_restore(game: Any) -> str:
    state = ensure_state(game)
    state["restore_oath_unlocked"] = True
    state["bargain_unlocked"] = True
    state["odran_confronted"] = True
    state["relic_stabilized"] = True
    set_flag(game, "serai_accepts_truth")
    set_flag(game, "odran_confronted")
    set_flag(game, "restore_oath_unlocked")
    set_flag(game, "bargain_unlocked")
    save_checkpoint(game, "odran_confronted")
    prompt_info(
        game,
        "Relikwiarz odblokowany",
        "Serai przyjmuje prawdę. Relikwiarz świeci pełnym białym światłem; możecie przywrócić przysięgę albo świadomie pozwolić Odranowi odejść z relikwią.",
        source="restore_unlocked",
    )
    update_leds(game, "restore_oath_unlocked")
    return "Relikwiarz jest gotowy do przywrócenia przysięgi."


def confront_odran(game: Any) -> str:
    state = ensure_state(game)
    state["odran_confronted"] = True
    state["bargain_unlocked"] = True
    set_flag(game, "odran_confronted")
    set_flag(game, "bargain_unlocked")
    save_checkpoint(game, "odran_confronted")
    update_leds(game, "odran_pressure")
    return "Odran wypowiedział układ na głos. Od tej chwili Brama Odrana jest świadomą, kosztowną decyzją finałową."


def mark_oath_restored(game: Any) -> None:
    state = ensure_state(game)
    state["oath_restored"] = True
    state["final_choice_locked"] = True
    set_flag(game, "oath_restored")
    save_checkpoint(game, "oath_restored")
    update_leds(game, "oath_restored")


def mark_costly_ending(game: Any) -> None:
    state = ensure_state(game)
    state["odran_escaped"] = True
    state["costly_ending_triggered"] = True
    state["final_choice_locked"] = True
    update_leds(game, "costly_ending")
