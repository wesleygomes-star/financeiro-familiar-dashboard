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
from lib.data import load_lancamentos, load_recorrentes, load_tetos, meses_disponiveis, filtrar, mes_anterior, progresso_mes, classificar_fixa_variavel
from lib.components import kpi_card, donut_categorias, barras_categoria_vs_teto, projecao_6_meses, tabela_top_despesas, detalhar_categoria, comparativo_mensal, fmt_brl, breakdown_fixa_variavel, detalhar_fixa_variavel


# set_page_config + auth ficam no router (streamlit_app.py)

# ============== CSS RESPONSIVO (mobile-friendly) ==============
st.markdown(
    """
    <style>
    /* Em telas <= 768px (celular/tablet pequeno), colunas viram stack vertical */
    @media (max-width: 768px) {
        div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 0.5rem;
        }
        /* KPI metric maior em mobile pra leitura rápida */
        div[data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
        }
        /* Reduz padding do bloco principal pra ganhar área útil */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        /* Título menor em mobile */
        h1 {
            font-size: 1.6rem !important;
        }
        h2 {
            font-size: 1.3rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        /* Tabelas com scroll horizontal em mobile */
        div[data-testid="stDataFrame"] {
            overflow-x: auto;
        }
        /* Esconde colunas auxiliares em mobile (atualização, espaços vazios) */
        .mobile-hide {
            display: none !important;
        }
    }
    /* Sempre — reduz padding excessivo do Streamlit */
    .block-container {
        max-width: 100% !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============== DADOS ==============
with st.spinner("Carregando dados..."):
    df_lanc = load_lancamentos()
    df_rec = load_recorrentes()
    df_tetos = load_tetos()

if df_lanc.empty:
    st.error("Sem dados na planilha. Verifique conexão.")
    st.stop()

# Classifica todas as despesas como Fixa ou Variável (matching com recorrentes ativas)
df_lanc = classificar_fixa_variavel(df_lanc, df_rec)


# ============== HEADER ==============
st.title("💰 Financeiro Família Gomes")

# ============== FILTROS (card único agrupado) ==============
with st.container(border=True):
    st.markdown("### 🔍 Filtros")

    # Linha 1: Modo (Competência/Caixa) + Atualizar
    col_modo, col_refresh = st.columns([4, 1])
    with col_modo:
        modo = st.radio(
            "🎯 Visão",
            ["Competência", "Caixa"],
            horizontal=True,
            help="Competência = a qual mês a despesa pertence (ideal pra controle de teto). Caixa = quando o dinheiro efetivamente sai (ideal pra fluxo de caixa).",
            label_visibility="collapsed",
        )
    with col_refresh:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Linha 2: Mês + Pessoa + Categoria + Forma Pgto
    meses = meses_disponiveis(df_lanc, modo=modo)
    mes_default = f"{datetime.now().month:02d}/{datetime.now().year}"
    idx_default = meses.index(mes_default) if mes_default in meses else 0

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        competencia = st.selectbox(
            f"📅 Mês ({modo})",
            meses,
            index=idx_default,
            key=f"mes_{modo}",
        )
    with f2:
        pessoa = st.selectbox("👥 Pessoa", ["Família (todos)", "Wesley", "Sabrina"])
    with f3:
        cats_disponiveis = ["Todas"] + sorted(df_lanc["Categoria"].dropna().unique().tolist())
        cat_avancada = st.selectbox("📂 Categoria", cats_disponiveis, key="filtro_cat")
    with f4:
        formas = ["Todas"] + sorted(df_lanc["Forma Pgto"].dropna().unique().tolist())
        forma_avancada = st.selectbox("💳 Forma Pgto", formas, key="filtro_forma")

    # Linha 3: Cartões (multiselect ocupa linha inteira pra acomodar várias chips)
    cartoes_disp = sorted([c for c in df_lanc["Cartão"].dropna().unique().tolist() if c])
    cartoes_selecionados = st.multiselect(
        "💳 Cartões (vazio = todos)",
        cartoes_disp,
        default=[],
        key="filtro_cartao_multi",
        placeholder="Selecione um ou mais cartões…",
        help="Selecione um ou mais cartões pra ver fatura combinada. Vazio = mostra todos.",
    )

# Linha-resumo do que tá filtrado (logo abaixo do card)
_resumo_parts = [f"**{modo}** {competencia}"]
if pessoa != "Família (todos)":
    _resumo_parts.append(f"👥 {pessoa}")
else:
    _resumo_parts.append("👥 Família (todos)")
if cat_avancada != "Todas":
    _resumo_parts.append(f"📂 {cat_avancada}")
if forma_avancada != "Todas":
    _resumo_parts.append(f"💳 {forma_avancada}")
if cartoes_selecionados:
    _resumo_parts.append(f"💳 Cartões: {', '.join(cartoes_selecionados)}")
_filtros_extras_ativos = (cat_avancada != "Todas") or (forma_avancada != "Todas") or bool(cartoes_selecionados)
_emoji_resumo = "🔎" if _filtros_extras_ativos else "📊"
st.caption(f"{_emoji_resumo} **Mostrando:** {' • '.join(_resumo_parts)}")

# Caption explicativo do modo (mantido, mas em fonte menor)
if modo == "Competência":
    st.caption("ℹ️ **Competência:** gastos pelo mês a que pertencem (compra de cartão em maio fica em maio, mesmo que pague em junho). Ideal pra **controle de tetos**.")
else:
    st.caption("ℹ️ **Caixa:** quando o dinheiro efetivamente sai da conta (compra de cartão em maio aparece em junho). Ideal pra **fluxo de caixa**.")

# Aplicar filtros
pessoa_filter = None if pessoa == "Família (todos)" else pessoa
df_filtrado = filtrar(df_lanc, competencia=competencia, pessoa=pessoa_filter, modo=modo)
# Aplica filtros adicionais
if cat_avancada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Categoria"] == cat_avancada]
if forma_avancada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Forma Pgto"] == forma_avancada]
if cartoes_selecionados:
    df_filtrado = df_filtrado[df_filtrado["Cartão"].isin(cartoes_selecionados)]

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

# Mês anterior — para deltas comparativos (aplica os mesmos filtros)
comp_anterior = mes_anterior(competencia)
df_anterior = filtrar(df_lanc, competencia=comp_anterior, pessoa=pessoa_filter, modo=modo)
if cat_avancada != "Todas":
    df_anterior = df_anterior[df_anterior["Categoria"] == cat_avancada]
if forma_avancada != "Todas":
    df_anterior = df_anterior[df_anterior["Forma Pgto"] == forma_avancada]
if cartoes_selecionados:
    df_anterior = df_anterior[df_anterior["Cartão"].isin(cartoes_selecionados)]

receita_ant = df_anterior[df_anterior["Tipo"] == "Receita"]["Valor"].sum()
despesa_ant = df_anterior[df_anterior["Tipo"] == "Despesa"]["Valor"].sum()
saldo_ant = receita_ant - despesa_ant
pct_teto_ant = despesa_ant / total_tetos if total_tetos > 0 else 0

if modo == "Caixa":
    saldo_label = f"💵 Caixa parcial (até {hoje.strftime('%d/%m')})" if mes_em_andamento else "💵 Saldo de Caixa"
else:
    saldo_label = f"📊 Saldo parcial (até {hoje.strftime('%d/%m')})" if mes_em_andamento else "📊 Saldo do mês"

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Receitas", total_receita, emoji="💚", valor_anterior=receita_ant)
with c2:
    # Despesa: subir é ruim → delta_inverso (vermelho quando sobe)
    kpi_card("Despesas", total_despesa, emoji="💸", valor_anterior=despesa_ant, delta_inverso=True)
with c3:
    kpi_card(saldo_label, saldo, emoji="", valor_anterior=saldo_ant)
with c4:
    kpi_card("Uso do teto", pct_teto, prefix="%", emoji="🎯", valor_anterior=pct_teto_ant, delta_inverso=True)

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

    # ---------- Indicador de ritmo (D) ----------
    # Compara % do teto gasto vs % do mês decorrido. Se ratio > 1 -> tá à frente do ritmo esperado.
    pct_mes = progresso_mes(competencia)
    if pct_mes > 0 and total_tetos > 0:
        ratio = pct_teto / pct_mes  # 1.0 = no ritmo; >1 = à frente; <1 = atrás
        pct_mes_str = f"{pct_mes*100:.0f}% do mês"
        pct_teto_str = f"{pct_teto*100:.0f}% do teto"
        if ratio >= 1.3:
            st.error(
                f"🚨 **Ritmo acelerado:** já consumiu {pct_teto_str} com apenas {pct_mes_str} decorrido "
                f"(gastando {(ratio-1)*100:.0f}% acima do esperado pro dia). "
                f"Se continuar nesse ritmo, fecha o mês em {fmt_brl(total_despesa/pct_mes)}."
            )
        elif ratio >= 1.1:
            st.warning(
                f"⚠️ **Atenção ao ritmo:** {pct_teto_str} consumido com {pct_mes_str} decorrido "
                f"({(ratio-1)*100:.0f}% acima do esperado). Projeção pro fim do mês: {fmt_brl(total_despesa/pct_mes)}."
            )
        else:
            st.success(
                f"✅ **No ritmo:** {pct_teto_str} consumido com {pct_mes_str} decorrido. "
                f"Projeção pro fim do mês: {fmt_brl(total_despesa/pct_mes)}."
            )
elif saldo < 0:
    st.error(f"⚠️ Mês fechou com déficit de {fmt_brl(abs(saldo))} — revisar despesas.")
else:
    if modo == "Caixa":
        st.success(f"✅ **Caixa do mês**: sobrou {fmt_brl(saldo)} efetivamente em conta.")
    else:
        st.success(f"✅ **Mês fechado**: sobra final de {fmt_brl(saldo)} — disponível pra investir/poupar.")


# ============== FIXA vs VARIÁVEL ==============
st.divider()
st.subheader("💰 Composição da despesa — Fixa vs Variável")
st.caption("👆 **Clique numa fatia da barra** pra ver os lançamentos do tipo")
tipo_clicado = breakdown_fixa_variavel(df_despesas, key=f"fixavar_{modo}_{competencia}_{pessoa}")
if tipo_clicado:
    st.divider()
    detalhar_fixa_variavel(df_despesas, tipo_clicado)


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
    cols_show = ["Data", "Tipo", "Tipo Despesa", "Categoria", "Subcategoria", "Descrição",
                 "Pessoa", "Forma Pgto", "Cartão", "Parcela", "Valor", "Data Caixa", "Mensagem Original"]
    cols_show = [c for c in cols_show if c in df_view.columns]
    df_display = df_view[cols_show].copy()
    df_display["Valor"] = df_display["Valor"].apply(fmt_brl)

    st.dataframe(df_display, hide_index=True, use_container_width=True, height=400)
    st.caption(f"Total filtrado: {len(df_view)} lançamentos • Soma: {fmt_brl(df_view['Valor'].sum())}")


# ============== FOOTER ==============
st.divider()
st.caption(f"💾 Dados atualizados automaticamente do Google Sheets (cache 60s) • Última carga: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
