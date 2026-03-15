from __future__ import annotations

from bonuses import BonusEffect, BonusType
from statuses import MageArmorStatus, SpeedBonusStatus, Status


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _remove_status(actor, status_id: str) -> int:
    if actor is None:
        return 0
    removed = 0
    statuses = list(getattr(actor, "statuses", []) or [])
    kept = []
    for status in statuses:
        sid = _normalize(getattr(status, "id", status))
        if sid == _normalize(status_id):
            removed += 1
            continue
        kept.append(status)
    if removed:
        try:
            setattr(actor, "statuses", kept)
        except Exception:
            pass
    return removed


def _add_bonus(actor, effect: BonusEffect) -> None:
    if actor is None:
        return
    adder = getattr(actor, "add_bonus", None)
    if callable(adder):
        try:
            adder(effect)
        except Exception:
            pass


def _heal_actor(actor, amount: int) -> int:
    if actor is None:
        return 0
    amount = max(0, int(amount or 0))
    healer = getattr(actor, "heal", None)
    if callable(healer):
        try:
            before = _safe_int(getattr(actor, "wounds", 0), 0)
            healer(amount)
            after = _safe_int(getattr(actor, "wounds", 0), 0)
            return max(0, before - after)
        except Exception:
            return 0
    return 0


def _heal_fraction_missing_hp(actor, fraction: float) -> int:
    if actor is None:
        return 0
    max_hp = max(1, _safe_int(getattr(actor, "max_hp", 1), 1))
    current_wounds = max(0, _safe_int(getattr(actor, "wounds", 0), 0))
    missing_hp = max(0, min(max_hp, current_wounds))
    heal_amount = max(1, int(round(float(missing_hp) * float(fraction)))) if missing_hp > 0 else 0
    return _heal_actor(actor, heal_amount)


def _append_hireling(actor, *, kind: str, skill_bonus: int) -> None:
    if actor is None:
        return
    hirelings = list(getattr(actor, "hirelings", []) or [])
    hirelings.append(
        {
            "kind": str(kind),
            "skill_bonus": int(skill_bonus),
            "active": True,
        }
    )
    try:
        setattr(actor, "hirelings", hirelings)
    except Exception:
        pass


def _add_service_credit(actor, *, credit_type: str, amount: int = 1) -> int:
    if actor is None:
        return 0
    credits = dict(getattr(actor, "service_credits", {}) or {})
    key = _normalize(credit_type)
    credits[key] = max(0, _safe_int(credits.get(key), 0) + int(amount))
    try:
        setattr(actor, "service_credits", credits)
    except Exception:
        pass
    return int(credits.get(key, 0))


def apply_service_effect(service_id: str, *, actor, game=None, provider_name: str = "") -> list[str]:
    sid = _normalize(service_id)
    out: list[str] = []
    provider = str(provider_name or "").strip()

    # Gospoda: jedzenie / nocleg / napoje
    if sid == "meal_poor":
        healed = _heal_actor(actor, 1)
        if healed > 0:
            out.append(f"Posilek ubogi: odnowiono {healed} HP.")
    elif sid == "meal_square":
        healed = _heal_actor(actor, 2)
        if healed > 0:
            out.append(f"Posilek syty: odnowiono {healed} HP.")
    elif sid == "meal_fine_dining":
        healed = _heal_actor(actor, 4)
        removed = _remove_status(actor, "fatigued")
        if healed > 0:
            out.append(f"Posilek wykwintny: odnowiono {healed} HP.")
        if removed:
            out.append("Posilek wykwintny: usunieto fatigued.")
    elif sid == "lodging_floor_space_day":
        healed = _heal_fraction_missing_hp(actor, 0.25)
        if healed > 0:
            out.append(f"Nocleg (podloga): odnowiono {healed} HP.")
    elif sid == "lodging_bed_day":
        healed = _heal_fraction_missing_hp(actor, 0.50)
        if healed > 0:
            out.append(f"Nocleg (lozko): odnowiono {healed} HP.")
    elif sid == "lodging_private_room_day":
        healed = _heal_fraction_missing_hp(actor, 0.75)
        removed = _remove_status(actor, "fatigued")
        if healed > 0:
            out.append(f"Nocleg (pokoj prywatny): odnowiono {healed} HP.")
        if removed:
            out.append("Nocleg (pokoj prywatny): usunieto fatigued.")
    elif sid == "lodging_extravagant_suite_day":
        healed = _heal_fraction_missing_hp(actor, 1.0)
        removed = _remove_status(actor, "fatigued")
        if healed > 0:
            out.append(f"Nocleg (apartament): odnowiono {healed} HP.")
        if removed:
            out.append("Nocleg (apartament): usunieto fatigued.")
    elif sid == "bottle_of_fine_wine":
        _add_bonus(
            actor,
            BonusEffect(
                type=BonusType.CIRCUMSTANCE,
                value=1,
                tag="diplomacy",
                source="service:fine_wine",
                label="fine wine",
                duration_turns=10,
            ),
        )
        out.append("Butelka dobrego wina: +1 circumstance do Diplomacy (10 tur).")

    # Hirelings
    elif sid == "hireling_unskilled_day":
        _append_hireling(actor, kind="unskilled", skill_bonus=0)
        out.append("Zatrudniono najemnika niewykwalifikowanego (+0).")
    elif sid == "hireling_skilled_day":
        _append_hireling(actor, kind="skilled", skill_bonus=4)
        out.append("Zatrudniono najemnika wykwalifikowanego (+4 w specjalizacji).")

    # Ogolne uslugi spellcasting z CRB (kredyt na przyszle rozliczenie)
    elif sid.startswith("spellcasting_service_rank_"):
        rank = sid.rsplit("_", 1)[-1]
        current = _add_service_credit(actor, credit_type=f"spellcasting_rank_{rank}", amount=1)
        out.append(
            f"Usluga rzucenia czaru (ranga {rank}): dodano kredyt uslugowy. "
            f"Aktywne kredyty rangi {rank}: {current}."
        )

    # Mage NPC
    elif sid == "mage_service_mage_armor":
        remover = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("mage_armor:")
            except Exception:
                pass
        _add_bonus(
            actor,
            BonusEffect(
                type=BonusType.ITEM,
                value=1,
                tag="ac",
                source="mage_armor:service",
                label="mage armor",
                duration_turns=10,
            ),
        )
        try:
            actor.add_status(MageArmorStatus(duration=10, source="service:mage_armor"))
        except Exception:
            pass
        out.append("Usluga maga: Mage Armor (+1 item AC, 10 tur).")
    elif sid == "mage_service_magic_weapon":
        remover = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("magic_weapon:")
            except Exception:
                pass
        for tag in ("attack_melee", "attack_ranged"):
            _add_bonus(
                actor,
                BonusEffect(
                    type=BonusType.ITEM,
                    value=1,
                    tag=tag,
                    source="magic_weapon:service",
                    label="magic weapon",
                    duration_turns=1,
                ),
            )
        out.append("Usluga maga: Magic Weapon (+1 item do ataku, 1 tura).")
    elif sid == "mage_service_longstrider":
        try:
            actor.add_status(SpeedBonusStatus(bonus_feet=10, duration=10, source="service:longstrider", label="longstrider +10ft"))
        except Exception:
            pass
        out.append("Usluga maga: Longstrider (+10 ft Speed, 10 tur).")

    # Priest NPC
    elif sid == "priest_service_heal_minor":
        healed = _heal_actor(actor, 12)
        out.append(f"Usluga kaplana: Leczenie mniejsze (odnowiono {healed} HP).")
    elif sid == "priest_service_heal_major":
        healed = _heal_actor(actor, 28)
        out.append(f"Usluga kaplana: Leczenie wieksze (odnowiono {healed} HP).")
    elif sid == "priest_service_bless":
        for tag in ("attack_melee", "attack_ranged", "magic"):
            _add_bonus(
                actor,
                BonusEffect(
                    type=BonusType.STATUS,
                    value=1,
                    tag=tag,
                    source="bless:service",
                    label="bless",
                    duration_turns=10,
                ),
            )
        try:
            actor.add_status(
                Status(
                    id="bless_service",
                    label="Bless",
                    duration=10,
                    source="service:priest",
                    data={"ui_description": "+1 status do atakow przez 10 tur."},
                )
            )
        except Exception:
            pass
        out.append("Usluga kaplana: Bless (+1 status do atakow, 10 tur).")
    elif sid == "priest_service_remove_fear":
        removed = 0
        for fear_id in ("frightened", "fear", "panic"):
            removed += _remove_status(actor, fear_id)
        if removed > 0:
            out.append(f"Usluga kaplana: usunieto efekty strachu ({removed}).")
        else:
            out.append("Usluga kaplana: brak aktywnych efektow strachu do usuniecia.")

    if not out and sid:
        who = f" ({provider})" if provider else ""
        out.append(f"Zakupiono usluge{who}: {sid}. Efekt mechaniczny: brak (fabularnie).")
    if game is not None:
        logger_fn = getattr(game, "ui_log", None)
        if callable(logger_fn):
            for line in out:
                try:
                    logger_fn(line)
                except Exception:
                    continue
    return out


__all__ = ["apply_service_effect"]

