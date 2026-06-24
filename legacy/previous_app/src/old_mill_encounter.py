from __future__ import annotations

from typing import Any, Iterable


STATE_KEY = "old_mill_encounter"
ALARM_THRESHOLD = 3

TOVIN_POS = (5, 8)
GEAR_POS = (7, 9)
BEAM_POS = (6, 9)
SACKS_POS = (10, 7)
LEDGER_POS = (11, 8)
HOIST_POS = (8, 6)
BACK_TRACK_POS = (12, 7)
GUARD_POSITIONS = ((8, 7), (10, 8), (11, 9))

LED_IDLE = {
    TOVIN_POS: (130, 190, 255),
    GEAR_POS: (255, 185, 30),
    BEAM_POS: (130, 82, 35),
    SACKS_POS: (180, 180, 165),
    LEDGER_POS: (120, 95, 55),
    HOIST_POS: (255, 210, 80),
}


def ensure_state(game: Any) -> dict[str, Any]:
    state = getattr(game, STATE_KEY, None)
    if not isinstance(state, dict):
        state = {
            "alarm_level": 0,
            "alarm_threshold": ALARM_THRESHOLD,
            "tovin_secured": False,
            "tovin_in_danger": False,
            "tovin_dead": False,
            "false_ash_secured": False,
            "ledger_secured": False,
            "mill_mechanism_disabled": False,
            "beam_moved": False,
            "hidden_route_found": False,
            "guards_alerted": False,
            "evidence_threatened": False,
            "evidence_destroyed": False,
            "odran_warned": False,
            "rope_hoist_used": False,
            "overview_seen": False,
        }
        setattr(game, STATE_KEY, state)
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
    if not key:
        return
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


def prompt_info(game: Any, title: str, body: str, *, dedupe_key: str) -> None:
    text = str(body or "").strip()
    if not text:
        return
    player_prompt = getattr(game, "player_prompt", None)
    if player_prompt is not None and hasattr(player_prompt, "info"):
        try:
            player_prompt.info(
                title,
                body_markdown=text,
                summary="Stary Mlyn",
                source="old_mill_encounter",
                scope_key="old_mill_encounter",
                dedupe_key=dedupe_key,
                semantic_type="required_action",
            )
            return
        except Exception:
            pass
    try:
        game.ui_narration(text, summary=title, source="old_mill_encounter")
    except Exception:
        try:
            game.ui_log(text)
        except Exception:
            pass


def update_leds(game: Any, mode: str = "idle") -> None:
    conn = getattr(game, "conn", None)
    if conn is None:
        return
    state = ensure_state(game)
    mapping = dict(LED_IDLE)
    alarm = int(state.get("alarm_level", 0) or 0)
    if mode == "alarm_up" or alarm > 0:
        for pos in GUARD_POSITIONS:
            mapping[pos] = (255, 40, 30)
    if state.get("tovin_in_danger"):
        mapping[TOVIN_POS] = (255, 55, 55)
    if state.get("mill_mechanism_disabled"):
        mapping[GEAR_POS] = (170, 230, 255)
    if state.get("false_ash_secured"):
        mapping[SACKS_POS] = (45, 210, 95)
    if state.get("ledger_secured"):
        mapping[LEDGER_POS] = (45, 210, 95)
    if state.get("hidden_route_found"):
        mapping[BACK_TRACK_POS] = (45, 220, 90)
    if mode == "success":
        mapping[BACK_TRACK_POS] = (45, 220, 90)
        mapping[TOVIN_POS] = (45, 220, 90)
    if mode == "failure":
        for pos in (TOVIN_POS, SACKS_POS, LEDGER_POS):
            mapping[pos] = (180, 20, 20)
    setter = getattr(conn, "set_leds", None)
    if callable(setter):
        for pos, color in mapping.items():
            try:
                setter([pos], color)
            except TypeError:
                try:
                    setter(pos, color)
                except Exception:
                    continue
            except Exception:
                continue


def present_overview(game: Any) -> str:
    state = ensure_state(game)
    state["overview_seen"] = True
    update_leds(game, "idle")
    bonuses = active_context_notes(game)
    body = (
        "Wnetrze mlyna pracuje jak pulapka: mechanizm bije stalowym rytmem, Tovin siedzi zwiazany przy workach, "
        "a strażnicy Vale'a pilnują środka sali. Szare worki nie pachną zwykłą mąką. Przy tylnej ścianie deski układają "
        "się zbyt równo, jakby ukrywały wąski trakt.\n\n"
        "Mozecie dzialac po cichu, ale kazdy halas podnosi alarm: najpierw straznicy ustawiaja obrone, potem beda niszczyc "
        "dowody, zagrozic Tovinowi i wyslac ostrzezenie do Odrana."
    )
    if bonuses:
        body += "\n\nKontekst z poprzednich map: " + "; ".join(bonuses) + "."
    prompt_info(game, "Stary Mlyn", body, dedupe_key="old_mill:overview")
    return body


def active_context_notes(game: Any) -> list[str]:
    notes: list[str] = []
    if flag_enabled(game, "villager_mill_hint"):
        notes.append("wiesniacy wskazali worki przy mechanizmie")
    if flag_enabled(game, "elna_tovin_fear_seen"):
        notes.append("strach Elny pomaga uspokoic Tovina")
    if flag_enabled(game, "public_square_heartened"):
        notes.append("Tovin latwiej uwierzy, ze moze zeznawac")
    if flag_enabled(game, "vale_guards_shaken"):
        notes.append("straze Vale'a maja slabsze morale")
    if flag_enabled(game, "chapel_tracks_read"):
        notes.append("slady z kaplicy pasuja do popiolu w workach")
    if flag_enabled(game, "relic_theft_discovered"):
        notes.append("Tovin moze powiazac mlyn z kradzieza relikwiarza")
    if flag_enabled(game, "warden_medallion_recovered"):
        notes.append("ledger nabiera wiekszej wagi przeciw Odranowi")
    if flag_enabled(game, "charred_deacon_defeated"):
        notes.append("prawdziwy popiol rytualny z kaplicy rozni sie od falszywego pylu")
    return notes


def increase_alarm(game: Any, amount: int = 1, *, reason: str = "") -> int:
    state = ensure_state(game)
    old = int(state.get("alarm_level", 0) or 0)
    new = max(0, old + int(amount or 0))
    state["alarm_level"] = new
    if new >= 1:
        state["guards_alerted"] = True
        set_flag(game, "mill_alarm_raised")
    if new >= 2:
        state["evidence_threatened"] = True
    if new >= 3 and not state.get("tovin_secured"):
        state["tovin_in_danger"] = True
    if new >= 4:
        state["odran_warned"] = True
        set_flag(game, "odran_warned")
    update_leds(game, "alarm_up")
    details = alarm_status_text(new)
    if reason:
        details = f"{reason}\n\n{details}"
    prompt_info(game, "Alarm w mlynie", details, dedupe_key=f"old_mill:alarm:{new}:{reason}")
    return new


def alarm_status_text(level: int) -> str:
    if level <= 0:
        return "Alarm jest cichy. Straznicy jeszcze nie wiedza, ze weszliscie do srodka."
    if level == 1:
        return "Alarm 1: straznicy zwieraja szyk i pilnuja dojscia do Tovina."
    if level == 2:
        return "Alarm 2: tylny straznik zaczyna interesowac sie dowodami. Worki i ledger sa zagrozone."
    if level == 3:
        return "Alarm 3: Tovin jest bezposrednio zagrozony. Jesli go nie zabezpieczycie, cel mapy moze sie zalamac."
    return "Alarm 4: jeden ze straznikow probuje uciec tylnym traktem z raportem do Odrana."


def disable_mechanism(game: Any) -> str:
    state = ensure_state(game)
    if state.get("mill_mechanism_disabled"):
        return "Mechanizm mlyna jest juz unieruchomiony."
    state["mill_mechanism_disabled"] = True
    set_flag(game, "mill_mechanism_disabled")
    update_leds(game, "idle")
    message = "Dzwignia ustawia kola w martwym punkcie. Zolty puls przy mechanizmie przechodzi w zimne swiatlo."
    prompt_info(game, "Mechanizm mlyna", message, dedupe_key="old_mill:mechanism_disabled")
    return message


def secure_false_ash(game: Any) -> str:
    state = ensure_state(game)
    if state.get("false_ash_secured"):
        return "Probka falszywego popiolu jest juz zabezpieczona."
    state["false_ash_secured"] = True
    set_flag(game, "false_ash_found")
    set_flag(game, "false_ash_secured")
    update_leds(game, "idle")
    message = "Zabezpieczacie probke falszywego popiolu. To nie jest popiol z kaplicy, tylko przygotowany pyl z dodatkiem sadzy i ziol."
    if flag_enabled(game, "charred_deacon_defeated"):
        message += " Po kaplicy roznica jest oczywista: ten pyl udaje rytualny slad, ale nie niesie zadnej swietej ani nekrotycznej mocy."
    prompt_info(game, "Falszywy popiol", message, dedupe_key="old_mill:false_ash_secured")
    return message


def secure_ledger(game: Any) -> str:
    state = ensure_state(game)
    if state.get("ledger_secured"):
        return "Strona księgi jest już zabezpieczona."
    state["ledger_secured"] = True
    set_flag(game, "mill_ledger_secured")
    update_leds(game, "idle")
    message = "Z księgi wypada strona z płatnościami dla ludzi Vale'a. Przy jednej pozycji zapisano: 'popiół przed nocą kaplicy'."
    if flag_enabled(game, "warden_medallion_recovered"):
        message += " Z medalionem strażniczki i pieczęcią Vale'a ta strona tworzy mocny łańcuch dowodów przeciw Odranowi."
    prompt_info(game, "Księga młyna", message, dedupe_key="old_mill:ledger_secured")
    return message


def secure_tovin(game: Any) -> str:
    state = ensure_state(game)
    if state.get("tovin_dead"):
        return "Tovin nie zyje. Mozecie nadal zabezpieczyc dowody, ale swiadek zostal utracony."
    if state.get("tovin_secured"):
        return "Tovin jest juz zabezpieczony."
    state["tovin_secured"] = True
    state["tovin_in_danger"] = False
    set_flag(game, "tovin_secured")
    set_flag(game, "tovin_rescued")
    set_flag(game, "tovin_ready_to_testify")
    save_checkpoint(game, "tovin_rescued")
    update_leds(game, "success")
    message = "Tovin jest wolny. Trzyma sie sciany, ale oddycha rowno i wskazuje tylna czesc mlyna: 'Tamtedy wynosili worki do ruin'."
    if flag_enabled(game, "public_square_heartened"):
        message += " Wie, ze rynek nie jest juz calkiem sparalizowany strachem, wiec zgadza sie zeznawac."
    prompt_info(game, "Tovin uratowany", message, dedupe_key="old_mill:tovin_secured")
    return message


def mark_tovin_dead(game: Any, *, reason: str = "") -> str:
    state = ensure_state(game)
    if state.get("tovin_secured"):
        return "Tovin jest zabezpieczony; straznicy nie moga juz uzyc go jako zakladnika."
    state["tovin_dead"] = True
    state["tovin_in_danger"] = False
    set_flag(game, "tovin_dead")
    update_leds(game, "failure")
    message = "Cel ratunkowy przepada: Tovin ginie w zamieszaniu."
    if reason:
        message += f" {reason}"
    message += " Scenariusz trwa dalej, ale tracicie swiadka przeciw Odranowi."
    prompt_info(game, "Tovin utracony", message, dedupe_key="old_mill:tovin_dead")
    return message


def use_rope_hoist(game: Any) -> str:
    state = ensure_state(game)
    if state.get("rope_hoist_used"):
        return "Wciagarka jest juz zerwana."
    state["rope_hoist_used"] = True
    set_flag(game, "mill_rope_hoist_used")
    message = "Worki spadaja z wciagarki i zasypuja przejscie. Przez jedna runde straznik albo minion na tej linii powinien byc spowolniony lub zmuszony do obejscia."
    prompt_info(game, "Wciagarka", message, dedupe_key="old_mill:rope_hoist_used")
    return message


def reveal_hidden_route(game: Any) -> str:
    state = ensure_state(game)
    if state.get("hidden_route_found"):
        return "Ukryty trakt do ruin jest juz odkryty."
    state["hidden_route_found"] = True
    set_flag(game, "hidden_mill_route_found")
    save_checkpoint(game, "hidden_mill_route_found")
    session = getattr(game, "scenario_session", None)
    revealer = getattr(session, "reveal_object", None)
    if callable(revealer):
        try:
            revealer(
                "old_mill",
                "mill_hidden_track",
                state_updates={"hidden": False, "revealed": True},
                message="Z tylu mlyna otwiera sie waski trakt do ruin.",
            )
        except Exception:
            pass
    update_leds(game, "success")
    message = "Deski przy tylnej scianie odchylaja sie. Zielony LED wyznacza waski trakt prowadzacy ku ruinom."
    prompt_info(game, "Ukryty trakt", message, dedupe_key="old_mill:hidden_route_found")
    return message


def evidence_destroyed(game: Any) -> str:
    state = ensure_state(game)
    if state.get("false_ash_secured") and state.get("ledger_secured"):
        return "Dowody sa juz zabezpieczone."
    state["evidence_destroyed"] = True
    set_flag(game, "mill_evidence_destroyed")
    message = "Straznicy niszcza czesc dowodow. Nadal mozna ratowac Tovina i szukac traktu, ale sprawa przeciw Odranowi bedzie slabsza."
    prompt_info(game, "Dowody zagrozone", message, dedupe_key="old_mill:evidence_destroyed")
    return message


def morale_option_available(game: Any) -> bool:
    return bool(
        flag_enabled(game, "vale_guards_shaken")
        or flag_enabled(game, "warden_medallion_recovered")
        or flag_enabled(game, "relic_theft_discovered")
    )


def tactical_ai_notes(game: Any) -> list[str]:
    state = ensure_state(game)
    notes = [
        "najblizszy straznik blokuje dojscie do Tovina",
        "egzekutor spycha lub przewraca bohaterow w strone mechanizmu",
    ]
    alarm = int(state.get("alarm_level", 0) or 0)
    if alarm >= 2:
        notes.append("tylny straznik probuje niszczyc worki albo ledger")
    if alarm >= 4:
        notes.append("jeden przeciwnik probuje uciec ukrytym traktem z raportem do Odrana")
    if morale_option_available(game):
        notes.append("mocne dowody pozwalaja nacisnac morale straznikow Intimidation/Diplomacy")
    return notes


def all_positions() -> Iterable[tuple[int, int]]:
    return (TOVIN_POS, GEAR_POS, BEAM_POS, SACKS_POS, LEDGER_POS, HOIST_POS, BACK_TRACK_POS, *GUARD_POSITIONS)
