import { GoogleSpreadsheet } from 'google-spreadsheet';
import { JWT } from 'google-auth-library';
import { normalizeSlackId } from '../utils/slackUtils.js';

let cachedAuth = null;

// Normaliza strings para búsqueda de encabezados
function nk(s) {
  return s.toLowerCase().replace(/[^a-z0-9]/g, '');
}

// Busca el Slack ID en cualquier encabezado "Slack ID", "slackid", etc.
function getSlackIdFromRow(obj) {
  const keys = Object.keys(obj);
  for (const key of keys) {
    const norm = nk(key);
    if (norm.includes('slack') && norm.includes('id')) {
      return obj[key];
    }
  }
  // Fallback por si acaso
  return (
    obj['Slack ID'] ||
    obj['slackid'] ||
    obj['slack_id'] ||
    obj['idslack'] ||
    obj['slack']
  );
}

async function getAuth() {
  if (cachedAuth) return cachedAuth;
  const credsJson = process.env.MY_GOOGLE_CREDS;
  if (!credsJson) {
    console.error('[ERROR] MY_GOOGLE_CREDS not set');
    return null;
  }
  let credsDict;
  try {
    credsDict = JSON.parse(credsJson);
  } catch (error) {
    console.error('[ERROR] Invalid MY_GOOGLE_CREDS JSON');
    return null;
  }
  cachedAuth = new JWT({
    email: credsDict.client_email,
    key: credsDict.private_key,
    scopes: [
      'https://www.googleapis.com/auth/spreadsheets.readonly',
      'https://www.googleapis.com/auth/drive.readonly',
    ],
  });
  return cachedAuth;
}

async function openSheet() {
  const auth = await getAuth();
  if (!auth) return null;

  const sheetId = process.env.SHEET_ID;
  if (!sheetId) {
    console.error('[ERROR] SHEET_ID not set');
    return null;
  }

  const doc = new GoogleSpreadsheet(sheetId, auth);
  await doc.loadInfo();

  const tab = process.env.SHEET_TAB;
  const ws = tab ? doc.sheetsByTitle[tab] : doc.sheetsByIndex[0];
  return ws;
}

export async function getUserRecord(slackId) {
  try {
    const ws = await openSheet();
    if (!ws) return null;

    const rows = await ws.getRows();
    const target = normalizeSlackId(slackId);

    for (const row of rows) {
      const obj = row.toObject();
      let sid = getSlackIdFromRow(obj);
      sid = normalizeSlackId(String(sid || ''));
      if (sid === target) return obj;
    }
    return null;
  } catch (error) {
    console.error(`[SHEETS getUserRecord] ${error.message}`);
    return null;
  }
}

export { getPreferredName } from '../utils/nameResolution.js'; // Exporta si necesitas

