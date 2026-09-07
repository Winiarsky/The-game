function shieldBashHtml(pending) {
  const contest = `${esc(pending.actor_name)} przeciw ${esc(pending.target_name)} — sporny test Siły. Remis wygrywa obrońca.`;
  const defense = pending.defender_roll === null ? 'Za przeciwnika rzuci aplikacja.'
    : `Obrona przeciwnika (automat): k20 ${pending.defender_roll} ${signedNumber(pending.defender_modifier)} = ${pending.defender_roll + pending.defender_modifier}.`;
  if (pending.stage === 'result') {
    const push = pending.destination ? `Przesuń figurkę celu na (${pending.destination.join(',')}) — zielone pole na planszy.`
      : pending.succeeded ? 'Brak odepchnięcia: pole za celem jest zablokowane.' : 'Cel pozostaje na swoim polu.';
    return `<div class="combat-action-box" role="status"><h3>Uderzenie tarczą · ${pending.succeeded ? 'wygrana' : 'obrońca wygrywa'}</h3>
      <p>${contest}</p><p>${esc(defense)}</p><p><b>Test: ${pending.attacker_total} przeciw ${pending.defender_total}.</b></p>
      <p><b>Obrażenia: ${pending.damage}.</b> PW celu: ${pending.hp_before} → ${pending.hp_after}.</p>
      <p>${esc(push)}</p><p>${esc(pending.cost_note)}</p>
      <button data-card-action="accept" onclick="confirmShieldBashResult()">Zastosuj wynik · Enter</button></div>`;
  }
  const controls = pending.stage === 'contest'
    ? `<label>${esc(pending.actor_name)} · k20 Siły<input id="shield-bash-attacker-roll" type="number" min="1" max="20" data-roll-label="${esc(pending.actor_name)} · test Siły" required></label>`
    : `<label>Obrażenia k6<input id="shield-bash-damage-roll" type="number" min="1" max="6" data-roll-label="Uderzenie tarczą · obrażenia" required></label>`;
  return `<div class="combat-action-box"><p>${contest}</p><p>${esc(defense)}</p><p>${pending.stage === 'damage' ? 'Wygrany test. Rzuć k6; aplikacja doda modyfikator Siły Garrana.' : 'Wpisz naturalny wynik k20 bohatera. Aplikacja wykona rzut przeciwnika i doliczy modyfikatory Siły.'}</p>
    <div class="row">${controls}<button onclick="submitShieldBashRolls()">Potwierdź rzuty</button>
    <button class="secondary" onclick="cancelClassFeatureTargeting()">Anuluj</button></div></div>`;
}
function submitShieldBashRolls() {
  const pending = state.combat.shield_bash;
  const value = id => Number(document.getElementById(id).value);
  const data = pending.stage === 'contest'
    ? {attacker_roll:value('shield-bash-attacker-roll')}
    : {damage_roll:value('shield-bash-damage-roll')};
  api('/api/combat/shield-bash/rolls', data, 'Sprawdzam Uderzenie tarczą...');
}
function confirmShieldBashResult() {
  api('/api/combat/shield-bash/confirm', {}, 'Stosuję wynik Uderzenia tarczą...');
}
