function shieldBashHtml(pending) {
  const contest = `${esc(pending.actor_name)} przeciw ${esc(pending.target_name)} — sporny test Siły. Remis wygrywa obrońca.`;
  const defense = pending.defender_roll === null ? 'Za przeciwnika rzuci aplikacja.'
    : `Obrona przeciwnika (automat): k20 ${pending.defender_roll} ${signedNumber(pending.defender_modifier)} = ${pending.defender_roll + pending.defender_modifier}.`;
  const attack = pending.attacker_roll === null ? ''
    : `Twój rzut: k20 ${pending.attacker_roll} ${signedNumber(pending.attacker_modifier)} (Siła${pending.charge_bonus ? ` + naładowanie ${signedNumber(pending.charge_bonus)}` : ''}) = ${pending.attacker_roll + pending.attacker_modifier}.`;
  if (pending.stage === 'result') {
    const push = pending.destination ? `Przesuń figurkę celu na (${pending.destination.join(',')}) — zielone pole na planszy.`
      : pending.succeeded ? 'Brak odepchnięcia: pole za celem jest zablokowane.' : 'Cel pozostaje na swoim polu.';
    return `<div class="combat-action-box" role="status"><h3>Uderzenie tarczą · ${pending.succeeded ? 'wygrana' : 'obrońca wygrywa'}</h3>
      <p>${contest}</p><p>${esc(attack)}</p><p>${esc(defense)}</p><p><b>Test: ${pending.attacker_total} przeciw ${pending.defender_total}.</b></p>
      <p><b>Obrażenia: ${pending.damage}.</b> PW celu: ${pending.hp_before} → ${pending.hp_after}.</p>
      <p>${esc(push)}</p><p>${esc(pending.cost_note)}</p>
      <button data-card-action="accept" onclick="confirmShieldBashResult()">✓ Zastosuj wynik</button></div>`;
  }
  const damageDice = pending.damage_die_sides || Array(pending.damage_dice || 1).fill(6);
  const damageLabel = pending.damage_label || `${pending.damage_dice || 1}k6`;
  const controls = pending.stage === 'contest'
    ? `<label>${esc(pending.actor_name)} · k20 Siły<input id="shield-bash-attacker-roll" type="number" min="1" max="20" data-roll-label="Uderzenie tarczą · Twój rzut k20 Siły" required></label>`
    : damageDice.map((sides,index) => `<label>Obrażenia · k${sides}<input id="shield-bash-damage-roll-${index}" class="shield-bash-damage-die" type="number" min="1" max="${sides}" data-roll-label="Uderzenie tarczą · obrażenia k${sides}" data-roll-dice="1d${sides}" data-roll-modifier="0" required></label>`).join('');
  return `<div class="combat-action-box"><p>${contest}</p>${attack ? `<p>${esc(attack)}</p>` : ''}<p>${esc(defense)}</p><p>${pending.stage === 'damage' ? `Wygrany test. Rzuć ${damageLabel} i zatwierdź ✓ wynik każdej kości. Aplikacja zsumuje kości i raz doliczy modyfikator Siły Garrana.` : 'Rzuć fizyczną k20. Ustaw jej wynik przyciskami − / + i zatwierdź ✓. Dopiero po potwierdzeniu podsumowania aplikacja rzuci za przeciwnika.'}</p>
    <div class="row">${controls}<button onclick="submitShieldBashRolls()">Potwierdź rzuty</button>
    <button class="secondary" onclick="cancelClassFeatureTargeting()">Anuluj</button></div></div>`;
}
function submitShieldBashRolls() {
  const pending = state.combat.shield_bash;
  const value = id => Number(document.getElementById(id).value);
  const data = pending.stage === 'contest'
    ? {attacker_roll:value('shield-bash-attacker-roll')}
    : {damage_roll:[...document.querySelectorAll('.shield-bash-damage-die')].reduce((sum,input)=>sum+Number(input.value),0)};
  api('/api/combat/shield-bash/rolls', data, 'Sprawdzam Uderzenie tarczą...');
}
function confirmShieldBashResult() {
  api('/api/combat/shield-bash/confirm', {}, 'Stosuję wynik Uderzenia tarczą...');
}
