# ai-help-desk-bot


Built by using Claude over a couple days

An AI-powered IT triage app. It classifies incidents, writes troubleshooting
steps grounded in a live Confluence knowledge base, creates ServiceNow
incidents automatically, and emails a ticket summary.

**Live demo:** https://ai-app-desk-bot.streamlit.app
**2-minute walkthrough:** https://www.loom.com/share/1edd4710deab42f98f31b62f18042807

## How it works
1. The user describes an IT issue.
2. The app retrieves the closest articles from a ChromaDB index built from a Confluence space (RAG).
3. A Groq-hosted LLM returns the category, severity, summary, and four steps, using only the retrieved KB text.
4. The KB source shown is taken from the retrieval metadata, so it links to the real Confluence page.
5. A ServiceNow incident is created through the REST API using a least-privilege service account.
6. An email notification is sent, and the ticket is logged locally.

## Stack
Python, Streamlit, Groq (qwen/qwen3.8-27b), ChromaDB, Confluence REST API,
ServiceNow Table API, SMTP email, Streamlit Community Cloud.

## Run locally
1. `pip install -r requirements.txt`
2. Create `.streamlit/secrets.toml` with `GROQ_API_KEY`, `SNOW_INSTANCE`,
   `SNOW_USER`, `SNOW_PASSWORD`, `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`,
   `CONFLUENCE_TOKEN`, `CONFLUENCE_SPACE`, plus your email settings.
3. `streamlit run app.py`

## Notes
- The knowledge base is re-pulled from Confluence on startup and via the
  "Refresh KB" button.
- Ticket history in SQLite resets when the cloud app restarts.
- Credentials live only in Streamlit Secrets and are never committed.
