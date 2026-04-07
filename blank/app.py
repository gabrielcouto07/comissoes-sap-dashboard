#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — Dashboard de Comissões Scientific PRD v3.0
====================================================
CORREÇÕES v3.0:
- FIX #1: pd.read_excel agora usa io.BytesIO(content) — resolve "No columns to parse"
- FIX #2: load_commission_table sem @st.cache_data (evita bug com st.error em cache)
- FIX #3: Filtros corrigidos (sel_filial, sel_uf retornam list sempre)
- FIX #4: Melhor detecção de colunas (aliases, case-insensitive)
- NOVO: Filtros pós-resultado (UF, Grupo, comissão mínima)
- NOVO: UI melhorada com cards KPI, header gradiente, diagnóstico de erros
"""

import os, re, io, warnings
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# CONFIG DA PÁGINA
# ─────────────────────────────────────────────────────────────
st.set_page_config(
  page_title="Comissões · Scientific PRD",
  page_icon="💰",
  layout="wide",
  initial_sidebar_state="expanded",
)

st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#1e293b 0%,#0f172a 100%);
}
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
section[data-testid="stSidebar"] hr { border-color:#334155 !important; }

.page-header {
    background: linear-gradient(135deg,#0f172a 0%,#1e40af 55%,#6d28d9 100%);
    border-radius:14px; padding:1.4rem 2rem; color:white; margin-bottom:1.5rem;
}
.page-header h1 { color:white; margin:0; font-size:1.6rem; }
.page-header p  { color:#bfdbfe; margin:0.2rem 0 0; font-size:0.85rem; }

.kpi-card {
    background:white; border-radius:10px; padding:0.9rem 1.1rem;
    border-left:4px solid; box-shadow:0 2px 6px rgba(0,0,0,.07);
}
.kpi-card.blue   { border-color:#3b82f6; }
.kpi-card.green  { border-color:#22c55e; }
.kpi-card.purple { border-color:#a855f7; }
.kpi-card.amber  { border-color:#f59e0b; }
.kpi-card.teal   { border-color:#14b8a6; }
.kpi-card.rose   { border-color:#f43f5e; }
.kpi-title { font-size:.7rem; font-weight:600; color:#64748b;
             text-transform:uppercase; letter-spacing:.05em; margin:0; }
.kpi-value { font-size:1.4rem; font-weight:700; color:#0f172a; margin:.2rem 0 0; }
.kpi-sub   { font-size:.68rem; color:#94a3b8; margin:.1rem 0 0; }

.filter-box {
    background:#f8fafc; border:1px solid #e2e8f0;
    border-radius:12px; padding:1rem 1.2rem; margin-bottom:1.2rem;
}
.diag-box {
    background:#fff7ed; border:1px solid #fed7aa;
    border-radius:8px; padding:1rem; margin:0.5rem 0;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def parse_decimal(value) -> float:
  if pd.isna(value):
      return 0.0
  s = str(value).strip().replace(",", ".")
  s = re.sub(r"[^\d.\-]", "", s)
  try:
      return float(s)
  except ValueError:
      return 0.0

def fmt_brl(v: float) -> str:
  try:
      r = f"R$ {abs(v):,.2f}".replace(",","X").replace(".","," ).replace("X",".")
      return f"-{r}" if v < 0 else r
  except:
      return "R$ 0,00"

def pct_fmt(v: float) -> str:
  return f"{v:.2f}%"


# ─────────────────────────────────────────────────────────────
# MAPEAMENTO DE COLUNAS (aliases do SAP)
# ─────────────────────────────────────────────────────────────
# Chave = nome canônico esperado pelo app
# Valor = lista de possíveis nomes no export SAP
COLUMN_ALIASES = {
  "Documento":               ["Documento"],
  "Filial":                  ["Filial", "BPLName"],
  "Código Item":             ["Código Item", "Codigo Item", "ItemCode"],
  "Descrição Item":          ["Descrição Item", "Descricao Item", "Dscription", "ItemName"],
  "Grupo de Itens":          ["Grupo de Itens", "ItmsGrpNam"],
  "Vendedor":                ["Vendedor", "SlpName"],
  "SlpCode":                 ["SlpCode", "Cód. Vendedor"],
  "Cliente":                 ["Cliente", "CardName"],
  "Cód. Cliente":            ["Cód. Cliente", "Cod. Cliente", "CardCode"],
  "UF":                      ["UF", "Estado", "State"],
  "Nº NF":                   ["Nº NF", "Serial", "Nr NF"],
  "Nº Documento":            ["Nº Documento", "DocNum"],
  "Data Faturamento":        ["Data Faturamento", "DocDate"],
  "Uso":                     ["Uso", "Usage"],
  "Quantidade":              ["Quantidade", "Quantity"],
  "Valor de Venda (Linha)":  ["Valor de Venda (Linha)", "LineTotal"],
  "Valor Total NF":          ["Valor Total NF", "DocTotal"],
  "Valor Recebido (Linha)":  ["Valor Recebido (Linha)", "LineReceived"],
  "% Recebido NF":           ["% Recebido NF", "PctRecebido"],
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
  """Normaliza nomes de colunas usando aliases (case-insensitive, strip)."""
  reverse = {}
  for canonical, aliases in COLUMN_ALIASES.items():
      for a in aliases:
          reverse[a.upper().strip()] = canonical

  rename = {}
  for col in df.columns:
      canonical = reverse.get(col.upper().strip())
      if canonical:
          rename[col] = canonical
  df = df.rename(columns=rename)
  df.columns = [c.strip() for c in df.columns]

  # Numeric
  for col in ["Valor de Venda (Linha)", "Valor Total NF",
              "Valor Recebido (Linha)", "% Recebido NF", "Quantidade"]:
      if col in df.columns:
          df[col] = df[col].apply(parse_decimal)

  # SlpCode
  if "SlpCode" in df.columns:
      df["SlpCode"] = pd.to_numeric(df["SlpCode"], errors="coerce").fillna(-1).astype(int)

  # Strings uppercase
  for col in ["Código Item", "Vendedor", "Documento"]:
      if col in df.columns:
          df[col] = df[col].astype(str).str.strip().str.upper()

  # Date
  if "Data Faturamento" in df.columns:
      df["Data Faturamento"] = pd.to_datetime(
          df["Data Faturamento"], errors="coerce", dayfirst=True)

  return df


# ─────────────────────────────────────────────────────────────
# CARGA DO ARQUIVO DE VENDAS
# ─────────────────────────────────────────────────────────────
def load_sales_file(uploaded_file):
  """
  Retorna (DataFrame, erro_str).
  FIX #1: lê bytes e usa io.BytesIO para evitar "No columns to parse from file".
  """
  name = uploaded_file.name.lower()

  # Sempre seek(0) antes de ler
  try:
      uploaded_file.seek(0)
  except Exception:
      pass

  content = uploaded_file.read()
  if not content:
      return None, "Arquivo vazio."

  # ── Tenta Excel ────────────────────────────────────────────
  if name.endswith((".xlsx", ".xls")):
      errors_xl = []
      for header_row in [0, 1, 2]:          # tenta com cabeçalho em linhas diferentes
          try:
              df = pd.read_excel(
                  io.BytesIO(content),      # ← FIX #1 aqui
                  dtype=str,
                  header=header_row,
                  na_filter=False,
              )
              df.columns = [str(c).strip() for c in df.columns]
              if len(df.columns) >= 3 and len(df) > 0:
                  return df, None
          except Exception as e:
              errors_xl.append(str(e))
      # Fallback: tenta como CSV (SAP às vezes salva CSV com extensão .xlsx)
      for enc in ["utf-8-sig", "latin-1", "cp1252"]:
          try:
              text = content.decode(enc, errors="replace")
              for sep in ["\t", ";", ","]:
                  try:
                      df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, na_filter=False)
                      if len(df.columns) >= 3:
                          df.columns = [str(c).strip() for c in df.columns]
                          return df, None
                  except Exception:
                      continue
          except Exception:
              continue
      return None, f"Não foi possível ler o arquivo Excel. Erros: {'; '.join(errors_xl[:2])}"

  # ── CSV / TXT ──────────────────────────────────────────────
  for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
      try:
          text = content.decode(enc, errors="replace")
          for sep in ["\t", ";", ","]:
              try:
                  df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, na_filter=False)
                  if len(df.columns) >= 3:
                      df.columns = [str(c).strip() for c in df.columns]
                      return df, None
              except Exception:
                  continue
      except Exception:
          continue

  return None, f"Formato não reconhecido: '{uploaded_file.name}'"


# ─────────────────────────────────────────────────────────────
# CARGA DA TABELA DE COMISSÕES
# ─────────────────────────────────────────────────────────────
# FIX #2: sem @st.cache_data para evitar bug com st.error/st.stop dentro do cache
def load_commission_table(path: str):
  """Retorna (commission_dict, name_map_dict, error_str)."""
  # Tenta caminhos alternativos se o arquivo não existir
  if not os.path.exists(path):
      alt_path = os.path.join(os.path.dirname(__file__), path)
      if not os.path.exists(alt_path):
          return None, None, f"Arquivo '{path}' não encontrado. Coloque comissoes.csv na pasta do app (tentou: {path}, {alt_path})"
      path = alt_path

  try:
      df = pd.read_csv(path, sep=";", dtype=str)
  except Exception as e:
      return None, None, f"Erro ao ler comissoes.csv: {e}"

  required_cols = {"SlpCode", "ItemCode", "CommissionPct", "SlpName"}
  missing = required_cols - set(df.columns)
  if missing:
      return None, None, f"Colunas ausentes em comissoes.csv: {missing}"

  commission, name_map = {}, {}
  for _, row in df.iterrows():
      try:
          slp  = int(str(row["SlpCode"]).strip())
          item = str(row["ItemCode"]).strip().upper()
          pct  = parse_decimal(row["CommissionPct"])
          name = str(row["SlpName"]).strip().upper()
          key  = (slp, item)
          commission[key] = max(commission.get(key, 0.0), pct)
          name_map[slp]   = name
      except Exception:
          continue

  return commission, name_map, None


# ─────────────────────────────────────────────────────────────
# CÁLCULO DE COMISSÕES
# ─────────────────────────────────────────────────────────────
def calculate_commissions(df: pd.DataFrame, commission: dict, name_map: dict):
  has_slp  = "SlpCode" in df.columns
  inv_name = {v: k for k, v in name_map.items()}

  def resolve_slp(row):
      if has_slp:
          try:
              v = int(row.get("SlpCode", -1))
              if v > 0:
                  return v
          except Exception:
              pass
      nm = str(row.get("Vendedor", "")).strip().upper()
      return inv_name.get(nm, -1)

  missing_log = set()
  bases, pcts, comiss, slps = [], [], [], []

  for _, row in df.iterrows():
      slp  = resolve_slp(row)
      item = str(row.get("Código Item", "")).strip().upper()
      doc  = str(row.get("Documento", "NF")).strip().upper()

      # Dev NF → usa valor de venda (já negativo); NF → usa valor recebido
      if "DEV" in doc:
          base = parse_decimal(row.get("Valor de Venda (Linha)", 0))
      else:
          base = parse_decimal(row.get("Valor Recebido (Linha)", 0))

      key = (slp, item)
      pct = commission.get(key)
      if pct is None:
          missing_log.add(key)
          pct = 0.0

      bases.append(round(base, 2))
      pcts.append(pct)
      comiss.append(round(base * pct / 100, 2))
      slps.append(slp)

  df = df.copy()
  df["_SlpCode"]       = slps
  df["_BaseComissao"]  = bases
  df["_PctComissao"]   = pcts
  df["_ValorComissao"] = comiss

  return df, missing_log


# ─────────────────────────────────────────────────────────────
# EXPORTAÇÃO EXCEL
# ─────────────────────────────────────────────────────────────
def to_excel_bytes(sheets: dict) -> bytes:
  buf = io.BytesIO()
  with pd.ExcelWriter(buf, engine="openpyxl") as writer:
      for name, df in sheets.items():
          df.to_excel(writer, sheet_name=name[:31], index=False)
  return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
  st.markdown("""
  <div style="text-align:center;padding:1rem 0 0.5rem">
      <span style="font-size:2.5rem">💰</span>
      <h2 style="color:#e2e8f0;margin:.25rem 0 0;font-size:1.15rem">Comissões SAP</h2>
      <p style="color:#475569;font-size:.72rem;margin:0">Scientific PRD · v3.0</p>
  </div>
  """, unsafe_allow_html=True)

  st.markdown("---")
  st.subheader("📂 Upload de Dados")
  uploaded = st.file_uploader(
      "Export SAP (.xlsx / .csv)",
      type=["xlsx", "xls", "csv"],
      help="Arquivo gerado pela query SAP com as colunas padrão",
  )

  st.markdown("---")
  st.subheader("⚙️ Configurações")
  comm_path = st.text_input("Tabela de comissões", value="comissoes.csv")

  st.markdown("---")
  st.caption("© 2025 Scientific PRD")


# ─────────────────────────────────────────────────────────────
# TELA INICIAL
# ─────────────────────────────────────────────────────────────
if uploaded is None:
  st.markdown("""
  <div class="page-header">
      <h1>💰 Calculadora de Comissões</h1>
      <p>Scientific PRD · Carregue o export SAP para começar</p>
  </div>
  """, unsafe_allow_html=True)

  c1, c2, c3 = st.columns(3)
  c1.info("**1️⃣ Upload**\n\nImporte o export CSV/XLSX da query SAP pela sidebar esquerda.")
  c2.info("**2️⃣ Filtros**\n\nFiltre por vendedor, filial, UF, período e tipo de documento.")
  c3.info("**3️⃣ Resultados**\n\nVisualize gráficos, tabelas detalhadas e exporte em Excel.")

  with st.expander("📋 Colunas esperadas no export SAP"):
      st.markdown("""
      | Coluna | Obrigatória |
      |--------|:-----------:|
      | `Documento` | ✅ (NF / Dev NF) |
      | `Código Item` | ✅ |
      | `Vendedor` | ✅ |
      | `Valor de Venda (Linha)` | ✅ |
      | `Valor Recebido (Linha)` | ✅ |
      | `Filial` | Opcional |
      | `Data Faturamento` | Opcional |
      | `UF` | Opcional |
      | `Grupo de Itens` | Opcional |
      | `SlpCode` | Opcional (melhora precisão) |
      """)
  st.stop()


# ─────────────────────────────────────────────────────────────
# CARGA E PROCESSAMENTO
# ─────────────────────────────────────────────────────────────
with st.spinner("🔄 Carregando e calculando comissões..."):

  # 1. Tabela de comissões
  commission, name_map, comm_err = load_commission_table(comm_path)
  if comm_err:
      st.error(f"❌ {comm_err}")
      st.stop()

  # 2. Arquivo de vendas
  df_raw, file_err = load_sales_file(uploaded)
  if file_err or df_raw is None:
      st.error(f"❌ Erro ao ler arquivo: {file_err or 'Arquivo não pôde ser lido.'}")
      st.stop()

  # 3. Normalizar colunas
  df_raw = normalize_columns(df_raw)

  # 4. Validar colunas obrigatórias
  required = ["Documento", "Código Item", "Vendedor",
              "Valor de Venda (Linha)", "Valor Recebido (Linha)"]
  missing_cols = [c for c in required if c not in df_raw.columns]

  if missing_cols:
      st.error(f"❌ Colunas obrigatórias não encontradas: `{missing_cols}`")
      with st.expander("🔍 Diagnóstico — colunas encontradas no arquivo"):
          st.markdown('<div class="diag-box">', unsafe_allow_html=True)
          st.write(f"**{len(df_raw.columns)} colunas detectadas:**")
          st.code(", ".join(df_raw.columns.tolist()))
          st.write("**Primeiras 3 linhas:**")
          st.dataframe(df_raw.head(3))
          st.markdown('</div>', unsafe_allow_html=True)
      st.info("💡 Verifique se o export SAP usa exatamente os nomes de colunas esperados.")
      st.stop()

  # 5. Calcular comissões
  df_calc, missing_keys = calculate_commissions(df_raw, commission, name_map)


# ─────────────────────────────────────────────────────────────
# HEADER DA PÁGINA
# ─────────────────────────────────────────────────────────────
ts_now = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"""
<div class="page-header">
  <h1>💰 Relatório de Comissões</h1>
  <p>{uploaded.name} &nbsp;·&nbsp; {len(df_calc):,} linhas &nbsp;·&nbsp; {ts_now}</p>
</div>
""", unsafe_allow_html=True)

if missing_keys:
  st.warning(f"⚠️ **{len(missing_keys)}** combinações (Vendedor + Item) sem % cadastrado → comissão = R$ 0,00")


# ─────────────────────────────────────────────────────────────
# FILTROS  (FIX #3: todas as variáveis são sempre listas)
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="filter-box">', unsafe_allow_html=True)
st.markdown("**🔍 Filtros**")

vendedores_all = sorted(df_calc["Vendedor"].dropna().unique().tolist())
filiais_all    = sorted(df_calc["Filial"].dropna().unique().tolist())         if "Filial"          in df_calc.columns else []
uf_all         = sorted(df_calc["UF"].dropna().unique().tolist())             if "UF"              in df_calc.columns else []
docs_all       = sorted(df_calc["Documento"].dropna().unique().tolist())
grupos_all     = sorted(df_calc["Grupo de Itens"].dropna().unique().tolist()) if "Grupo de Itens"  in df_calc.columns else []

fa, fb, fc, fd, fe = st.columns([2, 2, 2, 2, 2])
with fa:
  sel_vend   = st.multiselect("👤 Vendedor",   vendedores_all, default=vendedores_all)
with fb:
  # FIX #3 — sempre retorna lista
  sel_filial = st.multiselect("🏢 Filial",     filiais_all,    default=filiais_all)   if filiais_all else []
with fc:
  sel_uf     = st.multiselect("📍 UF",         uf_all,         default=uf_all)        if uf_all     else []
with fd:
  sel_doc    = st.multiselect("📄 Documento",  docs_all,       default=docs_all)
with fe:
  sel_grupo  = st.multiselect("📦 Grupo",      grupos_all,     default=grupos_all)    if grupos_all else []

f2a, f2b = st.columns([3, 3])
with f2a:
  min_comis = st.number_input("💰 Comissão mínima (R$)", value=0.0, min_value=0.0, step=10.0)
with f2b:
  has_date = "Data Faturamento" in df_calc.columns and df_calc["Data Faturamento"].notna().any()
  if has_date:
      try:
          min_dt     = df_calc["Data Faturamento"].min().date()
          max_dt     = df_calc["Data Faturamento"].max().date()
          date_range = st.date_input("📅 Período", value=(min_dt, max_dt),
                                     min_value=min_dt, max_value=max_dt)
      except Exception:
          date_range = None
          has_date = False
  else:
      date_range = None
st.markdown('</div>', unsafe_allow_html=True)

# ── Aplica filtros ─────────────────────────────────────────────
df_f = df_calc.copy()
if sel_vend:                                              df_f = df_f[df_f["Vendedor"].isin(sel_vend)]
if sel_filial and "Filial" in df_f.columns:               df_f = df_f[df_f["Filial"].isin(sel_filial)]
if sel_uf and "UF" in df_f.columns:                       df_f = df_f[df_f["UF"].isin(sel_uf)]
if sel_doc:                                               df_f = df_f[df_f["Documento"].isin(sel_doc)]
if sel_grupo and "Grupo de Itens" in df_f.columns:        df_f = df_f[df_f["Grupo de Itens"].isin(sel_grupo)]
if min_comis > 0:                                         df_f = df_f[df_f["_ValorComissao"].abs() >= min_comis]
if date_range and len(date_range) == 2 and has_date and "Data Faturamento" in df_f.columns:
  d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
  df_f = df_f[df_f["Data Faturamento"].between(d0, d1)]

if df_f.empty:
  st.warning("⚠️ Nenhum dado com os filtros selecionados.")
  st.stop()


# ─────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────
tv  = df_f["Valor de Venda (Linha)"].sum()
tr  = df_f["Valor Recebido (Linha)"].sum()
tb  = df_f["_BaseComissao"].sum()
tc  = df_f["_ValorComissao"].sum()
pm  = (tc / tb * 100) if tb != 0 else 0
nv  = df_f["Vendedor"].nunique()

kpis = [
  ("💼 Vendas Totais",    fmt_brl(tv), "blue",   ""),
  ("💳 Valor Recebido",   fmt_brl(tr), "teal",   f"{tr/tv*100:.1f}% das vendas" if tv else ""),
  ("📊 Base Comissão",    fmt_brl(tb), "purple", ""),
  ("💰 Comissão Total",   fmt_brl(tc), "green",  f"% médio: {pm:.2f}%"),
  ("👤 Vendedores",       str(nv),     "amber",  f"{len(df_f):,} linhas"),
  ("🏪 Clientes",
   str(df_f["Cliente"].nunique()) if "Cliente" in df_f.columns else "-",
   "rose",  ""),
]
cols_k = st.columns(6)
for (label, value, color, sub), col in zip(kpis, cols_k):
  with col:
      st.markdown(f"""
      <div class="kpi-card {color}">
        <p class="kpi-title">{label}</p>
        <p class="kpi-value">{value}</p>
        <p class="kpi-sub">{sub if sub else "&nbsp;"}</p>
      </div>""", unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────
# AGREGAÇÕES
# ─────────────────────────────────────────────────────────────
resumo_vend = (
  df_f.groupby("Vendedor")
  .agg(
      Qtd_Linhas =("Documento",              "count"),
      Vendas     =("Valor de Venda (Linha)",  "sum"),
      Recebido   =("Valor Recebido (Linha)",  "sum"),
      Base       =("_BaseComissao",           "sum"),
      Comissao   =("_ValorComissao",          "sum"),
  )
  .reset_index()
  .sort_values("Comissao", ascending=False)
)
resumo_vend["% Com. Médio"] = (
  resumo_vend["Comissao"] / resumo_vend["Base"].replace(0, np.nan) * 100
).round(2).fillna(0)
resumo_vend["% Recebido"] = (
  resumo_vend["Recebido"] / resumo_vend["Vendas"].replace(0, np.nan) * 100
).round(2).fillna(0)

# Validar se 'Descrição Item' existe antes de usar (ERRO #2)
groupby_cols = ["Código Item"]
if "Descrição Item" in df_f.columns:
    groupby_cols.append("Descrição Item")

det_item = (
  df_f.groupby(groupby_cols)
  .agg(
      Qtd_Vendedores=("Vendedor",                "nunique"),
      Qtd           =("Quantidade",              "sum"),
      Vendas        =("Valor de Venda (Linha)",  "sum"),
      Base          =("_BaseComissao",           "sum"),
      Comissao      =("_ValorComissao",          "sum"),
  )
  .reset_index()
  .sort_values("Comissao", ascending=False)
)


# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
  "📊 Dashboard",
  "👤 Por Vendedor",
  "📦 Por Item",
  "📋 Dados Completos",
  "⚠️ Sem % Cadastrado",
  "📥 Exportar",
])

# ── TAB 1: DASHBOARD ──────────────────────────────────────────
with tab1:
  c1, c2 = st.columns(2)

  fig1 = px.bar(
      resumo_vend.sort_values("Comissao"),
      x="Comissao", y="Vendedor", orientation="h",
      title="💰 Comissão por Vendedor",
      labels={"Comissao": "R$", "Vendedor": ""},
      color="Comissao", color_continuous_scale=["#93c5fd","#1d4ed8"],
      text=resumo_vend.sort_values("Comissao")["Comissao"].apply(fmt_brl),
  )
  fig1.update_traces(textposition="outside")
  fig1.update_layout(
      showlegend=False, coloraxis_showscale=False,
      height=max(300, len(resumo_vend)*42+80),
      plot_bgcolor="white", paper_bgcolor="white",
      margin=dict(l=10, r=90, t=40, b=10),
  )
  fig1.update_xaxes(showgrid=True, gridcolor="#f1f5f9", zeroline=True)
  c1.plotly_chart(fig1, use_container_width=True)

  fig2 = px.pie(
      resumo_vend[resumo_vend["Comissao"] > 0],
      values="Comissao", names="Vendedor",
      title="🥧 Distribuição de Comissão",
      hole=0.45,
      color_discrete_sequence=px.colors.qualitative.Plotly,
  )
  fig2.update_traces(textinfo="percent+label", textfont_size=11)
  fig2.update_layout(showlegend=False, paper_bgcolor="white", height=360)
  c2.plotly_chart(fig2, use_container_width=True)

  c3, c4 = st.columns(2)

  if has_date:
      df_t = df_f.copy()
      df_t["Mês"] = df_t["Data Faturamento"].dt.to_period("M").astype(str)
      ev = df_t.groupby(["Mês","Vendedor"])["_ValorComissao"].sum().reset_index()
      fig3 = px.line(ev, x="Mês", y="_ValorComissao", color="Vendedor",
                     title="📈 Evolução Mensal", markers=True,
                     labels={"_ValorComissao": "R$", "Mês": ""})
      fig3.update_layout(plot_bgcolor="white", paper_bgcolor="white", height=300,
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
      fig3.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
      fig3.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
      c3.plotly_chart(fig3, use_container_width=True)
  else:
      c3.info("📅 'Data Faturamento' não disponível para gráfico temporal.")

  doc_g = df_f.groupby("Documento")["_ValorComissao"].sum().reset_index()
  fig4 = px.bar(doc_g, x="Documento", y="_ValorComissao",
                title="📄 Comissão NF vs Dev NF",
                labels={"_ValorComissao": "R$", "Documento": ""},
                color="Documento",
                color_discrete_map={"NF": "#22c55e", "DEV NF": "#ef4444"},
                text=doc_g["_ValorComissao"].apply(fmt_brl))
  fig4.update_traces(textposition="outside")
  fig4.update_layout(showlegend=False, plot_bgcolor="white",
                     paper_bgcolor="white", height=300)
  c4.plotly_chart(fig4, use_container_width=True)

  # Top 15 itens
  top15 = det_item.head(15).sort_values("Comissao")
  fig5 = px.bar(top15, x="Comissao", y="Código Item", orientation="h",
                title="🏆 Top 15 Itens por Comissão",
                labels={"Comissao": "R$", "Código Item": ""},
                color="Comissao", color_continuous_scale=["#86efac","#166534"],
                text=top15["Comissao"].apply(fmt_brl))
  fig5.update_traces(textposition="outside")
  fig5.update_layout(showlegend=False, coloraxis_showscale=False,
                     height=450, plot_bgcolor="white", paper_bgcolor="white",
                     margin=dict(l=10, r=90, t=40, b=10))
  st.plotly_chart(fig5, use_container_width=True)


# ── TAB 2: POR VENDEDOR ────────────────────────────────────────
with tab2:
  disp_rv = resumo_vend.copy()
  for c in ["Vendas","Recebido","Base","Comissao"]:
      disp_rv[c] = disp_rv[c].apply(fmt_brl)
  disp_rv["% Com. Médio"] = disp_rv["% Com. Médio"].apply(pct_fmt)
  disp_rv["% Recebido"]   = disp_rv["% Recebido"].apply(pct_fmt)
  st.caption(f"📊 {len(resumo_vend)} vendedores")
  st.dataframe(disp_rv, use_container_width=True, height=300)

  st.markdown("---")
  st.subheader("🔍 Detalhe por Vendedor + Item")
  sel_vend_det = st.selectbox("Vendedor:", resumo_vend["Vendedor"].tolist())

  if sel_vend_det:
      df_v = df_f[df_f["Vendedor"] == sel_vend_det]
      m1,m2,m3,m4 = st.columns(4)
      m1.metric("Vendas",       fmt_brl(df_v["Valor de Venda (Linha)"].sum()))
      m2.metric("Recebido",     fmt_brl(df_v["Valor Recebido (Linha)"].sum()))
      m3.metric("Base",         fmt_brl(df_v["_BaseComissao"].sum()))
      m4.metric("Comissão",     fmt_brl(df_v["_ValorComissao"].sum()))

      # Validar se 'Descrição Item' existe antes de usar (ERRO #3)
      groupby_cols_v = ["Código Item","_PctComissao"]
      if "Descrição Item" in df_v.columns:
          groupby_cols_v.insert(1, "Descrição Item")
      
      det_v = (
          df_v.groupby(groupby_cols_v)
          .agg(Qtd=("Quantidade","sum"),
               Vendas=("Valor de Venda (Linha)","sum"),
               Recebido=("Valor Recebido (Linha)","sum"),
               Base=("_BaseComissao","sum"),
               Comissao=("_ValorComissao","sum"))
          .reset_index()
          .sort_values("Comissao", ascending=False)
          .rename(columns={"_PctComissao":"% Comissão"})
      )
      srch = st.text_input("🔍 Filtrar itens", key="srch_v")
      if srch:
          mask = det_v.astype(str).apply(
              lambda col: col.str.contains(srch, case=False, na=False)).any(axis=1)
          det_v = det_v[mask]

      dv = det_v.copy()
      for c in ["Vendas","Recebido","Base","Comissao"]: dv[c] = dv[c].apply(fmt_brl)
      st.caption(f"{len(det_v)} itens para {sel_vend_det}")
      st.dataframe(dv, use_container_width=True, height=420)


# ── TAB 3: POR ITEM ────────────────────────────────────────────
with tab3:
  # Validar se det_item não está vazio (ERRO #4)
  if det_item.empty:
      st.warning("⚠️ Nenhum item encontrado para análise.")
  else:
      srch_item = st.text_input("🔍 Buscar item (código ou descrição)")
      di = det_item.copy()
      if srch_item:
          mask = di.astype(str).apply(
              lambda col: col.str.contains(srch_item, case=False, na=False)).any(axis=1)
          di = di[mask]
      st.caption(f"{len(di)} itens distintos")
      did = di.copy()
      for c in ["Vendas","Base","Comissao"]: did[c] = did[c].apply(fmt_brl)
      st.dataframe(did, use_container_width=True, height=480)


# ── TAB 4: DADOS COMPLETOS ─────────────────────────────────────
with tab4:
  show_cols = [c for c in [
      "Documento","Filial","Código Item","Descrição Item","Grupo de Itens",
      "Vendedor","Cliente","UF","Nº NF","Data Faturamento",
      "Quantidade","Valor de Venda (Linha)","Valor Recebido (Linha)",
      "_PctComissao","_BaseComissao","_ValorComissao",
  ] if c in df_f.columns]

  disp_full = df_f[show_cols].rename(columns={
      "_PctComissao":"% Comissão",
      "_BaseComissao":"Base Comissão",
      "_ValorComissao":"Valor Comissão",
  })

  da, db = st.columns([4, 2])
  srch_full = da.text_input("🔍 Buscar em todos os campos")
  doc_f2    = db.selectbox("Documento", ["Todos"] + docs_all, key="doc_full")

  if srch_full:
      mask = disp_full.astype(str).apply(
          lambda col: col.str.contains(srch_full, case=False, na=False)).any(axis=1)
      disp_full = disp_full[mask]
  if doc_f2 != "Todos":
      disp_full = disp_full[disp_full["Documento"] == doc_f2]

  st.caption(f"{len(disp_full):,} linhas")
  st.dataframe(disp_full, use_container_width=True, height=520)


# ── TAB 5: SEM % CADASTRADO ────────────────────────────────────
with tab5:
  if missing_keys:
      st.warning(f"⚠️ **{len(missing_keys)}** combinações sem % cadastrado → Comissão = R$ 0,00")
      miss_df = pd.DataFrame(
          sorted(missing_keys), columns=["SlpCode","Código Item"])
      miss_df["Vendedor"] = miss_df["SlpCode"].map(name_map).fillna("(não encontrado)")
      st.dataframe(miss_df, use_container_width=True)
      st.info("💡 Adicione as regras no SAP (tabela @RBH_COMISSAO) ou no `comissoes.csv`.")
  else:
      st.success("✅ Todos os itens possuem percentual cadastrado!")


# ── TAB 6: EXPORTAR ────────────────────────────────────────────
with tab6:
  st.subheader("📥 Exportar")
  ts = datetime.now().strftime("%Y%m%d_%H%M")

  export_dados = df_f[[c for c in [
      "Documento","Filial","Código Item","Descrição Item","Grupo de Itens",
      "Vendedor","Cliente","UF","Nº NF","Data Faturamento",
      "Quantidade","Valor de Venda (Linha)","Valor Recebido (Linha)",
      "_PctComissao","_BaseComissao","_ValorComissao",
  ] if c in df_f.columns]].rename(columns={
      "_PctComissao":"% Comissão",
      "_BaseComissao":"Base Comissão",
      "_ValorComissao":"Valor Comissão",
  })

  ec1, ec2, ec3 = st.columns(3)
  with ec1:
      xlsx = to_excel_bytes({
          "Resumo_Vendedor": resumo_vend,
          "Dados_Completos": export_dados,
          "Detalhe_Item":    det_item,
      })
      st.download_button("📊 Excel Completo (3 abas)", data=xlsx,
                         file_name=f"comissoes_{ts}.xlsx",
                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         use_container_width=True)
  with ec2:
      csv_r = resumo_vend.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
      st.download_button("📄 Resumo CSV", data=csv_r,
                         file_name=f"resumo_{ts}.csv", mime="text/csv",
                         use_container_width=True)
  with ec3:
      csv_d = export_dados.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
      st.download_button("📋 Dados Completos CSV", data=csv_d,
                         file_name=f"dados_{ts}.csv", mime="text/csv",
                         use_container_width=True)

  st.markdown("---")
  st.caption(f"Exportando {len(df_f):,} linhas filtradas • Gerado {ts_now}")

  pv = resumo_vend.copy()
  for c in ["Vendas","Recebido","Base","Comissao"]: pv[c] = pv[c].apply(fmt_brl)
  pv["% Com. Médio"] = pv["% Com. Médio"].apply(pct_fmt)
  st.dataframe(pv, use_container_width=True)