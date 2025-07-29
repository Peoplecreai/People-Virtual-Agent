import boltPkg from '@slack/bolt';
const { App, ExpressReceiver } = boltPkg;
import { sendChatMessage } from '../agent/gemini.js';
import logger from '../utils/logger.js';

// Globals (equivalentes a sets y caches)
export const processedIds = new Set();
export const sentTs = new Set();
export const processedEventIds = new Set();
export const greetedThreads = new Set(); // channel_id:thread_ts

// Configuración inicial
const signingSecret = process.env.SLACK_SIGNING_SECRET;
if (!signingSecret) throw new Error('SLACK_SIGNING_SECRET is not set');

const botToken = process.env.SLACK_BOT_TOKEN;
if (!botToken) throw new Error('SLACK_BOT_TOKEN is not set');

export let botUserId = process.env.BOT_USER_ID;
if (!botUserId) {
  // TODO: Fetch botUserId via auth.test si es necesario (usa app.client.auth.test)
}

// Setup de receiver con endpoint personalizado (para coincidir con Python '/')
const receiver = new ExpressReceiver({
  signingSecret,
  endpoints: { events: '/' }, // Maneja POST en /
});

// Setup de Bolt app
const app = new App({
  receiver,
  token: botToken,
});

// Exporta app para handlers y start
export { app };

// Start function
export async function startApp() {
  await app.start(process.env.PORT || 3000);
  logger.info('⚡️ Bolt app is running!');
}
