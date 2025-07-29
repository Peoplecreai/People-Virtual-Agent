// getSlackName carga app solo cuando se usa para evitar requerir variables de entorno durante tests

export function normalizeSlackId(value) {
  if (!value) return '';

  let v = String(value).trim();

  // <@U…|alias>
  if (v.startsWith('<@') && v.endsWith('>')) {
    v = v.slice(2, -1);
    if (v.includes('|')) v = v.split('|')[0];
  }

  // URL -> último segmento
  if (v.startsWith('https://')) {
    v = v.replace(/\/$/, '').split('/').pop();
  }

  // 'T……-U……' (team-user)
  if (v.includes('-')) {
    const parts = v.split('-');
    const right = parts[parts.length - 1];
    if (right && right.startsWith('U')) v = right;
  }

  // Si viene 'T…… U……' o algo raro, toma desde la 'U…'
  const uPos = v.indexOf('U');
  if (uPos > 0) v = v.slice(uPos);

  return v;
}

export function isTopLevelDm(event) {
  const ch = event.channel || '';
  const chType = event.channel_type;
  const isDm = ch.startsWith('D') || chType === 'im';
  const threadTs = event.thread_ts;
  const ts = event.ts;
  const isTop = !threadTs || threadTs === ts;
  return isDm && isTop;
}

export async function getSlackName(slackId) {
  try {
    const { app } = await import('../src/app.js');
codex/fix-nameresolution.js-functionality
    const sid = normalizeSlackId(slackId);
    const { user } = await app.client.users.info({ user: slackId });
    const profile = user.profile || {};
    return profile.display_name || profile.real_name;
  } catch (error) {
    console.error(`Failed to fetch Slack profile: ${error.message}`);
    return null;
  }
}
