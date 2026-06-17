"""Financeiro Família Gomes — router multi-page (st.navigation) com labels nomeados.

Auth única aqui; as views em views/ não chamam set_page_config nem auth.
"""
import streamlit as st

st.set_page_config(
    page_title="Financeiro Família Gomes",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============== Auth única (antes da navegação) ==============
if "auth_ok" not in st.session_state:
    st.title("💰 Financeiro Família Gomes")
    senha = st.text_input("🔐 Senha", type="password")
    if senha == st.secrets.get("auth", {}).get("password", "familia2026"):
        st.session_state["auth_ok"] = True
        st.rerun()
    elif senha:
        st.error("Senha incorreta")
    st.stop()

# ============== Navegação nomeada ==============
pages = [
    st.Page("views/visao_geral.py", title="Visão Geral", icon="💰", default=True),
    st.Page("views/visao_anual.py", title="Visão Anual", icon="📅"),
    st.Page("views/importar_fatura.py", title="Importar Fatura", icon="📥"),
    st.Page("views/dashboard_detalhado.py", title="Dashboard Detalhado", icon="📊"),
]
st.navigation(pages).run()
