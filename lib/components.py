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


# ---- Tokens semânticos de cor: cada cor tem UM significado no painel inteiro ----
COR = {
    "receita": "#1D9E75",         # verde — dinheiro que entra / positivo
    "despesa": "#E24B4A",         # vermelho — gasto
    "despesa_escura": "#B23434",  # camada secundária de despesa (stacks)
    "investimento": "#185FA5",    # azul — investimento / saldo / progresso
    "alerta": "#BA7517",          # âmbar — atenção
    "flexivel": "#7F77DD",        # roxo — gasto discricionário (flexível/variável)
    "neutro": "#888780",          # cinza — fixo / secundário
    "neutro_claro": "#B4B2A9",
}

# Config padrão dos gráficos (mobile-first: sem barra de ferramentas, sem zoom por gesto)
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}


def fig_mobile(fig):
    """Padroniza gráfico pro celular: eixos fixos (devolvem o scroll da página
    ao usuário) e separadores numéricos pt-BR (1.234,56)."""
    fig.update_layout(separators=",.", dragmode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


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

    rotulo = f"{emoji} {label}".strip()
    st.metric(label=rotulo, value=formatted, delta=delta, delta_color=delta_color)


# Paleta fixa por categoria (mesma família de cores do mockup aprovado)
CORES_CATEGORIA = {
    "Lazer & Restaurantes": "#7F77DD",
    "Alimentação": "#1D9E75",
    "Moradia": "#378ADD",
    "Transporte": "#888780",
    "Saúde": "#2E9EA4",  # teal — o vermelho é reservado pra 'despesa total'
    "Educação": "#EF9F27",
    "Vestuário": "#D4537E",
    "Pessoal & Beleza": "#F0997B",
    "Assinaturas & Streaming": "#5DCAA5",
    "Financeiro & Cartão": "#85B7EB",
    "Auxílio Familiar": "#FAC775",
    "Outros Imóveis": "#AFA9EC",
    "Investimentos em Imóvel": "#185FA5",
    "Outros": "#B4B2A9",
}
COR_FALLBACK = "#B4B2A9"


def donut_categorias(df_despesas: pd.DataFrame, titulo: str = "Despesas por Categoria"):
    """Donut de despesas por categoria — top 8 + 'Outras', legenda embaixo (sem callouts sobrepostos)."""
    if df_despesas.empty:
        st.info("Sem dados pra mostrar nesse filtro.")
        return
    agg = df_despesas.groupby("Categoria", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
    if len(agg) > 8:
        top = agg.head(8)
        outras = pd.DataFrame([{"Categoria": "Outras", "Valor": agg["Valor"].iloc[8:].sum()}])
        agg = pd.concat([top, outras], ignore_index=True)

    cores = [CORES_CATEGORIA.get(c, COR_FALLBACK) for c in agg["Categoria"]]
    total = agg["Valor"].sum()
    labels_legenda = [
        f"{c} · {v / total:.0%}" for c, v in zip(agg["Categoria"], agg["Valor"])
    ]

    fig = go.Figure(go.Pie(
        labels=labels_legenda,
        values=agg["Valor"],
        hole=0.62,
        marker=dict(colors=cores),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>",
        sort=False,
    ))
    fig.update_layout(
        title=titulo,
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font=dict(size=11)),
        height=420,
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#2C2C2A", size=12),
    )
    st.plotly_chart(fig_mobile(fig), use_container_width=True, config=PLOTLY_CONFIG)


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
    # Maior gasto em cima (mockup), cor fixa por categoria — semáforo vai só no texto do %
    agg = agg.sort_values("Valor", ascending=True)
    agg["Cor"] = agg["Categoria"].map(lambda c: CORES_CATEGORIA.get(c, COR_FALLBACK))

    def label(v, p, t):
        if t <= 0:
            return fmt_brl(v)
        emoji = "🔴" if p >= 1.0 else ("🟡" if p >= 0.8 else "")
        return f"{fmt_brl(v)} · {p:.0%} {emoji}".strip()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=agg["Categoria"],
        x=agg["Valor"],
        orientation="h",
        marker=dict(color=agg["Cor"], cornerradius=4),
        text=[label(v, p, t) for v, p, t in zip(agg["Valor"], agg["Pct"], agg["Teto"])],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=12),
        hovertemplate="<b>%{y}</b><br>Gasto: %{customdata[0]}<br>Teto: %{customdata[1]}<br>%{customdata[2]} do teto<br><i>clique para ver os lançamentos</i><extra></extra>",
        customdata=[[fmt_brl(v), fmt_brl(t) if t > 0 else "sem teto", f"{p:.0%}"] for v, t, p in zip(agg["Valor"], agg["Teto"], agg["Pct"])],
    ))
    fig.update_layout(
        title=titulo,
        height=max(300, 34 * len(agg) + 100),
        margin=dict(l=10, r=150, t=40, b=10),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#2C2C2A", size=12),
        xaxis=dict(title="", showgrid=True, gridcolor="rgba(128,128,128,0.18)"),
        yaxis=dict(title=""),
    )
    event = st.plotly_chart(fig_mobile(fig), use_container_width=True, key=key, on_select="rerun", config=PLOTLY_CONFIG)
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
    st.markdown(f"#### {categoria} — {len(df_cat)} lançamentos · {fmt_brl(total)}")
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
    Para meses futuros:
      - Caixa: parcelas de cartão já compradas (Data Caixa futura) + recorrentes ativas.
      - Competência: só recorrentes ativas (compras futuras ainda não existem).
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

        # Stack pra mostrar composição: Já lançado vs Recorrentes projetadas
        desp_lancada = 0.0
        desp_recorrente = 0.0
        rec_lancada = 0.0
        rec_recorrente = 0.0

        if is_atual:
            desp_lancada = desp_lanc
            rec_lancada = rec_lanc
            status = "🔄 Em andamento"
        elif comp < f"{hoje.month:02d}/{hoje.year}":  # mês passado
            desp_lancada = desp_lanc
            rec_lancada = rec_lanc
            status = "✅ Fechado"
        else:  # mês futuro
            # No modo Caixa: parcelas de cartão de compras passadas têm Data Caixa futura
            # e aparecem em lanc_mes. Somar com recorrentes projetadas.
            # No modo Competência: lanc_mes futuro normalmente = 0 (compras futuras não existem).
            desp_lancada = desp_lanc  # parcelas futuras (Caixa) ou lançamentos futuros manuais
            desp_recorrente = rec_despesa_mensal
            rec_lancada = rec_lanc
            rec_recorrente = rec_receita_mensal
            if modo == "Caixa" and desp_lanc > 0:
                status = f"📊 Projetado (parcelas {fmt_brl(desp_lanc)} + recorrentes)"
            else:
                status = "📊 Projetado"

        receita = rec_lancada + rec_recorrente
        despesa = desp_lancada + desp_recorrente

        pontos.append({
            "Mês": comp,
            "Receita": receita,
            "Despesa": despesa,
            "Saldo": receita - despesa,
            "Status": status,
            "Desp_Lancada": desp_lancada,
            "Desp_Recorrente": desp_recorrente,
        })

    df = pd.DataFrame(pontos)

    # Gráfico: barras agrupadas — Receita única + Despesa STACKED (parcelas/lançado + recorrente)
    fig = go.Figure()

    # Receita: 1 barra única
    fig.add_trace(go.Bar(
        x=df["Mês"], y=df["Receita"], name="Receita",
        marker_color=COR["receita"],
        text=[fmt_brl(v) for v in df["Receita"]], textposition="outside",
        offsetgroup="rec",
    ))
    # Despesa: stacked dentro do mesmo offsetgroup
    label_lancada = "Já lançado (parcelas + variáveis)" if modo == "Caixa" else "Já lançado"
    fig.add_trace(go.Bar(
        x=df["Mês"], y=df["Desp_Lancada"], name=label_lancada,
        marker_color=COR["despesa"],
        text=[fmt_brl(v) if v > 0 else "" for v in df["Desp_Lancada"]],
        textposition="inside",
        offsetgroup="desp",
    ))
    fig.add_trace(go.Bar(
        x=df["Mês"], y=df["Desp_Recorrente"], name="Recorrentes projetadas",
        marker_color=COR["despesa_escura"],
        text=[fmt_brl(v) if v > 0 else "" for v in df["Desp_Recorrente"]],
        textposition="inside",
        offsetgroup="desp",
    ))

    titulo_modo = "Caixa (quando entra/sai)" if modo == "Caixa" else "Competência (mês de pertencimento)"
    fig.update_layout(
        title=f"Receita × Despesa — próximos 6 meses · {titulo_modo}",
        barmode="relative",  # stacked dentro do mesmo offsetgroup, agrupado por offsetgroup
        height=460,
        margin=dict(l=10, r=10, t=60, b=10),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#2C2C2A", size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.18)"),
    )
    st.plotly_chart(fig_mobile(fig), use_container_width=True, config=PLOTLY_CONFIG)

    # Tabela detalhada
    df_display = df[["Mês", "Receita", "Despesa", "Desp_Lancada", "Desp_Recorrente", "Saldo", "Status"]].copy()
    df_display = df_display.rename(columns={
        "Desp_Lancada": "Já lançado",
        "Desp_Recorrente": "Recorrentes proj.",
    })
    for col in ["Receita", "Despesa", "Já lançado", "Recorrentes proj.", "Saldo"]:
        df_display[col] = df_display[col].apply(fmt_brl)
    with st.expander("Ver detalhamento dos próximos 6 meses"):
        st.dataframe(df_display, hide_index=True, use_container_width=True)
        if modo == "Caixa":
            st.caption(
                "**Em andamento**: o que já foi lançado este mês (parcial). "
                "**Projetado (Caixa)**: parcelas de cartão de compras passadas que vencem no mês futuro + recorrentes ativas. "
                "Compras futuras com cartão ainda não feitas NÃO aparecem (pois não existem na planilha)."
            )
        else:
            st.caption(
                "**Em andamento**: só inclui o que já foi lançado este mês. "
                "**Projetado (Competência)**: receitas e despesas recorrentes ativas. "
                "Compras avulsas futuras não aparecem."
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
        st.metric("Despesa fixa", fmt_brl(fixa), delta=f"{pct_fixa*100:.0f}% do total")
        st.caption("Recorrentes: aluguel, escola, assinaturas...")
    with col2:
        st.metric("Despesa variável", fmt_brl(variavel), delta=f"{pct_var*100:.0f}% do total")
        st.caption("Discricionário: mercado, lazer, eventual...")
    with col3:
        # Barra empilhada horizontal
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=["Composição"], x=[fixa], name="Fixa",
            orientation="h", marker_color=COR["neutro"],
            text=f"{fmt_brl(fixa)} ({pct_fixa*100:.0f}%)",
            textposition="inside", insidetextanchor="middle",
            hovertemplate="<b>Fixa</b><br>R$ %{x:,.2f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            y=["Composição"], x=[variavel], name="Variável",
            orientation="h", marker_color=COR["flexivel"],
            text=f"{fmt_brl(variavel)} ({pct_var*100:.0f}%)",
            textposition="inside", insidetextanchor="middle",
            hovertemplate="<b>Variável</b><br>R$ %{x:,.2f}<extra></extra>",
        ))
        fig.update_layout(
            barmode="stack",
            height=120,
            margin=dict(l=10, r=10, t=10, b=10),
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#2C2C2A", size=12),
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False),
        )
        event = st.plotly_chart(fig_mobile(fig), use_container_width=True, key=key, on_select="rerun", config=PLOTLY_CONFIG)
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
    total = df["Valor"].sum()
    st.markdown(f"#### Despesas {tipo.lower()}s — {len(df)} lançamentos · {fmt_brl(total)}")

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

    # Filtra categorias sem gasto em nenhum mês (deixa visual limpo)
    pivot_filtrado = pivot[pivot.sum(axis=1) > 0]
    pct_filtrado = pct.loc[pivot_filtrado.index]

    st.markdown(f"#### Evolução mensal por categoria — {modo}")
    st.caption("texto cinza = sem teto · verde até 60% · âmbar 60-80% · laranja 80-100% · vermelho >100%")

    # Monta dataframe formatado pra st.dataframe com cores no TEXTO (sem fundo)
    df_tabela = pd.DataFrame(index=pivot_filtrado.index, columns=pivot_filtrado.columns)
    for cat in pivot_filtrado.index:
        for mes in pivot_filtrado.columns:
            v = pivot_filtrado.loc[cat, mes]
            df_tabela.loc[cat, mes] = float(v)

    def color_pct(val, cat_idx, mes_col):
        try:
            p = pct_filtrado.loc[cat_idx, mes_col]
        except Exception:
            p = 0
        if p == 0 or val == 0:
            return "color: #B4B2A9;"  # cinza claro pros zeros
        if p < 0.6:
            return "color: #1D9E75; font-weight: 500;"  # verde
        if p < 0.8:
            return "color: #BA7517; font-weight: 500;"  # âmbar
        if p < 1.0:
            return "color: #D85A30; font-weight: 500;"  # laranja
        return "color: #A32D2D; font-weight: 600;"  # vermelho >100%

    def style_row(row):
        return [color_pct(row[col], row.name, col) for col in row.index]

    styled = (
        df_tabela.style
        .apply(style_row, axis=1)
        .format(lambda v: fmt_brl(v) if v else "—")
        .set_properties(**{"text-align": "right"})
    )
    st.dataframe(styled, use_container_width=True, height=min(600, 40 + 35 * len(pivot_filtrado.index)))

    # Linha de total despesa × receita por mês (overview)
    receitas = df_lancamentos[df_lancamentos["Tipo"] == "Receita"]
    despesas_total = pivot.sum(axis=0)
    receitas_total = receitas.groupby(coluna_mes)["Valor"].sum().reindex(meses, fill_value=0)
    saldo_total = receitas_total - despesas_total

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=meses, y=receitas_total, name="Receita", marker_color=COR["receita"]))
    fig2.add_trace(go.Bar(x=meses, y=despesas_total, name="Despesa", marker_color=COR["despesa"]))
    fig2.add_trace(go.Scatter(
        x=meses, y=saldo_total,
        name="Saldo", mode="lines+markers+text",
        line=dict(color=COR["investimento"], width=3),
        marker=dict(size=10),
        text=[fmt_brl(v) for v in saldo_total],
        textposition="top center",
    ))
    fig2.update_layout(
        title=f"Receita × Despesa × Saldo (últimos {n_meses} meses)",
        barmode="group",
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#2C2C2A", size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.18)"),
    )
    st.plotly_chart(fig_mobile(fig2), use_container_width=True, config=PLOTLY_CONFIG)


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
