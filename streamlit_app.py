"""Financeiro Família Gomes — router multi-page + auth híbrida.

Acesso: Login Google (st.login OIDC) quando o Streamlit suporta st.login (≥1.42)
E há credencial OAuth nos secrets (`[auth].client_id`); caso contrário, cai no
fallback de senha única. As views em views/ não chamam set_page_config nem auth.

Para ativar o Login Google:
1. requirements.txt: streamlit>=1.42 (testado em 1.47+)
2. Criar credencial OAuth no Google Cloud (redirect: https://<app>.streamlit.app/oauth2callback)
3. Secrets do Streamlit Cloud, seção [auth]:
     redirect_uri, cookie_secret, client_id, client_secret,
     server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
     allowed_emails = ["wesley@...", "sabrina@..."]
"""
import streamlit as st

st.set_page_config(
    page_title="Financeiro Família Gomes",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _oidc_disponivel() -> bool:
    """True só se o Streamlit suporta st.login E há credencial OAuth configurada."""
    try:
        return hasattr(st, "login") and bool(st.secrets.get("auth", {}).get("client_id"))
    except Exception:
        return False


def _gate_google():
    """Login por conta Google + allowlist de e-mails (secrets['auth']['allowed_emails'])."""
    if not st.user.is_logged_in:
        st.title("💰 Financeiro Família Gomes")
        st.caption("Entre com a sua conta Google autorizada.")
        st.button("Entrar com Google", type="primary", on_click=st.login)
        st.stop()
    allowed = [e.strip().lower() for e in st.secrets.get("auth", {}).get("allowed_emails", [])]
    email = (getattr(st.user, "email", "") or "").lower()
    if allowed and email not in allowed:
        st.title("💰 Financeiro Família Gomes")
        st.error(f"A conta {email} não está autorizada para este painel.")
        st.button("Sair", on_click=st.logout)
        st.stop()
    with st.sidebar:
        st.caption(f"👤 {email}")
        st.button("Sair", on_click=st.logout)


def _gate_senha():
    """Fallback: senha única (secrets['auth']['password'] ou 'familia2026')."""
    if "auth_ok" not in st.session_state:
        st.title("💰 Financeiro Família Gomes")
        senha = st.text_input("🔐 Senha", type="password")
        if senha == st.secrets.get("auth", {}).get("password", "familia2026"):
            st.session_state["auth_ok"] = True
            st.rerun()
        elif senha:
            st.error("Senha incorreta")
        st.stop()


if _oidc_disponivel():
    _gate_google()
else:
    _gate_senha()

# ============== Navegação nomeada ==============
pages = [
    st.Page("views/visao_geral.py", title="Visão Geral", icon="💰", default=True),
    st.Page("views/visao_anual.py", title="Visão Anual", icon="📅"),
    st.Page("views/importar_fatura.py", title="Importar Fatura", icon="📥"),
    st.Page("views/dashboard_detalhado.py", title="Dashboard Detalhado", icon="📊"),
    st.Page("views/custos.py", title="Custo da Ferramenta", icon="🛠️"),
]
st.navigation(pages).run()
