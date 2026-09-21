"""Cliente gspread com escopo de ESCRITA (separado do data.py que é read-only)."""
import json

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


SHEET_ID = "1cl9heM5gZiMVbGlWa8j_BlYEa0MwBq40k_bK27H_qaA"
SCOPES_RW = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def _write_client():
    """Cliente com permissão de leitura+escrita na planilha."""
    if "gcp_service_account" in st.secrets:
        sa_info = dict(st.secrets["gcp_service_account"])
    else:
        sa_info = json.load(open("/tmp/sa_key.json"))
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES_RW)
    return gspread.authorize(creds)


@st.cache_resource
def _write_sheet():
    return _write_client().open_by_key(SHEET_ID)


@st.cache_resource
def _write_ws_map() -> dict:
    """Worksheets por nome — `open_by_key` + `worksheet()` custavam 2 leituras de metadados por
    escrita; com a cota de 60 leituras/min isso pesava em cada clique da auditoria (21/09/2026)."""
    return {w.title: w for w in _write_sheet().worksheets()}


def write_ws(name: str):
    """Worksheet com permissão de escrita."""
    m = _write_ws_map()
    if name not in m:
        _write_ws_map.clear()
        m = _write_ws_map()
    return m[name]


def _com_retry(fn, tentativas: int = 4):
    """429 (cota) → espera e repete, em vez de traceback na tela."""
    import time
    for i in range(tentativas):
        try:
            return fn()
        except gspread.exceptions.APIError as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code == 429 and i < tentativas - 1:
                time.sleep(4 * (2 ** i))
                continue
            raise


def append_lancamentos(rows: list[list]) -> int:
    """Append linhas na aba Lançamentos.

    Cada row precisa ter 14 colunas, na ordem:
    Data | Competência | Tipo | Categoria | Subcategoria | Descrição | Pessoa |
    Forma Pgto | Valor | Mensagem Original | Data Caixa | Cartão | Parcela | Status

    A coluna A (row_number) é fórmula `=ROW()-1` e não entra no append.

    Returns:
        número de linhas inseridas
    """
    if not rows:
        return 0
    ws = write_ws("Lançamentos")
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)


# ===== Auditoria com botões (17/09/2026) — escrita mínima e reversível =====
@st.cache_resource
def _col_status_aba(aba: str) -> int:
    """Índice da coluna Status por aba — 1 leitura por processo, não por clique."""
    hdr = _com_retry(lambda: write_ws(aba).row_values(1))
    return hdr.index("Status") + 1


def _col_status(ws) -> int:
    return _col_status_aba(ws.title)


def resolver_auditoria(aba: str, row_number: int, status: str) -> None:
    """Escreve o Status de UM apontamento (aba 'Auditoria Fatura' ou 'Auditoria Lançamento')."""
    ws = write_ws(aba)
    col = _col_status(ws)
    _com_retry(lambda: ws.update_cell(int(row_number), col, status))


def resolver_auditoria_lote(aba: str, rows: list, status: str) -> int:
    """Mesmo Status pra vários apontamentos de uma vez (miúdos, 'todas desta fatura')."""
    if not rows:
        return 0
    ws = write_ws(aba)
    col = _col_status(ws)
    letra = gspread.utils.rowcol_to_a1(1, col).rstrip("1")
    _com_retry(lambda: ws.batch_update([{"range": f"{letra}{int(r)}", "values": [[status]]} for r in rows], value_input_option="RAW"))
    return len(rows)


def cancelar_lancamento(row_number: int, motivo: str) -> None:
    """Backup = Status 'Cancelado' (nunca apaga). O motivo vai pra Mensagem Original (col J)
    pra ficar rastreável, no mesmo padrão das conciliações feitas pelo Claude."""
    ws = write_ws("Lançamentos")
    r = int(row_number)
    msg = _com_retry(lambda: ws.acell(f"J{r}").value) or ""
    _com_retry(lambda: ws.batch_update([
        {"range": f"O{r}", "values": [["Cancelado"]]},
        {"range": f"J{r}", "values": [[(msg + " " + motivo).strip()]]},
    ], value_input_option="RAW"))
