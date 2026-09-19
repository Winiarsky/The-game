"""UI-driven Mission 0 playthroughs, deterministic physical cards and dice.

Run against the isolated audit server on localhost:8765 and Chrome CDP:9223.
Only visible UI controls and the board field-input endpoint drive gameplay.
"""

from __future__ import annotations
import json, random, time, re
from pathlib import Path
from typing import Any
from mission_playtest_browser import Browser, REPORT


class Playtest:
    def __init__(self, name: str = "p3", seed: int = 180903) -> None:
        self.b = Browser()
        self.name = name
        self.file = REPORT / f"{name}-driver.json"
        saved = json.loads(self.file.read_text()) if self.file.exists() else {}
        self.rng = random.Random(seed)
        if saved.get("random"):
            self.rng.setstate(self.tuples(saved["random"]))
        self.deck = saved.get("deck", [])
        self.flags = set(saved.get("flags", []))
        self.step = saved.get("step", 0)

    def tuples(self, x: Any) -> Any:
        return tuple(self.tuples(v) for v in x) if isinstance(x, list) else x

    def save(self) -> None:
        self.file.write_text(
            json.dumps(
                dict(
                    random=self.rng.getstate(),
                    deck=self.deck,
                    flags=list(self.flags),
                    step=self.step,
                )
            )
        )

    def view(self) -> dict[str, Any]:
        self.b.wait()
        return self.b.evaluate(
            "({mission:state.mission,confrontation:state.exploration_mana,combat:state.combat,setup:state.encounter_setup,board:state.board_selection,roll:keyboardRollWizard?{review:keyboardRollWizard.review,index:keyboardRollWizard.index}:null,actors:state.actors})"
        )

    def log(self, action: str, **data: Any) -> None:
        self.step += 1
        with (REPORT / f"{self.name}-events.jsonl").open("a") as f:
            f.write(
                json.dumps(
                    dict(step=self.step, time=time.time(), action=action, **data),
                    ensure_ascii=False,
                )
                + "\n"
            )
        self.save()

    def record(self, p: dict[str, Any]) -> None:
        m = p.get("mission") or {}
        c = p.get("confrontation") or {}
        combat = p.get("combat") or {}
        key = (
            "scene:"
            + str(m.get("stage"))
            + ":"
            + str((m.get("text") or {}).get("title"))
        )
        if c.get("active"):
            key += (
                ":"
                + str(c.get("scene", {}).get("id"))
                + ":"
                + c.get("phase", "")
                + ":"
                + c.get("mana", {}).get("phase", "")
            )
        if key not in self.flags:
            self.flags.add(key)
            self.log(
                "scene",
                stage=m.get("stage"),
                text=m.get("text"),
                confrontation=c.get("scene", {}).get("name"),
                body=self.b.evaluate(
                    "document.querySelector('#mission-panel')?.innerText||document.body.innerText"
                ),
            )
            self.b.shot(self.name + "-" + str(self.step) + "-" + str(m.get("stage")))

    def field(self, col: int, row: int) -> None:
        self.log("board", col=col, row=row)
        self.b.field(col, row)

    def option(self, options: list[dict[str, Any]], action: str, **extra: Any) -> None:
        choice = next(
            (
                c
                for c in options
                if c["action"] == action
                and all(c.get("extra", {}).get(k) == v for k, v in extra.items())
            ),
            None,
        )
        if not choice:
            raise RuntimeError(f"Missing visible option {action} {extra}")
        self.log("choice", label=choice["label"], action_id=action, extra=extra)
        self.field(19, 29 - choice["slot"])

    def dice(self) -> None:
        for _ in range(12):
            p = self.view()
            w = p["roll"]
            if not w:
                return
            if w.get("review"):
                self.log(
                    "dice_review",
                    text=self.b.evaluate(
                        "document.getElementById('keyboard-roll-wizard').innerText"
                    ),
                )
                self.b.click(
                    '#keyboard-roll-wizard button[onclick="submitKeyboardRollWizard()"]'
                )
                return
            sides = self.b.evaluate(
                "Number(document.getElementById('keyboard-roll-wizard-input').max)"
            )
            if not sides:
                raise RuntimeError("No die sides")
            value = self.rng.randint(1, sides)
            self.log("physical_die", sides=sides, natural=value)
            self.b.evaluate(
                "(()=>{const el=document.getElementById('keyboard-roll-wizard-input');el.focus();el.select()})()"
            )
            self.b.call("Input.insertText", dict(text=str(value)))
            if "tested-plus-minus" not in self.flags and value < sides:
                self.field(19, 2)
                self.field(19, 3)
                self.flags.add("tested-plus-minus")
            self.b.click(
                '#keyboard-roll-wizard button[onclick="confirmKeyboardRollStep()"]'
            )
        raise RuntimeError("Dice wizard loop")

    def confrontation(self, c: dict[str, Any]) -> None:
        choices = c["board_choices"]
        phase = c["phase"]
        pool = c["mana"]
        recovery = re.search(r"Oddech:.*?\(([CBZFN])\)", c.get("last", ""))
        if recovery and pool["deck"] == len(self.deck) + 1:
            self.deck.append(recovery[1])
            self.log("physical_return", color=recovery[1], instruction=c["last"])
        if phase == "recovery":
            self.deck.append(c["recovery_color"])
            self.option(choices, "confirm_recovery")
        elif c.get("compromise_pending"):
            self.option(choices, "decline_compromise")
        elif phase == "introduction":
            self.option(choices, "acknowledge")
        elif phase == "approach":
            best = max((a for a in c["approaches"] if a["available"]), key=lambda a: max(0, min(1, (21-a["dc"]+a["modifier"])/20)) * ((a["die"]+1)/2+a["modifier"]))
            self.option(choices, "approach", approach=best["id"])
        elif phase == "peek_choice":
            self.option(choices, "peek_finish", move_top=False)
        elif phase == "setup":
            self.deck = [color for color in "CBZFN" for _ in range(pool["copies"])]
            self.rng.shuffle(self.deck)
            self.log(
                "physical_shuffle",
                copies=pool["copies"],
                deck=self.deck.copy(),
                scene=c["scene"]["name"],
            )
            self.option(choices, "acknowledge")
        elif c["needs_resume"]:
            self.option(choices, "resume")
        elif pool["phase"] in ("reveal", "burn"):
            if len(self.deck) != pool["deck"]:
                raise RuntimeError(
                    f"Physical deck mismatch: {len(self.deck)} != {pool['deck']}"
                )
            if not self.deck:
                raise RuntimeError("Physical deck empty before requested draw")
            color = self.deck[0]
            self.option(choices, "color", color=color)
            self.deck.pop(0)
            self.log(
                "physical_draw",
                color=color,
                reason=pool["phase"],
                remaining=len(self.deck),
            )
        elif pool["phase"] == "choose":
            hero = next(h for h in c["party"] if h["id"] == c["actor"])
            index = max(
                range(len(pool["offer"])),
                key=lambda i: hero["values"][pool["offer"][i]],
            )
            self.option(choices, "take", index=index)
        elif phase == "turn":
            if any(x["action"] == "compromise" for x in choices) and self.name in (
                "p3",
                "p5",
            ):
                self.option(choices, "compromise")
                return
            if c["dc"] >= 25 and self.rng.random() < 0.5:
                supports = [x for x in choices if x["action"] == "support"]
                if supports:
                    candidates = {h["id"]: h for h in c["party"]}
                    best = min(
                        supports, key=lambda x: candidates[x["extra"]["target"]]["dc"]
                    )
                    self.option(choices, "support", **best["extra"])
                    return
            bonus = max(x["extra"]["bonus"] for x in choices if x["action"] == "test")
            self.option(choices, "test", bonus=bonus)
        elif phase == "reaction":
            self.option(choices, "react")
        elif phase in ("after_action", "after_reaction"):
            self.option(choices, "advance")
        elif phase == "result":
            self.log(
                "confrontation_result",
                outcome=c["outcome"],
                rounds=c["round"],
                deck=pool["deck"],
                text=c["result"],
            )
            self.option(choices, "next")
        else:
            raise RuntimeError(f'Unhandled confrontation {phase}/{pool["phase"]}')

    def combat_pool(self, pool: dict[str, Any]) -> None:
        choices = pool["choices"]
        phase = pool["phase"]
        if phase in ("setup", "drain"):
            self.deck = [c for c in "CBZFN" for _ in range(pool["copies"])]
            self.rng.shuffle(self.deck)
            self.log(
                "physical_shuffle",
                deck=self.deck.copy(),
                copies=pool["copies"],
                scene="combat " + phase,
            )
            choice = next(c for c in choices if c["command"] == "pool_shuffle")
        elif phase == "choose":
            hero = next(h for h in pool["hands"] if h["hero"] == pool["actor"])
            index = max(
                range(len(pool["offer"])),
                key=lambda i: hero["values"][pool["offer"][i]],
            )
            choice = next(
                c
                for c in choices
                if c["command"] == "pool_take" and c["index"] == index
            )
        elif any(c["command"] == "pool_color" for c in choices):
            if len(self.deck) != pool["deck"]:
                raise RuntimeError(
                    f"Physical combat deck mismatch: {len(self.deck)} != {pool['deck']}"
                )
            if not self.deck:
                raise RuntimeError("Physical combat deck empty")
            color = self.deck.pop(0)
            choice = next(c for c in choices if c.get("color") == color)
            self.log(
                "physical_draw", color=color, reason=phase, remaining=len(self.deck)
            )
        else:
            raise RuntimeError("Unknown pool " + str(choices))
        self.log("combat_pool", phase=phase, label=choice["label"])
        self.field(19, 29 - choice["slot"])

    def combat_step(self, c: dict[str, Any]) -> None:
        if c.get("status") == "finished":
            self.log(
                "combat_finished",
                round=c["round_number"],
                outcome=c["encounter_result"],
                hp={a["id"]: a["hp"] for a in c["actors"]},
            )
            self.b.shot(self.name + "-combat-finished")
            self.b.click('button[onclick="resolveCombatOutcome()"]')
            return
        pool = (c.get("shared_mana") or {}).get("pool_view") or {}
        if pool.get("choices"):
            self.combat_pool(pool)
            return
        if (c.get("shared_mana") or {}).get("declaration"):
            self.field(19, 1)
            return
        actor = c["current_actor"]
        menu = c.get("turn_action_menu") or {}
        key = f"combat-turn:{c['round_number']}:{actor['id']}"
        if key not in self.flags:
            self.flags.add(key)
            self.log(
                "combat_turn",
                round=c["round_number"],
                actor=actor["id"],
                hp={a["id"]: a["hp"] for a in c["actors"]},
                body=self.b.inspect()["body"][-6500:],
            )
            self.b.shot(self.name + "-" + key.replace(":", "-"))
        if actor["faction"] == "enemy":
            preview = c.get("enemy_turn_preview") or {}
            if preview.get("kind") == "movement":
                self.field(*preview["destination"])
            elif preview.get("target_position"):
                self.field(*preview["target_position"])
            else:
                self.field(19, 1)
            return
        if (
            c.get("pending_player_attack")
            or c.get("movement_preview")
            or c.get("pending_board_selection")
            or c.get("pending_enemy_saving_throw")
        ):
            self.field(19, 1)
            return
        if c.get("reaction_window") or c.get("pending_opportunity_movement"):
            raise RuntimeError("Need reaction policy")
        if menu.get("stage") == "preview":
            op = menu["options"][menu["selected_index"]]
            if op["action"] == "move":
                enemies = [
                    a for a in c["actors"] if a["faction"] == "enemy" and a["hp"] > 0
                ]
                destinations = c["movement"]["destinations"]
                best = min(
                    destinations,
                    key=lambda d: (
                        min(
                            max(
                                abs(d["col"] - e["position"][0]),
                                abs(d["row"] - e["position"][1]),
                            )
                            for e in enemies
                        ),
                        d["cost_feet"],
                    ),
                )
                self.log("move_choice", destination=best)
                self.field(best["col"], best["row"])
                return
            if op["action"] == "select_attack_source":
                targets = c["legal_targets"]
                if not targets:
                    self.flags.add("skip:" + key + ":" + op["id"])
                    self.field(19, 0)
                    return
                target = min(targets, key=lambda t: t["hp"])
                self.log("attack_choice", target=target["id"])
                self.field(*target["position"])
                return
            self.field(19, 1)
            return
        opts = menu.get("options", [])
        available = [
            o
            for o in opts
            if not o.get("panel_unavailable_reason") and o.get("panel_slot") is not None
        ]
        rage = next((o for o in available if o.get("action_id") == "rage"), None)
        attacks = [
            o
            for o in available
            if o["action"] == "select_attack_source"
            and "skip:" + key + ":" + o["id"] not in self.flags
        ]
        move = next((o for o in available if o["action"] == "move"), None)
        if rage and "rage:" + key not in self.flags:
            self.flags.add("rage:" + key)
            choice = rage
        elif attacks:
            choice = (
                next(
                    (o for o in attacks if not o["label"].startswith("Atak:")),
                    attacks[0],
                )
                if self.name == "p6" and actor["id"] == "nimra"
                else attacks[0]
            )
        elif move and c["turn_action"]["action_use"] == "action_available":
            choice = move
        else:
            choice = next((o for o in available if o["action"] == "end_turn"), None)
        if not choice:
            raise RuntimeError(
                "No combat policy: "
                + str([(o["id"], o.get("panel_unavailable_reason")) for o in opts])
            )
        self.log("combat_action", label=choice["label"])
        self.field(19, 29 - choice["panel_slot"])

    def run(self, limit: int = 250) -> None:
        for _ in range(limit):
            p = self.view()
            self.record(p)
            m = p.get("mission") or {}
            c = p.get("confrontation") or {}
            print(
                self.step,
                m.get("stage"),
                c.get("phase"),
                c.get("mana", {}).get("phase"),
                flush=True,
            )
            if ((p.get("combat") or {}).get("shared_mana") or {}).get("declaration"):
                self.field(19, 1)
                continue
            if p["roll"]:
                self.dice()
                continue
            if c.get("active"):
                self.confrontation(c)
                continue
            if m.get("stage") == "surrender":
                self.log("surrender_offer", body=self.b.inspect()["body"])
                self.option(
                    m["choices"],
                    "accept" if self.name in ("p3", "p5", "p6") else "refuse",
                )
                continue
            if m.get("stage") == "potion_target":
                options = [x for x in m["choices"] if x["action"] == "potion_target"]
                actors = {a["id"]: a for a in p["combat"]["actors"]}
                choice = min(options, key=lambda x: actors[x["extra"]["target"]]["hp"])
                self.option(m["choices"], "potion_target", **choice["extra"])
                continue
            if p.get("combat"):
                combat = p["combat"]
                actor = combat["current_actor"]
                if any(x["action"] == "potion" for x in m.get("choices", [])):
                    hurt = [
                        a
                        for a in combat["actors"]
                        if a["faction"] == "ally"
                        and a["hp"] < a["max_hp"] / 2
                        and max(
                            abs(a["position"][0] - actor["position"][0]),
                            abs(a["position"][1] - actor["position"][1]),
                        )
                        <= 1
                    ]
                    if hurt:
                        self.option(m["choices"], "potion")
                        continue
                self.combat_step(p["combat"])
                continue
            if (p.get("setup") or {}).get("status") == "active":
                t = p["setup"]["current_step"]
                self.log("setup_step", label=t["label"])
                if t["can_confirm"]:
                    self.field(19, 1)
                else:
                    self.field(
                        *(
                            t.get("available_positions")
                            or p["board"]["legal_positions"]
                        )[0]
                    )
                continue
            if m.get("stage") == "battle":
                self.field(19, 1)
                continue
            stage = m.get("stage")
            choices = m.get("choices", [])
            if stage == "guild_hub":
                if self.name == "p6" and "arena-checked" not in self.flags:
                    self.flags.add("arena-checked")
                    self.field(*m["guild_points"]["visit_arena"])
                else:
                    self.field(5, 7)
            elif stage == "arena_unavailable":
                self.option(choices, "guild_back")
            elif stage == "brief":
                if "why" not in self.flags:
                    self.flags.add("why")
                    self.option(choices, "why")
                elif "road_info" not in self.flags:
                    self.flags.add("road_info")
                    self.option(choices, "road_info")
                elif any(x["action"] == "compliments" for x in choices):
                    self.option(choices, "compliments")
                elif any(x["action"] == "negotiate" for x in choices):
                    self.option(choices, "negotiate")
                else:
                    self.option(choices, "depart")
            elif stage == "compliments":
                compliments = [x for x in choices if x["action"] == "compliment"]
                self.option(
                    choices,
                    "compliment",
                    **compliments[1 if self.name == "p6" else 0]["extra"],
                )
            elif stage == "equipment":
                self.option(choices, "equipment_accept")
            elif stage == "departure":
                self.field(9, 24)
            elif stage == "road":
                self.option(choices, "cart")
            elif stage == "arrival":
                self.option(choices, "battle")
            elif stage == "explore":
                if "debt-done" not in self.flags or "rumor-done" not in self.flags:
                    self.field(9, 12)
                elif "visited-armory" not in self.flags:
                    self.flags.add("visited-armory")
                    self.field(5, 7)
                elif "visited-quarters" not in self.flags:
                    self.flags.add("visited-quarters")
                    self.field(14, 7)
                elif "visited-store" not in self.flags:
                    self.flags.add("visited-store")
                    self.field(4, 15)
                else:
                    self.option(choices, "dilemma")
            elif stage == "leader":
                if "debt-done" not in self.flags:
                    self.flags.add("debt-done")
                    action = (
                        "debt_garran"
                        if any(x["action"] == "debt_garran" for x in choices)
                        else (
                            "debt_help" if self.name in ("p3", "p5") else "debt_decline"
                        )
                    )
                    self.option(choices, action)
                elif any(x["action"] == "rumor" for x in choices):
                    self.flags.add("rumor-done")
                    self.option(choices, "rumor")
                else:
                    self.flags.add("rumor-done")
                    self.option(choices, "back")
            elif stage in ("armory", "quarters"):
                action = (
                    "collect"
                    if self.name in ("p5", "p6") and stage == "armory"
                    else "search"
                )
                self.option(choices, action, room=stage)
            elif stage == "search_result":
                if any(x["action"] == "identify_nimra" for x in choices):
                    self.option(choices, "identify_nimra")
                else:
                    self.option(choices, "back")
            elif stage == "dilemma":
                action = (
                    "bell_fence"
                    if any(x["action"] == "bell_fence" for x in choices)
                    and self.name in ("p4", "p6")
                    else "bell_village" if self.name == "p3" else "bell_guild"
                )
                self.option(choices, action)
            elif stage == "load":
                self.option(choices, "loaded")
            elif stage == "guild_return":
                if (
                    any(x["action"] == "ring" for x in choices)
                    and "guild-ring" not in self.flags
                ):
                    self.flags.add("guild-ring")
                    self.option(choices, "ring")
                else:
                    self.option(choices, "summary")
            elif stage == "ring":
                if any(x["action"] == "identify_guild" for x in choices):
                    self.option(choices, "identify_guild")
                elif any(x["action"] == "identify_nimra" for x in choices):
                    self.option(choices, "identify_nimra")
                else:
                    self.option(choices, "ring_back")
            elif stage == "ring_identified":
                self.option(choices, "ring_back")
            elif stage == "identify_failure":
                self.option(choices, "ring_view")
            elif stage == "summary":
                self.log("mission_completed", mission=m, body=self.b.inspect()["body"])
                self.b.shot(self.name + "-final-summary")
                self.save()
                return
            elif any(x["action"] == "back" for x in choices):
                self.option(choices, "back")
            elif any(x["action"] == "brief_back" for x in choices):
                self.option(choices, "brief_back")
            elif any(x["action"] == "next" for x in choices):
                self.option(choices, "next")
            else:
                raise RuntimeError(f"Unhandled mission {stage}: {choices}")
        self.save()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--party", default="p3")
    parser.add_argument("--limit", type=int, default=250)
    args = parser.parse_args()
    Playtest(args.party, 180900 + int(args.party[1:])).run(args.limit)
