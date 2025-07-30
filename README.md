# Slack Gemini Agent

Este proyecto implementa un bot de Slack en Node.js que utiliza la API de Gemini y almacena el contexto de las conversaciones en Firebase. También puede consultar un Google Sheet para resolver nombres de usuario.

## Requisitos
- Node.js 18 o superior
- Una cuenta de Slack con permisos para crear aplicaciones
- Credenciales de Google (para Firestore y Google Sheets)

## Instalación
```bash
npm install
```

Copia el archivo `.env.example` a `.env` y completa los valores necesarios.

```bash
cp .env.example .env
```

## Variables de entorno
- `SLACK_SIGNING_SECRET` – token de firma de tu app de Slack.
- `SLACK_BOT_TOKEN` – token del bot de Slack.
- `BOT_USER_ID` – ID del usuario bot (opcional).
- `PORT` – puerto donde se ejecutará la aplicación (3000 por defecto).
- `GEMINI_API_KEY` – clave de API para usar Gemini.
- `GEMINI_MODEL` – nombre del modelo de Gemini (opcional).
- `MY_GOOGLE_CREDS` – JSON con las credenciales de servicio de Google.
- `SHEET_ID` – ID del Google Sheet con los usuarios.
- `SHEET_TAB` – nombre de la pestaña del Sheet (opcional).

## Uso
Inicia la aplicación con:
```bash
npm start
```

Ejecuta las pruebas con:
```bash
npm test
```

Los registros se guardan en `logs/app.log` y `logs/errors.log`.
