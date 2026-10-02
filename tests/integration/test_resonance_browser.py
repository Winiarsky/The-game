"""Actual /play, automatic physical scans and compact laptop presentation."""
from pathlib import Path
from threading import Event, Thread
from typing import Any
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from tests.unit.test_mission_zero import session, start_battle
from tests.unit.test_tabletop_combat_browser import CombatBoard


@pytest.mark.parametrize("width,height", [(1366, 768), (1131, 720), (390, 844)])
def test_real_panel_dice_and_no_laptop_scrolling(tmp_path: Path, width: int, height: int) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome required")
    from dnd_board_game.ui.training_arena import training_hero
    game = session(tmp_path, 6, legacy_combat=False)
    game.configure_custom_party(tuple(training_hero(key) for key in ("garran", "brakka", "dagna", "mira", "lorian", "nimra")))
    game = start_battle(game)
    board = CombatBoard()
    game.attach_board_connection(board, backend="simulator")
    app = create_app(game, character_dir=tmp_path / "characters")
    done, report = Event(), {}

    @app.post("/__test/press")
    def press() -> dict[str, Any]:
        return dict(delivered=board.press_field(tuple(request.get_json()["position"])))

    @app.post("/__test/result")
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return dict(ok=True)

    @app.post("/__test/dense")
    def dense() -> dict[str, Any]:
        from dnd_board_game.ui import resonance
        e = resonance.engine(game)
        e.s.index = e.s.order.index("nimra")
        e.s.queue.clear()
        e.s.task = e.s.action = e.s.preview = None
        e.s.phase = "idle"
        e.begin_turn()
        e.end_chain("przygotowanie testu")
        for contributor, rune in (("garran", "Wieża"), ("garran", "Grot"), ("nimra", "Klepsydra")):
            e.add_rune(contributor, rune)
        e.s.queue.clear()
        e.s.task = None
        e.s.phase = "idle"
        e.s.revision += 1
        game.combat_state = e.combat_state()
        game.board_selection_revision += 1
        game._sync_board_leds()
        return game.state_payload()

    @app.post("/__test/bonuses")
    def bonuses() -> dict[str, Any]:
        from dnd_board_game.ui import resonance
        e = resonance.engine(game)
        e.s.index = e.s.order.index("mira")
        e.s.queue.clear()
        e.s.task = e.s.action = e.s.preview = None
        e.s.phase = "idle"
        e.begin_turn()
        e.end_chain("przygotowanie testu")
        for contributor, rune in (("garran", "Grot"), ("brakka", "Hak"), ("brakka", "Schody")):
            e.add_rune(contributor, rune)
        e.s.queue.clear()
        e.s.task = None
        e.s.phase = "idle"
        assert e.choose("hide")
        e.s.revision += 1
        game.combat_state = e.combat_state()
        game.board_selection_revision += 1
        game._sync_board_leds()
        return game.state_payload()

    @app.post("/__test/reaction-load")
    def reaction_load() -> dict[str, Any]:
        from dataclasses import replace
        from dnd_board_game.actors import Faction
        from dnd_board_game.rules.resonance import ChargeState
        from dnd_board_game.ui import resonance
        from dnd_board_game.world import line_of_sight_clear
        from dnd_board_game.world.movement import neighbors
        e = resonance.engine(game)
        enemy = next(actor for actor in e.actors.values() if actor.faction == Faction.ENEMY and actor.hp > 0)
        target = e.actor("mira")
        origin = next(pos for pos in neighbors(e.board, target.position)
                      if e.free(pos, str(enemy.id)) and line_of_sight_clear(e.board, pos, target.position))
        e.update_actor(replace(enemy, position=origin))
        e.fighter(str(enemy.id)).reaction = True
        e.s.preview = e.s.action = e.s.task = None
        e.s.queue = [dict(type="attack", actor=str(enemy.id), target="mira", power="opportunity", reaction_pending=True)]
        e.s.phase = "idle"
        e.advance()
        e.s.revision += 1
        e.s = ChargeState.from_payload(e.s.as_payload(), set(e.actors))
        game.combat_state = e.combat_state()
        game.board_selection_revision += 1
        game._sync_board_leds()
        return game.state_payload()

    @app.post("/__test/preview-gallery")
    def preview_gallery() -> dict[str, Any]:
        from itertools import product
        from dnd_board_game.rules.resonance import ResonanceChain, ResonanceEntry
        from dnd_board_game.ui.resonance import presentation
        from tests.unit.test_resonance_presentation import relations_game
        views = []
        for hero in ("garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"):
            for card in relations_game(hero).cards():
                e = relations_game(hero, ("garran" if hero != "garran" else "nimra",))
                required = set(card.requires_resonance)
                symbols = [rune for rune in e.catalog["rules"]["starter_runes"] if rune != "Fala"]
                words = (word for size in range(1, 4) for word in product(symbols, repeat=size))
                legal = (word for word in words if required <= set(word)
                         and all(right in e.next_runes(left) for left, right in zip(word, word[1:]))
                         and card.rune in e.next_runes(word[-1]))
                word = max(legal, key=lambda word: (sum(set(bonus["requires"]) <= set(word) for bonus in card.resonance_bonuses), -len(word)))
                e.s.chain = ResonanceChain(1, [ResonanceEntry(rune, hero, rune) for rune in word], [hero])
                e.s.serial = 1
                if card.id == "shadow_attack":
                    e.fighter().hidden = ["enemy0"]
                assert e.choose(card.id), e.unavailable(card.id)
                views.append(presentation(e)[0])
        return dict(views=views)

    harness = r"""<script>
(async()=>{
 const check=(v,m)=>{if(!v)throw Error(m)};
 const wait=async(f,m)=>{for(let i=0;i<250;i++){if(f())return;await new Promise(r=>setTimeout(r,20))}throw Error('timeout '+m)};
 const v=()=>state.combat.resonance;
 const bounds=label=>{
   const box=document.querySelector('.rc-combat').getBoundingClientRect();
   if(innerWidth>650)check(box.bottom<=innerHeight+2,label+' bottom '+box.bottom+'/'+innerHeight);
   check(document.documentElement.scrollWidth<=innerWidth,label+' horizontal overflow');
   if(innerWidth>650)for(const s of document.querySelectorAll('.rc-main,.rc-decision,.rc-roster'))check(s.scrollHeight<=s.clientHeight+2,label+' internal overflow '+s.className+' '+s.scrollHeight+'/'+s.clientHeight);
 };
 const slot=async n=>{
   await wait(()=>boardScanInFlight&&!busy&&!boardPanelSyncPromise,'arm '+n);
   const revision=v().revision;
   let delivered=false;
   for(let i=0;i<150&&!delivered;i++){
     delivered=(await(await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position:[19,29-n]})})).json()).delivered;
     if(!delivered)await new Promise(r=>setTimeout(r,20));
   }
   check(delivered,'delivery '+n);
   await wait(()=>v().revision!==revision&&!busy&&!boardPanelSyncPromise,'resolved '+n);
 };
 try {
   await wait(()=>state?.combat?.resonance&&!busy&&document.querySelector('.rc-combat'),'opening');
   check(v().active==='garran','Garran first');
   check(v().profile==='rune_relations_v03','accepted production profile');
   check(document.querySelectorAll('.rc-powers button').length===4,'Garran powers');
   check(document.querySelectorAll('.rc-powers svg').length===4,'rune icons');
   check(!document.querySelector('.tt-legal-targets'),'no redundant field list');
   bounds('idle');
   await slot(25);check(v().decision.inspected==='garran','star');bounds('info');
   await slot(26);check(v().decision.title==='Żywa osłona','passive page');bounds('passive');
   await slot(29);await slot(12);bounds('preview'); // Błysk / Żar odnowy
   check(!v().controls.some(c=>c.command==='mode'),'one mode');
   check(v().decision.cost===4,'single cost');
   check(document.querySelectorAll('.rc-card-bonuses>div').length===2,'card-specific bonus conditions');
   await slot(28);check(v().decision.die.sides===10,'base healing die without global flash');
   check(v().decision.die.value===5,'healing die midpoint');bounds('heal die');
   await slot(26);check(v().decision.die.value===6,'physical plus');
   await slot(28);check(v().phase==='result','result');bounds('result');
   await slot(28);check(v().chain.entries.at(-1).rune==='Błysk','rune after resolution');
   check(!v().chain.bonuses.length&&!document.querySelector('.rc-bonuses'),'no global aura');bounds('chain idle');
   await slot(3);await slot(28);check(v().active!=='garran','next actor');bounds('next turn');
   await stopBoardScanLoop();
   state=await(await fetch('/__test/dense',{method:'POST'})).json();render();
   check(document.querySelectorAll('.rc-memory-track .rc-rune').length===3,'three-rune memory');
   check(document.querySelectorAll('.rc-next .rc-rune').length===4,'legal next rune glyphs');
   check(document.querySelectorAll('.rc-reserved button[disabled]').length===9,'future runes locked');
   check(!v().controls.some(c=>c.id==='flame_fan'),'finisher cannot be activated without both runes');
   check(document.querySelectorAll('.rc-powers button').length===5,'Nimra five powers');bounds('dense resonance');
   await stopBoardScanLoop();
   state=await(await fetch('/__test/bonuses',{method:'POST'})).json();render();
   check(v().decision.resonance.active_bonuses.length===3,'three simultaneous hide bonuses');
   check(document.querySelectorAll('.rc-bonus-active').length===2,'bonus first page');bounds('bonus preview');
   document.querySelector('[data-rc-page="bonus"][data-delta="1"]').click();
   check(document.querySelectorAll('.rc-bonus-active').length===1,'bonus second page');bounds('bonus second page');
   check(!v().controls.some(c=>c.command==='mode'),'no mode in bonus preview');
   await stopBoardScanLoop();
   state=await(await fetch('/__test/reaction-load',{method:'POST'})).json();render();
   check(v().decision.enemy&&!v().decision.die,'loaded enemy roll is automatic');bounds('reaction after load');
   await slot(25);bounds('reaction info');await slot(29);
   check(v().decision.enemy&&v().phase==='task','star preserved loaded reaction');
   await slot(28);check(v().decision.rolls?.length>0,'enemy result shown after confirmation');bounds('reaction result');
   await stopBoardScanLoop();
   const previews=(await(await fetch('/__test/preview-gallery',{method:'POST'})).json()).views;
   check(previews.length===29,'all accepted power previews');
   const current=state.combat.resonance;
   for(const preview of previews){
     state.combat.resonance=preview;
     document.querySelector('.rc-combat').outerHTML=ChargeCombat.html();
     bounds('card '+preview.decision.title);
     for(const next of document.querySelectorAll('[data-rc-page="bonus"][data-delta="1"]')){next.click();bounds('card bonus page '+preview.decision.title)}
   }
   state.combat.resonance=current;
   await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-2500),layout:[...document.querySelectorAll('.rc-main,.rc-main>*')].map(el=>({class:el.className,height:el.clientHeight,scroll:el.scrollHeight,width:el.clientWidth,rect:el.getBoundingClientRect().toJSON()})),phase:boardInputPhase,error:boardScanError})})}
})();</script>"""
    error_hook = """<script>window.alert=message=>{throw Error(message)};window.addEventListener('error',e=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(e.message)+' '+e.filename+':'+e.lineno})}));</script>"""

    @app.after_request
    def inject(response: Any) -> Any:
        if request.path == "/play" and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace("<head>", "<head>"+error_hook).replace("</body>", harness+"</body>"))
        return response

    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--no-first-run",
            "--disable-background-networking", "--no-proxy-server", f"--user-data-dir={tmp_path / 'chrome'}", f"--window-size={width},{height}",
            f"http://127.0.0.1:{server.server_port}/play"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(45), "Browser did not report"
        assert report.get("result") == "PASS", report
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        board.cancel_scan()
        server.shutdown()
        worker.join(timeout=2)
