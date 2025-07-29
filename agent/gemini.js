import { GoogleGenAI } from "@google/genai";
import logger from '../utils/logger.js';

const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) throw new Error('GEMINI_API_KEY is not set');

const modelName = process.env.GEMINI_MODEL || 'gemini-2.5-flash'; // Actualizado a versión 2025

const genai = new GoogleGenAI({ apiKey });

export async function generateContent(contents) {
  try {
    const response = await genai.models.generateContent({
      model: modelName,
      contents,
    });
    return response.text;
  } catch (error) {
    logger.error(`Gemini API error: ${error.message}`);
    throw error;
  }
}
