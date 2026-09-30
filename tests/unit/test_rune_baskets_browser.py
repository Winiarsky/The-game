"""Standalone basket-controller transitions; never connect to hardware or runtime."""
from html import unescape
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]

CHECK = r"""
addEventListener('load', () => {
  const failures = [], checks = [];
  const check = (ok, label) => { checks.push(label); if (!ok) failures.push(label); };
  try {
    const app = window.RuneBaskets, data = window.RUNE_BASKET_DATA;
    check(!!app, 'prototype loaded');
    const s = () => app.state;
    const start = (active='garran',party=['garran','mira','lorian']) => app.startCombat({active,party});
    const resources = () => JSON.stringify(s().resources);
    const chargeCount = id => Object.values(s().resources[id]).reduce((n,b) => n+b.charged.length,0);
    const pickBash = () => { app.press(18); app.selectField(4,2); app.press(17); };
    const invariant = label => check(app.validate(s()) && s().party.every(id => Object.values(s().resources[id]).every(b => b.charged.length <= b.capacity)),label);
    app.reset();
    check(data.heroes.length===7, 'all seven hero cards available');
    check(document.querySelectorAll('.hero-choice').length===7, 'all seven heroes selectable');
    for(const id of ['brakka','dagna','erynd']) app.toggleHero(id);
    check(s().party.length===6, 'party supports six heroes');
    app.toggleHero('nimra');
    check(s().party.length===6, 'seventh hero cannot join');
    app.reset(); app.toggleHero('mira');
    check(!app.bindings().get(28).enabled, 'fewer than three heroes cannot prepare');
    app.toggleHero('mira'); app.press(28);
    check(s().phase==='prepare', 'preparation starts on confirm');
    app.press(29); app.press(29); app.press(17); app.press(17); app.press(17);
    check(s().preparations.garran.offense.join(',')==='Grot,Grot', 'preparation accepts duplicate symbols up to category capacity');
    app.press(29);
    check(!app.bindings().get(28).enabled, 'incomplete category cannot be confirmed');
    app.press(17);
    check(app.bindings().get(28).enabled, 'exact category capacities restore confirmation');
    app.reset(); start();
    check(document.querySelectorAll('.board-pad').length===29 && document.querySelectorAll('.board-gap').length===1, 'fixed 30-slot controller has information next to controls');
    check(app.slot('Spirala')===19 && app.slot('Gwiazda')===25, 'focus and information have fixed controls');
    check(!document.querySelector('.ability-list'), 'idle has no on-screen ability catalogue');
    check(s().resources.garran.defense.capacity===4 && chargeCount('garran')===9, 'personal capacities replace seven-card hand');
    const opening=resources();
    app.press(18);
    check(s().phase==='target', 'Kotwica is ability button, no rune spent');
    check(!document.querySelector('.legal-targets button'), 'target list is informational');
    check(!app.selectField(6,4), 'melee excludes distant target');
    check(app.selectField(4,2) && s().phase==='base', 'figure selection advances without intermediate confirm');
    app.press(17);
    check(s().phase==='resonance' && s().pending.base==='Grot', 'any own offense symbol pays base');
    app.press(13);
    check(s().pending.payer==='garran' && document.querySelector('.push-preview').textContent.includes('2'), 'Oko previews push from one to two fields');
    check(resources()===opening && s().budgets.special, 'all selections are free before final confirm');
    const oldRevision=s().revision;
    app.press(28);
    check(s().phase==='resolution' && chargeCount('garran')===7, 'single final confirm commits base and resonance');
    check(!s().budgets.special && s().budgets.ordinary && s().actors.garran.reaction, 'self resonance costs special but not ordinary or reaction');
    const paid=resources();
    check(!app.press(28,oldRevision) && resources()===paid, 'stale confirm cannot resolve or double pay');
    app.resolvePhysical(true,5);
    check(s().phase==='push' && s().actors.enemy_1.hp===31, 'physical success records exact submitted damage and opens push');
    check(app.selectField(6,2), 'Oko makes two-field push legal');
    app.press(28);
    check(s().actors.enemy_1.x===6 && s().actors.enemy_1.y===2, 'push updates target figure on board');
    app.press(28); app.press(28);
    check(resources()===paid, 'extra confirmation never pays twice');
    invariant('capacity invariant after complete boosted action');

    start(); pickBash(); app.press(13); app.press(21);
    check(s().phase==='support', 'Most opens explicit supporter figure step');
    check(!app.selectField(4,2), 'enemy cannot support');
    check(app.selectField(2,2) && s().phase==='resonance' && s().pending.payer==='mira', 'ally figure returns directly to final summary');
    check(document.querySelector('.payment-summary').textContent.includes('Mira'), 'chosen payer remains visible');
    const beforeSupport=resources();
    app.press(29); app.press(29); app.press(29);
    check(s().phase==='idle' && resources()===beforeSupport && s().actors.mira.reaction, 'backtracking cancels both personal costs and ally reaction');
    pickBash(); app.press(13); app.press(21); app.selectField(2,2); app.press(28);
    check(chargeCount('garran')===8 && chargeCount('mira')===8 && !s().actors.mira.reaction, 'support atomically spends each owner rune and ally reaction');
    check(s().resources.garran.mobility.charged.includes('Oko'), 'ally support preserves actor own resonance rune');
    app.resolvePhysical(false,0); app.press(28);
    app.press(3); app.press(28);
    check(s().active==='mira' && !s().actors.mira.reaction, 'own turn does not reset spent support reaction');
    app.press(3); app.press(28); app.press(3); app.press(28);
    check(s().round===2 && s().actors.mira.reaction, 'round boundary restores support reaction');

    start(); s().resources.garran.offense.charged=[]; app.render();
    check(!app.bindings().get(18).enabled, 'ally cannot lend base-category payment');
    start(); s().resources.garran.mobility.charged=[]; s().actors.mira.reaction=false; s().actors.lorian.x=8; s().actors.lorian.y=6; app.render(); pickBash();
    check(!app.bindings().get(13).enabled, 'resonance unavailable when allies lack reaction or range');
    start(); pickBash(); app.press(13); app.press(6);
    check(s().pending.resonance!=='push' && s().pending.payer==='garran', 'second resonance replaces first instead of stacking');
    app.press(28);
    check(chargeCount('garran')===7 && s().resources.garran.mobility.charged.includes('Oko'), 'only selected resonance is paid');

    start(); s().resources.garran.offense.charged=[]; app.render(); app.press(19);
    check(s().phase==='focus_pick' && s().budgets.special, 'focus selection is free before confirmation');
    app.press(17); app.press(17);
    check(s().pending.selections.join(',')==='offense,offense', 'focus can select two places in same category');
    app.press(28);
    check(s().phase==='recharge' && !s().budgets.special && s().rechargeQueue.length===2, 'focus commits special once and requests two physical k4s');
    app.press(26); app.press(26); app.press(26); app.press(26);
    check(s().die===4, 'physical k4 input bounded at four');
    app.save(); s().die=1; app.restore(); app.render();
    check(s().die===4 && s().rechargeQueue.length===2 && !s().budgets.special, 'save restore keeps pending k4 and spent budget');
    app.press(28);
    check(s().resources.garran.offense.charged.join(',')==='Błysk' && s().rechargeQueue.length===1, 'k4 four gives fourth offense symbol');
    app.press(26); app.press(28);
    check(s().resources.garran.offense.charged.join(',')==='Błysk,Hak', 'second k4 gives same category different symbol');
    invariant('capacity invariant after focus and restoration');

    start();
    const guard=data.heroes.find(h=>h.id==='garran').regeneration[0];
    app.recordEvent('garran',guard.event);
    check(s().phase==='idle' && s().regenUsed[`garran:${guard.id}`]===1, 'full basket consumes first-event limit without loading');
    s().resources.garran.defense.charged.pop(); app.render();
    check(!app.recordEvent('garran',guard.event) && s().resources.garran.defense.charged.length===3, 'repeated same-round event cannot farm runes');
    s().round=2; app.render(); app.recordEvent('garran',guard.event);
    check(s().phase==='recharge' && s().rechargeQueue[0].category==='defense', 'next round qualifying event recharges correct personal category');
    app.press(28);
    check(s().resources.garran.defense.charged.length===4, 'event charges only the emptied category place');

    start('erynd',['garran','mira','erynd']);
    const shot=data.heroes.find(h=>h.id==='erynd').cards.find(c=>c.id==='anchoring_arrow');
    app.chooseAction(shot.id); app.selectField(4,2);
    if(s().phase==='base') app.press(app.slot(s().resources.erynd[shot.category].charged[0]));
    check(s().phase==='surcharge', 'adjacent ally triggers paid-shot flaw surcharge');
    const ownBefore=chargeCount('erynd');
    const available=[...app.bindings()].find(([slot,b])=>slot>=5&&slot<24&&b.enabled);
    app.press(available[0]);
    check(s().phase==='resonance' && s().pending.surcharge.length===1, 'player explicitly selects personal surcharge rune');
    app.press(28);
    check(chargeCount('erynd')===ownBefore-2, 'base and flaw surcharge committed atomically');

    start('lorian',['garran','mira','lorian']);
    s().resources.garran.offense.charged=[]; app.render();
    app.chooseAction('mana_recovery'); app.selectField(3,2);
    app.press(app.slot('Korona'));
    check(s().phase==='resonance', 'recovery uses generic own aura base selection');
    s().budgets.ordinary=false; app.render();
    check(!app.bindings().get(app.slot('Wieża')).enabled, 'recovery extra charge requires resonance A+S budget');
    app.press(28); app.press(17); app.press(17); app.press(28); app.press(28); app.press(28); app.press(28);
    check(s().resources.garran.offense.charged.length===2 && s().onceUsed.includes('lorian:mana_recovery'), 'recovery restores ally old empty places and records once-per-battle');
    invariant('invariants after ally recovery');

    for(const active of data.heroes.map(h=>h.id)) {
      const party=[active,...data.heroes.map(h=>h.id).filter(id=>id!==active).slice(0,2)];
      start(active,party); app.press(25);
      check(document.getElementById('info-content').textContent.includes(data.heroes.find(h=>h.id===active).name),`information shows ${active}`);
      app.press(29);
      check(document.documentElement.scrollWidth<=innerWidth+1,`no horizontal overflow ${active}`);
      const panel=document.querySelector('.controller').getBoundingClientRect();
      check(panel.bottom<=innerHeight+1 && panel.top>=0,`controller visible ${active}`);
      invariant(`initial personal capacities ${active}`);
    }
  } catch(error) { failures.push(error.stack || String(error)); }
  const out=document.createElement('pre'); out.id='browser-check'; out.textContent=JSON.stringify({failures,checks}); document.body.append(out);
});
"""


@pytest.mark.parametrize("width", [1131, 1280])
def test_personal_basket_controller_roundtrip(tmp_path: Path, width: int) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Local Chrome required")
    source = ROOT / "docs/ui/rune-baskets.html"
    html = source.read_text().replace(
        "<head>", f'<head><base href="{source.parent.as_uri()}/">'
    )
    html = html.replace("</body>", f"<script>{CHECK}</script></body>")
    check = tmp_path / "check.html"
    check.write_text(html)
    result = subprocess.run(
        [
            chrome, "--headless", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--disable-background-networking",
            "--allow-file-access-from-files", f"--window-size={width},720",
            "--virtual-time-budget=4000", f"--user-data-dir={tmp_path / 'chrome'}",
            "--dump-dom", check.as_uri(),
        ],
        capture_output=True, text=True, timeout=40,
    )
    assert result.returncode == 0, result.stderr[-1500:]
    found = re.search(r'<pre id="browser-check">(.*?)</pre>', result.stdout, re.S)
    assert found, "Browser did not finish interaction check: " + result.stderr[-1000:]
    report = json.loads(unescape(found.group(1)))
    assert not report["failures"], report["failures"]
    assert len(report["checks"]) >= 60
