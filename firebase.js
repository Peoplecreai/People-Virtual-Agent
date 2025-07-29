import admin from 'firebase-admin';

let cachedDb = null;
let cachedApp = null;

function getCreds() {
  const credsJson = process.env.MY_GOOGLE_CREDS;
  if (!credsJson) {
    console.error('[ERROR] MY_GOOGLE_CREDS not set');
    return null;
  }
  try {
    return JSON.parse(credsJson);
  } catch (error) {
    console.error('[ERROR] Invalid MY_GOOGLE_CREDS JSON');
    return null;
  }
}

export async function getDb() {
  if (cachedDb) return cachedDb;

  const creds = getCreds();
  if (!creds) return null;

  if (!cachedApp) {
    cachedApp = admin.initializeApp({
      credential: admin.credential.cert(creds),
    });
  }
  cachedDb = admin.firestore();
  return cachedDb;
}

// Función para obtener historial por user_id
export async function getUserHistory(userId) {
  const db = await getDb();
  if (!db) return null;

  try {
    const doc = await db.collection('chats').doc(userId).get();
    return doc.exists ? doc.data().history : [];
  } catch (error) {
    console.error(`[FIRESTORE getUserHistory] ${error.message}`);
    return [];
  }
}

// Función para guardar historial por user_id
export async function saveUserHistory(userId, history) {
  const db = await getDb();
  if (!db) return null;

  try {
    await db.collection('chats').doc(userId).set({ history }, { merge: true });
    return true;
  } catch (error) {
    console.error(`[FIRESTORE saveUserHistory] ${error.message}`);
    return false;
  }
}

// (Opcional) Función para borrar historial
export async function resetUserHistory(userId) {
  const db = await getDb();
  if (!db) return null;

  try {
    await db.collection('chats').doc(userId).delete();
    return true;
  } catch (error) {
    console.error(`[FIRESTORE resetUserHistory] ${error.message}`);
    return false;
  }
}
