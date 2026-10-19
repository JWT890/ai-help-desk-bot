SYSTEM_PROMPT = """You are an IT help desk triage AI.
Base the steps only on the KB text provided. If the KB doesn't cover the issue, say so in the summary and set escalate to true.
Respond ONLY with a JSON object. No markdown. Schema:
{
  "category": "VPN|Password/Account|Microsoft 365|Printer|Network|Software Installation|Other",
  "severity":  "Low|Medium|High",
  "summary":   "one sentence max 15 words",
  "steps":     ["step1","step2","step3","step4"],
  "escalate":  true or false,
  "escalate_reason": "reason or empty string"
}"""
from groq import Groq
import json, os, sqlite3, uuid, chromadb
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from confluence import get_chroma_client


def get_secret(key):
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val).strip()
    except:
        pass
    return os.getenv(key)

client = Groq(api_key=get_secret("GROQ_API_KEY"))
client = Groq(api_key=get_secret("GROQ_API_KEY"))
MODEL = "qwen/qwen3.8-27b"   # keep in one place, reuse in app.py

def get_collection():
    return get_chroma_client().get_or_create_collection("it_kb")

def search_kb(query, n=2):
    res = get_collection().query(query_texts=[query], n_results=n)
    return res["documents"][0], res["metadatas"][0]

def triage_issue(issue: str) -> dict:
    docs, metas = search_kb(issue)
    kb = "\n\n---\n\n".join(docs)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"KB:\n{kb}\n\nIssue: {issue}"}
        ],
        temperature=0.1, max_tokens=500,
        response_format={"type": "json_object"}
    )
    result = json.loads(resp.choices[0].message.content)
    top = metas[0] if metas else {}
    result["kb_article"] = top.get("title", "")   # from Confluence, not the model
    result["kb_url"] = top.get("url", "")
    return result

from datetime import timezone

def log_ticket_locally(issue, triage, snow=None) -> str:
    tid = "INC-" + str(uuid.uuid4())[:8].upper()
    con = sqlite3.connect("tickets.db")
    con.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id TEXT, created_at TEXT, issue TEXT,
        category TEXT, severity TEXT, summary TEXT,
        steps TEXT, escalate INTEGER, escalate_reason TEXT,
        kb_article TEXT, snow_number TEXT, snow_url TEXT)""")
    con.execute("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
        tid, datetime.now(timezone.utc).isoformat(), issue,
        triage.get("category"), triage.get("severity"),
        triage.get("summary"), json.dumps(triage.get("steps", [])),
        int(triage.get("escalate", False)), triage.get("escalate_reason", ""),
        triage.get("kb_article", ""),
        snow["number"] if snow else "", snow["url"] if snow else ""
    ))
    con.commit()
    con.close()
    return tid


def get_recent_tickets(limit=15):
    try:
        con = sqlite3.connect("tickets.db")
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        con.close()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []