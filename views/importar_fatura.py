"""Página: Importar Fatura.

Fluxo:
1. Upload PDF de fatura paga (qualquer cartão)
2. IA (Claude Sonnet 4.5 ou GPT-4o) extrai todas as transações
3. Sistema marca duplicatas (transações já lançadas via WhatsApp)
4. Wesley revisa em tabela editável (ajustar categoria, marcar quais incluir)
5. Insere em batch — Competência = mês do pagamento (caixa, decisão Wesley 05/06)
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from lib.data import load_lancamentos
from lib.ocr_fatura import dedupe_against_existing, extract_transactions
from lib.sheets_writer import append_lancamentos


# set_page_config + auth ficam no router (streamlit_app.py)

# ----- Header -----
st.title("Importar Fatura")
st.markdown(
    """
**Como funciona:**
1. Faça upload do PDF da fatura paga (qualquer cartão)
2. IA extrai todas as transações
3. Sistema marca duplicatas (compras já lançadas via WhatsApp)
4. Você revisa, ajusta categorias e marca quais inserir
5. Lança em batch — Competência = mês do pagamento da fatura (caixa)
"""
)

# ----- Check API key configurada -----
has_anthropic = bool(st.secrets.get("ANTHROPIC_API_KEY"))
has_openai = bool(st.secrets.get("OPENAI_API_KEY"))

if not has_anthropic and not has_openai:
    st.error(
        "⚠️ **Nenhuma API key de IA configurada.**\n\n"
        "Edite `.streamlit/secrets.toml` e adicione UMA das duas:\n\n"
        "```toml\n"
        'ANTHROPIC_API_KEY = "sk-ant-..."\n'
        "# OU\n"
        'OPENAI_API_KEY = "sk-..."\n'
        "```\n\n"
        "**Custo estimado:** R$ 3-5/mês com 6 faturas/mês."
    )
    st.stop()

provider_label = "Claude Sonnet 4.5" if has_anthropic else "GPT-4o"
st.caption(f"IA configurada: **{provider_label}**")

# ----- Upload -----
file = st.file_uploader("Arraste sua fatura PDF aqui", type=["pdf"])

if file is None:
    st.info("⬆️ Envie um PDF de fatura paga (XP, Itaú, Visa, Master, Azul, etc)")
    st.stop()

pdf_bytes = file.read()
st.success(f"**{file.name}** — {len(pdf_bytes) / 1024:.1f} KB")

# Limpar resultado anterior se subir arquivo novo
if st.session_state.get("ocr_filename") != file.name:
    for k in ("ocr_result", "ocr_filename"):
        st.session_state.pop(k, None)

# ----- Extrair via IA -----
if "ocr_result" not in st.session_state:
    if st.button("Extrair transações com IA", type="primary"):
        with st.spinner(f"{provider_label} analisando fatura... (~30s)"):
            try:
                result = extract_transactions(pdf_bytes)
                st.session_state["ocr_result"] = result
                st.session_state["ocr_filename"] = file.name
                st.rerun()
            except Exception as e:
                st.error(f"❌ Falhou: {e}")
                st.stop()
    st.stop()

# ----- Resultado -----
result = st.session_state["ocr_result"]
fatura_info = result.get("fatura", {})
transacoes = result.get("transacoes", [])

st.divider()
st.subheader("Fatura extraída")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Banco", fatura_info.get("banco", "?"))
col2.metric("Titular", fatura_info.get("cartao_titular", "?"))
col3.metric("Vencimento", fatura_info.get("ciclo_vencimento", "?"))
total = fatura_info.get("total", 0)
col4.metric(
    "Total",
    "R$ " + f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
)

# ----- Dedupe -----
with st.spinner("Comparando com lançamentos já existentes..."):
    df_lancs = load_lancamentos(incluir_cancelados=False)
    cartao_str = fatura_info.get("cartao_titular", "")
    # heurística: tentar match por sobrenome do titular ou banco
    cartao_keys = [k for k in ["XP", "Itaú", "Visa", "Master", "Azul"] if k.lower() in cartao_str.lower() or k.lower() in fatura_info.get("banco", "").lower()]
    cartao_match = cartao_keys[0] if cartao_keys else None
    transacoes = dedupe_against_existing(transacoes, df_lancs, cartao_match=cartao_match)

# ----- Filtrar pagamentos anteriores (não entram na revisão) -----
transacoes_visiveis = [t for t in transacoes if not t.get("is_pagamento_anterior")]
n_filtrado = len(transacoes) - len(transacoes_visiveis)
if n_filtrado > 0:
    st.caption(
        f"ℹ️ {n_filtrado} linha(s) de 'pagamento de fatura anterior' filtrada(s) automaticamente"
    )

n_dup = sum(1 for t in transacoes_visiveis if t.get("duplicata_provavel"))
n_novo = len(transacoes_visiveis) - n_dup
st.subheader(
    f"{len(transacoes_visiveis)} transações — {n_novo} novas · {n_dup} prováveis duplicatas"
)

# ----- Tabela editável -----
def _flag(t: dict) -> str:
    if t.get("duplicata_provavel"):
        return f"🔄 Duplicata (#{t.get('duplicata_row', '?')})"
    if t.get("is_iof"):
        return "💰 IOF"
    if t.get("is_estorno"):
        return "↩️ Estorno"
    parcela = t.get("parcela_atual")
    if parcela:
        return f"📅 Parcela {parcela}/{t.get('parcela_total', '?')}"
    if t.get("moeda_origem") and t["moeda_origem"] != "BRL":
        return f"🌍 {t['moeda_origem']}"
    return "✨ Nova"


# Colunas de decisão primeiro (Inserir/Flag/Descrição/Valor cabem na tela do celular).
# Parcela sai da tabela (já aparece na Flag) — na inserção vem de transacoes_visiveis.
df_review = pd.DataFrame(
    [
        {
            "Inserir": not t.get("duplicata_provavel", False),
            "Flag": _flag(t),
            "Descrição": t.get("descricao", ""),
            "Valor": float(t.get("valor", 0) or 0),
            "Categoria": t.get("categoria_sugerida", "Outros"),
            "Data": t.get("data", ""),
        }
        for t in transacoes_visiveis
    ]
)

CATEGORIAS = [
    "Moradia",
    "Outros Imóveis",
    "Investimentos em Imóvel",
    "Auxílio Familiar",
    "Alimentação",
    "Transporte",
    "Saúde",
    "Educação",
    "Lazer & Restaurantes",
    "Vestuário",
    "Pessoal & Beleza",
    "Assinaturas & Streaming",
    "Financeiro & Cartão",
    "Outros",
]

edited_df = st.data_editor(
    df_review,
    column_config={
        "Inserir": st.column_config.CheckboxColumn(default=True, width="small"),
        "Flag": st.column_config.TextColumn(disabled=True, width="medium"),
        "Valor": st.column_config.NumberColumn(format="R$ %.2f", width="small"),
        "Categoria": st.column_config.SelectboxColumn(options=CATEGORIAS, width="medium"),
        "Data": st.column_config.TextColumn(width="small"),
    },
    hide_index=True,
    use_container_width=True,
    height=min(600, 40 + len(df_review) * 36),
    key="editor_transacoes",
)

# ----- Config de inserção -----
st.divider()
st.subheader("Configuração da inserção")

col1, col2, col3 = st.columns(3)
with col1:
    # regra do projeto: lançamento é SEMPRE individual (nunca "Casal")
    pessoa = st.selectbox("Pessoa", ["Wesley", "Sabrina"], index=0)
with col2:
    cartao_label = st.text_input(
        "Nome do cartão (planilha)",
        value=cartao_str,
        help="Como vai aparecer na coluna 'Cartão' da planilha (ex: 'XP Wesley')",
    )
with col3:
    data_pgto = st.date_input("Data do pagamento da fatura", value=datetime.now())

data_pgto_str = data_pgto.strftime("%d/%m/%Y")
competencia = data_pgto.strftime("%m/%Y")

# ----- Resumo -----
n_inserir = int(edited_df["Inserir"].sum())
total_inserir = float(edited_df.loc[edited_df["Inserir"], "Valor"].sum())
st.info(
    f"**Vai inserir {n_inserir} transações** totalizando "
    f"R$ {total_inserir:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    + f" — competência **{competencia}** (mês do pagamento)"
)

# ----- Insert -----
if st.button(
    f"Inserir {n_inserir} transações na planilha",
    type="primary",
    disabled=(n_inserir == 0),
):
    rows_to_insert = []
    msg_orig = f"[fatura ANEXO {cartao_label} pago em {data_pgto_str}]"

    # data_editor preserva a ordem das linhas → i alinha com transacoes_visiveis
    for i, r in edited_df.reset_index(drop=True).iterrows():
        if not r["Inserir"]:
            continue
        t = transacoes_visiveis[i]
        parcela = (
            f"{t['parcela_atual']}/{t['parcela_total']}" if t.get("parcela_atual") else ""
        )
        rows_to_insert.append(
            [
                r["Data"],          # Data
                competencia,        # Competência (mês do pagamento)
                "Despesa",          # Tipo
                r["Categoria"],     # Categoria
                "",                 # Subcategoria
                r["Descrição"],     # Descrição
                pessoa,             # Pessoa
                "Crédito",          # Forma Pgto
                float(r["Valor"]),  # Valor
                msg_orig,           # Mensagem Original
                data_pgto_str,      # Data Caixa = data do pagamento
                cartao_label,       # Cartão
                parcela,            # Parcela
                "Ativo",            # Status
            ]
        )

    try:
        with st.spinner(f"Inserindo {len(rows_to_insert)} linhas..."):
            n = append_lancamentos(rows_to_insert)
        st.success(f"✅ {n} transações inseridas com sucesso!")
        st.balloons()
        st.cache_data.clear()
        # Limpar sessão pra liberar próxima fatura
        for k in ("ocr_result", "ocr_filename"):
            st.session_state.pop(k, None)
    except Exception as e:
        st.error(f"❌ Erro ao inserir: {e}")
