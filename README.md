# People Virtual Agent

This project implements a Slack bot using Flask and Bolt for Python. The bot uses Google's Gemini API to generate responses when you mention it or send a direct message.

> **Note**: This project now uses the `google-genai` library for Gemini API calls. See the [official code generation guidelines](https://github.com/googleapis/python-genai/blob/main/codegen_instructions.md) for up‑to‑date usage examples.

## Local testing

Install dependencies and run the service locally:

```bash
pip install -r requirements.txt
python main.py
```

Set the environment variables `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, and `GEMINI_API_KEY` before running the application. Optionally define `BOT_USER_ID` with the identifier of your Slack bot user so the application can avoid replying to its own messages. If `BOT_USER_ID` is not set, the bot will attempt to determine it using Slack's `auth.test` API method. The bot uses the `gemini-2.0-flash` model by default, but you can override this by setting `GEMINI_MODEL`.

Slack verifies requests using the signing secret. Expose the `/` route via a tunnel (e.g. `ngrok`) and configure the resulting URL as the Slack event request URL.

The bot keeps track of the timestamps of the messages it posts and ignores any events that contain those timestamps to avoid responding to itself.

## Deployment

The application is designed for Cloud Run. Environment variables for `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, and `GEMINI_API_KEY` must be provided. The service will fail to start if any of these variables are missing.

Use the `/healthz` route for health checks; it simply returns `OK`.

## Resources

- [Slack API documentation](https://docs.slack.dev/) – reference for events, authentication and best practices.
- [Gemini API code generation instructions](https://github.com/googleapis/python-genai/blob/main/codegen_instructions.md) – recommended usage patterns for the Gemini API.

## Proposed improvements and features

- **Migrate to `google-genai`** for better support of the latest Gemini features.
- **Add slash commands or interactive components** to give users more ways to interact with the bot.
- **Persist conversation history** using Slack threads or an external database to provide context across sessions.
- **Implement structured outputs or function calling** available in the new Gemini API to integrate external data sources.
- **Add unit tests and error handling** to improve reliability and maintainability.
