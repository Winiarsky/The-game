"""Real /play and automatic hardware scans through allocation and a full turn."""
from dataclasses import replace
import json
from pathlib import Path
from threading import Event, Thread
from typing import Any
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.combat import current_actor, replace_actor
from dnd_board_game.ui.exploration_app import _remaining_movement_range
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate
from dnd_board_game.rules.runes import RESOURCE_RUNES, new_runes
from dnd_board_game.rules.shared_mana import sync_runes
from tests.unit.test_readonly_modal_scanning_browser import WaitingBoard
from tests.unit.test_rune_combat_board import rune_game


class CombatBoard(WaitingBoard):
    def press_field(self, position: tuple[int, int]) -> bool:
        with self.lock:
            if self.receiver is None or position not in self.positions:
                return False
            self.receiver.put(position)
            return True


@pytest.mark.parametrize('width', [1131, 1300])
def test_real_combat_board_flow_and_rune_layout(tmp_path: Path, width: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    game = rune_game(tmp_path, 6)
    # Exercise the transition from a hero action menu to the enemy confirmation.
    order = game.combat_state.initiative_order
    enemy_entry = next(entry for entry in order.entries if str(entry.actor.id) == 'borut')
    entries = (order.entries[0], enemy_entry, *(entry for entry in order.entries[1:] if entry != enemy_entry))
    game.combat_state = replace(game.combat_state, initiative_order=replace(order, entries=entries))
    pool = game.combat_state.shared_mana.runes
    opening = ['Kotwica', 'Kotwica', 'Kielich', 'Kielich', 'Klucz', 'Błysk', 'Oko', 'Korona']
    deck = [rune for _ in pool.heroes for rune in RESOURCE_RUNES]
    for rune in opening:
        deck.remove(rune)
    pool = new_runes(pool.heroes, (*opening, *deck))
    game.combat_state = replace(game.combat_state, shared_mana=sync_runes(game.combat_state.shared_mana, pool))
    hero = current_actor(game.combat_state)
    assert str(hero.id) == 'garran'
    target_position = Coordinate(hero.position.col - 1, hero.position.row)
    assert target_position not in {a.position for a in game.combat_state.actors}
    enemy = next(a for a in game.combat_state.actors if str(a.id) == 'borut')
    game.combat_state = replace_actor(game.combat_state, replace(enemy, position=target_position))
    movement = _remaining_movement_range(game._active_encounter().board, game.combat_state, hero)
    move_position = next(p for p in sorted(movement.reachable_tiles)
        if p != hero.position and max(abs(p.col - hero.position.col), abs(p.row - hero.position.row)) == 1
        and max(abs(p.col - target_position.col), abs(p.row - target_position.row)) == 1)
    board = CombatBoard()
    game.attach_board_connection(board, backend='simulator')
    app = create_app(game, character_dir=tmp_path / 'characters')
    done = Event()
    report: dict[str, Any] = {}

    @app.post('/__test/press')
    def press() -> dict[str, object]:
        position = tuple(request.get_json()['position'])
        return {'delivered': board.press_field(position), 'leds': [list(p) for p in board.leds]}

    @app.get('/__test/snapshot')
    def snapshot() -> dict[str, str]:
        return {'value': repr((game.combat_state, game.active_combat_effects,
                              game.pending_player_attack, game.combat_turn_preview_option_id))}

    @app.post('/__test/result')
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return {'ok': True}

    harness = r'''<script>
(async()=>{
const check=(v,m)=>{if(!v)throw Error(m)};
const wait=async(f,m='condition')=>{for(let i=0;i<250;i++){if(f())return;await new Promise(r=>setTimeout(r,20))}throw Error('timeout '+m)};
const legal=n=>(state.board_selection.legal_positions||[]).some(p=>p[0]===19&&p[1]===29-n);
const press=async position=>{
 await wait(()=>boardScanInFlight&&!busy&&!boardPanelSyncPromise,'armed '+position);
 const revision=state.board_selection.revision;
 let delivered=false;
 for(let i=0;i<150&&!delivered;i++){
  const r=await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position})});
  delivered=(await r.json()).delivered;
  if(!delivered)await new Promise(resolve=>setTimeout(resolve,20));
 }
 check(delivered,'no physical receiver '+position);
 await wait(()=>state.board_selection.revision!==revision&&!busy&&!boardPanelSyncPromise,'resolved '+position);
};
const slot=n=>press([19,29-n]);
const snapshot=async()=>JSON.stringify(await (await fetch('/__test/snapshot')).json());
const bounds=()=>check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
const dice=async()=>{
 for(let i=0;i<15;i++){
  await wait(()=>!busy&&!boardPanelSyncPromise,'dice stable');
  if(!keyboardRollWizard)return;
  await slot(28);
 }
 throw Error('dice wizard never finished');
};
try{
 await wait(()=>state?.combat?.shared_mana?.rune_view?.phase==='allocation'&&!busy&&document.querySelector('.tt-rune-allocation'),'opening allocation');
 check(state.combat.current_actor.id==='garran','Garran first');
 check(document.querySelectorAll('.tt-actor').length===14,'full vertical initiative');
 check(document.querySelectorAll('.tt-atlas').length===8,'eight opponent portraits');
 check(!document.querySelector('.initiative-ribbon'),'duplicate initiative');
 bounds();
 await slot(18);check(legal(18),'duplicate anchor must stay lit');
 await slot(18);check(!legal(18),'depleted anchor must go dark');
 await slot(29);check(legal(18),'undo must restore anchor');
 while(state.combat.shared_mana.rune_view.phase==='allocation'){
  const rune=state.combat.shared_mana.rune_view;
  const take=rune.choices.find(choice=>choice.command==='rune_take'&&choice.rune==='Klucz')||rune.choices.find(choice=>choice.command==='rune_take');
  if(take)await slot(take.slot);else await slot(28);
 }
 await wait(()=>document.querySelector('.tt-idle'),'idle after allocation');
 check(document.querySelector('.tt-idle').textContent.includes('Wybierz akcję'),'clean idle');
 const handBefore=JSON.stringify(state.combat.shared_mana.rune_view.hands);
 const deckBefore=state.combat.shared_mana.rune_view.deck_count;
 const before=await snapshot();await slot(24);await wait(()=>TabletopCombat.getView().inspected==='garran','star opens active hero');
 check(TabletopCombat.panel().exclusive,'information owns its controls');
 check(document.querySelector('[data-tt-inspection="garran"]').innerText.includes('Aktualne stany'),'full status information');
 check(document.querySelector('.tt-actor.is-active').dataset.ttActor==='garran','info changes turn');
 await slot(29);await wait(()=>!TabletopCombat.getView().inspected,'close info');
 check(before===await snapshot(),'info changed engine state');
 await slot(0);await wait(()=>state.combat.turn_action_menu?.preview_option_id==='turn:move','movement preview');
 check(!legal(28),'movement confirm lit before field');
 check(!document.querySelector('[data-movement-distance]'),'screen distance selector');
 await press(MOVE_POSITION);check(legal(28),'movement confirm dark after field');
 await slot(28);await wait(()=>state.combat.current_actor.position.join(',')===MOVE_POSITION.join(','),'movement committed');
 await slot(1);await wait(()=>state.combat.turn_action_menu?.stage==='preview','attack preview');
 check(!legal(28),'attack confirm lit before target');
 check(!document.querySelector('.tt-legal-targets button'),'targets are rune buttons');
 await slot(24);await wait(()=>TabletopCombat.getView().inspected,'info from action');await slot(29);
 await wait(()=>!TabletopCombat.getView().inspected,'return to preview');
 check(state.combat.turn_action_menu.stage==='preview','info lost action');
 const target=state.combat.actors.find(a=>a.id==='borut');
 await press(target.position);await wait(()=>state.combat.pending_player_attack?.stage==='confirm_attack','target chosen');
 check(document.querySelector('.tt-target').dataset.ttTarget==='borut','wrong target identity');
 check(legal(28),'target cannot confirm');bounds();
 const targetBefore=await snapshot();await slot(24);await wait(()=>TabletopCombat.getView().inspected,'target info');await slot(29);
 await wait(()=>!TabletopCombat.getView().inspected,'target info closed');
 check(targetBefore===await snapshot(),'information changed pending target/resources');
 await slot(28);await wait(()=>state.combat.pending_player_attack?.stage==='attack_roll'&&keyboardRollWizard,'attack die');
 check(!TabletopCombat.canBrowse(),'information stole dice');
 check(desiredBoardPanel().context.startsWith('dice:'),'dice owns panel');
 const natural=keyboardRollWizard.steps[keyboardRollWizard.index].raw;
 await slot(26);check(keyboardRollWizard.steps[keyboardRollWizard.index].raw===natural+1,'plus wrong direction');
 await slot(27);check(keyboardRollWizard.steps[keyboardRollWizard.index].raw===natural,'minus wrong direction');
 await dice();
 await wait(()=>keyboardRollWizard||!state.combat.pending_player_attack,'attack result');
 if(keyboardRollWizard)await dice();
 await wait(()=>!state.combat.pending_player_attack&&!keyboardRollWizard,'damage resolved');
 check(state.combat.actors.find(a=>a.id==='borut').hp<target.hp,'damage not applied');
 check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===handBefore,'ordinary attack spent runes');
 if(resultAck){await slot(28);await wait(()=>!resultAck,'result acknowledgement');}
 const stanceHand=JSON.stringify(state.combat.shared_mana.rune_view.hands);
 const stanceCount=state.combat.shared_mana.rune_view.hands.find(h=>h.hero==='garran').count;
 const stanceAC=state.combat.current_actor.ac;
 await slot(6);await wait(()=>state.combat.shared_mana.declaration?.stage==='payment','special payment after weapon attack');
 check(!legal(24)&&!TabletopCombat.canBrowse(),'information stole rune payment');
 check(document.querySelector('.tt-rune-payment'),'missing rune payment preview');
 check([...document.querySelectorAll('.tt-rune-payment .tt-rune-cost')].every(el=>el.textContent.startsWith('1 × ')),'rune cost omits quantity');
 const boost=state.combat.shared_mana.declaration.boost_options.find(o=>o.boost_id==='temp_hp');
 check(boost?.enabled,'temporary HP boost unavailable');
 await slot(boost.slot);
 check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===stanceHand,'preview spent runes');
 await slot(29);await wait(()=>!state.combat.shared_mana.declaration,'cancel rune payment');
 check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===stanceHand,'cancel spent runes');
 await slot(6);await wait(()=>state.combat.shared_mana.declaration?.stage==='payment','reopen rune payment');
 await slot(boost.slot);await slot(28);
 await wait(()=>state.combat.shared_mana.rune_view.phase==='rune_choices','choose exact payment');
 check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===stanceHand,'entering choice spent runes');
 check(!legal(28),'confirm lit with incomplete payment');
 const choiceSlot=rune=>state.combat.shared_mana.rune_view.choices.find(c=>c.rune===rune).slot;
 const chalice=choiceSlot('Kielich');
 const keyCount=state.combat.shared_mana.rune_view.hands.find(h=>h.hero==='garran').cards.filter(r=>r==='Klucz').length;
 const revision=state.combat.shared_mana.revision;
 const beforeScroll=JSON.stringify(state.combat.shared_mana.rune_view.hands);
 check(legal(26)&&legal(27),'physical scroll controls missing');
 await slot(26);await slot(27);
 check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===beforeScroll,'scroll changed resources');
 await slot(chalice);check(legal(chalice),'first duplicate choice extinguished both copies');
 await slot(chalice);check(!legal(chalice),'depleted duplicate remains lit');
 check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===stanceHand,'provisional choice spent runes');
 const stale=await fetch('/api/combat/shared-mana',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:'rune_choice_confirm',revision})});
 check(stale.status===400||stale.status===409,'stale payment revision accepted');
 check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===stanceHand,'stale command spent runes');
 await slot(29);check(legal(chalice),'undo failed to restore selected duplicate');
 await slot(chalice);await slot(choiceSlot('Kotwica'));
 check(legal(28),'complete choice cannot confirm');
 check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===stanceHand,'payment taken before final confirm');
 await slot(28);
 await wait(()=>!state.combat.shared_mana.declaration&&state.combat.shared_mana.rune_view.special_used,'special committed');
 check(state.combat.shared_mana.rune_view.hands.find(h=>h.hero==='garran').count===stanceCount-3,'fallback plus boost should cost three runes');
 check(state.combat.shared_mana.rune_view.hands.find(h=>h.hero==='garran').cards.filter(r=>r==='Klucz').length===keyCount,'choice failed to preserve Key');
 check(state.combat.current_actor.temp_hp===5,'special boost missing');
 check(state.combat.current_actor.ac===stanceAC+2,'defensive stance AC missing');
 if(resultAck){await slot(28);await wait(()=>!resultAck,'special acknowledgement');}
 await slot(3);await wait(()=>state.combat.turn_action_menu?.preview_option_id==='turn:end','end preview');
 await slot(28);await wait(()=>state.combat.current_actor.id!=='garran','next turn');
 check(state.combat.shared_mana.rune_view.phase==='ready','unexpected new allocation');
 check(state.combat.shared_mana.rune_view.deck_count===deckBefore,'unexpected new draw');
 check(state.combat.current_actor.faction==='enemy','next turn must test an enemy');
 check(legal(28),'enemy start must light accept');
 check(!legal(23),'Key must not replace enemy confirmation');
 await slot(28);
 await wait(()=>state.combat.enemy_turn_intent||state.combat.enemy_turn_preview||state.combat.enemy_turn_result,'physical accept starts enemy action');
 await stopBoardScanLoop();
 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
}catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,phase:boardInputPhase,error:boardScanError,body:document.body.innerText.slice(-2200)})})}
})();</script>'''.replace('MOVE_POSITION', json.dumps(list(move_position.as_tuple())))
    error_hook = """<script>window.alert=message=>{throw Error(message)};window.addEventListener('error',e=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(e.message)+' '+e.filename+':'+e.lineno})}));</script>"""

    @app.after_request
    def inject(response: Any) -> Any:
        if request.path == '/play' and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace('<head>', '<head>' + error_hook).replace('</body>', harness + '</body>'))
        return response

    server = make_server('127.0.0.1', 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([
            chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--no-first-run', '--disable-background-networking', '--no-proxy-server',
            f'--user-data-dir={tmp_path / "chrome"}', f'--window-size={width},863',
            f'http://127.0.0.1:{server.server_port}/play'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(70), 'Browser did not report'
        assert report.get('result') == 'PASS', report
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
