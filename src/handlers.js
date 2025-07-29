import { app, processedIds, sentTs, processedEventIds, greetedThreads } from './app.js';
import { generateContent } from '../agent/gemini.js';
import { resolveName } from '../utils/nameResolution.js';
import { isTopLevelDm, normalizeSlackId } from '../utils/slackUtils.js';
import { botUserId } from './app.js';
import logger from '../utils/logger.js'

// Registra handlers en app
export function registerHandlers() {
  // 1) assistant_thread_started: saluda y marca el hilo
  app.event('assistant_thread_started', async ({ event, say, client }) => {
    const at = event.assistant_thread || {};
    const userId = at.user_id;
    let channelId = at.channel_id || at.context?.channel_id; // Fallback por issue conocido
    if (!channelId) {
      // Fetch si falta (de search, a veces falta)
      console.warn('Missing channel_id, attempting fallback');
      channelId = event.channel; // O usa client para inferir
    }
    const threadTs = at.thread_ts;
    if (channelId && threadTs) {
      const key = `${channelId}:${threadTs}`;
      if (!greetedThreads.has(key)) {
        const name = await resolveName(userId);
        const saludo = name ? `Hola ${name}, ¿cómo te puedo ayudar hoy?` : '¡Hola! ¿Cómo estás? ¿En qué puedo ayudarte hoy?';
        try {
          await say({ text: saludo, thread_ts: threadTs });
          greetedThreads.add(key);
        } catch (error) {
          logger.error(`Error in message: ${error.message}`);
        }
      }
    }
  });

  // 2) Mensajes (incluye DM fallback y app_mention)
  app.event('message', async ({ event, say, client }) => {
    const eventTs = event.ts;
    const user = event.user;
    const botId = event.bot_id;
    const subtype = event.subtype;
    const threadTs = event.thread_ts || eventTs;

    // Ignora bots, duplicados
    if (sentTs.has(eventTs) || user === botUserId || botId || subtype === 'bot_message') return;

    // DM normal o channel_type im/app_home
    const channel = event.channel || '';
    const channelType = event.channel_type;
    if (channel.startsWith('D') || ['im', 'app_home'].includes(channelType)) {
      try {
        const response = await generateContent(event.text || '');
        const textOut = (response || '').replace(/\*\*/g, '*') || '¿Puedes repetir tu mensaje?';
        const resp = await say({ text: textOut, thread_ts: threadTs });
        sentTs.add(resp.ts);
      } catch (error) {
        console.error(`Error in message: ${error.message}`);
      }
    }
  });

  // 3) app_mention
  app.event('app_mention', async ({ event, say }) => {
    if (event.user === botUserId) return;
    const clientMsgId = event.client_msg_id;
    if (processedIds.has(clientMsgId)) return;

    const threadTs = event.thread_ts || event.ts;
    try {
      const response = await generateContent(event.text || '');
      const textOut = (response || '').replace(/\*\*/g, '*');
      const resp = await say({ text: textOut, thread_ts: threadTs });
      sentTs.add(resp.ts);
      processedIds.add(clientMsgId);
    } catch (error) {
      console.error(`Error in app_mention: ${error.message}`);
    }
  });
}

// Llama esto en index.js o app.js después de setup
// Pero como es import, llama registerHandlers() después de import en index si necesitas.
