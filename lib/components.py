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


def kpi_card(label: str, value: float, prefix: str = "R$", delta: str = None,
             delta_color="normal", emoji: str = "",
             valor_anterior: float = None, delta_inverso: bool = False):
    """Card grande com KPI. Use dentro de uma coluna st.columns.

    Args:
        valor_anterior: se informado, calcula delta automaticamente como
            (valor - valor_anterior). Exibe variação absoluta + percentual.
        delta_inverso: True para métricas onde subir é ruim (ex: despesa).
            Inverte a cor (vermelho quando sobe, verde quando cai).
    """
    formatted = fmt_brl(value) if prefix == "R$" else f"{value:.1%}" if prefix == "%" else f"{prefix}{value}"

    # Se valor_anterior foi passado, monta delta automaticamente
    if valor_anterior is not None and delta is None:
        diff = value - valor_anterior
        if abs(valor_anterior) > 0.01:
            pct = (diff / abs(valor_anterior)) * 100
            pct_str = f" ({pct:+.0f}%)"
        else:
            pct_str = ""
        if prefix == "R$":
            delta = f"{fmt_brl(diff)}{pct_str} vs mês anterior"
        elif prefix == "%":
            delta = f"{diff*100:+.1f}pp vs mês anterior"
        else:
            delta = f"{diff:+.2f}{pct_str} vs mês anterior"
        if delta_inverso:
            delta_color = "inverse"

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


def projecao_6_meses(df_lancamentos: pd.DataFrame, df_recorrentes: pd.DataFrame, modo: str = "Competência"):
    """Tabela + gráfico de barras agrupadas: Receita × Despesa por mês (6 meses).

    modo='Competência': agrupa pelo mês que a despesa pertence.
    modo='Caixa': agrupa pelo mês que o dinheiro efetivamente sai (Data Caixa).

    Para o mês atual: mostra o que JÁ foi lançado (parcial).
    Para meses futuros: mostra a projeção baseada nas recorrentes ativas.
    """
    from datetime import datetime
    hoje = datetime.now()
    coluna_mes = "Mês Caixa" if modo == "Caixa" else "Competência"

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
        lanc_mes = df_lancamentos[df_lancamentos[coluna_mes] == comp]
        rec_lanc = lanc_mes[lanc_mes["Tipo"] == "Receita"]["Valor"].sum()
        desp_lanc = lanc_mes[lanc_mes["Tipo"] == "Despesa"]["Valor"].sum()

        if is_atual:
            receita = rec_lanc
            despesa = desp_lanc
            status = "🔄 Em andamento"
        elif i == 0 or comp < f"{hoje.month:02d}/{hoje.year}":
            receita = rec_lanc
            despesa = desp_lanc
            status = "✅ Fechado"
        else:
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
    titulo_modo = "Caixa (quando entra/sai)" if modo == "Caixa" else "Competência (mês de pertencimento)"
    fig.update_layout(
        title=f"📊 Receita × Despesa nos próximos 6 meses — {titulo_modo}",
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


def breakdown_fixa_variavel(df_despesas: pd.DataFrame, key: str = "fixavar"):
    """Renderiza breakdown Fixa vs Variável: 2 KPIs + barra horizontal proporcional.

    Espera coluna 'Tipo Despesa' já preenchida ('Fixa' / 'Variável').
    Retorna o tipo clicado ('Fixa', 'Variável') ou None.
    """
    if df_despesas.empty or "Tipo Despesa" not in df_despesas.columns:
        return None

    fixa = df_despesas[df_despesas["Tipo Despesa"] == "Fixa"]["Valor"].sum()
    variavel = df_despesas[df_despesas["Tipo Despesa"] == "Variável"]["Valor"].sum()
    total = fixa + variavel

    if total <= 0:
        return None

    pct_fixa = fixa / total
    pct_var = variavel / total

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        st.metric("🔒 Despesa Fixa", fmt_brl(fixa), delta=f"{pct_fixa*100:.0f}% do total")
        st.caption("Recorrentes: aluguel, escola, assinaturas...")
    with col2:
        st.metric("🎲 Despesa Variável", fmt_brl(variavel), delta=f"{pct_var*100:.0f}% do total")
        st.caption("Discricionário: mercado, lazer, eventual...")
    with col3:
        # Barra empilhada horizontal
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=["Composição"], x=[fixa], name="🔒 Fixa",
            orientation="h", marker_color="#6366F1",
            text=f"{fmt_brl(fixa)} ({pct_fixa*100:.0f}%)",
            textposition="inside", insidetextanchor="middle",
            hovertemplate="<b>Fixa</b><br>%{x:,.2f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            y=["Composição"], x=[variavel], name="🎲 Variável",
            orientation="h", marker_color="#F97316",
            text=f"{fmt_brl(variavel)} ({pct_var*100:.0f}%)",
            textposition="inside", insidetextanchor="middle",
            hovertemplate="<b>Variável</b><br>%{x:,.2f}<extra></extra>",
        ))
        fig.update_layout(
            barmode="stack",
            height=120,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False),
        )
        event = st.plotly_chart(fig, use_container_width=True, key=key, on_select="rerun")
        if event and hasattr(event, "selection"):
            pts = event.selection.get("points", [])
            if pts:
                nome = pts[0].get("legendgroup") or pts[0].get("curve_number")
                # extrai pelo curveNumber (0 = Fixa, 1 = Variável)
                idx = pts[0].get("curve_number", pts[0].get("curveNumber"))
                if idx == 0:
                    return "Fixa"
                if idx == 1:
                    return "Variável"
    return None


def detalhar_fixa_variavel(df_despesas: pd.DataFrame, tipo: str):
    """Lista lançamentos de Fixa ou Variável, agrupados por categoria."""
    df = df_despesas[df_despesas["Tipo Despesa"] == tipo].sort_values("Valor", ascending=False)
    if df.empty:
        st.info(f"Sem despesas {tipo.lower()}s nesse filtro.")
        return
    icone = "🔒" if tipo == "Fixa" else "🎲"
    total = df["Valor"].sum()
    st.markdown(f"### {icone} Despesas **{tipo}s** — {len(df)} lançamentos, total {fmt_brl(total)}")

    # Resumo por categoria
    resumo = df.groupby("Categoria", as_index=False).agg(
        Valor=("Valor", "sum"),
        Qtd=("Valor", "count"),
    ).sort_values("Valor", ascending=False)
    resumo["Valor"] = resumo["Valor"].apply(fmt_brl)
    st.markdown("**Por categoria:**")
    st.dataframe(resumo, hide_index=True, use_container_width=True)

    # Lista detalhada
    cols_show = ["Data", "Categoria", "Subcategoria", "Descrição", "Pessoa", "Forma Pgto", "Valor"]
    cols_show = [c for c in cols_show if c in df.columns]
    df_display = df[cols_show].copy()
    df_display["Valor"] = df_display["Valor"].apply(fmt_brl)
    with st.expander(f"Ver todos os {len(df)} lançamentos {tipo.lower()}s"):
        st.dataframe(df_display, hide_index=True, use_container_width=True)


def comparativo_mensal(df_lancamentos: pd.DataFrame, df_tetos: pd.DataFrame, modo: str = "Competência", n_meses: int = 6):
    """Evolução mensal: heatmap por categoria × mês + linha de total.

    Mostra últimos n_meses incluindo o atual.
    Cores: verde (baixo % do teto), amarelo (médio), vermelho (alto/estouro).
    """
    from datetime import datetime
    hoje = datetime.now()
    coluna_mes = "Mês Caixa" if modo == "Caixa" else "Competência"

    # Lista de meses (do mais antigo pro mais recente)
    meses = []
    for i in range(n_meses - 1, -1, -1):
        m = hoje.month - i
        y = hoje.year
        while m < 1:
            m += 12; y -= 1
        meses.append(f"{m:02d}/{y}")

    # Despesas por categoria × mês
    despesas = df_lancamentos[df_lancamentos["Tipo"] == "Despesa"].copy()
    if despesas.empty:
        st.info("Sem despesas pra comparar.")
        return

    pivot = despesas.pivot_table(
        index="Categoria",
        columns=coluna_mes,
        values="Valor",
        aggfunc="sum",
        fill_value=0,
    )
    # Mantém só meses do período + ordena
    pivot = pivot.reindex(columns=meses, fill_value=0)

    # Tetos
    tetos_map = dict(zip(df_tetos["Categoria"], df_tetos["Teto Mensal"])) if not df_tetos.empty else {}

    # Calcula % do teto pra colorir
    pct = pivot.copy()
    for cat in pct.index:
        teto = tetos_map.get(cat, 0)
        if teto > 0:
            pct.loc[cat] = pivot.loc[cat] / teto
        else:
            pct.loc[cat] = 0

    # Heatmap usando Plotly
    fig = go.Figure(data=go.Heatmap(
        z=pct.values,
        x=pivot.columns,
        y=pivot.index,
        # Colorscale precisa estar normalizado em [0,1]. Como zmax=1.2,
        # o valor 1.0 na escala = 120% do teto. Mapeamento:
        #   0%   -> verde     (0/1.2 = 0.00)
        #   60%  -> verde     (0.6/1.2 = 0.50)
        #   80%  -> amarelo   (0.8/1.2 ≈ 0.67)
        #   100% -> vermelho  (1.0/1.2 ≈ 0.83)
        #   120% -> vinho     (1.2/1.2 = 1.00)
        colorscale=[
            [0.00, "#10B981"],   # verde
            [0.50, "#10B981"],   # verde (até 60% do teto)
            [0.67, "#F59E0B"],   # amarelo (~80%)
            [0.83, "#EF4444"],   # vermelho (~100%)
            [1.00, "#7F1D1D"],   # vinho (estouro forte, ≥120%)
        ],
        zmin=0, zmax=1.2,
        text=[[fmt_brl(v) for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont={"size": 11, "color": "white"},
        hovertemplate="<b>%{y}</b><br>%{x}<br>Gasto: %{text}<br>% teto: %{z:.0%}<extra></extra>",
        showscale=True,
        colorbar=dict(title="% teto", tickformat=".0%"),
    ))
    fig.update_layout(
        title=f"🗓️ Evolução mensal por categoria — {modo}",
        height=max(350, 35 * len(pivot.index) + 100),
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(side="top"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Linha de total despesa × receita por mês (overview)
    receitas = df_lancamentos[df_lancamentos["Tipo"] == "Receita"]
    despesas_total = pivot.sum(axis=0)
    receitas_total = receitas.groupby(coluna_mes)["Valor"].sum().reindex(meses, fill_value=0)
    saldo_total = receitas_total - despesas_total

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=meses, y=receitas_total, name="💚 Receita", marker_color="#10B981"))
    fig2.add_trace(go.Bar(x=meses, y=despesas_total, name="💸 Despesa", marker_color="#EF4444"))
    fig2.add_trace(go.Scatter(
        x=meses, y=saldo_total,
        name="📊 Saldo", mode="lines+markers+text",
        line=dict(color="#FCD34D", width=3),
        marker=dict(size=10),
        text=[fmt_brl(v) for v in saldo_total],
        textposition="top center",
    ))
    fig2.update_layout(
        title=f"📊 Receita × Despesa × Saldo (últimos {n_meses} meses)",
        barmode="group",
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig2, use_container_width=True)


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
