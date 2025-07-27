# People Virtual Agent

This project implements a simple Slack bot using Flask and Bolt for Python. The bot replies with `hello world` when you mention it or send a direct message.

## Local testing

Install dependencies and run the service locally:

```bash
pip install -r requirements.txt
python main.py
```

Expose the `/` route via a tunnel (e.g. `ngrok`) and configure the resulting URL as the Slack event request URL.

## Deployment

The application is designed to be deployed to Cloud Run. Environment variables for `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` must be provided. The service will fail to start if any of these variables are missing.

The `/healthz` route can be used for basic health checks and simply returns `OK`.
