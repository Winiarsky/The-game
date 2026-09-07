/* Local vector dice: shape plus label, legible without relying on color. */
const diceIconShapes = {
  4: {outline:'M32 5 60 56H4Z', facets:'M32 5v34L4 56m28-17 28 17'},
  6: {outline:'M8 8h48v48H8Z', facets:'M8 8l10 10h28L56 8M18 18v28L8 56m10-10h28l10 10M46 18v28'},
  8: {outline:'M32 3 59 32 32 61 5 32Z', facets:'M32 3 19 32l13 29m0-58 13 29-13 29M5 32h14m26 0h14'},
  10: {outline:'M32 3 59 25 48 49 32 61 16 49 5 25Z', facets:'M32 3 17 23 16 49m16-46 15 20 1 26M5 25l12-2m30 0 12 2M16 49l16-9 16 9M32 40v21'},
  12: {outline:'M21 3h22l17 17v24L43 61H21L4 44V20Z', facets:'M32 15 49 27 42 47H22L15 27ZM21 3l11 12L43 3M4 20l11 7M60 20 49 27M4 44l18 3-1 14M60 44l-18 3 1 14'},
  20: {outline:'M32 3 58 18v28L32 61 6 46V18Z', facets:'M32 3 18 22 6 18m26-15 14 19 12-4M18 22h28l-14 24ZM6 46l12-24m40 24L46 22M6 46h26l26 0M32 46v15'},
};
function rollStepDieSides(step) {
  if (step.fixed !== null && step.fixed !== undefined && Number.isFinite(step.fixed)) return null;
  if (step.dice) return Number(step.dice.sides);
  // D20 tests and optional bonus dice use bounded individual-result inputs.
  return Number(step.min) === 1 && diceIconShapes[Number(step.max)] ? Number(step.max) : null;
}
function diceIconHtml(sides, count = 1) {
  const shape = diceIconShapes[sides];
  if (!shape) return '';
  const quantity = Number.isInteger(count) && count > 1 ? count : 1;
  return `<span class="dice-icon-group" role="img" aria-label="${quantity > 1 ? quantity + ' kości' : 'Kość'} k${sides}" title="${quantity > 1 ? quantity + ' × ' : ''}k${sides}">${quantity > 1 ? `<small class="dice-icon-count">${quantity}×</small>` : ''}<svg class="dice-icon dice-icon-k${sides}" viewBox="0 0 64 64" aria-hidden="true"><path class="dice-icon-outline" d="${shape.outline}"/><path class="dice-icon-facets" d="${shape.facets}"/><text x="32" y="36" text-anchor="middle">k${sides}</text></svg></span>`;
}
function rollStepDiceIconHtml(step) {
  return diceIconHtml(rollStepDieSides(step), step.dice?.count || 1);
}
