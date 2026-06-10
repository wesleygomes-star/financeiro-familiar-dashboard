"""Visão Geral — painel principal v4 (família, sem 'Casal', com auditoria)."""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import (
    aportes_historico,
    auditar_contas_fixas,
    compromissos_proximos_meses,
    fatura_estimada,
    kpis_familia,
    load_faturas,
    load_lancamentos,
    load_recorrentes,
    load_saldo_investido,
    meses_disponiveis,
    saldo_estocado_atual,
    split_movimentos,
)


st.set_page_config(page_title="Visão Geral", page_icon="💰", layout="wide")

# Auth
if "auth_ok" not in st.session_state:
    senha = st.text_input("🔐 Senha", type="password")
    if senha == st.secrets.get("auth", {}).get("password", "familia2026"):
        st.session_state["auth_ok"] = True
        st.rerun()
    elif senha:
        st.error("Senha incorreta")
    st.stop()


def fmt(v: float, com_cifrao: bool = True) -> str:
    s = f"{abs(v):,.0f}".replace(",", ".")
    sinal = "-" if v < 0 else ""
    return f"{sinal}R$ {s}" if com_cifrao else f"{sinal}{s}"


# ============== Carregar dados ==============
df_lanc = load_lancamentos(incluir_cancelados=False)
df_rec = load_recorrentes()
df_faturas = load_faturas()
df_saldo = load_saldo_investido()

# ============== Header + filtros ==============
st.title("💰 Visão Geral")

c_filtro, c_modo, c_refresh = st.columns([2, 2, 1])
meses_caixa = meses_disponiveis(df_lanc, modo="Caixa")
meses_comp = meses_disponiveis(df_lanc, modo="Competência")
meses_lista = meses_caixa or meses_comp or [f"{datetime.now().month:02d}/{datetime.now().year}"]
mes_corrente = f"{datetime.now().month:02d}/{datetime.now().year}"
idx_default = meses_lista.index(mes_corrente) if mes_corrente in meses_lista else 0

with c_filtro:
    competencia = st.selectbox("Mês", meses_lista, index=idx_default)
with c_modo:
    modo = st.radio("Visão", ["Caixa", "Competência"], horizontal=True, index=0,
                    help="Caixa: quando o $ sai (vencimento da fatura). Competência: data da compra.")
with c_refresh:
    st.write("")  # espaço
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ============== KPIs (4 cards) ==============
kpis = kpis_familia(df_lanc, df_saldo, competencia, modo=modo)

st.subheader("Indicadores do mês")

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric("Receita família", fmt(kpis["receita_total"]))
    for p, v in kpis["receita_por_pessoa"].items():
        st.caption(f"{p}: {fmt(v)}")

with k2:
    st.metric("Gastos família", fmt(kpis["despesa_total"]))
    for p, v in kpis["despesa_por_pessoa"].items():
        st.caption(f"{p}: {fmt(v)}")

with k3:
    aporte = kpis["aporte_total"]
    estocado = kpis["saldo_estocado_total"]
    if aporte == 0 and estocado == 0:
        st.markdown("**📈 Investido**")
        st.info("Categoria Investimentos ainda não rastreada", icon="💡")
        st.caption("➕ Lançar 1º aporte · 👁 Ver histórico ↓")
    else:
        st.metric("Investido", fmt(aporte) if aporte > 0 else "—", help="Aporte do mês")
        if aporte > 0:
            for p, v in kpis["aporte_por_pessoa"].items():
                st.caption(f"{p}: {fmt(v)}")
        if estocado > 0:
            st.caption(f"📦 Saldo estocado: **{fmt(estocado)}**")
        else:
            st.caption("📦 Saldo estocado: preencher aba `Saldo Investido`")

with k4:
    # Faturas pendentes
    if not df_faturas.empty and "Status" in df_faturas.columns:
        pend = df_faturas[df_faturas["Status"].astype(str).str.lower() == "pendente"]
        if not pend.empty and "Vencimento_dt" in pend.columns:
            hoje = pd.Timestamp(datetime.now().date())
            pend = pend.assign(_dias=(pend["Vencimento_dt"] - hoje).dt.days)
            pend = pend[(pend["_dias"] >= -30) & (pend["_dias"] <= 30)].sort_values("_dias")
            total_pend = float(pend["Total_num"].fillna(0).sum()) if "Total_num" in pend.columns else 0
            st.metric("Faturas a debitar", fmt(total_pend) if total_pend > 0 else "—")
            for _, r in pend.head(5).iterrows():
                d = int(r["_dias"])
                txt = f"venceu há {abs(d)}d" if d < 0 else (f"em {d}d" if d > 0 else "HOJE")
                emoji = "🔴" if d < 0 else ("🟠" if d <= 5 else "🟡")
                cartao = str(r.get("Cartão", "?"))[:24]
                st.caption(f"{emoji} {cartao} — {txt}")
        else:
            st.metric("Faturas a debitar", "—")
            st.caption("Nenhuma janela 30d")
    else:
        st.metric("Faturas", "—")

st.divider()

# ============== Caixa × Competência ==============
st.subheader("Caixa × competência")

splits_caixa = split_movimentos(df_lanc[df_lanc["Mês Caixa"] == competencia]) if "Mês Caixa" in df_lanc.columns else {"despesas": pd.DataFrame()}
splits_comp = split_movimentos(df_lanc[df_lanc["Competência"] == competencia]) if "Competência" in df_lanc.columns else {"despesas": pd.DataFrame()}

caixa_total = float(splits_caixa["despesas"]["Valor"].sum()) if not splits_caixa["despesas"].empty else 0.0
comp_total = float(splits_comp["despesas"]["Valor"].sum()) if not splits_comp["despesas"].empty else 0.0
empurrado = comp_total - caixa_total

cc1, cc2, cc3 = st.columns(3)
with cc1.container(border=True):
    st.caption("🪙 **Caixa do mês**")
    st.subheader(fmt(caixa_total))
    st.caption("o que saiu em $ esse mês (vencimentos+débitos)")
with cc2.container(border=True):
    st.caption("📅 **Competência do mês**")
    st.subheader(fmt(comp_total))
    st.caption("o que foi decidido (data da compra)")
with cc3.container(border=True):
    cor = "🟠" if empurrado > 0 else "🟢"
    st.caption(f"{cor} **Empurrado pro futuro**")
    st.subheader(fmt(empurrado))
    st.caption("parcelas que vão pesar próximos meses" if empurrado > 0 else "tudo decidido foi pago")

st.divider()

# ============== Contas Fixas — Auditoria ==============
st.subheader("Contas fixas · auditoria de pagamento")

audit = auditar_contas_fixas(df_lanc, df_rec, competencia)
if audit.empty:
    st.info("Sem recorrentes cadastrados (aba Recorrentes vazia ou sem Ativo='Sim').")
else:
    # Detecta se TODAS as recorrentes têm o mesmo Dia Cobrança (sinal de placeholder não revisado)
    dias_unicos = audit["Dia Cobrança"].nunique()
    todos_dia_5 = (dias_unicos == 1 and int(audit["Dia Cobrança"].iloc[0]) == 5)

    if todos_dia_5:
        # Mostra banner + funde Atrasada em Pendente (sem distinção até Wesley revisar)
        col_warn, col_btn = st.columns([5, 1])
        with col_warn:
            st.warning(
                f"**{len(audit)} das {len(audit)} recorrentes estão como Dia Cobrança = 5** — "
                "enquanto isso, _atrasada_ vs _pendente_ ficam indistinguíveis. "
                "Status \"Atrasada\" volta automático quando você corrigir os Dias.",
                icon="📅",
            )
        with col_btn:
            if st.button("Revisar agora", key="rev_dias", use_container_width=True):
                st.session_state["revisar_dias"] = True
        audit_show = audit.copy()
        audit_show.loc[audit_show["Status"] == "Atrasada", "Status"] = "Pendente"
    else:
        audit_show = audit

    pagas = audit_show[audit_show["Status"] == "Paga"]
    pend = audit_show[audit_show["Status"] == "Pendente"]
    atras = audit_show[audit_show["Status"] == "Atrasada"]

    if todos_dia_5:
        cs1, cs2, cs3 = st.columns(3)
        cs1.metric("✅ Pagas", len(pagas), fmt(float(pagas["Valor Pago"].sum())) if not pagas.empty else "R$ 0")
        cs2.metric("⏳ Pendentes", len(pend), fmt(float(pend["Valor Esperado"].sum())) if not pend.empty else "R$ 0")
        total_esp = float(audit_show["Valor Esperado"].sum())
        total_pago = float(audit_show["Valor Pago"].sum())
        pct = (total_pago / total_esp * 100) if total_esp > 0 else 0
        cs3.metric("Esperado / pago", fmt(total_esp), f"{pct:.0f}% pago")
    else:
        cs1, cs2, cs3, cs4 = st.columns(4)
        cs1.metric("✅ Pagas", len(pagas), fmt(float(pagas["Valor Pago"].sum())) if not pagas.empty else "R$ 0")
        cs2.metric("⏳ Pendentes", len(pend), fmt(float(pend["Valor Esperado"].sum())) if not pend.empty else "R$ 0")
        cs3.metric("🔴 Atrasadas", len(atras), fmt(float(atras["Valor Esperado"].sum())) if not atras.empty else "R$ 0")
        total_esp = float(audit_show["Valor Esperado"].sum())
        total_pago = float(audit_show["Valor Pago"].sum())
        pct = (total_pago / total_esp * 100) if total_esp > 0 else 0
        cs4.metric("Esperado / pago", fmt(total_esp), f"{pct:.0f}% pago")

    # Lista ordenada: atrasadas → pendentes → pagas
    audit_sort = audit_show.copy()
    audit_sort["_ord"] = audit_sort["Status"].map({"Atrasada": 0, "Pendente": 1, "Paga": 2})
    audit_sort = audit_sort.sort_values(["_ord", "Dia Cobrança"]).drop(columns=["_ord"])

    with st.expander(f"📋 Detalhe das {len(audit_show)} contas fixas", expanded=False):
        st.dataframe(
            audit_sort[["Status", "Descrição", "Categoria", "Pessoa Esperada", "Valor Esperado", "Dia Cobrança", "Data Pagamento", "Pessoa Pagou", "Valor Pago"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Valor Esperado": st.column_config.NumberColumn(format="R$ %.0f"),
                "Valor Pago": st.column_config.NumberColumn(format="R$ %.0f"),
            },
        )

st.divider()

# ============== Faturas em aberto + auditoria ==============
st.subheader("Faturas em aberto · auditoria fatura × lançamentos")
if df_faturas.empty:
    st.info("Aba Faturas vazia.")
else:
    pend_f = df_faturas[df_faturas["Status"].astype(str).str.lower() == "pendente"]
    if not pend_f.empty and "Vencimento_dt" in pend_f.columns:
        hoje = pd.Timestamp(datetime.now().date())
        pend_f = pend_f.assign(_dias=(pend_f["Vencimento_dt"] - hoje).dt.days)
        pend_f = pend_f[(pend_f["_dias"] >= -30) & (pend_f["_dias"] <= 30)].sort_values("_dias")

        for _, r in pend_f.iterrows():
            cartao = str(r.get("Cartão", "?"))
            mes_ref = str(r.get("Mês Referência", "?"))
            d = int(r["_dias"])
            total = float(r.get("Total_num", 0))
            audit_st = str(r.get("Status Auditoria", "")).strip()

            # Estima valor + conta lançamentos
            total_estimado, qtd_lanc = fatura_estimada(cartao, mes_ref, df_lanc)

            label_prazo = f"venceu há {abs(d)}d" if d < 0 else (f"em {d}d" if d > 0 else "HOJE")
            emoji = "🔴" if d < 0 else ("🟠" if d <= 5 else "🟡" if d <= 15 else "⚪")

            with st.container(border=True):
                cf1, cf2, cf3 = st.columns([3, 2, 1])
                with cf1:
                    st.markdown(f"**{emoji} {cartao} · {mes_ref}**")
                    st.caption(f"vence {r.get('Vencimento','?')} · {label_prazo}")
                    if audit_st:
                        st.caption(f"🔍 auditoria: {audit_st}")
                    else:
                        st.caption(f"⏳ aguardando fatura · **{qtd_lanc} lançamentos individuais** no Zap")
                with cf2:
                    if total > 0:
                        st.metric("Total fatura", fmt(total), help="total real reconciliado")
                        st.caption("total real reconciliado")
                    elif total_estimado > 0:
                        st.metric("Total fatura", f"~ {fmt(total_estimado)}", help="estimado pelos lançamentos individuais")
                        st.caption(f"_estimado de {qtd_lanc} lançamentos_")
                    else:
                        st.caption("fatura ainda não carregada · sem lançamentos pra estimar")
                with cf3:
                    st.write("")
                    st.write("")
                    if st.button("Abrir", key=f"open_{cartao}_{mes_ref}"):
                        st.session_state["fatura_open"] = f"{cartao}|{mes_ref}"
    else:
        st.success("✅ Nenhuma fatura pendente nos próximos 30 dias.")

st.divider()

# ============== Drill-down Investimentos ==============
expanded_inv = (kpis["aporte_total"] == 0 and kpis["saldo_estocado_total"] == 0)
with st.expander("📈 Drill-down · Investimentos da família", expanded=expanded_inv):
    st.caption("aporte mensal + saldo estocado + rendimento (calculado entre snapshots)")

    di1, di2, di3 = st.columns(3)
    with di1.container(border=True):
        st.caption("**Aporte do mês**")
        if kpis["aporte_total"] > 0:
            st.markdown(f"### {fmt(kpis['aporte_total'])}")
            for p, v in kpis["aporte_por_pessoa"].items():
                st.caption(f"{p}: {fmt(v)}")
        else:
            st.markdown(":blue[aguardando 1º lançamento]")
    with di2.container(border=True):
        st.caption("**Saldo estocado**")
        if kpis["saldo_estocado_total"] > 0:
            st.markdown(f"### {fmt(kpis['saldo_estocado_total'])}")
            for p, v in kpis["saldo_estocado"].items():
                st.caption(f"{p}: {fmt(v)}")
        else:
            st.markdown("preencher aba `Saldo Investido`")
    with di3.container(border=True):
        st.caption("**Rendimento 12m**")
        if len(df_saldo) >= 2:
            # cálculo simples: saldo atual - saldo mais antigo - soma de aportes desde então
            st.markdown("calcular…")
        else:
            st.markdown("precisa ≥ 2 snapshots")

    # Histórico de aportes
    hist = aportes_historico(df_lanc)
    if not hist.empty:
        st.markdown("**Aportes por mês**")
        pivot = hist.pivot_table(index="Competência", columns="Pessoa", values="Valor", aggfunc="sum").fillna(0)
        st.bar_chart(pivot, height=200)

        with st.expander("Tabela completa", expanded=False):
            st.dataframe(
                hist.sort_values("Competência", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={"Valor": st.column_config.NumberColumn(format="R$ %.0f")},
            )
    else:
        st.caption("— sem lançamentos de aporte ainda —")

    cta1, cta2 = st.columns(2)
    cta1.info("💬 No Zap, mande: `aporte 5000 CDB XP` pra registrar")
    cta2.info("📊 Atualize a aba `Saldo Investido` pra ver saldo estocado aqui")

st.divider()

# ============== Compromissos próximos 6 meses ==============
st.subheader("Compromissos contraídos · próximos 6 meses")
st.caption("O que já está no caixa antes do mês começar — barras empilhadas = compromisso total, linha verde = receita projetada (média 3m).")

cron = compromissos_proximos_meses(df_lanc, df_rec, df_faturas, n_meses=6, partir_de=competencia)
if cron.empty:
    st.info("Sem dados suficientes pra projeção.")
else:
    # Receita projetada = média dos últimos 3 meses
    receita_proj = 0.0
    if "Competência" in df_lanc.columns and not df_lanc.empty:
        receitas = df_lanc[df_lanc["Tipo"].astype(str).str.lower() == "receita"]
        if not receitas.empty:
            por_mes = receitas.groupby("Competência")["Valor"].sum().tail(3)
            if not por_mes.empty:
                receita_proj = float(por_mes.mean())

    fig = go.Figure()
    fig.add_bar(name="Parcelas em curso", x=cron["Mês"], y=cron["Parcelas em curso"], marker_color="#888780")
    fig.add_bar(name="Contas fixas", x=cron["Mês"], y=cron["Contas fixas"], marker_color="#B4B2A9")
    fig.add_bar(name="Faturas em aberto", x=cron["Mês"], y=cron["Faturas em aberto"], marker_color="#EF9F27")
    if receita_proj > 0:
        fig.add_scatter(name="Receita projetada", x=cron["Mês"], y=[receita_proj] * len(cron),
                        mode="lines", line=dict(color="#1D9E75", width=2, dash="dash"))
    fig.update_layout(
        barmode="stack",
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="R$",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Mini cards de saldo livre por mês
    if receita_proj > 0:
        cols = st.columns(len(cron))
        for i, (_, r) in enumerate(cron.iterrows()):
            livre = receita_proj - r["Total"]
            cor = "normal" if livre >= 0 else "inverse"
            cols[i].metric(f"livre {r['Mês'][:2]}", fmt(livre), delta_color=cor)

st.divider()

# ============== Contribuição individual ==============
st.subheader("Contribuição individual")
ci1, ci2 = st.columns(2)
for col, pessoa in zip([ci1, ci2], ["Wesley", "Sabrina"]):
    with col.container(border=True):
        rec = kpis["receita_por_pessoa"].get(pessoa, 0)
        desp = kpis["despesa_por_pessoa"].get(pessoa, 0)
        apo = kpis["aporte_por_pessoa"].get(pessoa, 0)
        saldo = rec - desp - apo
        taxa = (saldo / rec * 100) if rec > 0 else 0

        st.markdown(f"### {pessoa}")
        st.write(f"⬆️ Receita: **{fmt(rec)}**")
        st.write(f"⬇️ Gastos: **{fmt(desp)}**")
        st.write(f"📈 Investido: **{fmt(apo) if apo > 0 else '—'}**")
        st.write(f"💰 Saldo: **{fmt(saldo)}**")
        if rec > 0:
            st.progress(min(max(taxa / 100, 0), 1.0), text=f"Taxa de poupança: {taxa:.0f}%")

st.caption("ℹ️ Metas serão calibradas após carregar histórico Jan-Mai 2026.")
