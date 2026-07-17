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
    load_tetos,
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
    @media (min-width: 1024px) {
      .block-container { max-width: 1180px !important; }
      /* KPIs preenchem a altura do hero (sem buraco embaixo) */
      div[data-testid="column"]:has(.k5grid), div[data-testid="stColumn"]:has(.k5grid) { display: flex; }
      div[data-testid="column"]:has(.k5grid) > div, div[data-testid="stColumn"]:has(.k5grid) > div { width: 100%; }
      .k5grid { height: 100%; grid-auto-rows: 1fr; margin-bottom: 0; }
      .k5 { display: flex; flex-direction: column; justify-content: center; min-height: 158px; }
    }
    /* a coluna que contém o pill vira o contexto de posicionamento (pill sempre sobre o hero) */
    div[data-testid="column"]:has(.st-key-mespill), div[data-testid="stColumn"]:has(.st-key-mespill) { position: relative; }
    /* seletor de mês vira o pill do hero (sobreposto no canto direito, ao lado do avatar).
       largura TRAVADA com !important — o stVerticalBlock nativo força 100% e o pill
       virava uma barra gigante no desktop */
    .st-key-mespill {
      position: absolute !important; top: 44px !important; right: 20px !important;
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
    /* olho de privacidade, colado no pill */
    .st-key-olho { position: absolute !important; top: 44px !important; right: 152px !important;
      width: 44px !important; z-index: 21; }
    .st-key-olho button { background: rgba(7,56,44,0.55) !important; border: 1px solid rgba(255,255,255,0.28) !important;
      border-radius: 999px !important; color: #EAF7F0 !important; height: 32px; min-height: 32px !important;
      padding: 0 10px !important; font-size: 14px !important; width: 44px; }
    .st-key-olho button:hover { background: rgba(7,56,44,0.8) !important; }
    </style>""",
    unsafe_allow_html=True,
)


_PRIV = bool(st.session_state.get("modo_privado", False))


def _toggle_privado():
    st.session_state["modo_privado"] = not st.session_state.get("modo_privado", False)


def fmt(v: float) -> str:
    if _PRIV:
        return "R$ ••••"
    s = f"{abs(v):,.0f}".replace(",", ".")
    return ("-" if v < 0 else "") + f"R$ {s}"


def fmt_mil(v: float) -> str:
    """R$ compacto pros chips: 63,9 mil."""
    if _PRIV:
        return "••••"
    if abs(v) >= 1000:
        return f"{v/1000:,.1f}".replace(".", ",") + " mil"
    return f"{v:,.0f}".replace(",", ".")


if _PRIV:
    # borra o que não passa pelo fmt (tabelas e gráficos)
    st.markdown("<style>[data-testid='stDataFrame'], .stPlotlyChart { filter: blur(6px); }</style>",
                unsafe_allow_html=True)


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
# ============== Zona do topo: hero (esq) | KPIs (dir) — empilha no celular ==============
col_hero, col_cp = st.columns(2, gap="medium")

# o widget fica no fluxo do código AQUI, mas o CSS o posiciona DENTRO do hero
# (canto superior direito, estilo pill do mockup)
with col_hero:
    with st.container(key="mespill"):
        competencia = st.selectbox("Mês", meses, index=0, format_func=_label, label_visibility="collapsed")
    with st.container(key="olho"):
        st.button("🙈" if _PRIV else "👁", on_click=_toggle_privado,
                  help="esconder/mostrar os valores")

# ============== Cálculos ==============
lpg = livre_para_gastar(df_lanc, df_rec, df_faturas, df_saldo, competencia)
livre = lpg["livre"]
k = kpis_familia(df_lanc, df_saldo, competencia, "Competência")
caixa = kpis_familia(df_lanc, df_saldo, competencia, "Caixa")
estocado = k["saldo_estocado_total"]
aporte = k["aporte_total"]


# RD (pro KPI e pro expander)
df_rd = df_lanc[df_lanc.apply(is_rd, axis=1)] if not df_lanc.empty else df_lanc
_rd_gasto = df_rd[df_rd["Tipo"] == "Despesa"]["Valor"].sum() if not df_rd.empty else 0.0
_rd_reemb = df_rd[df_rd["Tipo"] == "Receita"]["Valor"].sum() if not df_rd.empty else 0.0
_rd_saldo = _rd_gasto - _rd_reemb

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

# ============== v7 · Linha 1: CAIXA (verde) | COMPETÊNCIA (azul) ==============
_h = datetime.now().hour
saud = "bom dia" if _h < 12 else ("boa tarde" if _h < 18 else "boa noite")
sobrou = caixa["saldo_mes"]
sinal = '<span class="mais">+</span>' if sobrou >= 0 else '<span class="menos">−</span>'
with col_hero:
    st.markdown(
        f"""
    <div class="hero5">
      <div class="h5-bar">
        <div><div class="h5-ola">{saud},</div><div class="h5-nome">Família Gomes</div></div>
      </div>
      <div class="h5-rot">sobrou no mês · caixa</div>
      <div class="h5-num">{sinal}R$ {f"{abs(sobrou):,.0f}".replace(",", ".")}</div>
      <div class="h5-chips">
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#7CE0B8" stroke-width="2.2"><path d="M8 13V3M4 7l4-4 4 4"/></svg>entrou {fmt_mil(caixa['receita_total'])}</span>
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#FFAFA8" stroke-width="2.2"><path d="M8 3v10M4 9l4 4 4-4"/></svg>saiu {fmt_mil(caixa['despesa_total'])}</span>
      </div>
      <div class="h5-sub">dinheiro que efetivamente entrou e saiu da conta</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

_saldo_cp = k["saldo_mes"]
_sinal_cp = "+" if _saldo_cp >= 0 else "−"
col_cp.markdown(
    f"""
    <div class="hero5 h5-azul">
      <div class="h5-bar">
        <div><div class="h5-ola">visão de consumo,</div><div class="h5-nome">Competência</div></div>
      </div>
      <div class="h5-rot">consumo do mês</div>
      <div class="h5-num">R$ {f"{k['despesa_total']:,.0f}".replace(",", ".")}</div>
      <div class="h5-chips">
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#9CC8F0" stroke-width="2.2"><path d="M8 13V3M4 7l4-4 4 4"/></svg>receita {fmt_mil(k['receita_total'])}</span>
        <span class="h5-chip">saldo {_sinal_cp}{fmt_mil(abs(_saldo_cp))}</span>
      </div>
      <div class="h5-sub">compra no cartão conta na hora, mesmo pagando depois</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============== Quem movimenta ==============
st.subheader("Quem movimenta")
st.caption("régua do caixa (cartão verde) · linha cinza = consumo (cartão azul)")
_cards = ""
for pessoa, cor_av in [("Wesley", COR["investimento"]), ("Sabrina", COR["flexivel"])]:
    rec = caixa["receita_por_pessoa"].get(pessoa, 0)
    desp = caixa["despesa_por_pessoa"].get(pessoa, 0)
    apo = caixa["aporte_por_pessoa"].get(pessoa, 0)
    consumo_p = k["despesa_por_pessoa"].get(pessoa, 0)
    saldo = rec - desp - apo
    cor_saldo = COR["receita"] if saldo >= 0 else COR["despesa"]
    _inv = f'<div class="pr"><span>investido</span><b>{fmt(apo)}</b></div>' if apo > 0 else ""
    _cards += (
        f'<div class="pss"><div class="ph"><span class="pa" style="background:{cor_av}">{pessoa[0]}</span>'
        f'<span class="pn">{pessoa}</span>'
        f'<span class="psaldo" style="color:{cor_saldo}">{"+" if saldo >= 0 else "−"}{fmt(abs(saldo))}</span></div>'
        f'<div class="pr"><span>entrou</span><b>{fmt(rec) if rec > 0 else "—"}</b></div>'
        f'<div class="pr"><span>saiu</span><b>{fmt(desp)}</b></div>{_inv}'
        f'<div class="pr"><span style="color:#8B978F">consumo do mês</span><b style="color:#8B978F">{fmt(consumo_p)}</b></div>'
        f'</div>'
    )
st.markdown(f'<div class="casal">{_cards}</div>', unsafe_allow_html=True)

# ============== Patrimônio | Contas fixas (clica pra abrir) ==============
col_p, col_f = st.columns(2, gap="medium")

with col_p.expander(f"🏦 Patrimônio — {fmt(estocado) if estocado > 0 else '—'} · ver evolução", expanded=False):
    if not df_saldo.empty and "Data Snapshot_dt" in df_saldo.columns:
        _ev = df_saldo.dropna(subset=["Data Snapshot_dt"]).groupby("Data Snapshot_dt")["Saldo Total"].sum().reset_index()
        if len(_ev) >= 1:
            figp = go.Figure(go.Scatter(
                x=_ev["Data Snapshot_dt"], y=_ev["Saldo Total"], mode="lines+markers+text",
                line=dict(color=COR["investimento"], width=3), marker=dict(size=9),
                text=["" if _PRIV else fmt(vv) for vv in _ev["Saldo Total"]], textposition="top center"))
            figp.update_layout(height=230, margin=dict(l=10, r=10, t=28, b=10), template="plotly_white",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="#2C2C2A", size=12), showlegend=False,
                               yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"))
            st.plotly_chart(fig_mobile(figp), use_container_width=True, config=PLOTLY_CONFIG)
        ic1, ic2, ic3 = st.columns(3)
        ic1.metric("aporte do mês", fmt(aporte) if aporte > 0 else "—")
        rend = rendimento_investido(df_saldo)
        ic2.metric("rendimento", f"+{rend['pct']:.2f}%" if rend else "—")
        ic3.metric("snapshots", str(df_saldo["Data Snapshot"].nunique()))
        st.caption("cada print de investimento no Zap vira um ponto novo na curva")
    else:
        st.info("Mande o print do app do banco no grupo do Zap — o patrimônio entra sozinho.")

with col_f.expander(f"🕐 Contas fixas — {n_pagas} pagas / {n_fixas} · ver detalhe", expanded=False):
    if not audit.empty:
        _ash = audit.sort_values("Dia Cobrança")
        st.dataframe(
            _ash[["Status", "Descrição", "Valor Pago", "Valor Esperado", "Dia Cobrança"]],
            use_container_width=True, hide_index=True,
            column_config={
                "Valor Pago": st.column_config.NumberColumn(format="R$ %.0f", help="o que realmente saiu este mês"),
                "Valor Esperado": st.column_config.NumberColumn(format="R$ %.0f", help="referência do cadastro"),
            },
        )
        st.caption("cadastro alimenta os alertas do Zap e a projeção; coluna Fim encerra contas (vigência)")

# ============== A conta do mês (conta + baldes + metas num card só) ==============
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

with st.expander(f"🧾 A conta do mês — consumo {fmt(k['despesa_total'])} · abrir", expanded=False):
    _cor_livre = COR["receita"] if livre >= 0 else COR["despesa"]
    st.markdown(
        f"""
        <div class="brow"><span class="bl">entrou</span><span class="bv" style="color:{COR['receita']}">{fmt(lpg['receita'])}</span></div>
        <div class="brow"><span class="bl">contas fixas</span><span class="bv">−{fmt(lpg['fixas'])}</span></div>
        <div class="brow"><span class="bl">faturas a pagar</span><span class="bv">−{fmt(lpg['faturas_pagar'])}</span></div>
        <div class="brow"><span class="bl">já gastei (flexível)</span><span class="bv">−{fmt(lpg['flex_gasto'])}</span></div>
        <div class="brow" style="border-top:1px solid #EDF2EE;margin-top:4px;padding-top:9px;">
          <span class="bl" style="font-weight:700;">livre pra gastar até o fim do mês</span>
          <span class="bv" style="color:{_cor_livre};">{fmt(livre)}</span></div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<h4 style="margin:14px 0 8px;font-size:13.5px">Para onde foi o consumo</h4>'
                f'<div class="segbar">{_seg}</div>{_rows}', unsafe_allow_html=True)
    with st.popover("ver itens dos baldes"):
        for b in ["Fixo", "Recorrente", "Flexível"]:
            st.markdown(f"**{BALDE_META[b][0]}** — {fmt(baldes[b]['total'])}")
            for it in baldes[b]["itens"]:
                cc1, cc2 = st.columns([3, 1])
                cc1.caption(it["desc"])
                cc2.caption(fmt(it["valor"]))

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
        '<h4 style="margin:14px 0 8px;font-size:13.5px">Metas do mês</h4><div class="rings">'
        + _ring(p_inv, COR["investimento"], f"{p_inv*100:.0f}%", f"investir<br>{fmt_mil(aporte)} / {fmt_mil(mInvest)}")
        + _ring(p_poup, COR["receita"], f"{p_poup*100:.0f}%", f"poupança<br>{poup_real:.0f}% / {mPoup:.0f}%")
        + _ring(p_flex, cor_flex, f"{p_flex*100:.0f}%", f"teto flexível<br>{fmt_mil(flex_real)} / {fmt_mil(mFlex)}")
        + "</div>",
        unsafe_allow_html=True,
    )

    try:
        df_tetos = load_tetos()
    except Exception:
        df_tetos = pd.DataFrame()
    if not df_tetos.empty and "Categoria" in df_tetos.columns:
        _desp_cat = split_movimentos(no_mes)["despesas"].groupby("Categoria")["Valor"].sum()
        _tmap = dict(zip(df_tetos["Categoria"], pd.to_numeric(df_tetos.get("Teto Mensal", 0), errors="coerce").fillna(0)))
        _linhas_teto = ""
        for cat, gasto in _desp_cat.sort_values(ascending=False).head(6).items():
            teto = float(_tmap.get(cat, 0) or 0)
            pct = gasto / teto if teto > 0 else 0
            cor_b = COR["receita"] if pct < 0.8 else (COR["alerta"] if pct <= 1 else COR["despesa"])
            largura = min(pct, 1.15) / 1.15 * 100 if teto > 0 else 0
            rot = f"{pct*100:.0f}% do teto" if teto > 0 else "sem teto"
            _linhas_teto += (
                f'<div style="margin:7px 0"><div style="display:flex;justify-content:space-between;font-size:12.5px">'
                f'<span>{cat}</span><b>{fmt(gasto)} <span style="color:#8B978F;font-weight:500">· {rot}</span></b></div>'
                f'<div style="height:6px;border-radius:4px;background:#EDF2EE;margin-top:3px">'
                f'<div style="width:{largura:.0f}%;height:6px;border-radius:4px;background:{cor_b}"></div></div></div>'
            )
        st.markdown(f'<h4 style="margin:14px 0 4px;font-size:13.5px">Tetos por categoria</h4>{_linhas_teto}',
                    unsafe_allow_html=True)

# ============== Faturas (fechado · filtro por mês) ==============
def _fatura_rows(df_f):
    rows = ""
    for _, r in df_f.iterrows():
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
        rows += (
            f'<div class="frow"><span class="fstripe" style="background:{cor_s}"></span>'
            f'<span class="fmeio"><span class="ft">{cartao} · {mes_ref}</span>'
            f'<div class="fs">{status}</div></span>'
            f'<span class="fval">{prefixo if val_txt != "—" else ""}{val_txt}</span></div>'
        )
    return rows


with st.expander(f"💳 Faturas — próxima: {_prox_fat_val or '—'} · {_prox_fat_txt} · abrir", expanded=False):
    if not ab.empty:
        fc0, fc1, fc2 = st.columns(3)
        _meses_f = ["todos os meses"] + sorted(ab["Mês Referência"].astype(str).unique().tolist(), reverse=True)
        f_mes = fc0.selectbox("Mês", _meses_f)
        _cartoes = ["todos os cartões"] + sorted(ab["Cartão"].astype(str).unique().tolist())
        f_cart = fc1.selectbox("Cartão", _cartoes)
        f_stat = fc2.selectbox("Status", ["todas", "aguardando fatura", "vencidas", "carregadas"])
        filt = ab.copy()
        if f_mes != "todos os meses":
            filt = filt[filt["Mês Referência"].astype(str) == f_mes]
        if f_cart != "todos os cartões":
            filt = filt[filt["Cartão"].astype(str) == f_cart]
        _low = filt["Status"].astype(str).str.lower()
        if f_stat == "aguardando fatura":
            filt = filt[(_low != "carregada") & (filt["_dias"] >= 0)]
        elif f_stat == "vencidas":
            filt = filt[(_low != "carregada") & (filt["_dias"] < 0)]
        elif f_stat == "carregadas":
            filt = filt[_low == "carregada"]
        if filt.empty:
            st.caption("nada com esse filtro")
        else:
            st.markdown(f'<div class="c5">{_fatura_rows(filt)}</div>', unsafe_allow_html=True)
    else:
        st.info("Aba Faturas vazia.")

# ============== Projeção (linhas: receita, fixas, parcelas e o LIVRE) ==============
st.subheader("Projeção")
cron = compromissos_proximos_meses(df_lanc, df_rec, df_faturas, 6, partir_de=competencia)
if not cron.empty:
    receita_proj = 0.0
    receitas = df_lanc[df_lanc["Tipo"].astype(str).str.lower() == "receita"]
    if not receitas.empty:
        por_mes = receitas.groupby("Competência")["Valor"].sum().tail(3)
        receita_proj = float(por_mes.mean()) if not por_mes.empty else 0
    comp_cols = [c for c in ("Parcelas em curso", "Contas fixas", "Faturas em aberto") if c in cron.columns]
    cron["Compromissos"] = cron[comp_cols].sum(axis=1)
    cron["Livre"] = receita_proj - cron["Compromissos"]
    figj = go.Figure()
    figj.add_scatter(name="Receita prevista", x=cron["Mês"], y=[receita_proj] * len(cron),
                     mode="lines", line=dict(color=COR["receita"], width=2, dash="dash"))
    if "Contas fixas" in cron.columns:
        figj.add_scatter(name="Contas fixas", x=cron["Mês"], y=cron["Contas fixas"],
                         mode="lines+markers", line=dict(color=COR["neutro"], width=2))
    if "Parcelas em curso" in cron.columns:
        figj.add_scatter(name="Parcelas", x=cron["Mês"], y=cron["Parcelas em curso"],
                         mode="lines+markers", line=dict(color=COR["alerta"], width=2))
    figj.add_scatter(name="LIVRE (sobra prevista)", x=cron["Mês"], y=cron["Livre"],
                     mode="lines+markers+text", line=dict(color=COR["investimento"], width=4),
                     marker=dict(size=9),
                     text=["" if _PRIV else fmt_mil(vv) for vv in cron["Livre"]], textposition="top center")
    figj.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white",
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       font=dict(color="#2C2C2A", size=12),
                       legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
                       yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"))
    st.plotly_chart(fig_mobile(figj), use_container_width=True, config=PLOTLY_CONFIG)
    st.caption(
        f"receita prevista = média dos últimos 3 meses ({fmt(receita_proj)}). "
        f"LIVRE = receita − fixas − parcelas − faturas em aberto (faturas entram no cálculo)."
    )
    with st.expander("ver composição mês a mês"):
        _dcron = cron[["Mês"] + comp_cols + ["Compromissos", "Livre"]].copy()
        st.dataframe(_dcron, use_container_width=True, hide_index=True,
                     column_config={c: st.column_config.NumberColumn(format="R$ %.0f")
                                    for c in _dcron.columns if c != "Mês"})

# ============== RD — despesas corporativas ==============
with st.expander(f"🏢 RD — despesas corporativas · a receber {fmt(_rd_saldo)}" if _rd_saldo > 0.005
                 else "🏢 RD — despesas corporativas", expanded=False):
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
        st.caption("RD é neutro no consumo e nos tetos. Comando `rd` no Zap mostra este saldo.")
