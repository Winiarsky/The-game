"""Local Chrome UI playtest support; uses installed websocket-client, no game state writes."""

from __future__ import annotations
import base64
import json
import time
from pathlib import Path
from typing import Any
import requests
import websocket

REPORT = Path("docs/playtests/2026-09-18-misja0")


class Browser:
    def __init__(self) -> None:
        pages = requests.get("http://127.0.0.1:9223/json", timeout=5).json()
        page = next(
            p for p in pages if p["type"] == "page" and ":8765" in p.get("url", "")
        )
        self.ws = websocket.create_connection(
            page["webSocketDebuggerUrl"], timeout=40, origin="http://localhost"
        )
        self.index = 0
        self.call("Page.enable")
        self.call("Runtime.enable")

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self.index += 1
        self.ws.send(
            json.dumps(dict(id=self.index, method=method, params=params or {}))
        )
        while True:
            message = json.loads(self.ws.recv())
            if message.get("method") == "Page.javascriptDialogOpening":
                with (REPORT / "browser-alerts.jsonl").open("a") as f:
                    f.write(json.dumps(message) + "\n")
                self.ws.send(
                    json.dumps(
                        dict(
                            id=100000 + self.index,
                            method="Page.handleJavaScriptDialog",
                            params={"accept": True},
                        )
                    )
                )
            if message.get("method") == "Runtime.exceptionThrown":
                with (REPORT / "console-errors.jsonl").open("a") as f:
                    f.write(json.dumps(message) + "\n")
            if message.get("id") == self.index:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message.get("result", {})

    def evaluate(self, expression: str) -> Any:
        result = self.call(
            "Runtime.evaluate",
            dict(expression=expression, returnByValue=True, awaitPromise=True),
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"])
        return result.get("result", {}).get("value")

    def wait(self) -> None:
        self.evaluate(
            """(async()=>{for(let i=0;i<200;i++){if(typeof busy==='undefined'||(!busy&&!boardPanelSyncPromise))return;await new Promise(r=>setTimeout(r,50));}throw Error('UI stayed busy');})()"""
        )
        time.sleep(0.08)

    def click(self, selector: str) -> None:
        point = self.evaluate(
            f"""(()=>{{const el=document.querySelector({json.dumps(selector)});if(!el)throw Error('Missing selector');if(el.disabled)throw Error('Disabled');el.scrollIntoView({{block:'center'}});const r=el.getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}};}})()"""
        )
        self.call(
            "Input.dispatchMouseEvent",
            dict(type="mousePressed", button="left", clickCount=1, **point),
        )
        self.call(
            "Input.dispatchMouseEvent",
            dict(type="mouseReleased", button="left", clickCount=1, **point),
        )
        time.sleep(0.2)
        self.wait()

    def field(self, col: int, row: int) -> None:
        self.wait()
        self.evaluate(f"api('/api/board/select',{{col:{col},row:{row}}},'')")
        self.wait()

    def shot(self, name: str) -> str:
        folder = REPORT / "screenshots"
        folder.mkdir(exist_ok=True, parents=True)
        path = folder / f"{name}.png"
        path.write_bytes(
            base64.b64decode(
                self.call("Page.captureScreenshot", dict(format="png"))["data"]
            )
        )
        return str(path)

    def inspect(self) -> Any:
        return self.evaluate(
            """(()=>{const visible=el=>el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden';const s=typeof state==='undefined'?{}:state;
return {url:location.pathname,body:document.body.innerText.slice(-14000),buttons:[...document.querySelectorAll('button,a,input,select')].filter(visible).map(e=>({tag:e.tagName,id:e.id,text:(e.innerText||e.value||e.getAttribute('aria-label')||'').slice(0,170),disabled:e.disabled,onclick:e.getAttribute('onclick'),rune:e.dataset.manaSlot||e.dataset.missionSlot||e.dataset.boardRune})),stage:s.mission?.stage,combat:s.combat?{keys:Object.keys(s.combat),current:s.combat.current_actor,phase:s.combat.phase}:null,roll:typeof keyboardRollWizard==='undefined'?null:keyboardRollWizard,setup:s.encounter_setup,confrontation:s.exploration_mana};})()"""
        )


if __name__ == "__main__":
    b = Browser()
    b.call(
        "Emulation.setDeviceMetricsOverride",
        dict(width=1300, height=720, deviceScaleFactor=1, mobile=False),
    )
    print(json.dumps(b.inspect(), ensure_ascii=False, indent=2))
