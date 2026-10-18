import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_secret(key):
    try:
        import streamlit as st
        return st.secrets.get(key) or os.getenv(key)
    except:
        return os.getenv(key)

def send_ticket_email(ticket_id: str, triage: dict, 
                      issue: str, snow: dict | None = None):
    """
    Sends a ticket notification email.
    Escalated tickets get a high-priority subject line.
    """
    sender   = get_secret("EMAIL_ADDRESS")
    password = get_secret("EMAIL_PASSWORD")
    receiver = get_secret("EMAIL_NOTIFY")

    if not all([sender, password, receiver]):
        print("[Email] Not configured — skipping")
        return False

    escalated = triage.get("escalate", False)
    severity  = triage.get("severity", "Medium")
    category  = triage.get("category", "Other")
    steps     = triage.get("steps", [])

    # Subject line — escalated tickets get ⚠ prefix
    subject = (
        f"⚠ ESCALATED — {ticket_id} [{category}] {severity}"
        if escalated else
        f"New IT Ticket — {ticket_id} [{category}] {severity}"
    )

    # Build HTML email body
    steps_html = "".join(f"<li>{s}</li>" for s in steps)
    snow_line  = (
        f'<p><a href="{snow["url"]}">🟢 Open {snow["number"]} in ServiceNow</a></p>'
        if snow else
        "<p>ServiceNow not configured — ticket logged locally</p>"
    )
    escalate_html = (
        f'<div style="background:#fef2f2;border:1px solid #fecaca;'
        f'padding:10px;border-radius:6px;color:#dc2626;margin:10px 0">'
        f'<strong>⚠ Escalation recommended</strong><br>'
        f'{triage.get("escalate_reason","")}</div>'
        if escalated else ""
    )

    body = f"""
    <html><body style="font-family:sans-serif;max-width:600px">
      <h2 style="color:#1a202c">IT Help Desk — New Ticket</h2>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;color:#718096">Ticket</td>
            <td style="padding:6px;font-family:monospace">{ticket_id}</td></tr>
        <tr><td style="padding:6px;color:#718096">Category</td>
            <td style="padding:6px">{category}</td></tr>
        <tr><td style="padding:6px;color:#718096">Severity</td>
            <td style="padding:6px">{severity}</td></tr>
        <tr><td style="padding:6px;color:#718096">Issue</td>
            <td style="padding:6px">{issue}</td></tr>
      </table>
      <h3>Summary</h3>
      <p>{triage.get("summary","")}</p>
      <h3>AI Troubleshooting Steps</h3>
      <ol>{steps_html}</ol>
      <p style="color:#718096;font-size:12px">
        KB source: {triage.get("kb_article","")}
      </p>
      {escalate_html}
      {snow_line}
      <hr>
      <p style="color:#718096;font-size:11px">
        Sent by AI IT Help Desk · ai-app-desk-bot.streamlit.app
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = receiver
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print(f"[Email] Sent: {subject}")
        return True
    except Exception as e:
        print(f"[Email] Failed: {e}")
        return False