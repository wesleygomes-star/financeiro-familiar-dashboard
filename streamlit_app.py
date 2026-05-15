"""Dashboard Financeiro Familiar — Página Família (consolidado).

Estrutura:
- Filtro de competência (mês) no topo
- 4 KPIs (Receita, Despesa, Saldo, Disponível pra investir)
- Barras categorias vs teto (semáforo)
- Donut despesas por categoria
- Linha saldo 6 meses
- Top 10 maiores despesas
"""
import streamlit as st
from datetime import datetime
from lib.data import load_lancamentos, load_recorrentes, load_tetos, meses_disponiveis, filtrar
from lib.components import kpi_card, donut_categorias, barras_categoria_vs_teto, projecao_6_meses, tabela_top_despesas, detalhar_categoria, comparativo_mensal, fmt_brl


st.set_page_config(
    page_title="Financeiro Familiar",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auth simples por senha (proteção mínima — só Wesley e Sabrina)
def check_password():
    if st.session_state.get("auth_ok"):
        return True
    senha_correta = st.secrets.get("auth", {}).get("password", "familia2026")
    senha = st.sidebar.text_input("🔐 Senha", type="password", key="senha_input")
    if senha == senha_correta:
        st.session_state["auth_ok"] = True
        st.rerun()
    elif senha:
        st.sidebar.error("Senha incorreta")
    return False


if not check_password():
    st.title("💰 Financeiro Familiar")
    st.info("👈 Digite a senha na barra lateral pra entrar.")
    st.stop()


# ============== DADOS ==============
with st.spinner("Carregando dados..."):
    df_lanc = load_lancamentos()
    df_rec = load_recorrentes()
    df_tetos = load_tetos()

if df_lanc.empty:
    st.error("Sem dados na planilha. Verifique conexão.")
    st.stop()


# ============== HEADER ==============
st.title("💰 Financeiro Família Gomes")

# Linha 1: Modo de visualização (Competência vs Caixa)
col_modo, col_explicacao = st.columns([1, 3])
with col_modo:
    modo = st.radio(
        "🎯 Modo de visão",
        ["Competência", "Caixa"],
        horizontal=True,
        help="Competência = a qual mês a despesa pertence (ideal pra controle de teto). Caixa = quando o dinheiro efetivamente sai (ideal pra fluxo de caixa).",
    )
with col_explicacao:
    st.write("")
    if modo == "Competência":
        st.caption("📅 **Competência:** mostra os gastos pelo mês a que pertencem. *Ex: compra de cartão em maio fica em maio, mesmo que o pagamento da fatura seja em junho.* Ideal pra **controle de tetos**.")
    else:
        st.caption("💵 **Caixa:** mostra quando o dinheiro efetivamente sai da conta. *Ex: compra de cartão em maio aparece em junho (quando paga a fatura).* Ideal pra **fluxo de caixa**.")

# Linha 2: Filtros
col_filtro, col_pessoa, col_refresh = st.columns([2, 2, 1])

with col_filtro:
    meses = meses_disponiveis(df_lanc, modo=modo)
    mes_default = f"{datetime.now().month:02d}/{datetime.now().year}"
    idx_default = meses.index(mes_default) if mes_default in meses else 0
    competencia = st.selectbox(
        f"📅 {modo} (mês)",
        meses,
        index=idx_default,
        key=f"mes_{modo}",
    )

with col_pessoa:
    pessoa = st.selectbox("👥 Visão", ["Família (todos)", "Wesley", "Sabrina"])

with col_refresh:
    st.write("")
    st.write("")
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()


# Filtros avançados (collapsable)
with st.expander("🔍 Filtros avançados", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        cats_disponiveis = ["Todas"] + sorted(df_lanc["Categoria"].dropna().unique().tolist())
        cat_avancada = st.selectbox("Categoria", cats_disponiveis, key="filtro_cat")
    with fc2:
        formas = ["Todas"] + sorted(df_lanc["Forma Pgto"].dropna().unique().tolist())
        forma_avancada = st.selectbox("Forma Pgto", formas, key="filtro_forma")
    with fc3:
        cartoes = ["Todos"] + sorted([c for c in df_lanc["Cartão"].dropna().unique().tolist() if c])
        cartao_avancado = st.selectbox("Cartão", cartoes, key="filtro_cartao")

# Aplicar filtros
pessoa_filter = None if pessoa == "Família (todos)" else pessoa
df_filtrado = filtrar(df_lanc, competencia=competencia, pessoa=pessoa_filter, modo=modo)
# Aplica filtros avançados
if cat_avancada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Categoria"] == cat_avancada]
if forma_avancada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Forma Pgto"] == forma_avancada]
if cartao_avancado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Cartão"] == cartao_avancado]

df_receitas = df_filtrado[df_filtrado["Tipo"] == "Receita"]
df_despesas = df_filtrado[df_filtrado["Tipo"] == "Despesa"]


# ============== KPIs ==============
st.divider()
total_receita = df_receitas["Valor"].sum()
total_despesa = df_despesas["Valor"].sum()
saldo = total_receita - total_despesa
total_tetos = df_tetos["Teto Mensal"].sum() if not df_tetos.empty else 1
pct_teto = total_despesa / total_tetos if total_tetos > 0 else 0

# Detecta se o mês selecionado está em andamento
hoje = datetime.now()
mes_atual_str = f"{hoje.month:02d}/{hoje.year}"
mes_em_andamento = (competencia == mes_atual_str)

if modo == "Caixa":
    saldo_label = f"💵 Caixa parcial (até {hoje.strftime('%d/%m')})" if mes_em_andamento else "💵 Saldo de Caixa"
else:
    saldo_label = f"📊 Saldo parcial (até {hoje.strftime('%d/%m')})" if mes_em_andamento else "📊 Saldo do mês"

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Receitas", total_receita, emoji="💚")
with c2: kpi_card("Despesas", total_despesa, emoji="💸")
with c3: kpi_card(saldo_label, saldo, emoji="")
with c4: kpi_card("Uso do teto", pct_teto, prefix="%", emoji="🎯")

# Aviso pra mês em andamento (sem dar percepção falsa de sobra)
if mes_em_andamento:
    if modo == "Caixa":
        st.info(
            f"🔄 **Mês em andamento.** Esse caixa é parcial até {hoje.strftime('%d/%m')}. "
            f"Pagamentos previstos (faturas de cartão, recorrentes) ainda podem entrar/sair."
        )
    else:
        st.info(
            f"🔄 **Mês em andamento.** Esse saldo é parcial até {hoje.strftime('%d/%m')}. "
            f"Despesas ainda podem ser lançadas até fim do mês. "
            f"O 'disponível pra investir' aparece só quando o mês fecha."
        )
elif saldo < 0:
    st.error(f"⚠️ Mês fechou com déficit de {fmt_brl(abs(saldo))} — revisar despesas.")
else:
    if modo == "Caixa":
        st.success(f"✅ **Caixa do mês**: sobrou {fmt_brl(saldo)} efetivamente em conta.")
    else:
        st.success(f"✅ **Mês fechado**: sobra final de {fmt_brl(saldo)} — disponível pra investir/poupar.")


# ============== GASTOS POR CATEGORIA vs TETO ==============
st.divider()
st.subheader(f"📋 Gastos por Categoria — {modo} {competencia}")
st.caption("👆 **Clique numa barra** pra ver os lançamentos da categoria")
col_a, col_b = st.columns([3, 2])
with col_a:
    cat_clicada = barras_categoria_vs_teto(df_despesas, df_tetos, titulo="", key=f"barras_{modo}_{competencia}_{pessoa}")
with col_b:
    donut_categorias(df_despesas, titulo="Distribuição")

# Drill-down: mostra lançamentos da categoria clicada
if cat_clicada:
    st.divider()
    detalhar_categoria(df_despesas, cat_clicada)


# ============== EVOLUÇÃO MENSAL (HEATMAP) ==============
st.divider()
st.subheader(f"🗓️ Evolução Mensal — últimos 6 meses ({modo})")
df_evolucao_base = df_lanc if pessoa_filter is None else filtrar(df_lanc, pessoa=pessoa_filter, modo=modo)
comparativo_mensal(df_evolucao_base, df_tetos, modo=modo, n_meses=6)


# ============== PROJEÇÃO 6 MESES ==============
st.divider()
st.subheader(f"🔮 Projeção dos próximos 6 meses ({modo})")
projecao_6_meses(df_evolucao_base, df_rec, modo=modo)


# ============== TOP DESPESAS ==============
st.divider()
st.subheader(f"🔝 Top 10 maiores despesas — {modo} {competencia}")
tabela_top_despesas(df_despesas, n=10)


# ============== TODOS OS LANÇAMENTOS (drill-down) ==============
st.divider()
with st.expander(f"📜 Ver TODOS os lançamentos ({modo} {competencia}) — {len(df_filtrado)} registros"):
    col_search, col_tipo, col_cat = st.columns([2, 1, 1])
    with col_search:
        busca = st.text_input("🔍 Buscar (descrição/categoria)", "")
    with col_tipo:
        tipo_filter = st.selectbox("Tipo", ["Todos", "Despesa", "Receita"])
    with col_cat:
        cats = ["Todas"] + sorted(df_filtrado["Categoria"].dropna().unique().tolist())
        cat_filter = st.selectbox("Categoria", cats)

    df_view = df_filtrado.copy()
    if busca:
        mask = df_view["Descrição"].astype(str).str.contains(busca, case=False, na=False) | \
               df_view["Categoria"].astype(str).str.contains(busca, case=False, na=False)
        df_view = df_view[mask]
    if tipo_filter != "Todos":
        df_view = df_view[df_view["Tipo"] == tipo_filter]
    if cat_filter != "Todas":
        df_view = df_view[df_view["Categoria"] == cat_filter]

    # Ordena por valor decrescente
    df_view = df_view.sort_values("Valor", ascending=False)

    # Formata pra exibição
    cols_show = ["Data", "Tipo", "Categoria", "Subcategoria", "Descrição",
                 "Pessoa", "Forma Pgto", "Cartão", "Parcela", "Valor", "Data Caixa", "Mensagem Original"]
    cols_show = [c for c in cols_show if c in df_view.columns]
    df_display = df_view[cols_show].copy()
    df_display["Valor"] = df_display["Valor"].apply(fmt_brl)

    st.dataframe(df_display, hide_index=True, use_container_width=True, height=400)
    st.caption(f"Total filtrado: {len(df_view)} lançamentos • Soma: {fmt_brl(df_view['Valor'].sum())}")


# ============== FOOTER ==============
st.divider()
st.caption(f"💾 Dados atualizados automaticamente do Google Sheets (cache 60s) • Última carga: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
