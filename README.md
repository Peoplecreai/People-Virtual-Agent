# People Virtual Agent

This project implements a Slack bot using Flask and Bolt for Python. The bot connects to the Gemini API to generate responses when you mention it or send a direct message.

## Local testing

Install dependencies and run the service locally:

```bash
pip install -r requirements.txt
python main.py
```

Set the environment variables `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, and
`GEMINI_API_KEY` before running the application. Optionally, provide
`BOT_USER_ID` with the identifier of your Slack bot user so the application can
avoid responding to its own messages. The bot uses the `gemini-2.5-flash` model
by default, but you can override this by setting `GEMINI_MODEL`.

Expose the `/` route via a tunnel (e.g. `ngrok`) and configure the resulting URL as the Slack event request URL.

## Deployment

The application is designed to be deployed to Cloud Run. Environment variables
for `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, and `GEMINI_API_KEY` must be
provided. The service will fail to start if any of these variables are missing.

The `/healthz` route can be used for basic health checks and simply returns `OK`.
