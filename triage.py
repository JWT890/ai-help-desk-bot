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
    c = chromadb.PersistentClient("./chroma_db")
    return c.get_collection("it_kb")

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