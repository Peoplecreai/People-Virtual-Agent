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
    const prevHistory = await getChatHistory(userId);
    const updatedHistory = [
      ...prevHistory,
      { role: 'user', text: userMessage }
    ];

    const ai = new GoogleGenAI({ apiKey });
    const chat = ai.chats.create({
      model: modelName,
      history: historyToGeminiFormat(updatedHistory)
    });

    const response = await chat.sendMessage({ message: userMessage });

    updatedHistory.push({ role: 'model', text: response.text });

    await saveChatHistory(userId, updatedHistory);

    return response.text;
  } catch (error) {
    logger.error(`Gemini Chat/Firestore error: ${error.message}`);
    throw error;
  }
}
