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
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Financeiro Família Gomes",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _tags_app_tela_inicial():
    """Injeta no <head> as tags de 'app na tela inicial' (iOS/Android).

    O Streamlit não serve /apple-touch-icon.png na raiz, então o iOS cai no
    fallback feio (screenshot da página). O Safari, porém, lê o DOM vivo na
    hora do 'Adicionar à Tela de Início' — injetar a <link> via JS resolve.
    Ícones via jsDelivr (CDN do repo GitHub): o Community Cloud não ativou o
    enableStaticServing sem reboot manual, e o CDN serve image/png correto.
    """
    cdn = "https://cdn.jsdelivr.net/gh/wesleygomes-star/financeiro-familiar-dashboard@main/static"
    components.html(
        f"""<script>
        (function () {{
          const head = window.parent.document.head;
          if (head.querySelector('#fg-pwa')) return;
          const tags = [
            ['link',  {{id: 'fg-pwa', rel: 'apple-touch-icon', sizes: '180x180', href: '{cdn}/icon-180.png'}}],
            ['link',  {{rel: 'manifest', href: '{cdn}/manifest.json', crossorigin: 'anonymous'}}],
            ['meta',  {{name: 'apple-mobile-web-app-capable', content: 'yes'}}],
            ['meta',  {{name: 'apple-mobile-web-app-status-bar-style', content: 'default'}}],
            ['meta',  {{name: 'apple-mobile-web-app-title', content: 'Financeiro'}}],
            ['meta',  {{name: 'theme-color', content: '#0F6E56'}}],
          ];
          for (const [tag, attrs] of tags) {{
            const el = window.parent.document.createElement(tag);
            for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
            head.appendChild(el);
          }}
        }})();
        </script>""",
        height=0,
    )


_tags_app_tela_inicial()


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
