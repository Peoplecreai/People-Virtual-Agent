import { app, sentTs, processedEventIds, greetedThreads } from './app.js';
import { sendChatMessage } from '../agent/gemini.js';
import { resolveName } from '../utils/nameResolution.js';
import { normalizeSlackId } from '../utils/slackUtils.js';
import { botUserId } from './app.js';
import logger from '../utils/logger.js';

export function registerHandlers() {
  // 1) Saludo inicial SOLO en AI App
  app.event('assistant_thread_started', async ({ event, say, client }) => {
    const at = event.assistant_thread || {};
    const userId = at.user_id;
    let channelId = at.channel_id || at.context?.channel_id;
    if (!channelId) {
      // Fallback para obtener canal si falta
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
        const saludo = name
          ? `Hola ${name}, ¿cómo te puedo ayudar hoy?`
          : '¡Hola! ¿Cómo estás? ¿En qué puedo ayudarte hoy?';
        try {
          await client.chat.postMessage({ channel: channelId, text: saludo, thread_ts: threadTs });
          greetedThreads.add(key);
        } catch (error) {
          logger.error(`Error in message: ${error.message}`);
        }
      }
    }
  });

  // 2) Solo responde mensajes en hilos de AI App (NO DMs normales, NO canales)
  app.event('message', async ({ event, say, client, body }) => {
    const eventTs = event.ts;
    const eventId = body.event_id;
    const user = event.user;
    const botId = event.bot_id;
    const subtype = event.subtype;
    const threadTs = event.thread_ts || eventTs;
    const channel = event.channel || '';

    // Ignora bots, duplicados, y mensajes fuera de hilo
    if (
      sentTs.has(eventTs) ||
      processedEventIds.has(eventId) ||
      user === botUserId ||
      botId ||
      subtype === 'bot_message' ||
      !threadTs
    ) return;

    // Solo responde si el hilo ya fue saludado (AI App), no responde en DMs ni canales random
    const key = `${channel}:${threadTs}`;
    if (!greetedThreads.has(key)) return;

    processedEventIds.add(eventId);

    try {
      const response = await generateContent(event.text || '');
      const textOut = (response || '').replace(/\*\*/g, '*') || '¿Puedes repetir tu mensaje?';
      const resp = await say({ text: textOut, thread_ts: threadTs });
      sentTs.add(resp.ts);
    } catch (error) {
      logger.error(`Error in message: ${error.message}`);
    }
  });
}
