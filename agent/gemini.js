import { GoogleGenerativeAI } from '@google/generative-ai';
import logger from '../utils/logger.js';

const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) throw new Error('GEMINI_API_KEY is not set');

const modelName = process.env.GEMINI_MODEL || 'gemini-1.5-flash'; // Actualizado a versión 2025

const genai = new GoogleGenerativeAI(apiKey);
const model = genai.getGenerativeModel({ model: modelName });

export async function generateContent(contents) {
  try {
    const result = await model.generateContent(contents);
    return result.response.text();
  } catch (error) {
    logger.error(`Gemini API error: ${error.message}`);
    throw error;
  }
}
