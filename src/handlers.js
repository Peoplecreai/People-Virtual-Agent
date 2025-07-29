import { app, processedIds, sentTs, processedEventIds, greetedThreads } from './app.js';
import { generateContent } from '../agent/gemini.js';
import { resolveName } from '../utils/nameResolution.js';
import { isTopLevelDm, normalizeSlackId } from '../utils/slackUtils.js';
import { botUserId } from './app.js';
import logger from '../utils/logger.js'

// Registra handlers en app
export function registerHandlers() {
  // Solo handler para assistant_thread_started: saluda y marca el hilo
  app.event('assistant_thread_started', async ({ event, say, client }) => {
    const at = event.assistant_thread || {};
    const userId = at.user_id;
    let channelId = at.channel_id || at.context?.channel_id; // Fallback por issue conocido
    if (!channelId) {
      // Fetch si falta (de search, a veces falta)
      console.warn('Missing channel_id, attempting fallback');
      try {
        const dm = await client.conversations.open({ users: normalizeSlackId(userId) });
        channelId = dm.channel.id;
      } catch (error) {
        logger.error(`Error opening DM: ${error.message}`);
        return;
      }
    }
    const threadTs = at.thread_ts;
    if (channelId && threadTs) {
      const key = `${channelId}:${threadTs}`;
      if (!greetedThreads.has(key)) {
        const name = await resolveName(userId);
        const saludo = name ? `Hola ${name}, ¿cómo te puedo ayudar hoy?` : '¡Hola! ¿Cómo estás? ¿En qué puedo ayudarte hoy?';
        try {
          const resp = await client.chat.postMessage({ channel: channelId, text: saludo, thread_ts: threadTs });
          greetedThreads.add(key);
        } catch (error) {
          logger.error(`Error in message: ${error.message}`);
        }
      }
    }
  });

  // Handler global de mensajes eliminado.
  // Si después quieres permitir mensajes en DM o en canal, aquí se reactivaría.
}
