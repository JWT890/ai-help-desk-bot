import streamlit as st
import json
from pathlib import Path
from triage import triage_issue, log_ticket_locally, get_recent_tickets
from servicenow import create_snow_incident, snow_status
from confluence import ingest_confluence_to_chromadb, confluence_status, create_kb_article

st.set_page_config(page_title="AI IT Help Desk",
                   page_icon="🤖", layout="wide")

# Pull KB from Confluence on cold start
if not Path("chroma_db").exists():
    with st.spinner("Pulling knowledge base from Confluence…"):
        ingest_confluence_to_chromadb()

with st.sidebar:
    st.title("🤖 AI IT Help Desk")
    st.caption("Groq · Llama 3.1 · Confluence · ServiceNow")
    st.divider()

    snow = snow_status()
    if snow["connected"]:
        st.success("ServiceNow connected")
        st.caption(snow.get("instance",""))
    else:
        st.warning("ServiceNow not configured")

    conf = confluence_status()
    if conf["connected"]:
        st.success("Confluence connected")
        st.caption(f"Space: {conf['space']}")
        if st.button("Refresh KB from Confluence"):
            with st.spinner("Refreshing…"):
                n = ingest_confluence_to_chromadb()
            st.success(f"Refreshed {n} articles")
            st.rerun()
    else:
        st.warning("Confluence not configured")

    st.divider()
    st.caption("Model: llama-3.1-8b-instant")

if "result" in st.session_state:
    r = st.session_state["result"]
    snow = r.get("snow_ticket")
    st.divider()
    col1, col2 = st.columns([3,1])
    with col1:
        st.subheader(f"Ticket {r['ticket_id']}")
        if snow:
            st.markdown(
                f"[🟢 {snow['number']} — open in ServiceNow]({snow['url']})")
    with col2:
        icons = {"High":"🔴","Medium":"🟡","Low":"🟢"}
        st.metric("Severity",
                  f"{icons.get(r['severity'],'')} {r['severity']}")

    st.info(f"**{r['category']}** — {r['summary']}")

    st.subheader("Troubleshooting steps")
    for i, step in enumerate(r["steps"], 1):
        st.markdown(f"{i}. {step}")

    # Link to source Confluence article
    st.caption(f"KB source: {r['kb_article']}")
    if r.get("escalate"):
        st.error(f"⚠️ **Escalation needed** — {r['escalate_reason']}")

st.title("Submit an IT issue")
st.caption("Quick examples:")
cols = st.columns(6)
examples = {
    "VPN":     "My laptop cannot connect to VPN from home.",
    "Password":"I forgot my password and am locked out.",
    "Outlook": "Outlook keeps crashing when I open emails.",
    "Network": "My internet is very slow and sites unreachable.",
    "Printer": "The office printer is offline and not printing.",
    "Software":"I need Adobe Acrobat but get a permissions error.",
}
for i, (label, text) in enumerate(examples.items()):
    if cols[i].button(label, use_container_width=True):
        st.session_state["prefill"] = text

issue = st.text_area(
    "Describe your issue",
    value=st.session_state.get("prefill", ""),
    height=100,
    placeholder="e.g. I can't connect to VPN from home"
)

if st.button("Submit issue", type="primary") and issue.strip():
    with st.spinner("Triaging with Groq…"):
        result   = triage_issue(issue)
        snow_t   = create_snow_incident(issue, result)
        ticket   = log_ticket_locally(issue, result, snow_t)
        result["ticket_id"]   = ticket
        result["snow_ticket"] = snow_t
    st.session_state["result"] = result
    st.session_state.pop("prefill", None)
    st.rerun()

# ── Triage result ──────────────────────────────────────────
if "result" in st.session_state:
    r    = st.session_state["result"]
    snow = r.get("snow_ticket")
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"Ticket {r['ticket_id']}")
        if snow:
            st.markdown(
                f"[🟢 {snow['number']} — open in ServiceNow]({snow['url']})")
        else:
            st.caption("Logged locally · add SNOW credentials to enable ServiceNow")
    with col2:
        icons = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
        st.metric("Severity",
                  f"{icons.get(r['severity'], '')} {r['severity']}")
    st.info(f"**{r['category']}** — {r['summary']}")
    st.subheader("Troubleshooting steps")
    for i, step in enumerate(r["steps"], 1):
        st.markdown(f"{i}. {step}")
    st.caption(f"KB: {r['kb_article']}")
    if r.get("escalate"):
        st.error(f"⚠️ **Escalation needed** — {r['escalate_reason']}")

# ── Recent tickets ─────────────────────────────────────────
st.divider()
st.subheader("Recent tickets")
import pandas as pd
tickets = get_recent_tickets(15)
if tickets:
    df = pd.DataFrame(tickets)[[
        "id", "created_at", "category", "severity", "escalate", "snow_number"
    ]]
    df.columns = ["Ticket", "Created", "Category", "Severity", "Escalated", "SNOW #"]
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.caption("No tickets yet.")

st.divider()
st.subheader("Recent tickets")
tickets = get_recent_tickets(15)
if tickets:
    rows = [{
        "Ticket": ticket.get("id"),
        "Created": ticket.get("created_at"),
        "Category": ticket.get("category"),
        "Severity": ticket.get("severity"),
        "Escalated": ticket.get("escalate"),
        "SNOW #": ticket.get("snow_number"),
    } for ticket in tickets]
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.caption("No tickets yet.")

