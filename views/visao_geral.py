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
    load_auditoria_fatura,
    load_bens,
    load_faturas,
    patrimonio_imobilizado,
    load_lancamentos,
    load_metas,
    load_recorrentes,
    load_saldo_investido,
    meta_valor,
    meses_disponiveis,
    rendimento_investido,
    serie_estocado,
    split_movimentos,
    valor_a_receber_hoje,
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
    /* os dois heróis com a mesma altura */
    .hero5 { min-height: 300px; display: flex; flex-direction: column; }
    .hero5 .h5-sub { margin-top: auto; padding-top: 10px; }
    /* cabeçalho ACIMA dos cartões: Família Gomes à esquerda · olho + mês à direita.
       TUDO absoluto dentro do cabec (altura fixa) — flex com invólucros do Streamlit
       deixava o título sobrepor os controles em telas largas e matava o clique */
    .st-key-cabec { position: relative !important; height: 58px; margin-bottom: 14px;
      border-radius: 18px;
      background: linear-gradient(90deg, #0C5949 0%, #0A4A3A 38%, #0E3A62 66%, #082744 100%);
      box-shadow: 0 8px 20px rgba(10,45,55,0.28); }
    /* invólucros internos NÃO podem ser contexto de posicionamento (o título ancorava neles) */
    .st-key-cabec > div, .st-key-cabec [data-testid="stElementContainer"],
    .st-key-cabec [data-testid="stMarkdown"] { position: static !important; }
    .st-key-cabec .cab-nome { position: absolute; left: 18px; top: 50%; transform: translateY(-50%);
      display: flex; align-items: center; gap: 12px;
      font-size: 16.5px; font-weight: 700; color: #F2FBF6; max-width: calc(100% - 215px);
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .cab-av { width: 34px; height: 34px; border-radius: 10px; background: rgba(255,255,255,0.16);
      color: #7CE0B8; font-weight: 800; font-size: 16px; display: inline-flex;
      align-items: center; justify-content: center; flex: 0 0 34px; }
    .cab-tx { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    @media (max-width: 640px) {
      /* celular: sem o cifrão, o nome inteiro cabe ao lado do olho + mês */
      .cab-av { display: none; }
      .st-key-cabec .cab-nome { left: 16px; font-size: 15.5px; }
    }
    /* pill do mês — largura TRAVADA (o stVerticalBlock nativo força 100%) */
    .st-key-mespill {
      position: absolute !important; top: 50% !important; transform: translateY(-50%);
      right: 16px !important; left: auto !important; z-index: 6;
      width: 126px !important; min-width: 126px !important; max-width: 126px !important;
    }
    .st-key-mespill div[data-testid="stSelectbox"],
    .st-key-mespill [data-baseweb="select"] { width: 126px !important; max-width: 126px !important; }
    .st-key-mespill div[data-testid="stSelectbox"] > div > div {
      background: rgba(255,255,255,0.14) !important; border: 1px solid rgba(255,255,255,0.30) !important;
      border-radius: 999px !important; min-height: 32px; height: 32px;
    }
    .st-key-mespill div[data-testid="stSelectbox"] * { color: #EAF7F0 !important; font-size: 12px !important; }
    .st-key-mespill svg { fill: #EAF7F0 !important; }
    /* olho de privacidade, colado no pill */
    .st-key-olho { position: absolute !important; top: 50% !important; transform: translateY(-50%);
      right: 150px !important; left: auto !important; z-index: 6;
      width: 44px !important; min-width: 44px !important; }
    .st-key-olho button { background: rgba(255,255,255,0.14) !important; border: 1px solid rgba(255,255,255,0.30) !important;
      border-radius: 999px !important; color: #EAF7F0 !important; height: 32px; min-height: 32px !important;
      padding: 0 10px !important; font-size: 14px !important; width: 44px; }
    .st-key-olho button:hover { background: rgba(255,255,255,0.26) !important; }

    /* ===== L4: linhas expansíveis com bolha + valor à direita ===== */
    /* nome (bold) à esquerda, valor (code) à direita — flex no parágrafo do label */
    [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p {
      display: flex; align-items: baseline; justify-content: space-between;
      width: 100%; gap: 12px; margin: 0; font-size: 14.5px; }
    [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] strong {
      font-weight: 700; color: #21322A; flex: 0 0 auto; }
    [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] code {
      background: none !important; color: #21322A; font-family: inherit !important;
      font-weight: 800; font-size: 14.5px; white-space: nowrap; padding: 0;
      font-variant-numeric: tabular-nums; overflow: hidden; text-overflow: ellipsis;
      min-width: 0; flex: 0 1 auto; }
    /* markdown ocupa a largura → o valor vai pra ponta direita */
    [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] { flex: 1 1 auto; min-width: 0; }
    /* summary é flex mas o span-filho (ícone+texto) não herda o limite de largura sozinho —
       sem min-width:0 aqui, o conteúdo vaza pra fora do card em colunas estreitas */
    [data-testid="stExpander"] summary { width: 100%; box-sizing: border-box; }
    [data-testid="stExpander"] summary > span { min-width: 0; flex: 1 1 auto; }
    /* ícone (emoji do param icon=) vira bolha colorida por seção — é o 1º span DENTRO do span-flex */
    [data-testid="stExpander"] summary > span > span:first-child {
      border-radius: 9px; padding: 5px 6px; margin-right: 6px; line-height: 1;
      display: inline-flex; align-items: center; flex: 0 0 auto; }
    .st-key-lin-patr    [data-testid="stExpander"] summary > span > span:first-child { background: #E7F5EF; }
    .st-key-lin-fix     [data-testid="stExpander"] summary > span > span:first-child { background: #E6EEF7; }
    .st-key-lin-consumo [data-testid="stExpander"] summary > span > span:first-child { background: #FBEFE0; }
    .st-key-lin-fat     [data-testid="stExpander"] summary > span > span:first-child { background: #EFEDFB; }
    .st-key-lin-audit-fatura [data-testid="stExpander"] summary > span > span:first-child { background: #FDECD2; }
    /* remove o gap-fantasma dos containers keyed das linhas */
    div:has(> .st-key-lin-patr), div:has(> .st-key-lin-fix),
    div:has(> .st-key-lin-consumo), div:has(> .st-key-lin-fat),
    div:has(> .st-key-lin-audit-fatura), div:has(> .st-key-lin-group-b),
    div:has(> .st-key-lin-compos), div:has(> .st-key-lin-rd) { display: contents; }
    /* o tema pinta TODO stVerticalBlockBorderWrapper como card branco com sombra
       (components.py) — dentro do grupo B isso recriava um card solto por linha.
       Neutraliza o invólucro das linhas internas e dos grupos. */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-lin-consumo),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-lin-fat),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-lin-audit-fatura),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-lin-group-b),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-lin-compos),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-lin-rd),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-lin-projecao-card),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-lin-projecao-chart) {
      background: transparent !important; box-shadow: none !important; border-radius: 0 !important;
    }
    /* Patrimônio / Contas fixas: cartão próprio com sombra (acesso igual, só ajuste estético) */
    .st-key-lin-patr [data-testid="stExpander"], .st-key-lin-fix [data-testid="stExpander"] {
      box-shadow: 0 3px 12px rgba(12,60,45,0.10) !important;
      margin-bottom: 10px !important;
    }
    /* rótulo em cima / valor embaixo (tipo KPI, como o mockup) — só nesses dois, que agora
       dividem a largura ao meio; lado a lado numa linha só não cabia rótulo + valor juntos */
    .st-key-lin-patr summary p, .st-key-lin-fix summary p {
      flex-direction: column !important; align-items: flex-start !important; gap: 2px !important; }
    .st-key-lin-patr summary strong, .st-key-lin-fix summary strong {
      font-size: 10.5px !important; text-transform: uppercase; letter-spacing: .04em;
      color: #5C6B62 !important; font-weight: 700 !important; }
    .st-key-lin-patr summary code, .st-key-lin-fix summary code {
      font-size: 16px !important; color: #1C2420 !important; width: 100%; display: block; }
    /* Contas fixas tem resumo longo (19/21 pagas · X de Y) — quebra em 2 linhas em vez de cortar */
    .st-key-lin-fix summary code {
      font-size: 13px !important; white-space: normal !important; line-height: 1.35; }
    /* sem ícone nesses dois (como o mockup) — sobra mais largura pro valor não truncar */
    .st-key-lin-patr summary > span > span:first-child,
    .st-key-lin-fix summary > span > span:first-child { display: none !important; }
    /* Patrimônio + Contas fixas ficam lado a lado mesmo no celular (o Streamlit empilha
       colunas sozinho abaixo de ~640px; o mockup sempre mostra as duas juntas, tipo KPI) */
    div[data-testid="stHorizontalBlock"]:has(.st-key-lin-patr),
    div[data-testid="stHorizontalBlock"]:has(.st-key-lin-fix) {
      flex-wrap: nowrap !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.st-key-lin-patr) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(.st-key-lin-patr) > div[data-testid="column"],
    div[data-testid="stHorizontalBlock"]:has(.st-key-lin-fix) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(.st-key-lin-fix) > div[data-testid="column"] {
      width: 50% !important; flex: 1 1 50% !important; min-width: 0 !important;
    }

    /* ===== Opção B (12/08): consumo + faturas + auditoria = 1 card único, trilho de cor por linha ===== */
    .st-key-lin-group-b, .st-key-lin-compos, .st-key-lin-rd {
      background: linear-gradient(180deg, #FBFDFC, #F6FAF7);
      border: 1px solid #E1EAE4; border-radius: 16px; overflow: hidden; margin-top: 2px;
      padding: 4px 6px; gap: 0 !important;
    }
    .st-key-lin-consumo, .st-key-lin-fat, .st-key-lin-audit-fatura { margin-top: 0 !important; gap: 0 !important; }
    .st-key-lin-group-b [data-testid="stExpander"],
    .st-key-lin-compos [data-testid="stExpander"], .st-key-lin-rd [data-testid="stExpander"] {
      background: transparent !important; box-shadow: none !important;
      border-radius: 0 !important; border: 0 !important;
      margin-bottom: 0 !important; position: relative;
    }
    /* o <details> nativo do expander tem borda+raio próprios — era ele que ainda
       desenhava um "sub-card" branco por linha dentro do grupo */
    .st-key-lin-group-b [data-testid="stExpander"] details,
    .st-key-lin-compos [data-testid="stExpander"] details,
    .st-key-lin-rd [data-testid="stExpander"] details {
      border: 0 !important; border-radius: 0 !important; background: transparent !important;
    }
    /* trilho de cor: pill inset à esquerda (como o mockup), não uma borda colada no card */
    .st-key-lin-consumo [data-testid="stExpander"]::before,
    .st-key-lin-fat [data-testid="stExpander"]::before,
    .st-key-lin-audit-fatura [data-testid="stExpander"]::before,
    .st-key-lin-compos [data-testid="stExpander"]::before,
    .st-key-lin-rd [data-testid="stExpander"]::before {
      content: ""; position: absolute; left: 4px; top: 12px; bottom: 12px;
      width: 4px; border-radius: 4px;
    }
    .st-key-lin-consumo [data-testid="stExpander"]::before { background: #E4A15C; }
    .st-key-lin-fat [data-testid="stExpander"]::before { background: #A79AE8; }
    .st-key-lin-audit-fatura [data-testid="stExpander"]::before { background: #BA7517; }
    .st-key-lin-compos [data-testid="stExpander"]::before { background: #185FA5; }
    .st-key-lin-rd [data-testid="stExpander"]::before { background: #1D9E75; }
    /* separador tracejado entre as linhas do grupo */
    .st-key-lin-fat [data-testid="stExpander"],
    .st-key-lin-audit-fatura [data-testid="stExpander"] { border-top: 1px dashed #DCE6E0 !important; }
    .st-key-lin-group-b [data-testid="stExpander"] summary,
    .st-key-lin-compos [data-testid="stExpander"] summary,
    .st-key-lin-rd [data-testid="stExpander"] summary { padding-left: 18px !important; }
    /* card do gráfico de Projeção — topo arredondado, base colada na legenda (Opção B, 12/08) */
    .st-key-lin-projecao-card { gap: 0 !important; }
    .st-key-lin-projecao-chart {
      background: #fff; border-radius: 16px 16px 4px 4px; box-shadow: 0 2px 8px rgba(12,60,45,0.06);
      padding: 14px 6px 2px; margin-top: 2px; border-bottom: 3px solid #EAF0EC;
    }
    .proj-cap-b {
      background: #fff; border-radius: 0 0 12px 12px; box-shadow: 0 2px 8px rgba(12,60,45,0.06);
      margin-top: -1px; padding: 9px 14px 12px; font-size: 11.5px; color: #5C6B62; line-height: 1.4;
    }
    .proj-cap-b b { color: #1C2420; }
    /* rótulos de grupo dentro dos cards de pessoa (caixa × competência) */
    .pss .pgrp { font-size: 9.5px; font-weight: 800; text-transform: uppercase;
      letter-spacing: .09em; color: #9BAaa1; margin: 8px 0 2px; }
    .pss .pgrp { color: #97A69D; }
    /* abertura da receita: "entrou" vira clicável e mostra as linhas que compõem (18/08) */
    .pss details.pdet summary { cursor: pointer; list-style: none; }
    .pss details.pdet summary::-webkit-details-marker { display: none; }
    .pss details.pdet summary > span:first-child::after {
      content: "⌄"; font-size: 10px; color: #97A69D; margin-left: 5px; font-weight: 800; }
    .pss details.pdet[open] summary > span:first-child::after { content: "⌃"; }
    .pss .pdd { margin: 2px 0 5px; padding: 4px 10px; background: #F2F7F3; border-radius: 8px; }
    .pss .pdd .pr { padding: 2px 0; }
    .pss .pdd .pr span { font-size: 11px; color: #7C8A81; font-weight: 600;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .pss .pdd .pr b { font-size: 11.5px; color: #4A564E; }
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
# ============== Cabeçalho acima dos cartões: título esq · olho + mês dir ==============
with st.container(key="cabec"):
    st.markdown('<div class="cab-nome"><span class="cab-av">$</span><span class="cab-tx">Família Gomes</span></div>',
                unsafe_allow_html=True)
    with st.container(key="olho"):
        st.button("🙈" if _PRIV else "👁", on_click=_toggle_privado,
                  help="esconder/mostrar os valores")
    with st.container(key="mespill"):
        competencia = st.selectbox("Mês", meses, index=0, format_func=_label, label_visibility="collapsed")

# ============== Zona do topo: hero caixa (esq) | hero competência (dir) ==============
col_hero, col_cp = st.columns(2, gap="medium")

# ============== Cálculos ==============
k = kpis_familia(df_lanc, df_saldo, competencia, "Competência")
caixa = kpis_familia(df_lanc, df_saldo, competencia, "Caixa")
estocado = k["saldo_estocado_total"]
aporte = k["aporte_total"]
# aporte FINANCEIRO (meta investir / aba Patrimônio) = aportes sem compra de bens
# (carro/AP saem do caixa como investimento, mas não são aplicação financeira)
_mes_cx = df_lanc[df_lanc["Mês Caixa"] == competencia] if "Mês Caixa" in df_lanc.columns else df_lanc
_aq_bens = float(_mes_cx[_mes_cx["Categoria"].astype(str).str.strip() == "Aquisição de Bem"]["Valor"].sum()) if not _mes_cx.empty else 0.0
aporte_fin = max(aporte - _aq_bens, 0.0)


# RD (pro KPI e pro expander)
df_rd = df_lanc[df_lanc.apply(is_rd, axis=1)] if not df_lanc.empty else df_lanc
_rd_gasto = df_rd[df_rd["Tipo"] == "Despesa"]["Valor"].sum() if not df_rd.empty else 0.0
_rd_reemb = df_rd[df_rd["Tipo"] == "Receita"]["Valor"].sum() if not df_rd.empty else 0.0
_rd_saldo = _rd_gasto - _rd_reemb

# contas fixas + próxima fatura (pros KPIs)
audit = auditar_contas_fixas(df_lanc, df_rec, competencia)
n_pagas = int((audit["Status"] == "Paga").sum()) if not audit.empty else 0
n_fixas = len(audit)
_fixas_provisao = float(audit["Valor Esperado"].sum()) if not audit.empty else 0.0
_fixas_pago = float(audit["Valor Pago"].sum()) if not audit.empty else 0.0
_fixas_restante = max(_fixas_provisao - _fixas_pago, 0.0)

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
        if _c0.lower().startswith("xp"):
            _sp0 = fatura_split_pessoa(_c0, str(r0.get("Mês Referência", "")), df_lanc,
                                       vencimento=str(r0.get("Vencimento", "")))
            if _sp0:
                _prox_fat_txt += " · " + " · ".join(f"{p} {fmt_mil(v)}" for p, v in _sp0.items())

# ============== v7 · Linha 1: CAIXA (verde) | COMPETÊNCIA (azul) ==============
def _num_hero(v: float) -> str:
    """número grande dos cartões — respeita o modo privacidade"""
    return "••••" if _PRIV else f"{abs(v):,.0f}".replace(",", ".")


# sobrou = entrou − saiu − investido (fecha com os 3 chips). O "investido" é o
# líquido que saiu DA CONTA pra patrimônio (pagamentos direto do investimento
# têm par de resgate e zeram — só conta o que realmente passou pela conta).
sobrou = caixa["saldo_mes"]
sinal = '' if sobrou >= 0 else '<span class="menos">−</span>'
with col_hero:
    st.markdown(
        f"""
    <div class="hero5">
      <div class="h5-bar">
        <div><div class="h5-ola">visão de caixa,</div><div class="h5-nome">Caixa</div></div>
      </div>
      <div class="h5-rot">sobrou no mês</div>
      <div class="h5-num">{sinal}R$ {_num_hero(sobrou)}</div>
      <div class="h5-chips">
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#7CE0B8" stroke-width="2.2"><path d="M8 13V3M4 7l4-4 4 4"/></svg>entrou {fmt_mil(caixa['receita_total'])}</span>
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#FFAFA8" stroke-width="2.2"><path d="M8 3v10M4 9l4 4 4-4"/></svg>saiu {fmt_mil(caixa['despesa_total'])}</span>
        {f'<span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#9CD8F0" stroke-width="2.2"><path d="M2 13l4-5 3 3 5-7"/></svg>investido {fmt_mil(caixa["aporte_total"])}</span>' if abs(caixa['aporte_total']) > 0.5 else ''}
      </div>
      <div class="h5-sub">dinheiro que efetivamente entrou e saiu da conta · investido soma no Patrimônio</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# saldo = receita − consumo − investido (fecha com os 3 chips, em competência)
_saldo_cp = k["saldo_mes"]
_sinal_cp = '' if _saldo_cp >= 0 else '<span class="menos">−</span>'
col_cp.markdown(
    f"""
    <div class="hero5 h5-azul">
      <div class="h5-bar">
        <div><div class="h5-ola">visão de consumo,</div><div class="h5-nome">Competência</div></div>
      </div>
      <div class="h5-rot">saldo do mês</div>
      <div class="h5-num">{_sinal_cp}R$ {_num_hero(_saldo_cp)}</div>
      <div class="h5-chips">
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#9CC8F0" stroke-width="2.2"><path d="M8 13V3M4 7l4-4 4 4"/></svg>receita {fmt_mil(k['receita_total'])}</span>
        <span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#FFAFA8" stroke-width="2.2"><path d="M8 3v10M4 9l4 4 4-4"/></svg>consumo {fmt_mil(k['despesa_total'])}</span>
        {f'<span class="h5-chip"><svg viewBox="0 0 16 16" fill="none" stroke="#9CD8F0" stroke-width="2.2"><path d="M2 13l4-5 3 3 5-7"/></svg>investido {fmt_mil(k["aporte_total"])}</span>' if abs(k['aporte_total']) > 0.5 else ''}
      </div>
      <div class="h5-sub">compra no cartão conta na hora, mesmo pagando depois</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============== Quem movimenta ==============
st.markdown('<h2 style="text-align:center">Quem movimenta</h2>', unsafe_allow_html=True)
# abertura da receita por pessoa (pedido 18/08): mesmas linhas que compõem o "entrou"
# (split_movimentos sobre o mês caixa — idêntico ao cálculo do kpis_familia)
_rec_det = {}
if not df_lanc.empty and "Mês Caixa" in df_lanc.columns:
    _rc = split_movimentos(df_lanc[df_lanc["Mês Caixa"] == competencia])["receitas"]
    if not _rc.empty and "Pessoa" in _rc.columns:
        for _p, _g in _rc.groupby("Pessoa"):
            _rec_det[_p] = _g[["Descrição", "Valor"]].sort_values("Valor", ascending=False).values.tolist()

_cards = ""
for pessoa, cor_av in [("Wesley", COR["investimento"]), ("Sabrina", COR["flexivel"])]:
    rec = caixa["receita_por_pessoa"].get(pessoa, 0)
    desp = caixa["despesa_por_pessoa"].get(pessoa, 0)
    apo = caixa["aporte_por_pessoa"].get(pessoa, 0)
    consumo_p = k["despesa_por_pessoa"].get(pessoa, 0)
    saldo = rec - desp - apo  # fecha com as linhas do card: entrou − saiu − investido
    cor_saldo = COR["receita"] if saldo >= 0 else COR["despesa"]
    _inv = f'<div class="pr"><span>investido</span><b>{fmt(apo)}</b></div>' if apo > 0 else ""
    _det_rows = "".join(
        f'<div class="pr"><span>{str(d)[:28]}</span><b>{fmt(float(v))}</b></div>'
        for d, v in _rec_det.get(pessoa, [])
    )
    if rec > 0 and _det_rows:
        _entrou = (f'<details class="pdet"><summary class="pr"><span>entrou</span>'
                   f'<b>{fmt(rec)}</b></summary><div class="pdd">{_det_rows}</div></details>')
    else:
        _entrou = f'<div class="pr"><span>entrou</span><b>{fmt(rec) if rec > 0 else "—"}</b></div>'
    _cards += (
        f'<div class="pss" style="border:2px solid {cor_av}"><div class="ph"><span class="pa" style="background:{cor_av}">{pessoa[0]}</span>'
        f'<span class="pn">{pessoa}</span>'
        f'<span class="psaldo" style="color:{cor_saldo}" title="entrou − saiu (caixa)">{"+" if saldo >= 0 else "−"}{fmt(abs(saldo))}</span></div>'
        f'<div class="pgrp">caixa · conta no mês</div>'
        f'{_entrou}'
        f'<div class="pr"><span>saiu</span><b>{fmt(desp)}</b></div>{_inv}'
        f'<div class="pgrp">competência</div>'
        f'<div class="pr" title="outra lente sobre o mesmo mês: compra no cartão conta na hora, mesmo pagando a fatura depois">'
        f'<span style="color:#8B978F">consumo do mês</span><b style="color:#8B978F">{fmt(consumo_p)}</b></div>'
        f'</div>'
    )
st.markdown(f'<div class="casal">{_cards}</div>', unsafe_allow_html=True)

# ============== Patrimônio | Contas fixas (clica pra abrir) ==============
col_p, col_f = st.columns(2, gap="medium")

df_bens = load_bens()
_imob = patrimonio_imobilizado(df_bens)
_a_receber = valor_a_receber_hoje()
_patr_total = estocado + _imob["total"] + _a_receber
_patr_val = fmt(_patr_total) if _patr_total > 0 else "—"
_p_ctx = col_p.container(key="lin-patr")
with _p_ctx.expander(f"**Patrimônio** `{_patr_val}`", icon="🏦", expanded=False):
    def _linha_patr(rotulo, valor, dica, forte=False):
        v = fmt(valor) if valor > 0 else "—"
        peso = "800" if forte else "600"
        tam = "15.5px" if forte else "13.5px"
        borda = "border-top:1px solid #E1EAE4;margin-top:4px;padding-top:8px;" if forte else ""
        return (f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
                f'padding:4px 0;{borda}" title="{dica}">'
                f'<span style="font-size:12.5px;color:#5C6B62;font-weight:700;'
                f'text-transform:uppercase;letter-spacing:.04em">{rotulo}</span>'
                f'<span style="font-size:{tam};font-weight:{peso};'
                f'font-variant-numeric:tabular-nums">{v}</span></div>')

    st.markdown(
        '<div style="background:#F2F7F3;border-radius:12px;padding:10px 14px;margin-bottom:6px">'
        + _linha_patr("investível", estocado, "dinheiro que vira caixa fácil: bancos/corretoras (snapshots)")
        + _linha_patr("a receber", _a_receber, "recebíveis de prazo incerto (mútuo Empresta + sítio) — sem a liquidez de banco, não é bem físico")
        + _linha_patr("imobilizado", _imob["total"], "bens a valor de mercado − saldo devedor (aba Bens)")
        + _linha_patr("investido no mês", caixa["aporte_total"],
                      "quanto saiu do caixa pra patrimônio neste mês (aportes + compra de bens − resgates)")
        + _linha_patr("total", _patr_total, "investível + a receber + imobilizado", forte=True)
        + "</div>",
        unsafe_allow_html=True,
    )
    if _imob["total"] > 0:
        st.caption(f"imobilizado: {fmt(_imob['investimento'])} em bens de investimento + "
                   f"{fmt(_imob['uso'])} em bens de uso".replace("R$", "R\\$"))
    if not df_bens.empty and _imob["n_pendentes"] > 0:
        _pend = df_bens[df_bens["Valor de Mercado"].fillna(0) <= 0]["Nome"].tolist()
        st.caption(f"⏳ sem avaliação (fora do total): {', '.join(str(p) for p in _pend[:4])}")
    if not df_bens.empty and _imob["n_avaliados"] > 0:
        _bt = df_bens[df_bens["Valor de Mercado"].fillna(0) > 0][
            ["Nome", "Finalidade", "Valor de Mercado", "Saldo Devedor"]].copy()
        _bt["Equity"] = _bt["Valor de Mercado"] - _bt["Saldo Devedor"].fillna(0)

        def _brl(v):
            if _PRIV:
                return "R$ ••••"
            if pd.isna(v):
                return "—"
            return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        _sty = _bt.style.format({c: _brl for c in ("Valor de Mercado", "Saldo Devedor", "Equity")})
        st.dataframe(_sty, use_container_width=True, hide_index=True)
    st.markdown('<div style="font-size:13px;font-weight:700;margin:6px 0 0">Investível — evolução</div>',
                unsafe_allow_html=True)
    if not df_saldo.empty and "Data Snapshot_dt" in df_saldo.columns:
        _ev = serie_estocado(df_saldo)
        if len(_ev) >= 1:
            figp = go.Figure(go.Scatter(
                x=_ev["Data Snapshot_dt"], y=_ev["Saldo Total"], mode="lines+markers+text",
                line=dict(color=COR["investimento"], width=3), marker=dict(size=9),
                text=["" if _PRIV else fmt(vv) for vv in _ev["Saldo Total"]], textposition="top center"))
            figp.update_traces(cliponaxis=False)
            figp.update_layout(height=240, margin=dict(l=10, r=16, t=48, b=10), template="plotly_white",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="#2C2C2A", size=12), showlegend=False,
                               yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"))
            st.plotly_chart(fig_mobile(figp), use_container_width=True, config=PLOTLY_CONFIG)
        ic1, ic2, ic3 = st.columns(3)
        ic1.metric("aporte do mês", fmt(aporte_fin) if aporte_fin > 0 else "—",
                   help="aporte financeiro (compra de bens não conta aqui)")
        rend = rendimento_investido(df_saldo)
        ic2.metric("rendimento", f"+{rend['pct']:.2f}%" if rend else "—")
        ic3.metric("snapshots", str(df_saldo["Data Snapshot"].nunique()))
        st.caption("cada print de investimento no Zap vira um ponto novo na curva")
    else:
        st.info("Mande o print do app do banco no grupo do Zap — o patrimônio entra sozinho.")

_resumo_fixas = f"{n_pagas}/{n_fixas} pagas · {fmt(_fixas_pago)} de {fmt(_fixas_provisao)}"
_f_ctx = col_f.container(key="lin-fix")
with _f_ctx.expander(f"**Contas fixas** `{_resumo_fixas}`", icon="🕐", expanded=False):
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

_consumo_baldes = sum(baldes[b]["total"] for b in baldes)
with st.container(key="lin-group-b"):
    _c_ctx = st.container(key="lin-consumo")
    with _c_ctx.expander(f"**Para onde foi o consumo** `{fmt(_consumo_baldes)}`", icon="🧭", expanded=False):
        st.markdown(f'<div class="segbar">{_seg}</div>', unsafe_allow_html=True)
        _pb = st.columns(3)
        for _i, b in enumerate(["Fixo", "Recorrente", "Flexível"]):
            pct_b = baldes[b]["total"] / tot_baldes * 100
            with _pb[_i].popover(f"{BALDE_META[b][0].split(' ·')[0]} · {fmt_mil(baldes[b]['total'])} ({pct_b:.0f}%)",
                                 use_container_width=True):
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

        p_inv = (aporte_fin / mInvest) if mInvest > 0 else 0
        p_poup = (poup_real / mPoup) if mPoup > 0 else 0
        p_flex = (flex_real / mFlex) if mFlex > 0 else 0
        cor_flex = COR["flexivel"] if p_flex <= 1 else COR["despesa"]
        st.markdown(
            '<h4 style="margin:14px 0 8px;font-size:13.5px">Metas do mês</h4><div class="rings">'
            + _ring(p_inv, COR["investimento"], f"{p_inv*100:.0f}%", f"investir<br>{fmt_mil(aporte_fin)} / {fmt_mil(mInvest)}")
            + _ring(p_poup, COR["receita"], f"{p_poup*100:.0f}%", f"poupança<br>{poup_real:.0f}% / {mPoup:.0f}%")
            + _ring(p_flex, cor_flex, f"{p_flex*100:.0f}%", f"teto flexível<br>{fmt_mil(flex_real)} / {fmt_mil(mFlex)}")
            + "</div>",
            unsafe_allow_html=True,
        )

        try:
            df_tetos = load_tetos()
        except Exception:
            df_tetos = pd.DataFrame()
        _pop_tetos = st.popover("tetos por categoria · abrir", use_container_width=True)
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
            with _pop_tetos:
                st.markdown(_linhas_teto, unsafe_allow_html=True)

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
                cor_s, status = COR["despesa"], f"venceu há {abs(d)}d" + (" · ~valor estimado" if total > 0 else "")
            else:
                cor_s, status = COR["alerta"], f"vence em {d}d · aguardando fatura" + (" · ~valor estimado" if total > 0 else "")
            val_txt = fmt(total) if (carregada or total > 0) else "—"
            prefixo = "" if carregada else "~ "
            # XP Visa é cartão único com 2 portadores — mostra o rateio Wesley × Sabrina
            _split_txt = ""
            if cartao.lower().startswith("xp"):
                _split = fatura_split_pessoa(cartao, mes_ref, df_lanc, vencimento=venc)
                if _split:
                    _split_txt = ('<div class="fs" style="color:#185FA5;font-weight:600">'
                                  + " · ".join(f"{p} {fmt_mil(v)}" for p, v in _split.items())
                                  + "</div>")
            rows += (
                f'<div class="frow"><span class="fstripe" style="background:{cor_s}"></span>'
                f'<span class="fmeio"><span class="ft">{cartao} · {mes_ref}</span>'
                f'<div class="fs">{status}</div>{_split_txt}</span>'
                f'<span class="fval">{prefixo if val_txt != "—" else ""}{val_txt}</span></div>'
            )
        return rows


    _fat_ctx = st.container(key="lin-fat")
    with _fat_ctx.expander(f"**Faturas** `{_prox_fat_val or '—'}`", icon="💳", expanded=False):
        st.caption(f"próxima: {_prox_fat_txt}")
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

    # ============== Auditoria de cartão (apontamentos do WF1) ==============
    df_auditoria_fatura = load_auditoria_fatura()
    if not df_auditoria_fatura.empty and "Status" in df_auditoria_fatura.columns:
        _audit_pend = df_auditoria_fatura[df_auditoria_fatura["Status"].astype(str).str.strip().str.lower() == "pendente"]
        if not _audit_pend.empty:
            _audit_ctx = st.container(key="lin-audit-fatura")
            with _audit_ctx.expander(f"**⚠️ Auditoria de cartão** `{len(_audit_pend)} pendente(s)`", icon="🔍", expanded=False):
                st.caption(
                    "transações da fatura que NÃO foram lançadas antes no Zap — confira se a compra "
                    "é sua mesmo (assinatura esquecida, parcela antiga ou cobrança errada da bandeira). "
                    "Quando o apontamento cita outro cartão do mesmo banco, pode ser lançamento feito "
                    "no cartão errado. Nada foi bloqueado: a transação entrou normalmente no consumo."
                )
                for _, r in _audit_pend.sort_values("Data Processamento_dt", ascending=False).iterrows():
                    _tipo = str(r.get("Tipo", "") or "").strip()
                    _eh_ecom = "commerce" in _tipo.lower() or "assinatura" in _tipo.lower()
                    _pill = (f'<span style="font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:999px;'
                             f'background:{"#E6EEF7" if _eh_ecom else "#EFEDE5"};color:{"#1D4FA0" if _eh_ecom else "#6B6455"};'
                             f'margin-left:8px;white-space:nowrap">{_tipo}</span>') if _tipo else ""
                    _cartao_ex = str(r.get("Cartão Existente (possível)", "") or "").strip()
                    _rodape = (f'Lançamento existente em <b>{_cartao_ex}</b> — {r.get("Lançamento Existente", "?")}'
                               if _cartao_ex else str(r.get("Lançamento Existente", "")))
                    st.markdown(
                        f"""
                        <div style="background:#FFF7ED;border:1px solid #FCD9A8;border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:13px">
                          <div style="font-weight:700;color:#1C2420">{r.get('Descrição', '?')} — {fmt(float(r.get('Valor_num', 0) or 0))}{_pill}</div>
                          <div style="color:#5C6B62;margin-top:2px">Fatura: <b>{r.get('Fatura Cartão', '?')}</b> · {r.get('Data Transação', '?')}</div>
                          <div style="color:#B45309;margin-top:2px">{_rodape}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.caption("depois de revisar, marque \"Status\" como resolvido direto na aba Auditoria Fatura da planilha.")

# ============== Projeção (linhas: receita, fixas, parcelas e o LIVRE) ==============
st.markdown(
    f'<div style="position:relative;padding-left:12px;margin:26px 0 10px 2px">'
    f'<span style="position:absolute;left:0;top:2px;bottom:2px;width:4px;border-radius:4px;'
    f'background:{COR["investimento"]}"></span>'
    f'<h3 style="margin:0;font-size:19px;color:#1C2420">Projeção</h3>'
    f'<span style="font-size:11px;color:#97A69D">próximos 6 meses</span></div>',
    unsafe_allow_html=True,
)
cron = compromissos_proximos_meses(df_lanc, df_rec, df_faturas, 6, partir_de=competencia)
if not cron.empty:
    receita_proj = 0.0
    receitas = df_lanc[df_lanc["Tipo"].astype(str).str.lower() == "receita"]
    if not receitas.empty:
        por_mes = receitas.groupby("Competência")["Valor"].sum()
        # ordem CRONOLÓGICA e só meses até o atual — groupby ordena "MM/YYYY" alfabeticamente,
        # e parcelas antigas de fatura criam competências de anos anteriores no fim da lista
        _ult = sorted([c for c in por_mes.index if 0 < _key(c) <= _hoje], key=_key)[-3:]
        receita_proj = float(por_mes.loc[_ult].mean()) if _ult else 0
    comp_cols = [c for c in ("Parcelas em curso", "Contas fixas", "Faturas em aberto") if c in cron.columns]
    cron["Compromissos"] = cron[comp_cols].sum(axis=1)
    cron["Livre"] = receita_proj - cron["Compromissos"]
    figj = go.Figure()
    figj.add_scatter(name="Receita prevista", x=cron["Mês"], y=[receita_proj] * len(cron),
                     mode="lines+markers+text", line=dict(color=COR["receita"], width=2, dash="dash"),
                     marker=dict(size=5),
                     text=["" if _PRIV else fmt_mil(receita_proj) for _ in range(len(cron))],
                     textposition="top center", textfont=dict(size=10))
    if "Contas fixas" in cron.columns:
        figj.add_scatter(name="Contas fixas", x=cron["Mês"], y=cron["Contas fixas"],
                         mode="lines+markers+text", line=dict(color=COR["neutro"], width=2),
                         text=["" if _PRIV else fmt_mil(vv) for vv in cron["Contas fixas"]],
                         textposition="bottom center", textfont=dict(size=10))
    if "Parcelas em curso" in cron.columns:
        figj.add_scatter(name="Parcelas", x=cron["Mês"], y=cron["Parcelas em curso"],
                         mode="lines+markers+text", line=dict(color=COR["alerta"], width=2),
                         text=["" if _PRIV else fmt_mil(vv) for vv in cron["Parcelas em curso"]],
                         textposition="bottom center", textfont=dict(size=10))
    figj.add_scatter(name="LIVRE (sobra prevista)", x=cron["Mês"], y=cron["Livre"],
                     mode="lines+markers+text", line=dict(color=COR["investimento"], width=4),
                     marker=dict(size=9),
                     text=["" if _PRIV else fmt_mil(vv) for vv in cron["Livre"]], textposition="top center")
    figj.update_traces(cliponaxis=False)
    figj.update_layout(height=320, margin=dict(l=10, r=16, t=44, b=10), template="plotly_white",
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       font=dict(color="#2C2C2A", size=12),
                       legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
                       yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"))
    with st.container(key="lin-projecao-card"):
        with st.container(key="lin-projecao-chart"):
            st.plotly_chart(fig_mobile(figj), use_container_width=True, config=PLOTLY_CONFIG)
        st.markdown(
            f'<div class="proj-cap-b">'
            f'<b>Receita prevista {fmt(receita_proj)}</b> (média dos últimos 3 meses) · '
            f'LIVRE = receita − fixas − parcelas − faturas em aberto</div>',
            unsafe_allow_html=True,
    )
    _compos_ctx = st.container(key="lin-compos")
    with _compos_ctx.expander("**ver composição mês a mês**"):
        _dcron = cron[["Mês"] + comp_cols + ["Compromissos", "Livre"]].copy()
        _dcron.insert(1, "Receita prevista", receita_proj)
        st.dataframe(_dcron, use_container_width=True, hide_index=True,
                     column_config={c: st.column_config.NumberColumn(format="R$ %.0f")
                                    for c in _dcron.columns if c != "Mês"})

# ============== RD — despesas corporativas ==============
_rd_ctx = st.container(key="lin-rd")
with _rd_ctx.expander(f"**RD — despesas corporativas** `{fmt(_rd_saldo)} a receber`" if _rd_saldo > 0.005
                      else "**RD — despesas corporativas**", icon="🏢", expanded=False):
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
