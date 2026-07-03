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
          // No Community Cloud o app roda num iframe (/~/+/) DENTRO de uma página
          // wrapper do mesmo domínio — o iOS lê o head da página DE CIMA (top).
          let doc;
          try {{ doc = window.top.document; }} catch (e) {{ doc = window.parent.document; }}
          const head = doc.head;
          if (head.querySelector('#fg-pwa')) return;
          // remove o ícone/manifest padrão do Streamlit (senão o iOS usa o deles)
          head.querySelectorAll('link[rel="apple-touch-icon"], link[rel="manifest"]')
              .forEach((el) => el.remove());
          const tags = [
            ['link',  {{id: 'fg-pwa', rel: 'apple-touch-icon', sizes: '180x180', href: '{cdn}/icon-180.png'}}],
            ['link',  {{rel: 'manifest', href: '{cdn}/manifest.json', crossorigin: 'anonymous'}}],
            ['meta',  {{name: 'apple-mobile-web-app-capable', content: 'yes'}}],
            ['meta',  {{name: 'apple-mobile-web-app-status-bar-style', content: 'default'}}],
            ['meta',  {{name: 'apple-mobile-web-app-title', content: 'Financeiro'}}],
            ['meta',  {{name: 'theme-color', content: '#0F6E56'}}],
          ];
          for (const [tag, attrs] of tags) {{
            const el = doc.createElement(tag);
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


def _tela_login():
    """Visual da tela de login no padrão Verde Premium (mockup A)."""
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(160deg, #0C5949 0%, #0A4A3A 55%, #07382C 100%) !important; }
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        header[data-testid="stHeader"] { background: transparent; }
        .block-container { max-width: 380px !important; padding-top: 16vh !important; }
        .login-card { text-align: center; color: #F2FBF6; margin-bottom: 22px; }
        .login-logo { width: 74px; height: 74px; border-radius: 22px; background: rgba(255,255,255,0.14);
          display: grid; place-items: center; margin: 0 auto 14px;
          font-size: 36px; font-weight: 800; color: #7CE0B8;
          box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
        .login-nome { font-size: 22px; font-weight: 800; letter-spacing: -0.02em; }
        .login-sub { font-size: 13px; opacity: 0.72; margin-top: 3px; }
        div[data-testid="stTextInput"] input { border-radius: 12px !important; text-align: center;
          font-size: 16px !important; height: 48px; }
        div[data-testid="stTextInput"] > div { border-radius: 12px !important; }
        .stButton button { border-radius: 12px !important; height: 46px; font-weight: 700; }
        .login-hint { text-align: center; font-size: 11.5px; color: rgba(242,251,246,0.55); margin-top: 14px; }
        </style>
        <div class="login-card">
          <div class="login-logo">$</div>
          <div class="login-nome">Financeiro</div>
          <div class="login-sub">Família Gomes</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _gate_google():
    """Login por conta Google + allowlist de e-mails (secrets['auth']['allowed_emails'])."""
    if not st.user.is_logged_in:
        _tela_login()
        st.button("Entrar com Google", type="primary", on_click=st.login, use_container_width=True)
        st.markdown('<div class="login-hint">acesso restrito à família</div>', unsafe_allow_html=True)
        st.stop()
    allowed = [e.strip().lower() for e in st.secrets.get("auth", {}).get("allowed_emails", [])]
    email = (getattr(st.user, "email", "") or "").lower()
    if allowed and email not in allowed:
        _tela_login()
        st.error(f"A conta {email} não está autorizada para este painel.")
        st.button("Sair", on_click=st.logout, use_container_width=True)
        st.stop()
    with st.sidebar:
        st.caption(f"👤 {email}")
        st.button("Sair", on_click=st.logout)


def _gate_senha():
    """Fallback: senha única (secrets['auth']['password'] ou 'familia2026')."""
    if "auth_ok" not in st.session_state:
        _tela_login()
        senha = st.text_input(
            "Senha", type="password", placeholder="senha da família",
            label_visibility="collapsed",
        )
        if senha == st.secrets.get("auth", {}).get("password", "familia2026"):
            st.session_state["auth_ok"] = True
            st.rerun()
        elif senha:
            st.error("Senha incorreta")
        st.markdown('<div class="login-hint">digite a senha e aperte Enter</div>', unsafe_allow_html=True)
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
