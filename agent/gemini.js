import { GoogleGenAI } from "@google/genai";
import { getDb } from '../firebase.js';
import logger from '../utils/logger.js';

const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) throw new Error('GEMINI_API_KEY is not set');
const modelName = process.env.GEMINI_MODEL || 'gemini-2.5-flash-lite';

// Convierte historial simple [{role, text}] al formato de Gemini
function historyToGeminiFormat(history) {
  return (history || []).map(msg => ({
    role: msg.role,
    parts: [{ text: msg.text }]
  }));
}

// Obtiene historial del usuario desde Firestore
async function getChatHistory(userId) {
  const db = await getDb();
  if (!db) return [];
  const doc = await db.collection('chats').doc(userId).get();
  return doc.exists ? doc.data().history : [];
}

// Guarda historial del usuario en Firestore
async function saveChatHistory(userId, history) {
  const db = await getDb();
  if (!db) return;
  await db.collection('chats').doc(userId).set({ history }, { merge: true });
}

// Envía mensaje al chat de Gemini y guarda contexto
export async function sendChatMessage(userId, userMessage) {
  try {
    // 1. Obtén historial completo
    const prevHistory = await getChatHistory(userId);

    // 2. Arma historial actualizado
    const updatedHistory = [
      ...prevHistory,
      { role: 'user', text: userMessage }
    ];

    // 3. Envía historial completo al modelo
    const ai = new GoogleGenAI({ apiKey });
    const chat = ai.chats.create({
      model: modelName,
      history: historyToGeminiFormat(updatedHistory)
    });
    const response = await chat.sendMessage({ message: userMessage });

    // 4. Agrega respuesta del modelo al historial
    updatedHistory.push({ role: 'model', text: response.text });

    // 5. Guarda historial actualizado
    await saveChatHistory(userId, updatedHistory);

    // 6. Regresa respuesta
    return response.text;
  } catch (error) {
    logger.error(`Gemini Chat/Firestore error: ${error.message}`);
    throw error;
  }
}
