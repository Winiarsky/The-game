/* Text is authored in the mission pack; callers escape it for their HTML context. */
function sessionUiText(key, params = {}) {
  const copy = typeof state !== 'undefined' && state?.ui_copy
    ? state.ui_copy : window.SESSION_UI_COPY || {};
  let value = copy;
  for (const part of key.split('.')) value = value?.[part];
  if (typeof value !== 'string') {
    console.error('Missing UI copy:', key);
    return `[${key}]`;
  }
  return value.replace(/\{([a-zA-Z_][\w]*)\}/g, (match, name) =>
    Object.hasOwn(params, name) ? String(params[name]) : match);
}
