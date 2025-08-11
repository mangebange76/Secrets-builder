import streamlit as st
import json, textwrap
from google.oauth2.service_account import Credentials
import gspread

st.set_page_config(page_title="Secrets Builder", layout="centered")
st.title("🔐 Secrets Builder för Streamlit + Google Sheets")

st.markdown("Klistra in **din service_account.json** eller ladda upp filen. \
Fyll i Sheet-URL och fliknamn. Klicka **Generera** → kopiera resultatet till Streamlit Cloud → Edit secrets.")

sheet_url = st.text_input("SHEET_URL", value="https://docs.google.com/spreadsheets/d/11gpHa1FKR2UBi03byv4jJcFpmBAKQMEOlz13vxkxrP8/edit")
sheet_name = st.text_input("SHEET_NAME", value="Blad1")

tab1, tab2 = st.tabs(["Klistra in JSON", "Ladda upp JSON"])
json_text = ""
with tab1:
    json_text = st.text_area("Innehåll från service_account.json", height=220, placeholder='{\n  "type": "service_account",\n  ...\n}')
with tab2:
    up = st.file_uploader("Ladda upp service_account.json", type=["json"])
    if up:
        json_text = up.read().decode("utf-8")

def build_toml(d):
    pk = (d.get("private_key") or "").replace("\\n", "\n")
    return textwrap.dedent(f'''\
    SHEET_URL = "{sheet_url}"
    SHEET_NAME = "{sheet_name}"

    [GOOGLE_CREDENTIALS]
    type = "{d.get("type","service_account")}"
    project_id = "{d.get("project_id","")}"
    private_key_id = "{d.get("private_key_id","")}"
    private_key = """{pk}"""
    client_email = "{d.get("client_email","")}"
    client_id = "{d.get("client_id","")}"
    auth_uri = "{d.get("auth_uri","https://accounts.google.com/o/oauth2/auth")}"
    token_uri = "{d.get("token_uri","https://oauth2.googleapis.com/token")}"
    auth_provider_x509_cert_url = "{d.get("auth_provider_x509_cert_url","https://www.googleapis.com/oauth2/v1/certs")}"
    client_x509_cert_url = "{d.get("client_x509_cert_url","")}"
    ''')

if st.button("🔧 Generera secrets.toml", type="primary", disabled=not json_text.strip()):
    try:
        data = json.loads(json_text)
        toml_text = build_toml(data)
        st.success("Klart! Kopiera nedan och klistra in i Streamlit Cloud → Edit secrets.")
        st.code(toml_text, language="toml")
        st.download_button("⬇️ Ladda ner secrets.toml", data=toml_text, file_name="secrets.toml", mime="text/plain")
        st.info("Glöm inte: dela arket med din service-account-mail (Editor).")
    except Exception as e:
        st.error(f"Kunde inte läsa JSON: {e}")

st.divider()
st.subheader("✅ Snabbtest (valfritt)")
st.caption("Testar att autentisera och läsa bladet med dina (genererade) värden — kör efter att du klistrat in secrets i din riktiga app, eller klistra in TOML här tillfälligt.")

test_toml = st.text_area("Klistra in genererad TOML här för test (valfritt)", height=180)
if st.button("Kör testet"):
    try:
        # snabb TOML-parser för just vårt format
        def get(key):
            import re
            m = re.search(rf'^{key}\s*=\s*"(.*)"', test_toml, re.M)
            return m.group(1) if m else ""
        SHEET_URL_T = get("SHEET_URL")
        SHEET_NAME_T = get("SHEET_NAME")
        # plocka GOOGLE_CREDENTIALS som JSON-liknande: hämta nycklarna separat
        keys = ["type","project_id","private_key_id","private_key","client_email","client_id",
                "auth_uri","token_uri","auth_provider_x509_cert_url","client_x509_cert_url"]
        creds = {}
        import re
        for k in keys:
            if k == "private_key":
                m = re.search(r'private_key\s*=\s*"""(.*?)"""', test_toml, re.S)
                creds[k] = m.group(1) if m else ""
            else:
                m = re.search(rf'^{k}\s*=\s*"(.*)"', test_toml, re.M)
                creds[k] = m.group(1) if m else ""
        scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        gc = gspread.authorize(Credentials.from_service_account_info(creds, scopes=scopes))
        ws = gc.open_by_url(SHEET_URL_T).worksheet(SHEET_NAME_T)
        st.success(f"Allt OK! Hittade bladet. Radräkning: {len(ws.get_all_values())}")
    except Exception as e:
        st.error(f"Testet misslyckades: {e}")
        st.info("Vanligtvis: felaktiga radbrytningar i private_key, eller att arket inte är delat till client_email.")
