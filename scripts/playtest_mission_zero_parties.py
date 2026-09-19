"""Select test parties using the real launcher, then run the UI playtest."""

from __future__ import annotations
import argparse, time
from playtest_mission_zero_ui import Playtest

PARTIES = {
    "p3": ["brakka", "dagna", "erynd"],
    "p4": ["garran", "mira", "lorian", "nimra"],
    "p5": ["brakka", "dagna", "erynd", "garran", "nimra"],
    "p6": ["brakka", "dagna", "garran", "lorian", "mira", "nimra"],
}


def start_party(name: str) -> Playtest:
    p = Playtest(name, 180900 + int(name[1:]))
    p.b.call(
        "Emulation.setDeviceMetricsOverride",
        dict(
            width=1131 if name == "p6" else 1300,
            height=720,
            deviceScaleFactor=1,
            mobile=False,
        ),
    )
    p.b.call("Page.navigate", {"url": "http://127.0.0.1:8765/new-game"})
    time.sleep(1)
    for hero in PARTIES[name]:
        p.b.click(f'input[value="{hero}"]')
    p.b.shot(name + "-party-selection")
    p.b.click("#continue-to-scenario")
    p.b.click('input[value="misja_0_dzwon"]')
    time.sleep(1)
    p.log("party_start", heroes=PARTIES[name])
    return p


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("party")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    p = Playtest(args.party) if args.resume else start_party(args.party)
    p.run(1500)
