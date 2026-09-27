SYSTEM_PROMPT = """You are a IT help desk triage AI.
Respond ONLY with a JSON object. No markdown. No preamble. Schema:
{
    "category": "VPN|Password/Account|Microsoft 365|Printer|Network|Software Installation|Other",
    "severity": "Low|Medium|High|Critical",
    "summary": "one sentence, max 15 words",
    "steps": ["step1", "step2", "step3"],
    "escalate": true or false,
    "escalate_reason": "reason, or empty string",
    "kb_article": "most relevant KB article title"
}
severity: Critical=business impact, High=production blocking or security, Medium=work disrupted, Low=minor
escalate: true when hands on IT is needed, not just self-service steps"""

from http import client

from groq import Groq
import json, os, chromadb

import sqlite3, uuid
from datetime import datetime

def get_secret(key):
    try:
        import streamlit as st
        return st.secrets.get(key) or os.getenv(key)
    except: return os.gatenv(key)

client = Groq(api_key=get_secret("GROQ_API_KEY"))
_col = None

def get_collection():
    global _col
    if not _col:
        c = chromadb.PersistentClient("./chroma_db")
        _col = c.get_collection("it_kb")
    return _col

def search_kb(query, n=2):
    return get_collection().query(query_texts=[query], n_results=n)["documents"][0]

def triage_issue(issue: str) -> dict:
    kb = "\n\n---\n\n".join(search_kb(issue))
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"KB:\n{kb}\n\nIssue: {issue}"}
        ],
        temperature=0.1,
        max_tokens=1024,
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)

def _init_db():
    con = sqlite3.connect("tickets.db")
    con.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY,
        issue TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        summary TEXT NOT NULL,
        steps TEXT NOT NULL,
        escalate BOOLEAN NOT NULL,
        escalate_reason TEXT NOT NULL,
        kb_article TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")    
    con.commit()
    con.close()

_init_db()

def log_ticket_locally(issue, triage, snow=None) -> str:
    