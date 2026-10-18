import requests, os

def get_secret(key):
    try:
        import streamlit as st
        return st.secrets.get(key) or os.getenv(key)
    except: return os.getenv(key)

SNOW_INSTANCE = get_secret("SNOW_INSTANCE") or ""
SNOW_AUTH = (get_secret("SNOW_USER"), get_secret("SNOW_PASSWORD"))
HEADS = {"Content-Type":"application/json","Accept":"application/json"}
SEV_MAP = {"High":"1","Medium":"2","Low":"3"}
GROUP_MAP = {
    "VPN":                  "Network Support",
    "Password/Account":     "Identity & Access Management",
    "Microsoft 365":        "Desktop Support",
    "Printer":              "Desktop Support",
    "Network":              "Network Support",
    "Software Installation":"Desktop Support",
    "Other":                "IT Help Desk",
}

def create_snow_incident(issue, triage) -> dict | None:
    if not all([SNOW_INSTANCE, SNOW_AUTH[0], SNOW_AUTH[1]]):
        return None
    sev   = triage.get("severity","Medium")
    steps = "\n".join(f"{i+1}. {s}"
                      for i,s in enumerate(triage.get("steps",[])))
    try:
        r = requests.post(
            f"https://{SNOW_INSTANCE}/api/now/table/incident",
            json={
                "short_description": triage.get("summary",""),
                "description": f"Issue:\n{issue}\n\nAI steps:\n{steps}",
                "urgency":          SEV_MAP.get(sev,"2"),
                "impact":           SEV_MAP.get(sev,"2"),
                "priority":         "1" if triage.get("escalate") else SEV_MAP.get(sev,"2"),
                "assignment_group": GROUP_MAP.get(triage.get("category","Other"),"IT Help Desk"),
            },
            auth=SNOW_AUTH, headers=HEADS, timeout=10
        )
        res = r.json()["result"]
        return {"number": res["number"], "sys_id": res["sys_id"],
                "url": f"https://{SNOW_INSTANCE}/incident.do?sys_id={res['sys_id']}"}
    except Exception as e:
        print(f"[SNOW] {e}"); return None

def snow_status():
    if not SNOW_INSTANCE: return {"connected":False,"reason":"not configured"}
    try:
        r = requests.get(
            f"https://{SNOW_INSTANCE}/api/now/table/incident?sysparm_limit=1",
            auth=SNOW_AUTH, headers=HEADS, timeout=5)
        return {"connected": r.status_code==200, "instance": SNOW_INSTANCE}
    except Exception as e:
        return {"connected":False,"reason":str(e)}

from servicenow import create_snow_incident
r = create_snow_incident("Test — safe to delete", {
    "category":"VPN","severity":"Low",
    "summary":"Test ticket from AI triage system",
    "steps":["1","2","3","4"],
    "escalate":False,"escalate_reason":"","kb_article":"VPN"
})
print(r)
# {"number": "INC0010042", "sys_id": "...", "url": "..."}