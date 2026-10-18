SYSTEM_PROMPT = """You are an IT help desk triage AI.
Respond ONLY with a JSON object. No markdown. Schema:
{
  "category": "VPN|Password/Account|Microsoft 365|
               Printer|Network|Software Installation|Other",
  "severity":  "Low|Medium|High",
  "summary":   "one sentence max 15 words",
  "steps":     ["step1","step2","step3","step4"],
  "escalate":  true or false,
  "escalate_reason": "reason or empty string",
  "kb_article": "most relevant KB page title"
}"""
from groq import Groq
import json, os, sqlite3, uuid, chromadb
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


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
_col = None

def get_collection():
    global _col
    if not _col:
        c = chromadb.PersistentClient("./chroma_db")
        _col = c.get_collection("it_kb")
    return _col

def search_kb(query, n=2):
    return get_collection().query(
        query_texts=[query], n_results=n
    )["documents"][0]

def triage_issue(issue: str) -> dict:
    kb = "\n\n---\n\n".join(search_kb(issue))
    resp = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"KB:\n{kb}\n\nIssue: {issue}"}
        ],
        temperature=0.1, max_tokens=1024,
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)

def log_ticket_locally(issue, triage, snow=None) -> str:
    tid = "INC-" + str(uuid.uuid4())[:8].upper()
    con = sqlite3.connect("tickets.db")
    con.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id TEXT, created_at TEXT, issue TEXT,
        category TEXT, severity TEXT, summary TEXT,
        steps TEXT, escalate INTEGER, escalate_reason TEXT,
        kb_article TEXT, snow_number TEXT, snow_url TEXT)""")
    con.execute("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
        tid, datetime.utcnow().isoformat(), issue,
        triage.get("category"), triage.get("severity"),
        triage.get("summary"), json.dumps(triage.get("steps",[])),
        int(triage.get("escalate",False)), triage.get("escalate_reason",""),
        triage.get("kb_article",""),
        snow["number"] if snow else "", snow["url"] if snow else ""
    ))
    con.commit(); con.close()
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
        return []   # table doesn't exist yet — return empty list


# Confirm: clean JSON, steps from your Confluence content