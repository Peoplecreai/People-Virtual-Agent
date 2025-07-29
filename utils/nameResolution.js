import { getUserRecord } from '../tools/sheets.js';
import { getSlackName, normalizeSlackId } from './slackUtils.js';

const nameCache = {};

function nk(s) {
  return s.toLowerCase().replace(/[^a-z0-9]/g, '');
}

export async function getPreferredName(slackId) {
  const row = await getUserRecord(slackId);
  if (!row) return null;

  // Claves típicas
  let pref = row['Name (pref)'];
  if (typeof pref === 'string' && pref.trim()) return pref.trim();

  let first = row['Name (first)'];
  if (typeof first === 'string' && first.trim()) return first.trim();

  // Normalizadas
  const rn = Object.fromEntries(Object.entries(row).map(([k, v]) => [nk(k), v]));
  pref = rn.namepref;
  first = rn.namefirst || rn.firstname;
  if (typeof pref === 'string' && pref.trim()) return pref.trim();
  if (typeof first === 'string' && first.trim()) return first.trim();

  return null;
}

export async function resolveName(slackId) {
  const sid = normalizeSlackId(slackId);
  if (nameCache[sid]) return nameCache[sid];

  let name = await getSlackName(sid);
  const pref = await getPreferredName(sid);
  if (pref) name = pref;

  if (name) nameCache[sid] = name;
  return name;
}
