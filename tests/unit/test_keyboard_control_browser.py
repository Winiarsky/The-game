"""Keyboard events exercise the real browser, preview transport and combat UI."""
from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread
from typing import Any

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.rules.resonance import ResonanceChain, ResonanceEntry
from dnd_board_game.ui import resonance
from dnd_board_game.ui.routes import create_app
from tests.integration.test_combat_board_feedback import combat


def test_keyboard_preview_commit_panels_and_action_menu(tmp_path: Path) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome required for browser input check")
    game, board, _, legal = combat(tmp_path)
    engine = resonance.engine(game)
    engine.s.chain = ResonanceChain(
        1, [ResonanceEntry(rune, "erynd", rune) for rune in ("Oko", "Węzeł")], ["erynd"],
    )
    game.combat_state = engine.combat_state()
    game.configure_input_mode("keyboard")
    scans: list[object] = []
    original_scan = getattr(board, "scan_board", None)

    def unexpected_scan(*args: object, **kwargs: object) -> object:
        scans.append((args, kwargs))
        if original_scan:
            return original_scan(*args, **kwargs)
        raise AssertionError("Keyboard mode must not scan the board")

    board.scan_board = unexpected_scan
    app = create_app(game, character_dir=tmp_path / "characters")
    done = Event()
    report: dict[str, Any] = {}
    progress: dict[str, Any] = {}

    @app.before_request
    def remember_command() -> None:
        if request.path in {"/api/input/command", "/api/combat/resonance"}:
            progress["last_request"] = {"path": request.path, "body": request.get_json()}

    @app.get("/__test/domain")
    def domain() -> dict[str, Any]:
        preview = resonance.engine(game).s.preview or {}
        return {"value": repr(game.combat_state), "targets": preview.get("targets", [])}

    @app.post("/__test/result")
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return {"ok": True}

    harness = r'''<script>
    (async()=>{
      let stage='initializing',reported=false;
      const finish=async(result)=>{
        if(reported)return;
        reported=true;
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({result,stage,input:{kind:state?.input?.kind,cursor:state?.input?.cursor,
            selection_mode:state?.input?.selection_mode,can_accept:state?.input?.can_accept},
            phase:state?.combat?.resonance?.phase,
            focus:document.activeElement?.outerHTML.slice(0,300),
            dialogs:[...document.querySelectorAll('dialog[open]')].map(dialog=>dialog.id)})});
      };
      window.addEventListener('error',event=>finish('window error: '+(event.error?.stack||event.message)));
      window.addEventListener('unhandledrejection',event=>finish('unhandled rejection: '+(event.reason?.stack||event.reason)));
      setTimeout(()=>finish('browser timeout at '+stage),40000);
      const check=(value,message)=>{if(!value)throw Error(message)};
      const pause=()=>new Promise(resolve=>setTimeout(resolve,20));
      const wait=async(predicate,message)=>{
        if(message!=='input idle')stage=message;
        for(let i=0;i<350;i++){if(predicate())return;await pause();}
        throw Error('timeout '+message);
      };
      const key=(value,repeat=false,code=value.length===1 ? 'Key'+value.toUpperCase() : value)=>{
        const event=new KeyboardEvent('keydown',{
          key:value,code,location:code.startsWith('Numpad')?3:0,bubbles:true,cancelable:true,repeat,
        });
        (document.activeElement||document.body).dispatchEvent(event);
        document.dispatchEvent(new KeyboardEvent('keyup',{key:value,code,bubbles:true}));
        return event;
      };
      const numpad=(value,numLock=true,repeat=false)=>{
        const off={'0':'Insert','1':'End','2':'ArrowDown','3':'PageDown','4':'ArrowLeft',
          '5':'Clear','6':'ArrowRight','7':'Home','8':'ArrowUp','9':'PageUp','.':'Delete'};
        const code={Enter:'NumpadEnter','.':'NumpadDecimal',',':'NumpadDecimal',
          '+':'NumpadAdd','-':'NumpadSubtract','*':'NumpadMultiply','/':'NumpadDivide'}[value]
          ||'Numpad'+value;
        return key(numLock?value:(off[value]||value),repeat,code);
      };
      const settle=()=>wait(()=>!busy&&document.querySelector('[data-keyboard-sync]').hidden,'input idle');
      const domain=async()=>await(await fetch('/__test/domain')).json();
      const snapshot=async()=>JSON.stringify(await(await fetch('/__test/domain')).json());
      const actor=()=>state.combat.resonance.actors.find(actor=>actor.id==='erynd');
      const sessionOpen=()=>document.getElementById('session-navigation')?.open;
      const closeSession=()=>{
        for(let i=0;i<2&&sessionOpen();i++)key('Backspace');
        check(!sessionOpen(),'Backspace did not close session information');
      };
      const pointAtTarget=async()=>{
        const targetPosition=state.combat.resonance.actors.find(actor=>actor.id===LEGAL_TARGET).position;
        for(let i=0;i<30&&JSON.stringify(state.input.cursor)!==JSON.stringify(targetPosition);i++){
          const [col,row]=state.input.cursor;
          numpad(col!==targetPosition[0]?(col>targetPosition[0]?'8':'2'):(row>targetPosition[1]?'6':'4'));
          await settle();
        }
        check(JSON.stringify(state.input.cursor)===JSON.stringify(targetPosition),'numpad missed legal target');
      };
      const chooseDoubleShot=async()=>{
        stage='choose double shot';
        numpad('5');
        const power=state.combat.resonance.powers.find(power=>power.id==='double_shot');
        const target=document.querySelector(`.rc-powers [data-rc-slot="${power.slot}"]`);
        check(target&&!target.disabled,'double shot unavailable');
        for(let i=0;i<30&&document.activeElement!==target;i++)numpad('2');
        check(document.activeElement===target,'numpad cannot focus double shot');
        numpad('Enter');
        await wait(()=>state.input.selection_mode==='multiple'&&!busy,'multiple target preview');
        await pointAtTarget();
        check((await domain()).targets.length===0,'moving cursor selected a target');
      };
      try {
        window.alert=message=>{throw Error('Unexpected alert: '+message)};
        window.confirm=message=>{throw Error('Unexpected confirm: '+message)};
        await wait(()=>state?.input?.mode==='keyboard'&&!busy,'keyboard mode');
        check(!state.board_selection.auto_arm,'scanner automatically armed');
        check(!document.getElementById('keyboard-control-bar'),'keyboard shortcut bar still occupies the game screen');
        const controlsCard=document.getElementById('keyboard-controls-card');
        check(controlsCard?.closest('[data-side-panel-content="party"]'),'keyboard instructions missing from character card');
        for(const marker of ['status','sync','multiple']){
          check(controlsCard.querySelector(`[data-keyboard-${marker}]`),'character card missing keyboard '+marker);
        }
        const unavailable=document.querySelector('.rc-basic[aria-disabled="true"]');
        check(unavailable?.dataset.keyboardDisabled,'unavailable action has no keyboard explanation');
        const beforeUnavailable=await snapshot();
        key('Tab');unavailable.focus();numpad('Enter');
        check(await snapshot()===beforeUnavailable,'unavailable action spent resources');
        check(document.getElementById('keyboard-decision-hint').textContent.includes(unavailable.dataset.keyboardDisabled),'unavailable action explanation is hidden');
        state.board.led_output={pending:true,error:'Próba: WLED bez odpowiedzi'};
        renderBoardConnectionIndicator();
        const indicator=document.getElementById('board-connection-indicator');
        check(indicator.textContent.includes('LED-y niedostępne'),'offline LEDs reported connected');
        check(indicator.title.includes('WLED bez odpowiedzi'),'LED error explanation missing');
        const origin=JSON.stringify(actor().position);
        numpad('7');
        await wait(()=>state.input.kind==='map'&&!busy,'movement preview');
        const preview=await snapshot();
        for(const numLock of [true,false]){
          for(const [direction,expected] of [
            ['6',[3,2]], ['4',[3,3]], ['2',[4,3]], ['8',[3,3]],
          ]){
            numpad(direction,numLock);await settle();
            check(JSON.stringify(state.input.cursor)===JSON.stringify(expected),
              'board orientation incorrect for Numpad'+direction+' NumLock='+numLock+': '+JSON.stringify(state.input.cursor));
          }
        }
        numpad('5',false);
        check(document.activeElement.closest('.rc-actions'),'Numpad5 did not expose current map controls');
        numpad('5');
        numpad('8');await settle();
        check(JSON.stringify(state.input.cursor)!==origin,'arrows did not move cursor');
        check(document.querySelector('[data-keyboard-status]').textContent.includes('Koszt ruchu:'),'movement preview cost missing');
        const hint=document.getElementById('keyboard-decision-hint');
        check(hint&&!hint.hidden&&hint.closest('.rc-main'),'decision hint missing from combat');
        check(hint.innerText.includes('Koszt ruchu:')&&hint.innerText.includes('Enter'),'visible movement instructions missing');
        const accept=document.querySelector('[data-keyboard-accept]');
        check(accept&&!accept.disabled&&accept.textContent.includes('Wykonaj ruch'),'ready movement has no screen confirmation');
        check(!document.querySelector('.rc-prompt').textContent.includes('Wybierz cel na planszy'),'movement prompt is stale');
        check(JSON.stringify(actor().position)===origin,'preview moved actor');
        check(await snapshot()===preview,'arrow changed authoritative combat state');
        key('Tab');
        document.querySelector('.rc-actions [data-rc-slot="29"]').focus();
        key('Enter');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'explicit Tab control');
        check(JSON.stringify(actor().position)===origin,'Tab-focused Back committed movement');
        numpad('7',false);await wait(()=>state.input.kind==='map'&&!busy,'preview with NumLock off');
        key('ArrowUp');await settle();
        key('Backspace');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'cancel');
        check(JSON.stringify(actor().position)===origin,'cancel changed position');
        key('m');await wait(()=>state.input.kind==='map'&&!busy,'second preview');
        key('ArrowUp');await settle();
        const target=JSON.stringify(state.input.cursor);
        const enter=numpad('Enter');
        check(enter.defaultPrevented,'NumpadEnter retained native button activation');
        await wait(()=>JSON.stringify(actor().position)===target&&!busy,'commit movement');
        const committed=await snapshot();
        numpad('Enter',true,true);await pause();
        check(await snapshot()===committed,'repeated Enter performed another action');
        check(state.combat.resonance.phase==='result','movement did not keep its existing result acknowledgement');
        numpad('Enter');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'acknowledge movement result');
        numpad('7');await settle();numpad('8');await settle();
        const screenDestination=JSON.stringify(state.input.cursor);
        document.querySelector('[data-keyboard-accept]').click();
        await wait(()=>JSON.stringify(actor().position)===screenDestination&&!busy,'screen movement confirmation');
        check(state.combat.resonance.phase==='result','screen confirmation did not execute movement');
        numpad('Enter');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'screen movement acknowledgement');
        const idle=await snapshot();
        numpad('5');
        const focused=document.activeElement.dataset.rcSlot;
        numpad('1');numpad('3');
        check(sidePanelOpen&&sidePanelTab==='inventory','1 → 3 did not switch panels');
        const side=document.getElementById('side-panel');
        for(const details of side.querySelectorAll('.inventory-metadata'))details.open=true;
        check(side.scrollWidth<=side.clientWidth+1,'inventory overflows side panel');
        check(!side.querySelector('[data-side-panel-content="inventory"]').innerText.includes('Two handed'),'untranslated weapon property');
        numpad('1');
        check(sidePanelOpen&&sidePanelTab==='party','3 → 1 did not switch panels');
        check(side.querySelector('.panel-combat-summary'),'character panel lacks combat information');
        check(side.querySelector('.panel-combat-summary').innerText.includes('Moce runiczne'),'character panel lacks rune powers');
        numpad('1');
        check(!sidePanelOpen,'second 1 did not close character panel');
        check(document.activeElement.dataset.rcSlot===focused,'panel lost action focus');
        check(await snapshot()===idle,'information panels changed combat state');
        numpad('5');
        document.querySelector('.rc-info').click();
        check(sidePanelOpen&&sidePanelTab==='party','combat information button did not open the shared character panel');
        key('Backspace');
        key('Tab');document.getElementById('side-panel-toggle').focus();
        key('Enter');
        check(document.getElementById('session-navigation')?.open,'Tab-focused header menu did not open');
        key('Escape');
        check(!document.getElementById('session-navigation')?.open,'Esc did not close session menu');
        check(await snapshot()===idle,'session menu changed combat state');
        for(const numLock of [true,false]){
          for(const [shortcut,tab] of [['1','party'],['3','inventory']]){
            const beforePanel=await snapshot();
            numpad(shortcut,numLock);
            check(document.body.classList.contains('side-panel-open'),'numpad side panel did not open');
            check(sidePanelTab===tab,'wrong numpad side panel');
            if(tab==='party'){
              const controls=document.getElementById('keyboard-controls-card');
              check(!controls.closest('[hidden]')&&controls.getClientRects().length
                &&getComputedStyle(controls).visibility!=='hidden','1 did not reveal keyboard instructions');
              const keys=new Set([...controls.querySelectorAll('kbd')].map(key=>key.textContent.trim().replaceAll('−','-')));
              for(const value of ['0','1','2','3','4','5','6','7','8','9','Enter','Backspace','.',',','*','/','=','+','-']){
                check(keys.has(value),'character card missing numpad key '+value);
              }
            }
            numpad('7',numLock);numpad('9',numLock);numpad('0',numLock);numpad('.',numLock);
            await pause();
            check(await snapshot()===beforePanel,'numpad shortcut acted underneath side panel');
            key('Backspace');
            check(!document.body.classList.contains('side-panel-open'),'Backspace did not close side panel');
          }
          numpad('9',numLock);
          await wait(()=>state.input.kind==='map'&&state.combat.resonance.phase==='preview'&&!busy,'attack shortcut');
          key('Backspace');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'cancel attack');
          numpad('0',numLock);
          await wait(()=>state.combat.resonance.phase==='end-preview'&&!busy,'end turn preview');
          check(document.querySelector('.rc-unused')?.textContent.includes('atak / przedmiot'),'end turn lacks unused budgets');
          key('Backspace');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'cancel end turn');
        }
        const beforeSession=await snapshot();
        numpad('*');
        check(sessionOpen()&&SessionNavigation.panel().context.startsWith('session-journal:'),'multiply did not open journal');
        for(const numLock of [true,false]){
          numpad('7',numLock);numpad('9',numLock);numpad('0',numLock);numpad('.',numLock);
        }
        await pause();
        check(await snapshot()===beforeSession,'numpad shortcut acted underneath modal');
        closeSession();
        numpad('/');
        check(sessionOpen()&&SessionNavigation.panel().context.startsWith('session-menu:'),'divide did not open session menu');
        closeSession();
        key('=',false,'Equal');
        check(sessionOpen()&&SessionNavigation.panel().context.startsWith('session-help:'),'equals did not open help');
        const reading=document.querySelector('#session-navigation .session-navigation-content');
        check(reading.scrollHeight>reading.clientHeight,'help fixture cannot exercise scrolling');
        reading.scrollTop=0;
        numpad('+');await wait(()=>reading.scrollTop>0,'plus scrolls reading');
        const scrolled=reading.scrollTop;
        numpad('-');await wait(()=>reading.scrollTop<scrolled,'minus scrolls reading back');
        closeSession();
        key('r');
        check(document.activeElement.closest('.rc-powers'),'R did not focus powers');
        key('ArrowDown');
        check(document.activeElement.classList.contains('keyboard-choice-focused'),'menu focus missing');
        key('Enter');await wait(()=>state.combat.resonance.phase==='preview'&&!busy,'power selected');
        key('Escape');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'cancel power');
        const beforeTyping=await snapshot();
        for(const tag of ['input','textarea','div']){
          const text=document.createElement(tag);
          if(tag==='div')text.contentEditable='true';
          document.body.append(text);text.focus();
          for(const numLock of [true,false]){
            for(const value of ['7','9','5','1','3','0','.','Enter'])numpad(value,numLock);
          }
          numpad('*');numpad('/');key('=',false,'Equal');key('Backspace');key('m');key('d');
          check(await snapshot()===beforeTyping,'typing activated a game shortcut in '+tag);
          check(!document.body.classList.contains('side-panel-open')&&!sessionOpen(),'typing opened a panel in '+tag);
          text.remove();
        }
        check(physicalCardKeyBuffer==='','keyboard-wedge captured normal typing');
        await chooseDoubleShot();
        numpad('.');await settle();
        check((await domain()).targets.length===1,'decimal dot did not select one target');
        await pointAtTarget();
        numpad(',');await settle();
        check((await domain()).targets.length===2,'decimal comma did not add second target');
        key('Backspace');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'cancel multiple selection');
        await chooseDoubleShot();
        numpad('.',false);await settle();
        check((await domain()).targets.length===1,'NumLock-off Delete did not select one target');
        await pointAtTarget();
        numpad('.');await settle();
        check((await domain()).targets.length===2,'second target was not added');
        numpad('Enter');await wait(()=>state.input.kind==='dice'&&!busy,'confirm multiple targets');
        const die=state.combat.resonance.decision.die.value;
        numpad('+');await settle();
        check(state.combat.resonance.decision.die.value===die+1,'numpad plus did not adjust physical die');
        numpad('-');await settle();
        check(state.combat.resonance.decision.die.value===die,'numpad minus did not adjust physical die');
        check(!boardScanInFlight,'board scan running in keyboard mode');
        check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
        await finish('PASS');
      } catch(error) {
        await finish(String(error.stack));
      }
    })();</script>'''.replace("LEGAL_TARGET", repr(legal))

    @app.after_request
    def inject(response: Any) -> Any:
        if request.path == "/play" and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace("</body>", harness + "</body>"))
        return response

    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([
            chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
            "--no-first-run", "--disable-background-networking", "--no-proxy-server",
            f"--user-data-dir={tmp_path / 'chrome'}", "--window-size=1268,800",
            f"http://127.0.0.1:{server.server_port}/play",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(45), f"Browser did not report: {progress}"
        assert report.get("result") == "PASS", {**report, **progress}
        assert not scans, "Keyboard browser started a physical scan"
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
