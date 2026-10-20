import hashlib, os
from servicenow import get_secret
import streamlit as st
pw   = get_secret("SNOW_PASSWORD") or ""
user = get_secret("SNOW_USER") or ""
st.write("user repr:", repr(user))
st.write("pw len:", len(pw), "| sha:", hashlib.sha256(pw.encode()).hexdigest()[:8])
st.write("in st.secrets:", "SNOW_PASSWORD" in st.secrets, "| in env:", "SNOW_PASSWORD" in os.environ)