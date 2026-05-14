"""Componentes visuais reutilizáveis."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def fmt_brl(v) -> str:
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def kpi_card(label: str, value: float, prefix: str = "R$", delta: str = None, delta_color="normal", emoji: str = ""):
    """Card grande com KPI. Use dentro de uma coluna st.columns."""
    formatted = fmt_brl(value) if prefix == "R$" else f"{value:.1%}" if prefix == "%" else f"{prefix}{value}"
    st.metric(label=f"{emoji} {label}", value=formatted, delta=delta, delta_color=delta_color)


def donut_categorias(df_despesas: pd.DataFrame, titulo: str = "Despesas por Categoria"):
    """Donut de despesas por categoria."""
    if df_despesas.empty:
        st.info("Sem dados pra mostrar nesse filtro.")
        return
    agg = df_despesas.groupby("Categoria", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
    fig = px.pie(agg, values="Valor", names="Categoria", hole=0.55,
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(
        textposition="outside",
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
    )
    fig.update_layout(
        title=titulo,
        showlegend=False,
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def barras_categoria_vs_teto(df_despesas: pd.DataFrame, df_tetos: pd.DataFrame, titulo: str = "Gasto vs Teto", key: str = "barras_cat"):
    """Barras horizontais com semáforo por % do teto.
    Retorna a categoria clicada (string) ou None.
    """
    if df_despesas.empty:
        st.info("Sem dados.")
        return None
    agg = df_despesas.groupby("Categoria", as_index=False)["Valor"].sum()
    tetos_map = dict(zip(df_tetos["Categoria"], df_tetos["Teto Mensal"]))
    agg["Teto"] = agg["Categoria"].map(tetos_map).fillna(0)
    agg["Pct"] = agg.apply(lambda r: (r["Valor"] / r["Teto"]) if r["Teto"] > 0 else 0, axis=1)

    def cor(p):
        if p >= 1.0: return "#EF4444"
        if p >= 0.8: return "#F59E0B"
        return "#10B981"

    agg["Cor"] = agg["Pct"].apply(cor)
    agg = agg.sort_values("Pct", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=agg["Categoria"],
        x=agg["Valor"],
        orientation="h",
        marker_color=agg["Cor"],
        text=[f"{fmt_brl(v)} ({p:.0%})" for v, p in zip(agg["Valor"], agg["Pct"])],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Gasto: %{customdata[0]}<br>Teto: %{customdata[1]}<br>%{customdata[2]} do teto<br><i>👆 Clica pra ver detalhes</i><extra></extra>",
        customdata=[[fmt_brl(v), fmt_brl(t), f"{p:.0%}"] for v, t, p in zip(agg["Valor"], agg["Teto"], agg["Pct"])],
    ))
    fig.update_layout(
        title=titulo,
        height=max(300, 30 * len(agg) + 100),
        margin=dict(l=10, r=80, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="R$", showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title=""),
    )
    event = st.plotly_chart(fig, use_container_width=True, key=key, on_select="rerun")
    # extrai categoria clicada
    if event and hasattr(event, "selection"):
        pts = event.selection.get("points", [])
        if pts:
            return pts[0].get("y") or pts[0].get("label")
    return None


def detalhar_categoria(df_despesas: pd.DataFrame, categoria: str):
    """Mostra todos os lançamentos de uma categoria específica, ordenados por valor."""
    df_cat = df_despesas[df_despesas["Categoria"] == categoria].sort_values("Valor", ascending=False)
    if df_cat.empty:
        st.info(f"Sem lançamentos em {categoria}.")
        return
    total = df_cat["Valor"].sum()
    st.markdown(f"### 🔎 Detalhes de **{categoria}** — {len(df_cat)} lançamentos, total {fmt_brl(total)}")
    cols_show = ["Data", "Subcategoria", "Descrição", "Pessoa", "Forma Pgto", "Cartão", "Valor"]
    cols_show = [c for c in cols_show if c in df_cat.columns]
    df_display = df_cat[cols_show].copy()
    df_display["Valor"] = df_display["Valor"].apply(fmt_brl)
    st.dataframe(df_display, hide_index=True, use_container_width=True)


def projecao_6_meses(df_lancamentos: pd.DataFrame, df_recorrentes: pd.DataFrame):
    """Tabela + gráfico de barras agrupadas: Receita × Despesa por mês (6 meses).

    Para o mês atual: mostra o que JÁ foi lançado (parcial).
    Para meses futuros: mostra a projeção baseada nas recorrentes ativas.
    """
    from datetime import datetime
    hoje = datetime.now()

    rec_despesa_mensal = df_recorrentes[
        (df_recorrentes["Ativo_bool"]) & (df_recorrentes["Forma Pgto"] != "Crédito em conta")
    ]["Valor"].sum()
    rec_receita_mensal = df_recorrentes[
        (df_recorrentes["Ativo_bool"]) & (df_recorrentes["Forma Pgto"] == "Crédito em conta")
    ]["Valor"].sum()

    pontos = []
    for i in range(6):
        m = hoje.month + i
        y = hoje.year
        while m > 12:
            m -= 12; y += 1
        comp = f"{m:02d}/{y}"
        is_atual = (m == hoje.month and y == hoje.year)
        lanc_mes = df_lancamentos[df_lancamentos["Competência"] == comp]
        rec_lanc = lanc_mes[lanc_mes["Tipo"] == "Receita"]["Valor"].sum()
        desp_lanc = lanc_mes[lanc_mes["Tipo"] == "Despesa"]["Valor"].sum()

        if is_atual:
            receita = rec_lanc
            despesa = desp_lanc
            status = "🔄 Em andamento"
        elif i == 0 or comp < f"{hoje.month:02d}/{hoje.year}":
            # mês passado, mostra o real
            receita = rec_lanc
            despesa = desp_lanc
            status = "✅ Fechado"
        else:
            # mês futuro: projeção baseada em recorrentes
            receita = rec_receita_mensal
            despesa = rec_despesa_mensal
            status = "📊 Projetado"

        pontos.append({
            "Mês": comp,
            "Receita": receita,
            "Despesa": despesa,
            "Saldo": receita - despesa,
            "Status": status,
        })

    df = pd.DataFrame(pontos)

    # Gráfico: barras agrupadas
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Mês"], y=df["Receita"], name="💚 Receita",
        marker_color="#10B981",
        text=[fmt_brl(v) for v in df["Receita"]], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=df["Mês"], y=df["Despesa"], name="💸 Despesa",
        marker_color="#EF4444",
        text=[fmt_brl(v) for v in df["Despesa"]], textposition="outside",
    ))
    fig.update_layout(
        title="📊 Receita × Despesa nos próximos 6 meses",
        barmode="group",
        height=420,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabela detalhada
    df_display = df.copy()
    df_display["Receita"] = df_display["Receita"].apply(fmt_brl)
    df_display["Despesa"] = df_display["Despesa"].apply(fmt_brl)
    df_display["Saldo"] = df_display["Saldo"].apply(fmt_brl)
    with st.expander("📋 Ver detalhamento dos próximos 6 meses"):
        st.dataframe(df_display, hide_index=True, use_container_width=True)
        st.caption(
            "**Em andamento**: só inclui o que já foi lançado este mês. "
            "**Projetado**: receitas e despesas recorrentes ativas (sem variáveis futuras)."
        )


def tabela_top_despesas(df_despesas: pd.DataFrame, n: int = 10):
    """Top N maiores despesas do mês selecionado."""
    if df_despesas.empty:
        st.info("Sem despesas pra mostrar.")
        return
    cols = ["Data", "Descrição", "Categoria", "Forma Pgto", "Cartão", "Valor"]
    cols = [c for c in cols if c in df_despesas.columns]
    top = df_despesas.nlargest(n, "Valor")[cols].copy()
    top["Valor"] = top["Valor"].apply(fmt_brl)
    st.dataframe(top, hide_index=True, use_container_width=True)
