"""Visão Geral — painel principal v3 (redesign 16/06: hero, baldes, metas, patrimônio).

Combina o melhor dos benchmarks: hero 'livre pra gastar' (Finanzguru/Rocket),
transferência ≠ gasto (Copilot), 3 baldes + projeção (Monarch).
set_page_config + auth ficam no router (streamlit_app.py).
"""
import re
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import (
    auditar_contas_fixas,
    classificar_baldes,
    compromissos_proximos_meses,
    fatura_estimada,
    fatura_split_pessoa,
    kpis_familia,
    livre_para_gastar,
    load_faturas,
    load_lancamentos,
    load_metas,
    load_recorrentes,
    load_saldo_investido,
    meta_valor,
    meses_disponiveis,
    rendimento_investido,
    split_movimentos,
)

st.markdown(
    """
    <style>
    .block-container { max-width: 100% !important; padding-top: 1rem !important; }
    .hero { background: var(--background-color, #fff); border: 2px solid rgba(55,138,221,0.35);
            border-radius: 16px; padding: 22px; text-align: center; margin-bottom: 14px; }
    .hero-num { font-size: 42px; font-weight: 500; line-height: 1.05; margin: 4px 0; }
    .hero-calc { font-size: 11px; opacity: 0.65; }
    .kgrid { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 18px; }
    .kc { background: rgba(128,128,128,0.08); border-radius: 8px; padding: 12px 14px; }
    .kc-l { font-size: 11px; opacity: 0.7; }
    .kc-v { font-size: 18px; font-weight: 500; margin-top: 2px; }
    .kc-s { font-size: 10px; opacity: 0.6; }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 18px; }
    .gcard { border: 0.5px solid rgba(128,128,128,0.25); border-radius: 12px; padding: 13px 15px; }
    .balde-bar { height: 7px; background: rgba(128,128,128,0.2); border-radius: 4px; margin-top: 7px; }
    .balde-fill { height: 100%; border-radius: 4px; }
    @media (max-width: 768px) {
      .kgrid { grid-template-columns: 1fr 1fr !important; }
      .grid2 { grid-template-columns: 1fr !important; }
      .hero-num { font-size: 34px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt(v: float) -> str:
    s = f"{abs(v):,.0f}".replace(",", ".")
    return ("-" if v < 0 else "") + f"R$ {s}"


# ============== Dados ==============
df_lanc = load_lancamentos(False)
df_rec = load_recorrentes()
df_faturas = load_faturas()
df_saldo = load_saldo_investido()
df_metas = load_metas()

# ============== Header ==============
c1, c2, c3 = st.columns([2, 2, 1])
meses = meses_disponiveis(df_lanc, "Caixa") or meses_disponiveis(df_lanc, "Competência") or [f"{datetime.now().month:02d}/{datetime.now().year}"]
mes_atual = f"{datetime.now().month:02d}/{datetime.now().year}"
idx = meses.index(mes_atual) if mes_atual in meses else 0
with c1:
    st.markdown("### Família Gomes")
with c2:
    competencia = st.selectbox("Mês", meses, index=idx, label_visibility="collapsed")
with c3:
    if st.button("🔄", use_container_width=True, help="Atualizar dados"):
        st.cache_data.clear(); st.rerun()

# ============== Hero: livre pra gastar ==============
lpg = livre_para_gastar(df_lanc, df_rec, df_faturas, df_saldo, competencia)
livre = lpg["livre"]
cor_livre = "var(--color-text-success)" if livre >= 0 else "var(--color-text-danger)"
st.markdown(
    f"""
    <div class="hero">
      <div style="font-size:13px; opacity:0.7;">livre pra gastar este mês</div>
      <div class="hero-num" style="color:{cor_livre};">{fmt(livre)}</div>
      <div class="hero-calc">entrou {fmt(lpg['receita'])} − fixas {fmt(lpg['fixas'])} − faturas {fmt(lpg['faturas_pagar'])} − já gastei {fmt(lpg['flex_gasto'])}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============== KPIs ==============
k = kpis_familia(df_lanc, df_saldo, competencia, "Competência")
estocado = k["saldo_estocado_total"]
aporte = k["aporte_total"]
st.markdown(
    f"""
    <div class="kgrid">
      <div class="kc"><div class="kc-l">entrou</div><div class="kc-v" style="color:var(--color-text-success);">{fmt(k['receita_total'])}</div></div>
      <div class="kc"><div class="kc-l">gastou</div><div class="kc-v">{fmt(k['despesa_total'])}</div></div>
      <div class="kc"><div class="kc-l">investiu (mês)</div><div class="kc-v" style="color:var(--color-text-info);">{fmt(aporte) if aporte>0 else '—'}</div><div class="kc-s">{'aporte 5000 cdb no zap' if aporte==0 else ''}</div></div>
      <div class="kc"><div class="kc-l">patrimônio</div><div class="kc-v">{fmt(estocado) if estocado>0 else '—'}</div><div class="kc-s">{'preencha Saldo Investido' if estocado==0 else ''}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============== Caixa × Competência ==============
caixa = kpis_familia(df_lanc, df_saldo, competencia, "Caixa")
empurrado = k["despesa_total"] - caixa["despesa_total"]
st.markdown(
    f"""
    <div class="grid2">
      <div class="gcard"><div style="font-size:12px;opacity:0.7;">🪙 saiu da conta (caixa)</div>
        <div style="font-size:20px;font-weight:500;">{fmt(caixa['despesa_total'])}</div>
        <div style="font-size:11px;opacity:0.6;">o que efetivamente saiu este mês</div></div>
      <div class="gcard"><div style="font-size:12px;opacity:0.7;">📅 consumo do mês (competência)</div>
        <div style="font-size:20px;font-weight:500;">{fmt(k['despesa_total'])}</div>
        <div style="font-size:11px;color:var(--color-text-success);">saldo do mês {fmt(k['saldo_mes'])}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============== Metas ==============
st.subheader("Metas")
st.caption("serão calibradas com o histórico do ano — edite na aba Metas")
mInvest = meta_valor(df_metas, "investir")
mPoup = meta_valor(df_metas, "poupança")
mFlex = meta_valor(df_metas, "flexível")
no_mes = df_lanc[df_lanc["Competência"] == competencia] if "Competência" in df_lanc.columns else df_lanc
baldes = classificar_baldes(split_movimentos(no_mes)["despesas"], df_rec)
flex_real = baldes["Flexível"]["total"]
poup_real = (k["saldo_mes"] / k["receita_total"] * 100) if k["receita_total"] > 0 else 0
mc1, mc2, mc3 = st.columns(3)
def meta_card(col, label, atual, alvo, sufixo, cor, melhor_maior=True):
    pct = (atual / alvo * 100) if alvo > 0 else 0
    pct_bar = min(pct, 100)
    ok = (atual >= alvo) if melhor_maior else (atual <= alvo)
    with col.container(border=True):
        st.caption(label)
        st.markdown(f"**{atual:,.0f}{sufixo}** / {alvo:,.0f}{sufixo}".replace(",", "."))
        st.progress(pct_bar / 100)
        st.caption(f"{'✅ ok' if ok else f'{pct:.0f}%'}")
meta_card(mc1, "investir / mês", aporte, mInvest, "", "info")
meta_card(mc2, "poupança", poup_real, mPoup, "%", "success")
meta_card(mc3, "teto flexível", flex_real, mFlex, "", "warning", melhor_maior=False)

# ============== Para onde foi (3 baldes com drill-down) ==============
st.subheader("Para onde foi")
st.caption("3 baldes em vez de 14 categorias — clique pra abrir o detalhe")
BALDE_META = {
    "Fixo": ("🔒 fixo · não muda", "#888780"),
    "Recorrente": ("🔁 recorrente / parcelas", "#BA7517"),
    "Flexível": ("☕ flexível · dá pra cortar", "#534AB7"),
}
tot_baldes = sum(baldes[b]["total"] for b in baldes) or 1
for b in ["Fixo", "Recorrente", "Flexível"]:
    label, cor = BALDE_META[b]
    total = baldes[b]["total"]
    pct = total / tot_baldes * 100
    with st.expander(f"{label} — {fmt(total)}", expanded=(b == "Flexível")):
        st.markdown(f'<div class="balde-bar"><div class="balde-fill" style="width:{pct:.0f}%;background:{cor};"></div></div>', unsafe_allow_html=True)
        st.write("")
        for it in baldes[b]["itens"]:
            cc1, cc2 = st.columns([3, 1])
            cc1.caption(it["desc"])
            cc2.caption(fmt(it["valor"]))

# ============== Investimentos & Patrimônio ==============
with st.expander("📈 Investimentos & patrimônio", expanded=(estocado == 0 and aporte == 0)):
    ic1, ic2, ic3 = st.columns(3)
    ic1.metric("aporte do mês", fmt(aporte) if aporte > 0 else "—")
    ic2.metric("saldo estocado", fmt(estocado) if estocado > 0 else "—")
    rend = rendimento_investido(df_saldo)
    ic3.metric("rendimento", f"+{rend['pct']:.1f}%" if rend else "—",
               help="precisa de ≥2 registros na aba Saldo Investido")
    if estocado == 0 and aporte == 0:
        st.info("💬 No Zap: `aporte 5000 CDB XP` registra investimento. Preencha a aba `Saldo Investido` pro patrimônio aparecer.")

# ============== Faturas (auditoria) ==============
st.subheader("Faturas · auditando lançamentos individuais")
if not df_faturas.empty and "Vencimento_dt" in df_faturas.columns:
    ab = df_faturas[df_faturas["Status"].astype(str).str.lower().isin(["pendente", "carregada"])].copy()
    hoje = pd.Timestamp(datetime.now().date())
    ab["_dias"] = (ab["Vencimento_dt"] - hoje).dt.days
    ab = ab[(ab["_dias"] >= -40) & (ab["_dias"] <= 35)].sort_values("_dias")
    for _, r in ab.iterrows():
        cartao = str(r.get("Cartão", "?")); mes_ref = str(r.get("Mês Referência", "?"))
        carregada = str(r.get("Status", "")).lower() == "carregada"
        total = float(r.get("Total_num", 0) or 0)
        venc = str(r.get("Vencimento", ""))
        if total <= 0:
            total, _q = fatura_estimada(cartao, mes_ref, df_lanc, vencimento=venc)
        d = int(r["_dias"])
        if carregada:
            cor_bg = "var(--color-background-success)"; cor_tx = "var(--color-text-success)"; ic = "✓"; status = "carregada · conciliada"
        elif d < 0:
            cor_bg = "var(--color-background-danger)"; cor_tx = "var(--color-text-danger)"; ic = "🔴"; status = f"venceu há {abs(d)}d"
        else:
            cor_bg = "var(--color-background-warning)"; cor_tx = "var(--color-text-warning)"; ic = "⏳"; status = f"vence em {d}d · aguardando fatura"
        val_txt = fmt(total) if (carregada or total > 0) else "—"
        prefixo = "" if carregada else "~ "
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:9px 12px;background:{cor_bg};border-radius:8px;margin-bottom:6px;font-size:13px;">'
            f'<span style="color:{cor_tx};">{ic} {cartao} · {mes_ref} <span style="opacity:0.8;font-size:11px;">{status}</span></span>'
            f'<span style="color:{cor_tx};font-weight:500;">{prefixo}{val_txt}</span></div>',
            unsafe_allow_html=True,
        )
else:
    st.info("Aba Faturas vazia.")

# ============== Contas fixas (alertas + projeção) ==============
st.subheader("Contas fixas · alertas e projeção")
audit = auditar_contas_fixas(df_lanc, df_rec, competencia)
if not audit.empty:
    dias_unicos = audit["Dia Cobrança"].nunique()
    pagas = audit[audit["Status"] == "Paga"]
    pend = audit[audit["Status"].isin(["Pendente", "Atrasada"])]
    fc1, fc2, fc3 = st.columns(3)
    fc1.metric("✅ pagas", len(pagas))
    fc2.metric("⏳ a confirmar", len(pend))
    fc3.metric("comprometido/mês", fmt(audit["Valor Esperado"].sum()))
    with st.expander(f"📋 {len(audit)} contas fixas — detalhe + dias de cobrança", expanded=False):
        audit_show = audit.sort_values("Dia Cobrança")
        st.dataframe(
            audit_show[["Status", "Descrição", "Valor Esperado", "Dia Cobrança", "Pessoa Pagou"]],
            use_container_width=True, hide_index=True,
            column_config={"Valor Esperado": st.column_config.NumberColumn(format="R$ %.0f")},
        )
    st.caption("o cadastro dispara os alertas (dia 10/15 no Zap) e alimenta a projeção abaixo")

# ============== Projeção ==============
st.subheader("Projeção de saldo livre")
cron = compromissos_proximos_meses(df_lanc, df_rec, df_faturas, 6, partir_de=competencia)
if not cron.empty:
    receita_proj = 0.0
    receitas = df_lanc[df_lanc["Tipo"].astype(str).str.lower() == "receita"]
    if not receitas.empty:
        por_mes = receitas.groupby("Competência")["Valor"].sum().tail(3)
        receita_proj = float(por_mes.mean()) if not por_mes.empty else 0
    fig = go.Figure()
    fig.add_bar(name="Parcelas", x=cron["Mês"], y=cron["Parcelas em curso"], marker_color="#888780")
    fig.add_bar(name="Contas fixas", x=cron["Mês"], y=cron["Contas fixas"], marker_color="#B4B2A9")
    fig.add_bar(name="Faturas", x=cron["Mês"], y=cron["Faturas em aberto"], marker_color="#EF9F27")
    if receita_proj > 0:
        fig.add_scatter(name="Receita projetada", x=cron["Mês"], y=[receita_proj] * len(cron),
                        mode="lines", line=dict(color="#1D9E75", width=2, dash="dash"))
    fig.update_layout(barmode="stack", height=280, margin=dict(l=10, r=10, t=10, b=10),
                      template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#2C2C2A", size=12),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("conforme as faturas grandes saem, sua folga cresce mês a mês")

# ============== Wesley vs Sabrina ==============
st.subheader("Quem movimenta o quê")
wc1, wc2 = st.columns(2)
for col, pessoa in zip([wc1, wc2], ["Wesley", "Sabrina"]):
    with col.container(border=True):
        rec = k["receita_por_pessoa"].get(pessoa, 0)
        desp = k["despesa_por_pessoa"].get(pessoa, 0)
        apo = k["aporte_por_pessoa"].get(pessoa, 0)
        saldo = rec - desp - apo
        st.markdown(f"**{pessoa}**")
        st.write(f"receita: **{fmt(rec) if rec>0 else '—'}**" + ("" if rec > 0 else " _(não lança)_"))
        st.write(f"gastos: **{fmt(desp)}**")
        if apo > 0:
            st.write(f"investido: **{fmt(apo)}**")
        st.write(f"saldo: **{fmt(saldo)}**")

st.caption("ℹ️ Faltam as 2 faturas Bradesco da Sabrina — os gastos dela estão subestimados até carregar.")
