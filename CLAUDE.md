# Financeiro Família Gomes — Dashboard

Dashboard Streamlit conectado ao Google Sheets, alimentado pelo fluxo
WhatsApp (Evolution API) → n8n (Railway) → OpenAI → Google Sheets.

## Links rápidos

- **Dashboard produção:** https://financeiro-familia-gomes.streamlit.app (senha `familia2026`)
- **Repo:** https://github.com/wesleygomes-star/financeiro-familiar-dashboard
- **Planilha Google Sheets:** ID `1cl9heM5gZiMVbGlWa8j_BlYEa0MwBq40k_bK27H_qaA`
- **n8n self-host:** https://n8n-production-d185.up.railway.app
- **Evolution API:** https://evolution-api-production-8e8e.up.railway.app (instância `financeiro-familiar`)
- **Doc fonte-da-verdade:** `~/Library/Mobile Documents/com~apple~CloudDocs/IA WESLEY/PESSOAL/Financeiro Familiar/ESTADO_DO_PROJETO.md`

## Stack do dashboard

- Streamlit 1.40+ (Python)
- gspread + Google Service Account (leitura)
- plotly (gráficos interativos com drill-down `on_select="rerun"`)
- Streamlit Community Cloud (auto-deploy on push pra `main`)

## Estrutura

```
streamlit_app.py       # Página principal (Família)
lib/data.py            # Acesso Sheets + helpers (filtragem, classificação Fixa/Variável, mês anterior, ritmo)
lib/components.py      # KPIs, donut, barras, heatmap, breakdown Fixa/Var, projeção, tabelas
.streamlit/config.toml # Tema escuro
.streamlit/secrets.toml # NÃO COMMITAR (já está no gitignore)
```

## Comandos comuns

```bash
# Rodar local (precisa de /tmp/sa_key.json com a key da Service Account)
python3 -m pip install --user -r requirements.txt
streamlit run streamlit_app.py
# → abre em http://localhost:8501

# Deploy = git push pra main (Streamlit Cloud detecta sozinho em ~30-60s)
git push

# Se o deploy não pegar: trigger manual com commit vazio
git commit --allow-empty -m "chore: trigger redeploy" && git push

# Forçar reboot manual: share.streamlit.io → app → ⋮ → Reboot
```

## Segredos

Todos os tokens vivem em `~/.config/financeiro-familiar/secrets.env` (chmod 600, fora do iCloud):

- `RAILWAY_TOKEN`
- `N8N_ENCRYPTION_KEY`
- `N8N_SELFHOST_API_KEY`
- `EVOLUTION_TOKEN` (também: `80F738C3DDAE-4F87-9FCE-DB12850B1541`)
- `SHEET_ID`
- `GROUP_JID` (`120363409520000410@g.us`)
- `GITHUB_PAT`

Service Account JSON da planilha **não fica salva em disco** — em produção vem dos secrets do Streamlit; em dev local pode ser baixada pra `/tmp/sa_key.json` (descartável).

Service Account: `n8n-sheets@moonlit-ceiling-496122-k2.iam.gserviceaccount.com` (Editor na planilha).

## Estado atual (atualizado 2026-05-15 tarde)

✅ **Dashboard em produção** com:
- Auth simples por senha
- Filtros: Competência vs Caixa, mês, pessoa (Família/Wesley/Sabrina), categoria, forma pgto, cartão
- KPIs com **delta vs mês anterior** (cor invertida em Despesa/Uso teto)
- **Indicador de ritmo** do mês em andamento (🚨/⚠️/✅ + projeção fim do mês)
- Drill-down **Fixa vs Variável** (matching automático contra recorrentes)
- Barras categoria vs teto (semáforo) com drill-down clicável
- Heatmap evolução mensal 6 meses
- Projeção 6 meses (Receita × Despesa)
- Top 10 despesas + tabela completa com busca/filtros
- **Layout responsivo mobile** (CSS @media query empilha colunas em <768px)

✅ **Backend resiliente:**
- Healthcheck Railway (`/healthz`) + restart ON_FAILURE max 10 retries
- UptimeRobot externo (combinado — Wesley deve confirmar setup)
- WF7 alertas WhatsApp (≥3 erros/h, ≥5 erros/24h)

## Pendências

| Prioridade | Tarefa |
|------------|--------|
| Alta | Wesley validar visualmente as 4 melhorias da fase 2 (mobile, deltas, ritmo, Fixa/Var) |
| Alta | Decidir competência da "Fatura Cartão XP R$ 3.004,01" (abril vs maio) — pendente desde incidente 2026-05-15 |
| Média | Cadastrar despesas fixas da Sabrina (com ela presente) |
| Média | Próxima etapa: produto SaaS (onboarding multi-tenant, pricing, landing) |
| Baixa | Open Finance integration (fase futura) |

## Gotchas / convenções

- **Plotly heatmap colorscale** exige TODOS os stops em `[0, 1]`. `zmax` mapeia o limite superior dos dados. Bug clássico: usar `2.0` quebra com `ValueError`.
- **gspread** auto-converte "R$ 1.234,56" pra int 123456. Sempre usar `numericise_ignore=['all']` em `get_all_records()`. O parser PT-BR de valor está em `lib/data.py::_parse_valor()`.
- **Competência vs Caixa:** dois modos. Competência = mês a que a despesa pertence (controle de teto). Caixa = mês em que o dinheiro sai (fluxo). Coluna `Mês Caixa` é derivada de `Data Caixa` em `load_lancamentos()`.
- **Streamlit cache:** dados têm TTL 60s. Botão "🔄 Atualizar" faz `st.cache_data.clear()` + `st.rerun()`.
- **Senha do dashboard** vem de `st.secrets["auth"]["password"]` (default `familia2026` se não setada).
- **Drill-down clicável** depende de `st.plotly_chart(..., on_select="rerun")` — feature do Streamlit 1.40+.
- **Categoria de recorrente** pode não bater 100% com lançamentos (heurística substring). Se Wesley reportar "tudo virou Variável", revisar coluna Descrição na planilha Recorrentes.

## Workflows n8n (referência rápida)

| WF | ID | Função |
|----|----|--------|
| WF1 | `xQHgAqsOa5kTuMyf` | Lançamento via WhatsApp |
| WF2 | `qxXvvyeF0f5yZCdq` | Alerta teto (≥80%) |
| WF3 | `aHGLBkNgSy2rM7IL` | Resumo semanal (domingo 20h) |
| WF4 | `Yh5qxfRPiTb32DkF` | Fechamento mensal (dia 1, 8h) |
| WF5 | `4ISay6TsBfRwng7U` | Recorrentes (dia 1, 7h) |
| WF6 | `7pRLSvoia90U3tly` | Sugestão investimento (dia 25, 8h) |
| WF7 | `HcnZxoYxqLlBDMLW` | Alertas proativos (erros) |

## Categorias (14 despesas, validadas 2026-05-13)

Moradia, Alimentação, Transporte, Saúde, Educação, Lazer & Restaurantes,
Vestuário, Pessoal & Beleza, Assinaturas & Streaming, Financeiro & Cartão,
Outros Imóveis (subcat Boa Vista), Investimentos em Imóvel, Auxílio Familiar
(Unimed Mãe + Faxineira Mamãe), Outros.

Receitas (6): Salário Wesley, Salário Sabrina, Pró-labore, Freelance/Extra,
Rendimentos, Outras Receitas.

## Identificação Wesley vs Sabrina (LIDs do WhatsApp)

- `100515321004134@lid` → Wesley
- `244624274759793@lid` → Sabrina (dispositivo 1)
- `166069373243568@lid` → Sabrina (dispositivo 2)

Mapeamento vive no nó "📊 Formatar para Planilha" do WF1.
