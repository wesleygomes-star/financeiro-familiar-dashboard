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


def write_ws(name: str):
    """Worksheet com permissão de escrita."""
    return _write_client().open_by_key(SHEET_ID).worksheet(name)


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
