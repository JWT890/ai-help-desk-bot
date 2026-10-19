import requests, os

def get_secret(key):
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val).strip()
    except:
        pass
    return os.getenv(key)

HEADS = {"Content-Type":"application/json","Accept":"application/json"}
SEV_MAP = {"High":"1","Medium":"2","Low":"3"}
CATEGORY_MAP = {
    "VPN": "network",
    "Network": "network",
    "Software Installation": "software",
    "Printer": "hardware",
    "Password/Account": "inquiry",
    "Microsoft 365": "software",
}
GROUP_MAP = {
    "VPN": "IT Help Desk",
    "Network": "IT Help Desk",
    "Software Installation": "IT Help Desk",
    "Printer": "IT Help Desk",
    "Password/Account": "IT Help Desk",
    "Microsoft 365": "IT Help Desk",
}

def create_snow_incident(issue, triage) -> dict | None:
    snow_instance = get_secret("SNOW_INSTANCE") or ""
    snow_user     = get_secret("SNOW_USER")
    snow_auth     = (snow_user, get_secret("SNOW_PASSWORD"))

    if not all([snow_instance, snow_auth[0], snow_auth[1]]):
        return None
    sev   = triage.get("severity", "Medium")
    steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(triage.get("steps", [])))
    try:
        r = requests.post(
            f"https://{snow_instance}/api/now/table/incident",
            json={
                "caller_id":         snow_user,
                "category":          CATEGORY_MAP.get(triage.get("category", "Other"), "inquiry"),
                "short_description": triage.get("summary", ""),
                "description":       f"Issue:\n{issue}\n\nAI steps:\n{steps}",
                "urgency":           SEV_MAP.get(sev, "2"),
                "impact":            SEV_MAP.get(sev, "2"),
                "priority":          "1" if triage.get("escalate") else SEV_MAP.get(sev, "2"),
                "assignment_group":  GROUP_MAP.get(triage.get("category", "Other"), "IT Help Desk"),
            },
            auth=snow_auth, headers=HEADS, timeout=10
        )
        r.raise_for_status()
        res = r.json()["result"]
        return {"number": res["number"], "sys_id": res["sys_id"],
                "url": f"https://{snow_instance}/incident.do?sys_id={res['sys_id']}"}
    except Exception as e:
        print(f"[SNOW] {e}")
        return None
def snow_status():
    instance = get_secret("SNOW_INSTANCE")
    user     = get_secret("SNOW_USER")
    password = get_secret("SNOW_PASSWORD")
    if not all([instance, user, password]):
        return {"connected": False, "reason": "not configured"}
    try:
        r = requests.get(
            f"https://{instance}/api/now/table/incident?sysparm_limit=1",
            auth=(user, password),
            headers={"Accept": "application/json"},
            timeout=5
        )
        return {"connected": r.status_code == 200, 
                "instance": instance,
                "status_code": r.status_code,      # ← add this
                "response": r.text[:100]}           # ← and this
    except Exception as e:
        return {"connected": False, "reason": str(e)}