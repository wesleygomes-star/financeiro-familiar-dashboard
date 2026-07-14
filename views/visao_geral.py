"""Visão Geral — v5 'Verde Premium' (mockup aprovado 02/07).

Cabeçalho imersivo verde com hero + cards flutuando por cima, KPIs 2×2 com
ícones SVG, metas em anéis de progresso, faturas com faixa de status.
set_page_config + auth ficam no router (streamlit_app.py).
"""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.components import COR, PLOTLY_CONFIG, barra_navegacao, fig_mobile, tema_verde_premium
from lib.data import (
    auditar_contas_fixas,
    is_rd,
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

# ============== Tema Verde Premium (compartilhado) ==============
tema_verde_premium()
barra_navegacao("inicio")
st.markdown(
    """<style>
    .block-container { max-width: 680px !important; padding-top: 0.9rem !important; position: relative !important; }
    /* seletor de mês vira o pill do hero (sobreposto no canto direito, ao lado do avatar).
       largura TRAVADA com !important — o stVerticalBlock nativo força 100% e o pill
       virava uma barra gigante no desktop */
    .st-key-mespill {
      position: absolute !important; top: 44px !important; right: 64px !important;
      width: 126px !important; min-width: 126px !important; max-width: 126px !important;
      left: auto !important; z-index: 20;
    }
    .st-key-mespill div[data-testid="stSelectbox"],
    .st-key-mespill [data-baseweb="select"] { width: 126px !important; max-width: 126px !important; }
    .st-key-mespill div[data-testid="stSelectbox"] > div > div {
      background: rgba(7,56,44,0.55) !important; border: 1px solid rgba(255,255,255,0.28) !important;
      border-radius: 999px !important; min-height: 32px; height: 32px;
    }
    .st-key-mespill div[data-testid="stSelectbox"] * { color: #EAF7F0 !important; font-size: 12px !important; }
    .st-key-mespill svg { fill: #EAF7F0 !important; }
    </style>""",
    unsafe_allow_html=True,
)


def fmt(v: float) -> str:
    s = f"{abs(v):,.0f}".replace(",", ".")
    return ("-" if v < 0 else "") + f"R$ {s}"


def fmt_mil(v: float) -> str:
    """R$ compacto pros chips: 63,9 mil."""
    if abs(v) >= 1000:
        return f"{v/1000:,.1f}".replace(".", ",") + " mil"
    return f"{v:,.0f}".replace(",", ".")


# ============== Dados ==============
df_lanc = load_lancamentos(False)
df_rec = load_recorrentes()
df_faturas = load_faturas()
df_saldo = load_saldo_investido()
df_metas = load_metas()

# ============== Seletor de mês (pill) ==============
_todos = set(meses_disponiveis(df_lanc, "Competência")) | set(meses_disponiveis(df_lanc, "Caixa"))
mes_atual = f"{datetime.now().month:02d}/{datetime.now().year}"
_todos.add(mes_atual)
def _key(c):
    try:
        m, y = c.split("/"); return int(y) * 100 + int(m)
    except Exception:
        return 0
_hoje = datetime.now().year * 100 + datetime.now().month
_passados = sorted([c for c in _todos if _key(c) <= _hoje], key=_key, reverse=True)
_futuros = sorted([c for c in _todos if _key(c) > _hoje], key=_key)
meses = _passados + _futuros
_NOMES = {"01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai", "06": "jun",
          "07": "jul", "08": "ago", "09": "set", "10": "out", "11": "nov", "12": "dez"}
def _label(c):
    try:
        m, y = c.split("/"); return f"{_NOMES.get(m, m)}/{y}" + ("  ·  futuro" if _key(c) > _hoje else "")
    except Exception:
        return c
# o widget fica no fluxo do código AQUI, mas o CSS o posiciona DENTRO do hero
# (canto superior direito, estilo pill do mockup)
with st.container(key="mespill"):
    competencia = st.selectbox("Mês", meses, index=0, format_func=_label, label_visibility="collapsed")

# ============== Cálculos ==============
lpg = livre_para_gastar(df_lanc, df_rec, df_faturas, df_saldo, competencia)
livre = lpg["livre"]
k = kpis_familia(df_lanc, df_saldo, competencia, "Competência")
caixa = kpis_familia(df_lanc, df_saldo, competencia, "Caixa")
estocado = k["saldo_estocado_total"]
aporte = k["aporte_total"]

# sparkline: saldo (receita−despesa) dos últimos 6 meses fechados + selecionado
_spark_pts = ""
try:
    _meses_hist = [c for c in _passados if _key(c) <= _key(competencia)][:6][::-1]
    _saldos = []
    for c in _meses_hist:
        mm = df_lanc[df_lanc["Competência"] == c]
        r = mm[mm["Tipo"].astype(str).str.lower() == "receita"]["Valor"].sum()
        d = mm[mm["Tipo"].astype(str).str.lower() == "despesa"]["Valor"].sum()
        _saldos.append(float(r - d))
    if len(_saldos) >= 3:
        lo, hi = min(_saldos), max(_saldos)
        rng = (hi - lo) or 1.0
        n = len(_saldos)
        pts = [
            f"{2 + i * (112 / (n - 1)):.0f},{38 - (v - lo) / rng * 30:.0f}"
            for i, v in enumerate(_saldos)
        ]
        _ult = pts[-1].split(",")
        _spark_pts = (
            f'<svg class="h5-spark" viewBox="0 0 118 44" aria-hidden="true">'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="rgba(255,255,255,0.55)" '
            f'stroke-width="2" stroke-linecap="round"/>'
            f'<circle cx="{_ult[0]}" cy="{_ult[1]}" r="3.5" fill="#7CE0B8"/></svg>'
        )
except Exception:
    _spark_pts = ""

# contas fixas + próxima fatura (pros KPIs)
audit = auditar_contas_fixas(df_lanc, df_rec, competencia)
n_pagas = int((audit["Status"] == "Paga").sum()) if not audit.empty else 0
n_fixas = len(audit)

_prox_fat_txt, _prox_fat_val = "—", ""
ab = pd.DataFrame()
if not df_faturas.empty and "Vencimento_dt" in df_faturas.columns:
    ab = df_faturas[df_faturas["Status"].astype(str).str.lower().isin(["pendente", "carregada"])].copy()
    hoje_ts = pd.Timestamp(datetime.now().date())
    ab["_dias"] = (ab["Vencimento_dt"] - hoje_ts).dt.days
    ab = ab[(ab["_dias"] >= -40) & (ab["_dias"] <= 35)].sort_values("_dias")
    pend = ab[ab["Status"].astype(str).str.lower() != "carregada"]
    if not pend.empty:
        r0 = pend.iloc[0]
        _c0 = str(r0.get("Cartão", "?"))
        _t0 = float(r0.get("Total_num", 0) or 0)
        if _t0 <= 0:
            _t0, _ = fatura_estimada(_c0, str(r0.get("Mês Referência", "")), df_lanc, vencimento=str(r0.get("Vencimento", "")))
        _d0 = int(r0["_dias"])
        _prox_fat_val = ("~" if float(r0.get("Total_num", 0) or 0) <= 0 else "") + fmt(_t0) if _t0 > 0 else "—"
        _prox_fat_txt = f"{_c0} · " + (f"vence em {_d0}d" if _d0 >= 0 else f"venceu há {abs(_d0)}d")

# ============== Hero ==============
_h = datetime.now().hour
saud = "bom dia" if _h < 12 else ("boa tarde" if _h < 18 else "boa noite")
sinal = '<span class="mais">+</span>' if livre >= 0 else '<span class="menos">−</span>'
st.markdown(
    f"""
    <div class="hero5">
      <div class="h5-bar">
        <div><div class="h5-ola">{saud},</div><div class="h5-nome">Família Gomes</div></div>
        <div class="h5-right"><span class="h5-av">WG</span></div>
      </div>
      <div class="h5-rot">livre pra gastar</div>
      <div class="h5-num">{sinal}R$ {f"{abs(livre):,.0f}".replace(",", ".")}</div>
      <div class="h5-chips">
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#7CE0B8" stroke-width="2.2"><path d="M8 13V3M4 7l4-4 4 4"/></svg>entrou {fmt_mil(k['receita_total'])}</span>
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#FFAFA8" stroke-width="2.2"><path d="M8 3v10M4 9l4 4 4-4"/></svg>gastou {fmt_mil(k['despesa_total'])}</span>
      </div>
      {_spark_pts}
    </div>
    """,
    unsafe_allow_html=True,
)

with st.popover("ver a conta do mês"):
    _cor_livre_pop = COR["receita"] if livre >= 0 else COR["despesa"]
    st.markdown(
        f"""
        <div style="min-width:280px">
          <div class="brow"><span class="bl">entrou</span><span class="bv" style="color:{COR['receita']}">{fmt(lpg['receita'])}</span></div>
          <div class="brow"><span class="bl">contas fixas</span><span class="bv">−{fmt(lpg['fixas'])}</span></div>
          <div class="brow"><span class="bl">faturas a pagar</span><span class="bv">−{fmt(lpg['faturas_pagar'])}</span></div>
          <div class="brow"><span class="bl">já gastei (flexível)</span><span class="bv">−{fmt(lpg['flex_gasto'])}</span></div>
          <div class="brow" style="border-top:1px solid #EDF2EE;margin-top:4px;padding-top:9px;">
            <span class="bl" style="font-weight:700;">livre pra gastar</span>
            <span class="bv" style="color:{_cor_livre_pop};">{fmt(livre)}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # \$ evita o markdown tratar dois R$ na mesma frase como fórmula LaTeX
    st.caption(
        f"Consumo (competência): {fmt(k['despesa_total'])} — o que o mês consumiu, mesmo pagando depois. "
        f"Saiu da conta (caixa): {fmt(caixa['despesa_total'])} — o que efetivamente debitou. "
        f"Saldo do mês: {fmt(k['saldo_mes'])}.".replace("R$", "R\\$")
    )

# ============== KPIs 2×2 ==============
IC_INV = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 13l4-5 3 3 5-7"/></svg>'
IC_PAT = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="5" width="12" height="8" rx="2"/><path d="M5 5V3.5A1.5 1.5 0 016.5 2h3A1.5 1.5 0 0111 3.5V5"/></svg>'
IC_FIX = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="8" cy="8" r="6"/><path d="M8 5v3l2 2"/></svg>'
IC_FAT = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="4" width="12" height="9" rx="2"/><path d="M2 7h12"/></svg>'
st.markdown(
    f"""
    <div class="k5grid">
      <div class="k5"><div class="k5-l">{IC_INV} investiu</div>
        <div class="k5-v">{fmt(aporte) if aporte > 0 else '—'}</div>
        <div class="k5-s">{'este mês' if aporte > 0 else 'aporte 5000 CDB no Zap'}</div></div>
      <div class="k5"><div class="k5-l">{IC_PAT} patrimônio</div>
        <div class="k5-v">{fmt(estocado) if estocado > 0 else '—'}</div>
        <div class="k5-s">{'saldo investido' if estocado > 0 else 'preencha Saldo Investido'}</div></div>
      <div class="k5"><div class="k5-l">{IC_FIX} fixas pagas</div>
        <div class="k5-v">{n_pagas} <span style="font-size:13px;font-weight:600;color:#8B978F">/ {n_fixas}</span></div>
        <div class="k5-s">{'todas confirmadas' if n_pagas == n_fixas and n_fixas > 0 else 'a confirmar no mês'}</div></div>
      <div class="k5"><div class="k5-l">{IC_FAT} faturas a pagar</div>
        <div class="k5-v">{_prox_fat_val or '—'}</div>
        <div class="k5-s">{_prox_fat_txt}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============== Para onde foi (baldes) ==============
no_mes = df_lanc[df_lanc["Competência"] == competencia] if "Competência" in df_lanc.columns else df_lanc
baldes = classificar_baldes(split_movimentos(no_mes)["despesas"], df_rec)
BALDE_META = {
    "Fixo": ("Fixo · não muda", COR["neutro"]),
    "Recorrente": ("Recorrente / parcelas", COR["alerta"]),
    "Flexível": ("Flexível · dá pra cortar", COR["flexivel"]),
}
tot_baldes = sum(baldes[b]["total"] for b in baldes) or 1
_seg = "".join(
    f'<div style="width:{baldes[b]["total"] / tot_baldes * 100:.1f}%;background:{BALDE_META[b][1]}"></div>'
    for b in ["Fixo", "Recorrente", "Flexível"]
)
_rows = "".join(
    f'<div class="brow"><span class="dot" style="background:{BALDE_META[b][1]}"></span>'
    f'<span class="bl">{BALDE_META[b][0]}</span><span class="bv">{fmt(baldes[b]["total"])}</span>'
    f'<span class="bp">{baldes[b]["total"] / tot_baldes * 100:.0f}%</span></div>'
    for b in ["Fixo", "Recorrente", "Flexível"]
)
st.markdown(f'<div class="c5"><h4>Para onde foi</h4><div class="segbar">{_seg}</div>{_rows}</div>',
            unsafe_allow_html=True)
with st.expander("Ver itens dos baldes"):
    for b in ["Fixo", "Recorrente", "Flexível"]:
        st.markdown(f"**{BALDE_META[b][0]}** — {fmt(baldes[b]['total'])}")
        for it in baldes[b]["itens"]:
            cc1, cc2 = st.columns([3, 1])
            cc1.caption(it["desc"])
            cc2.caption(fmt(it["valor"]))

# ============== Metas (anéis) ==============
mInvest = meta_valor(df_metas, "investir")
mPoup = meta_valor(df_metas, "poupança")
mFlex = meta_valor(df_metas, "flexível")
flex_real = baldes["Flexível"]["total"]
poup_real = (k["saldo_mes"] / k["receita_total"] * 100) if k["receita_total"] > 0 else 0

def _ring(pct, cor, valor_txt, label):
    C = 163.4
    off = C * (1 - min(max(pct, 0), 1))
    return (
        f'<div class="ring"><svg viewBox="0 0 62 62">'
        f'<circle cx="31" cy="31" r="26" fill="none" stroke="#EDF2EE" stroke-width="7"/>'
        f'<circle cx="31" cy="31" r="26" fill="none" stroke="{cor}" stroke-width="7" '
        f'stroke-linecap="round" stroke-dasharray="{C}" stroke-dashoffset="{off:.0f}"/></svg>'
        f'<div class="rv">{valor_txt}</div><div class="rl">{label}</div></div>'
    )

p_inv = (aporte / mInvest) if mInvest > 0 else 0
p_poup = (poup_real / mPoup) if mPoup > 0 else 0
p_flex = (flex_real / mFlex) if mFlex > 0 else 0
cor_flex = COR["flexivel"] if p_flex <= 1 else COR["despesa"]
st.markdown(
    '<div class="c5"><h4>Metas do mês</h4><div class="rings">'
    + _ring(p_inv, COR["investimento"], f"{p_inv*100:.0f}%", f"investir<br>{fmt_mil(aporte)} / {fmt_mil(mInvest)}")
    + _ring(p_poup, COR["receita"], f"{p_poup*100:.0f}%", f"poupança<br>{poup_real:.0f}% / {mPoup:.0f}%")
    + _ring(p_flex, cor_flex, f"{p_flex*100:.0f}%", f"teto flexível<br>{fmt_mil(flex_real)} / {fmt_mil(mFlex)}")
    + "</div></div>",
    unsafe_allow_html=True,
)

# ============== Faturas ==============
st.subheader("Faturas")
st.warning("Faltam as 2 faturas Bradesco da Sabrina — os gastos dela estão subestimados até carregar.")
if not ab.empty:
    _frows = ""
    for _, r in ab.iterrows():
        cartao = str(r.get("Cartão", "?")); mes_ref = str(r.get("Mês Referência", "?"))
        carregada = str(r.get("Status", "")).lower() == "carregada"
        total = float(r.get("Total_num", 0) or 0)
        venc = str(r.get("Vencimento", ""))
        if total <= 0:
            total, _q = fatura_estimada(cartao, mes_ref, df_lanc, vencimento=venc)
        d = int(r["_dias"])
        if carregada:
            cor_s, status = COR["receita"], "carregada · conciliada"
        elif d < 0:
            cor_s, status = COR["despesa"], f"venceu há {abs(d)}d"
        else:
            cor_s, status = COR["alerta"], f"vence em {d}d · aguardando fatura"
        val_txt = fmt(total) if (carregada or total > 0) else "—"
        prefixo = "" if carregada else "~ "
        _frows += (
            f'<div class="frow"><span class="fstripe" style="background:{cor_s}"></span>'
            f'<span class="fmeio"><span class="ft">{cartao} · {mes_ref}</span>'
            f'<div class="fs">{status}</div></span>'
            f'<span class="fval">{prefixo if val_txt != "—" else ""}{val_txt}</span></div>'
        )
    st.markdown(f'<div class="c5">{_frows}</div>', unsafe_allow_html=True)
else:
    st.info("Aba Faturas vazia.")

# ============== Contas fixas (detalhe) ==============
if not audit.empty:
    with st.expander(f"Contas fixas — {n_pagas} pagas / {n_fixas} no mês · {fmt(audit['Valor Esperado'].sum())} comprometido"):
        audit_show = audit.sort_values("Dia Cobrança")
        st.dataframe(
            audit_show[["Status", "Descrição", "Valor Pago", "Valor Esperado", "Dia Cobrança"]],
            use_container_width=True, hide_index=True,
            column_config={
                "Valor Pago": st.column_config.NumberColumn(format="R$ %.0f", help="o que realmente saiu este mês"),
                "Valor Esperado": st.column_config.NumberColumn(format="R$ %.0f", help="referência do cadastro"),
            },
        )
        st.caption("o cadastro dispara os alertas (dia 10/15 no Zap) e alimenta a projeção abaixo")

# ============== RD — despesas corporativas (reembolso) ==============
df_rd = df_lanc[df_lanc.apply(is_rd, axis=1)] if not df_lanc.empty else df_lanc
_rd_gasto = df_rd[df_rd["Tipo"] == "Despesa"]["Valor"].sum() if not df_rd.empty else 0.0
_rd_reemb = df_rd[df_rd["Tipo"] == "Receita"]["Valor"].sum() if not df_rd.empty else 0.0
_rd_saldo = _rd_gasto - _rd_reemb
with st.expander(f"RD — despesas corporativas · a receber {fmt(_rd_saldo)}" if _rd_saldo > 0.005
                 else "RD — despesas corporativas", expanded=False):
    if df_rd.empty:
        st.caption("Nenhum lançamento RD. Marque no Zap incluindo **RD** na mensagem — "
                   "ex: `120 almoço cliente RD` · reembolso: `1500 reembolso RD`. Comando `rd` mostra o saldo.")
    else:
        _cor_rd = COR["alerta"] if _rd_saldo > 0.005 else (COR["despesa"] if _rd_saldo < -0.005 else COR["receita"])
        st.markdown(
            f"""
            <div class="brow"><span class="bl">gastos corporativos</span><span class="bv">{fmt(_rd_gasto)}</span></div>
            <div class="brow"><span class="bl">reembolsado pela empresa</span><span class="bv" style="color:{COR['receita']}">{fmt(_rd_reemb)}</span></div>
            <div class="brow" style="border-top:1px solid #EDF2EE;margin-top:4px;padding-top:9px;">
              <span class="bl" style="font-weight:700;">{'a receber' if _rd_saldo >= 0 else 'reembolso excedente'}</span>
              <span class="bv" style="color:{_cor_rd};">{fmt(abs(_rd_saldo))}</span></div>
            """,
            unsafe_allow_html=True,
        )
        _rd_show = df_rd[["Data", "Tipo", "Descrição", "Valor"]].copy().sort_values("Data")
        st.dataframe(_rd_show, use_container_width=True, hide_index=True,
                     column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")})
        st.caption("RD é neutro no consumo e nos tetos — vive só aqui e no caixa. Comando `rd` no Zap mostra este saldo.")

# ============== Investimentos (detalhe) ==============
with st.expander("Investimentos & patrimônio", expanded=(estocado == 0 and aporte == 0)):
    ic1, ic2, ic3 = st.columns(3)
    ic1.metric("aporte do mês", fmt(aporte) if aporte > 0 else "—")
    ic2.metric("saldo estocado", fmt(estocado) if estocado > 0 else "—")
    rend = rendimento_investido(df_saldo)
    ic3.metric("rendimento", f"+{rend['pct']:.1f}%" if rend else "—",
               help="precisa de ≥2 registros na aba Saldo Investido")
    if estocado == 0 and aporte == 0:
        st.info("No Zap: `aporte 5000 CDB XP` registra investimento. Preencha a aba `Saldo Investido` pro patrimônio aparecer.")

# ============== Projeção ==============
st.subheader("Projeção")
cron = compromissos_proximos_meses(df_lanc, df_rec, df_faturas, 6, partir_de=competencia)
if not cron.empty:
    receita_proj = 0.0
    receitas = df_lanc[df_lanc["Tipo"].astype(str).str.lower() == "receita"]
    if not receitas.empty:
        por_mes = receitas.groupby("Competência")["Valor"].sum().tail(3)
        receita_proj = float(por_mes.mean()) if not por_mes.empty else 0
    fig = go.Figure()
    fig.add_bar(name="Parcelas", x=cron["Mês"], y=cron["Parcelas em curso"], marker_color=COR["neutro"])
    fig.add_bar(name="Contas fixas", x=cron["Mês"], y=cron["Contas fixas"], marker_color=COR["neutro_claro"])
    fig.add_bar(name="Faturas", x=cron["Mês"], y=cron["Faturas em aberto"], marker_color=COR["alerta"])
    if receita_proj > 0:
        fig.add_scatter(name="Receita projetada", x=cron["Mês"], y=[receita_proj] * len(cron),
                        mode="lines", line=dict(color=COR["receita"], width=2, dash="dash"))
    fig.update_layout(barmode="stack", height=280, margin=dict(l=10, r=10, t=10, b=10),
                      template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#2C2C2A", size=12),
                      legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5))
    st.plotly_chart(fig_mobile(fig), use_container_width=True, config=PLOTLY_CONFIG)
    st.caption("conforme as faturas grandes saem, sua folga cresce mês a mês")

# ============== Wesley × Sabrina ==============
st.subheader("Quem movimenta")
_cards = ""
for pessoa, cor_av in [("Wesley", COR["investimento"]), ("Sabrina", COR["flexivel"])]:
    rec = k["receita_por_pessoa"].get(pessoa, 0)
    desp = k["despesa_por_pessoa"].get(pessoa, 0)
    apo = k["aporte_por_pessoa"].get(pessoa, 0)
    saldo = rec - desp - apo
    cor_saldo = COR["receita"] if saldo >= 0 else COR["despesa"]
    _inv = f'<div class="pr"><span>investido</span><b>{fmt(apo)}</b></div>' if apo > 0 else ""
    _cards += (
        f'<div class="pss"><div class="ph"><span class="pa" style="background:{cor_av}">{pessoa[0]}</span>'
        f'<span class="pn">{pessoa}</span></div>'
        f'<div class="pr"><span>entrou</span><b>{fmt(rec) if rec > 0 else "—"}</b></div>'
        f'<div class="pr"><span>gastou</span><b>{fmt(desp)}</b></div>{_inv}'
        f'<div class="pr"><span>saldo</span><b style="color:{cor_saldo}">{"+" if saldo >= 0 else ""}{fmt(saldo)}</b></div></div>'
    )
st.markdown(f'<div class="casal">{_cards}</div>', unsafe_allow_html=True)
