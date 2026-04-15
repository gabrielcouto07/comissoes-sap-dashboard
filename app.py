import io
import re
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# ════════════════════════════════════════════════════════════════════════════
# INJEÇÃO DE CSS — DEVE SER A PRIMEIRA COISA DO APP
# ════════════════════════════════════════════════════════════════════════════

def _inject_css():
    """Injeta theme.css no início da renderização — antes de qualquer elemento."""
    css_path = Path(__file__).parent / "theme.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

_inject_css()

# ════════════════════════════════════════════════════════════════════════════
# IMPORTS: Design System + UI Components
# ════════════════════════════════════════════════════════════════════════════

from config.colors import PALETTE, CHART_COLORS
from templates.ui import (
    load_theme,
    kpi_card,
    render_kpi_row,
    apply_chart_style,
    render_header,
    render_period_filter,
    render_separator,
    detect_time_granularity,
)

# Único import externo: VendasModel (lógica separada por complexidade)
from models.vendas_model import VendasModel

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO GLOBAL — DEBUG MODE
# ════════════════════════════════════════════════════════════════════════════

DEBUG_MODE = False   # True = mostra debug | False = oculta para apresentação

# FASE 1: FUNÇÕES DE FILTROS NOVOS (Sidebar Compacto)

def render_filtros_sidebar_vendas(df: pd.DataFrame):
    """
    Filtros compactos na sidebar — Fase 1 do Roadmap.
    ✅ Período com presets (Últ. 30/90 dias, Este ano)
    ✅ Vendedor com busca + "Selecionar todos"
    ✅ Estado como checkboxes em grid
    ✅ Grupo de Item com "Selecionar todos"
    ✅ Contadores de seleção
    """
    from datetime import timedelta
    
    st.sidebar.markdown("### 🔍 Filtros Inteligentes")
    filtros = {}
    
    # ── 1. Período com presets ────────────────────────────────────────
    if "SaleDate" in df.columns and df["SaleDate"].notna().any():
        d_min = df["SaleDate"].min().date()
        d_max = df["SaleDate"].max().date()
        
        st.sidebar.markdown("**📅 Período**")
        preset = st.sidebar.radio(
            "Escolha período",
            ["Todo período", "Últ. 30 dias", "Últ. 3 meses", "Este ano", "4️⃣ Personalizado"],
            horizontal=False, label_visibility="collapsed", key="v_preset"
        )
        
        hoje = pd.Timestamp.now().date()
        if preset == "Últ. 30 dias":
            d0, d1 = hoje - timedelta(30), hoje
        elif preset == "Últ. 3 meses":
            d0, d1 = hoje - timedelta(90), hoje
        elif preset == "Este ano":
            d0, d1 = pd.Timestamp(hoje.year, 1, 1).date(), hoje
        elif preset == "4️⃣ Personalizado":
            dr = st.sidebar.date_input("", value=(d_min, d_max), 
                                        min_value=d_min, max_value=d_max,
                                        key="v_date_custom", label_visibility="collapsed")
            d0, d1 = (dr[0], dr[1]) if len(dr) == 2 else (d_min, d_max)
        else:
            d0, d1 = d_min, d_max
        
        filtros["__date__"] = (d0, d1)
        st.sidebar.caption(f"📅 {d0.strftime('%d/%m/%y')} → {d1.strftime('%d/%m/%y')}")
    
    st.sidebar.markdown("---")
    
    # ── 2. Vendedor com busca ─────────────────────────────────────────
    if "SlpName" in df.columns:
        opts_vend = sorted(df["SlpName"].dropna().unique().tolist())
        st.sidebar.markdown(f"**👤 Vendedor** ({len(opts_vend)} disponíveis)")
        
        busca_v = st.sidebar.text_input("Buscar vendedor", key="v_busca_vend",
                                         placeholder="Digitar para filtrar...")
        opts_f = [o for o in opts_vend if busca_v.lower() in o.lower()] if busca_v else opts_vend
        
        todos_v = st.sidebar.checkbox(f"✅ Selecionar todos ({len(opts_f)})",
                                       value=True, key="v_all_vend")
        if todos_v:
            sel_v = opts_f
        else:
            sel_v = st.sidebar.multiselect("", opts_f, key="v_sel_vend",
                                           label_visibility="collapsed")
        filtros["SlpName"] = sel_v
    
    st.sidebar.markdown("---")
    
    # ── 3. Estado: checkboxes em grid 4 colunas ──────────────────────
    if "State" in df.columns:
        ufs = sorted(df["State"].dropna().unique().tolist())
        st.sidebar.markdown(f"**🗺️ Estado/UF** ({len(ufs)} disponíveis)")
        
        todos_uf = st.sidebar.checkbox("✅ Todos os estados", value=True,
                                        key="v_all_uf")
        if not todos_uf:
            sel_ufs = []
            cols_uf = st.sidebar.columns(4)
            for i, uf in enumerate(ufs):
                if cols_uf[i % 4].checkbox(uf, value=True, key=f"v_uf_{uf}"):
                    sel_ufs.append(uf)
            filtros["State"] = sel_ufs
        else:
            filtros["State"] = ufs
    
    st.sidebar.markdown("---")
    
    # ── 4. Grupo de Item ──────────────────────────────────────────────
    if "ItemGroup" in df.columns:
        grupos = sorted(df["ItemGroup"].dropna().unique().tolist())
        st.sidebar.markdown(f"**📦 Grupo** ({len(grupos)} disponíveis)")
        
        todos_g = st.sidebar.checkbox("✅ Todos os grupos", value=True,
                                       key="v_all_grp")
        if not todos_g:
            filtros["ItemGroup"] = st.sidebar.multiselect(
                "", grupos, key="v_sel_grp", label_visibility="collapsed"
            )
        else:
            filtros["ItemGroup"] = grupos
    
    # ── 5. Tipo de Venda ──────────────────────────────────────────────
    if "UsageType" in df.columns:
        usos = sorted(df["UsageType"].dropna().unique().tolist())
        st.sidebar.markdown("**🏷️ Tipo de Venda**")
        sel_uso = st.sidebar.multiselect("", usos, default=usos,
                                          key="v_sel_uso", label_visibility="collapsed")
        filtros["UsageType"] = sel_uso
    
    return filtros


def render_filtros_ativos_bar(filtros: dict, df_total: pd.DataFrame,
                               df_filtered: pd.DataFrame) -> None:
    """
    Barra de resumo dos filtros ativos — Fase 1.
    Mostra quantas linhas foram filtradas e quais critérios estão ativos.
    """
    n_total    = len(df_total)
    n_filtered = len(df_filtered)
    pct        = n_filtered / n_total * 100 if n_total > 0 else 0
    
    chips = []
    for col, val in filtros.items():
        if col.startswith("__"): continue
        if isinstance(val, list) and len(val) < len(df_total[col].dropna().unique()):
            chips.append(f"**{col}**: {len(val)}")
    
    if chips:
        st.info(
            f"🔍 **{n_filtered:,}/{n_total:,} linhas** ({pct:.0f}%) "
            f"| Filtros: {' · '.join(chips)}".replace(",", ".")
        )
    else:
        # Badge discreto em vez de st.success() grande
        n_fmt = f"{n_filtered:,}".replace(",", ".")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:.6rem;margin:-.5rem 0 1.2rem">'
            f'<span style="background:#1a2e1a;border:1px solid #2d5a2d;color:#6dbf6d;font-size:11px;font-weight:500;padding:.25rem .7rem;border-radius:20px">✅ {n_fmt} linhas</span>'
            f'<span style="color:#8b90a8;font-size:11px">sem filtros ativos</span>'
            f'</div>',
            unsafe_allow_html=True
        )

# ═════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — CONFIG DA PÁGINA
# ═════════════════════════════════════════════════════════════════════════

st.set_page_config(
  page_title="Power BI Automático",
  page_icon="📊",
  layout="wide",
  initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 1B — LOGO NA SIDEBAR
# ══════════════════════════════════════════════════════════════════════

import base64

def _render_sidebar_logo():
    """Renderiza logo + nome da aplicação no topo da sidebar."""
    logo_path = Path(__file__).parent / "logo.png"

    if logo_path.exists():
        b64 = base64.b64encode(logo_path.read_bytes()).decode()
        st.sidebar.markdown(f"""
        <div style="
            padding: 1.4rem 1rem 1rem;
            border-bottom: 1px solid #2d3144;
            margin-bottom: 1.2rem;
        ">
            <img
                src="data:image/png;base64,{b64}"
                style="
                    width: 100%;
                    max-height: 52px;
                    object-fit: contain;
                    object-position: left center;
                "
                alt="Scientific Dental"
            />
            <div style="
                color: #8b90a8;
                font-size: 10px;
                margin-top: .6rem;
                text-transform: uppercase;
                letter-spacing: .1em;
            ">Relatório Analítico · SAP B1</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        # Fallback se logo.png não for encontrado
        st.sidebar.markdown(f"""
        <div style="
            padding: 1rem;
            border-bottom: 1px solid #2d3144;
            margin-bottom: 1.2rem;
            display: flex; align-items: center; gap: .75rem;
        ">
            <div style="
                width:38px; height:38px; border-radius:9px;
                background:#4f8ef7; display:flex; align-items:center;
                justify-content:center; color:#fff;
                font-size:17px; font-weight:700; flex-shrink:0;
            ">S</div>
            <div>
                <div style="color:#e8eaf0; font-size:14px; font-weight:600">
                    Scientific Dental
                </div>
                <div style="color:#8b90a8; font-size:11px">
                    Relatório Analítico · SAP B1
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

_render_sidebar_logo()

# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 1C — SEPARADORES DE SEÇÃO NA SIDEBAR
# ══════════════════════════════════════════════════════════════════════

def _sidebar_section(title: str):
    """Separador visual de seção na sidebar — somente layout."""
    st.sidebar.markdown(f"""
    <div style="
        border-top: 1px solid #2d3144;
        margin: 1rem 0 .7rem;
        padding-top: .7rem;
    ">
        <span style="
            color: #8b90a8;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: .1em;
        ">{title}</span>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — HELPERS GENÉRICOS
# ══════════════════════════════════════════════════════════════════════

def parse_num(v) -> float:
  """Converte qualquer valor para float, tolerante a formatos BR/US e unidades."""
  if pd.isna(v):
      return 0.0
  s = str(v).strip()
  if s.lower() in ("nan", "none", "null", "", "n/a", "-"):
      return 0.0
  # Remover unidades (ex: "25.48 m3", "100 kg")
  s = re.sub(r'\s*[a-zA-Z%/]+.*$', '', s).strip()
  s = re.sub(r"[^\d.,\-]", "", s)
  if not s or not re.search(r"\d", s):
      return 0.0
  if re.search(r"\d{1,3}(\.\d{3})+,\d", s):
      s = s.replace(".", "").replace(",", ".")
  else:
      s = s.replace(",", ".")
  try:
      return float(s)
  except (ValueError, TypeError):
      return 0.0


def fmt_brl(v: float) -> str:
  try:
      s = f"R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
      return f"-{s}" if v < 0 else s
  except Exception:
      return "R$ 0,00"

def pct_fmt(v: float) -> str:
  try:
      return f"{float(v):.2f}%"
  except Exception:
      return "0,00%"


def smart_date(val) -> pd.Timestamp | type[pd.NaT]:
  if pd.isna(val):
      return pd.NaT
  s = str(val).strip()
  try:
      n = float(s)
      if 40000 < n < 60000:
          return pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
  except (ValueError, TypeError):
      pass
  for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
      try:
          return pd.Timestamp(datetime.strptime(s[:10], fmt))
      except Exception:
          continue
  try:
      return pd.to_datetime(s, errors="coerce")
  except Exception:
      return pd.NaT


def _get_first_mode(x):
  m = x.mode()
  return m.iloc[0] if len(m) > 0 else ""


def to_excel(sheets: dict) -> bytes:
  buf = io.BytesIO()
  with pd.ExcelWriter(buf, engine="openpyxl") as writer:
      for name, data in sheets.items():
          data.to_excel(writer, sheet_name=name[:31], index=False)
  return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 4 — COL_MAP COMISSÃO + REQUIRED
# ══════════════════════════════════════════════════════════════════════

COMM_COL_MAP = {
  "ReceiveDate":       ["Data do Recebimento", "ReceiveDate", "Data Recebimento"],
  "BranchName":        ["Filial Recebimento", "Filial", "BranchName"],
  "ReceiptNumber":     ["Numero Recibo", "Número Recibo", "ReceiptNumber"],
  "NumeroNC":          ["Numero NC", "Número NC", "NumeroNC"],
  "EventType":         ["Tipo Evento", "EventType"],
  "InvDocNum":         ["Numero NF", "Número NF", "InvDocNum", "DocNum"],
  "ObjectType":        ["Tipo de Objeto", "ObjectType"],
  "CardCode":          ["Codigo PN", "Código PN", "CardCode"],
  "CardName":          ["Nome do PN", "CardName", "Cliente"],
  "SlpCode":           ["Codigo Vendedor", "Código Vendedor", "SlpCode"],
  "SlpName":           ["Nome do Vendedor", "Nome do vendedor", "SlpName"],
  "ItemCode":          ["Numero do Item", "Número do Item", "ItemCode"],
  "ItemDescription":   ["Descricao do Item", "Descrição do Item", "ItemDescription"],
  "Installment":       ["Parcela", "Installment"],
  "Quantity":          ["Quantidade", "Quantity"],
  "Currency":          ["Moeda", "Currency"],
  "LineTotal":         ["Valor Total da Linha NF", "LineTotal", "Valor Linha"],
  "AmountReceived":    ["Valor Recebido NF Evento", "AmountReceived", "Valor Recebido"],
  "AllocatedExpenses": ["Despesas Adicionais Rateadas", "AllocatedExpenses"],
  "PaymentBase":       ["Base de Pagamento da Linha", "PaymentBase", "Base de Pagamento"],
  "CommissionPct":     ["Percentual Comissao", "Percentual Comissão", "CommissionPct"],
  "CommissionValue":   ["Comissao Final", "Comissão Final", "CommissionValue", "Valor Comissão"],
  "GLAccount":         ["Conta Contabil Recebimento", "Conta Contábil Recebimento", "GLAccount"],
  "GLAccountName":     ["Nome Conta Contabil", "Nome Conta Contábil", "GLAccountName"],
}

COMM_REQUIRED = [
  "ReceiveDate", "InvDocNum", "SlpName", "ItemCode",
  "LineTotal", "AmountReceived", "CommissionPct", "CommissionValue",
]

# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 5 — DEDUPLICAÇÃO COMISSÃO
# ══════════════════════════════════════════════════════════════════════

def add_dedup_flags(df: pd.DataFrame) -> pd.DataFrame:
  """
  Adiciona _lt_first e _ar_first para evitar múltipla contagem.
  _lt_first: 1ª ocorrência de (InvDocNum, ItemCode) ou (ReceiptNumber, ItemCode)
  _ar_first: 1ª ocorrência de (InvDocNum, ReceiptNumber) ou apenas ReceiptNumber

  FIX #3: guards verificam se colunas existem antes de acessar.
  """
  df = df.copy()

  # Guard: garantir colunas necessárias
  if "ReceiptNumber" not in df.columns:
      df["ReceiptNumber"] = ""
  if "ItemCode" not in df.columns:
      df["ItemCode"] = ""
  if "InvDocNum" not in df.columns:
      df["InvDocNum"] = np.nan

  has_nf = df["InvDocNum"].notna()

  # Chave para LineTotal / Quantity
  lt_key = np.where(
      has_nf,
      df["InvDocNum"].astype(str) + "‖" + df["ItemCode"].astype(str),
      df["ReceiptNumber"].astype(str) + "‖" + df["ItemCode"].astype(str),
  )
  df["_lt_first"] = ~pd.Series(lt_key, index=df.index).duplicated(keep="first")

  # Chave para AmountReceived
  ar_key = np.where(
      has_nf,
      df["InvDocNum"].astype(str) + "‖" + df["ReceiptNumber"].astype(str),
      df["ReceiptNumber"].astype(str),
  )
  df["_ar_first"] = ~pd.Series(ar_key, index=df.index).duplicated(keep="first")

  return df


# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 6 — LOAD FILE (genérico, aliases combinados)
# ══════════════════════════════════════════════════════════════════════

def _build_all_aliases() -> set:
  """Combina aliases de COMISSÃO + VENDAS para scoring ao carregar arquivo."""
  aliases = set()
  for col_map in [COMM_COL_MAP, VendasModel.COL_MAP]:
      for alias_list in col_map.values():
          for alias in alias_list:
              aliases.add(alias.upper().strip())
  return aliases


_ALL_ALIASES_UPPER = _build_all_aliases()


def load_file(f):
  """
  Carrega arquivo Excel ou CSV.
  FIX #1: usa getattr(f, 'name', '') → não quebra com io.BytesIO.
  Scoring usa aliases de AMBOS os modelos para escolher melhor sheet.
  """
  try:
      f.seek(0)
  except Exception:
      pass

  content = f.read()
  if not content:
      return None, "Arquivo vazio."

  # FIX #1: getattr com fallback
  name = getattr(f, "name", "arquivo.xlsx").lower()

  if name.endswith((".xlsx", ".xls")):
      try:
          xl = pd.ExcelFile(io.BytesIO(content))
          sheet_list = xl.sheet_names
      except Exception:
          sheet_list = [0]

      best_df, best_score = None, -1
      for sheet in sheet_list:
          for hrow in [0, 1, 2]:
              try:
                  df = pd.read_excel(
                      io.BytesIO(content), dtype=str, header=hrow,
                      sheet_name=sheet, na_filter=False,
                  )
                  df.columns = [str(c).strip() for c in df.columns]
                  if len(df.columns) < 5 or len(df) == 0:
                      continue
                  score = sum(
                      1 for col in df.columns
                      if col.upper().strip() in _ALL_ALIASES_UPPER
                  )
                  if score > best_score:
                      best_score, best_df = score, df
              except Exception:
                  continue
      if best_df is not None:
          return best_df, None

  # CSV fallback
  for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
      try:
          text = content.decode(enc, errors="replace")
          for sep in ["\t", ";", ","]:
              try:
                  df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str,
                                   na_filter=False)
                  if len(df.columns) >= 5:
                      df.columns = [str(c).strip() for c in df.columns]
                      return df, None
              except Exception:
                  continue
      except Exception:
          continue

  return None, f"Formato não reconhecido: {getattr(f, 'name', 'arquivo')}"


# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 7 — NORMALIZE COLUNAS (COMISSÃO)
# ══════════════════════════════════════════════════════════════════════

def normalize_columns_comm(df: pd.DataFrame) -> pd.DataFrame:
  """Normaliza DataFrame usando COMM_COL_MAP."""
  rev = {
      alias.upper().strip(): canon
      for canon, aliases in COMM_COL_MAP.items()
      for alias in aliases
  }
  df = df.rename(columns={
      col: rev[col.upper().strip()]
      for col in df.columns
      if col.upper().strip() in rev
  }).copy()
  df.columns = [str(c).strip() for c in df.columns]

  # Numéricos
  numeric_cols = [
      "Quantity", "LineTotal", "AmountReceived", "AllocatedExpenses",
      "PaymentBase", "CommissionPct", "CommissionValue",
  ]
  for c in numeric_cols:
      df[c] = df[c].apply(parse_num) if c in df.columns else 0.0

  # Data
  if "ReceiveDate" in df.columns:
      df["ReceiveDate"] = df["ReceiveDate"].apply(smart_date)  # type: ignore[arg-type]
      df = df[df["ReceiveDate"].notna()].copy()
  else:
      df["ReceiveDate"] = pd.NaT

  # Texto
  text_cols = [
      "BranchName", "ReceiptNumber", "NumeroNC", "EventType", "InvDocNum",
      "ObjectType", "CardCode", "CardName", "SlpCode", "SlpName",
      "ItemCode", "ItemDescription", "Installment", "Currency",
      "GLAccount", "GLAccountName",
  ]
  for c in text_cols:
      df[c] = df[c].astype(str).str.strip() if c in df.columns else ""

  # InvDocNum vazio → NaN (crítico para dedup)
  if "InvDocNum" in df.columns:
      df["InvDocNum"] = df["InvDocNum"].replace(
          {"": np.nan, "nan": np.nan, "None": np.nan}
      )

  # SlpName fallback
  if "SlpName" in df.columns and df["SlpName"].eq("").all():
      if "SlpCode" in df.columns:
          df["SlpName"] = "Vendedor " + df["SlpCode"].astype(str)

  # Colunas derivadas
  df["ReceiveMonth"] = np.where(
      df["ReceiveDate"].notna(),
      df["ReceiveDate"].dt.to_period("M").astype(str),
      "N/D",
  )
  if "CommissionValue" in df.columns:
      df["HasCommission"] = np.where(
          df["CommissionValue"] > 0, "Com comissão", "Sem comissão"
      )
  if "AmountReceived" in df.columns:
      df["HasReceipt"] = np.where(
          df["AmountReceived"] > 0, "Com recebimento", "Sem recebimento"
      )
  return df


# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 8 — MODEL REGISTRY, TEMAS E AUTO-DETECT
# ══════════════════════════════════════════════════════════════════════

MODEL_INFO = {
  "COMISSAO": {
      "icon": "💰",
      "description": "Análise de comissões de vendedores",
      "required_sample": "Data do Recebimento · Numero NF · Nome do Vendedor · Comissao Final",
  },
  "VENDAS": {
      "icon": "📈",
      "description": "Vendas por item — Query SAP B1",
      "required_sample": "Data do Faturamento · Vendedor · Valor dos Itens · Grupo de Itens",
  },
}

THEMES = {
  "COMISSAO": "135deg,#0f172a 0%,#1e40af 50%,#7c3aed 100%",
  "VENDAS":   "135deg,#064e3b 0%,#065f46 50%,#0f766e 100%",
}


def detect_model_auto(df: pd.DataFrame) -> tuple[str, float]:
  """
  FIX #4: compara aliases (não canonical names) contra colunas originais do df.
  Score = 70% required_match + 30% optional_match.
  """
  df_cols_up = {c.upper().strip() for c in df.columns}
  models = {
      "COMISSAO": {
          "col_map":  COMM_COL_MAP,
          "required": COMM_REQUIRED,
      },
      "VENDAS": {
          "col_map":  VendasModel.COL_MAP,
          "required": VendasModel.REQUIRED_COLS,
      },
  }

  scores = {}
  for name, cfg in models.items():
      col_map  = cfg["col_map"]
      required = cfg["required"]

      # Todos aliases em uppercase
      all_aliases_up = {
          alias.upper().strip()
          for canon, aliases in col_map.items()
          for alias in aliases
      }
      # Aliases das colunas obrigatórias
      req_aliases_up = set()
      for req in required:
          for alias in col_map.get(req, [req]):
              req_aliases_up.add(alias.upper().strip())

      found_req = sum(1 for a in req_aliases_up if a in df_cols_up)
      found_opt = sum(1 for a in all_aliases_up if a in df_cols_up)

      if found_req == 0:
          scores[name] = 0.0
      else:
          req_pct = found_req / max(len(required), 1)
          opt_pct = found_opt / max(len(all_aliases_up), 1)
          scores[name] = req_pct * 0.7 + opt_pct * 0.3

  best  = max(scores, key=scores.get)
  return best, round(scores[best] * 100, 1)


# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 9 — SIDEBAR
# ══════════════════════════════════════════════════════════════════════

st.sidebar.markdown("---")
st.sidebar.markdown("### 📂 Upload")

uploaded = st.sidebar.file_uploader(
  "Escolha arquivo",
  type=["xlsx", "xls", "csv"],
  help="Planilha Excel ou CSV com dados para análise",
  key="main_file_uploader"
)

# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 10 — WELCOME PAGE
# ══════════════════════════════════════════════════════════════════════

if uploaded is None:
  st.markdown("""
  <div class="welcome-header">
      <h1>📊 Power BI Automático</h1>
      <p>Plataforma de análise multi-modelos com detecção automática de layout</p>
  </div>
  """, unsafe_allow_html=True)

  c1, c2, c3 = st.columns(3)
  
  with c1:
      st.markdown("""
      <div class="welcome-feature-card">
          <div class="icon">💰</div>
          <div class="title">Comissões</div>
          <div class="description">Deduplicação inteligente de NFs · 7 perspectivas analíticas</div>
      </div>
      """, unsafe_allow_html=True)

  with c2:
      st.markdown("""
      <div class="welcome-feature-card">
          <div class="icon">📋</div>
          <div class="title">Vendas SAP</div>
          <div class="description">Query 'Vendas por Item' · 35+ campos · KPIs + UF + Tipo</div>
      </div>
      """, unsafe_allow_html=True)

  with c3:
      st.markdown("""
      <div class="welcome-feature-card">
          <div class="icon">🤖</div>
          <div class="title">Auto-detect</div>
          <div class="description">Modelo identificado automaticamente pelo layout do arquivo</div>
      </div>
      """, unsafe_allow_html=True)

  st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
  st.markdown("#### 🎯 Modelos Disponíveis")
  for key, info in MODEL_INFO.items():
      with st.expander(f"{info['icon']} **{key}** — {info['description']}"):
          st.markdown(f"**Colunas esperadas:** `{info['required_sample']}`")
  st.stop()

# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 11 — CACHE + CARREGAMENTO
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def _cached_load(file_bytes: bytes, filename: str):
  """
  FIX #2: @st.cache_data exige tipos serializáveis.
  Usa _Fakefile para adicionar .name ao io.BytesIO.
  Retorna DataFrame RAW (sem normalização) para ambos os modelos.
  """
  import io as _io

  class _Fakefile:
      def __init__(self, b: bytes, n: str):
          self._buf = _io.BytesIO(b)
          self.name = n
      def read(self):   return self._buf.read()
      def seek(self, p): return self._buf.seek(p)

  return load_file(_Fakefile(file_bytes, filename))


with st.spinner("🔄 Carregando e analisando arquivo..."):
  file_bytes = uploaded.read()
  df_raw, err = _cached_load(file_bytes, uploaded.name)
  if err or df_raw is None:
      st.error(f"❌ Erro ao ler arquivo: {err}")
      st.stop()

# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 12 — AUTO-DETECT + SELEÇÃO DE MODELO (sidebar continuação)
# ══════════════════════════════════════════════════════════════════════

model_detected, conf_score = detect_model_auto(df_raw)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 Auto-Detectado")

if conf_score >= 80:
  badge_html = f'<span class="detect-badge detect-high">✅ Alta ({conf_score:.0f}%)</span>'
elif conf_score >= 50:
  badge_html = f'<span class="detect-badge detect-medium">⚠️ Média ({conf_score:.0f}%)</span>'
else:
  badge_html = f'<span class="detect-badge detect-low">❌ Baixa ({conf_score:.0f}%)</span>'

st.sidebar.markdown(
  f"**{MODEL_INFO[model_detected]['icon']} {model_detected}**  \n"
  f"Confiança: {badge_html}",
  unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Escolher Modelo")

model_selected = st.sidebar.radio(
  "Selecione o modelo:",
  list(MODEL_INFO.keys()),
  index=list(MODEL_INFO.keys()).index(model_detected),
  format_func=lambda x: f"{MODEL_INFO[x]['icon']} {x}",
  horizontal=True,
)

# Opções extra por modelo na sidebar
if model_selected == "COMISSAO":
  st.sidebar.markdown("---")
  st.sidebar.markdown("### ⚙️ Opções")
  show_zero_commission = st.sidebar.checkbox("Incluir linhas sem comissão", value=True)
  show_zero_received   = st.sidebar.checkbox("Incluir linhas sem recebimento", value=True)
else:
  show_zero_commission = True
  show_zero_received   = True

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 Power BI Automático")

# ══════════════════════════════════════════════════════════════════════
# SEÇÃO 13 — HEADER TEMÁTICO
# ══════════════════════════════════════════════════════════════════════

# Montar preview de datas (tenta adivinhar coluna de data)
_date_col_map = {"COMISSAO": "ReceiveDate", "VENDAS": "SaleDate"}
_date_col = _date_col_map.get(model_selected, "")
_rev_date  = {
  alias.upper().strip(): canon
  for canon, aliases in (COMM_COL_MAP if model_selected == "COMISSAO"
                          else VendasModel.COL_MAP).items()
  for alias in aliases
}
# Mapear colunas do raw para canonical (apenas para preview de datas)
_raw_cols_mapped = {
  _rev_date.get(c.upper().strip(), c): c
  for c in df_raw.columns
}
_d_min_str = _d_max_str = "—"
if _date_col in _raw_cols_mapped:
  try:
      _dc_raw = df_raw[_raw_cols_mapped[_date_col]].apply(smart_date)  # type: ignore[arg-type]
      if _dc_raw.notna().any():
          _d_min_str = _dc_raw.min().strftime("%d/%m/%Y")
          _d_max_str = _dc_raw.max().strftime("%d/%m/%Y")
  except Exception:
      pass

ts_now    = datetime.now().strftime("%d/%m/%Y %H:%M")
gradient  = THEMES.get(model_selected, THEMES["COMISSAO"])
model_icon = MODEL_INFO[model_selected]["icon"]

st.markdown(f"""
<div class="page-header" style="background:linear-gradient({gradient})">
<h1>{model_icon} Relatório {model_selected}</h1>
<p>
  {uploaded.name} &nbsp;·&nbsp;
  {len(df_raw):,} linhas brutas &nbsp;·&nbsp;
  Período: {_d_min_str} → {_d_max_str} &nbsp;·&nbsp;
  {ts_now}
</p>
</div>
""".replace(",", "."), unsafe_allow_html=True)

if model_selected == "COMISSAO":

  # ── 13A: Normalizar ───────────────────────────────────────────────
  @st.cache_data(show_spinner=False)
  def _cached_normalize_comm(file_bytes: bytes, filename: str):
      import io as _io
      class _Fakefile:
          def __init__(self, b, n): self._buf = _io.BytesIO(b); self.name = n
          def read(self): return self._buf.read()
          def seek(self, p): return self._buf.seek(p)
      raw, err = load_file(_Fakefile(file_bytes, filename))
      if err or raw is None: return None, err
      return normalize_columns_comm(raw), None

  with st.spinner("🔄 Normalizando colunas de Comissão..."):
      df_comm, err_norm = _cached_normalize_comm(file_bytes, uploaded.name)
      if err_norm or df_comm is None:
          st.error(f"❌ Erro ao normalizar: {err_norm}"); st.stop()

  # ── 13B: Validar ──────────────────────────────────────────────────
  missing_comm = [c for c in COMM_REQUIRED if c not in df_comm.columns]
  if missing_comm:
      st.error(f"❌ Colunas obrigatórias não encontradas: `{missing_comm}`")
      with st.expander("🔍 Diagnóstico — colunas do arquivo"):
          st.code(", ".join(df_comm.columns.tolist()))
          st.dataframe(df_comm.head(3), use_container_width=True)
      st.info("💡 Este arquivo pode ser de **VENDAS**. Troque o modelo na sidebar.")
      st.stop()

  # ── 13C: Aplicar opções zero ──────────────────────────────────────
  df = df_comm.copy()
  if not show_zero_commission:
      df = df[df["CommissionValue"] > 0]
  if not show_zero_received:
      df = df[df["AmountReceived"] > 0]
  if df.empty:
      st.warning("⚠️ Nenhum dado após opções de zero. Altere na sidebar.")
      st.stop()

  # ── 13D: FILTROS DINÂMICOS ────────────────────────────────────────
  has_dates   = df["ReceiveDate"].notna().any()
  vend_opts   = sorted([x for x in df["SlpName"].dropna().astype(str).unique() if x])
  branch_opts = sorted([x for x in df["BranchName"].dropna().astype(str).unique() if x])
  client_opts = sorted([x for x in df["CardName"].dropna().astype(str).unique() if x])
  month_opts  = sorted([x for x in df["ReceiveMonth"].dropna().astype(str).unique()
                         if x and x != "N/D"])

  with st.expander("🔍 Filtros Dinâmicos", expanded=True):
      r1 = st.columns([2, 2, 2, 3])
      with r1[0]:
          sel_vend   = st.multiselect("👤 Vendedor", vend_opts,
                                       default=vend_opts, key="cv_vend")
      with r1[1]:
          sel_branch = st.multiselect("🏢 Filial", branch_opts,
                                       default=branch_opts, key="cv_branch")
      with r1[2]:
          sel_month  = st.multiselect("🗓️ Mês", month_opts,
                                       default=month_opts if month_opts else [],
                                       key="cv_month")
      with r1[3]:
          if has_dates:
              d_min = df["ReceiveDate"].min().date()
              d_max = df["ReceiveDate"].max().date()
              date_range = st.date_input("📅 Período", value=(d_min, d_max),
                                          min_value=d_min, max_value=d_max,
                                          key="cv_date")
          else:
              date_range = None

      r2 = st.columns([2, 2, 2, 2])
      with r2[0]:
          sel_client = st.multiselect("🏥 Cliente", client_opts,
                                       default=client_opts, key="cv_client")
      with r2[1]:
          comm_min = st.number_input("💰 Comissão mínima (R$)", value=0.0,
                                      step=100.0, key="cv_comm_min")
      with r2[2]:
          recv_min = st.number_input("💳 Recebimento mínimo (R$)", value=0.0,
                                      step=100.0, key="cv_recv_min")
      with r2[3]:
          top_n = st.slider("📌 Top ranking", min_value=5, max_value=30,
                             value=10, key="cv_topn")

  # ── 13E: Aplicar filtros ──────────────────────────────────────────
  filtered = df.copy()
  if sel_vend:
      filtered = filtered[filtered["SlpName"].isin(sel_vend)]
  if sel_branch:
      filtered = filtered[filtered["BranchName"].isin(sel_branch)]
  if sel_month and month_opts:
      filtered = filtered[filtered["ReceiveMonth"].isin(sel_month)]
  if sel_client:
      filtered = filtered[filtered["CardName"].isin(sel_client)]
  if comm_min > 0:
      filtered = filtered[filtered["CommissionValue"].abs() >= comm_min]
  if recv_min > 0:
      filtered = filtered[filtered["AmountReceived"].abs() >= recv_min]
  if has_dates and date_range and len(date_range) == 2:
      filtered = filtered[
          filtered["ReceiveDate"].between(
              pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
          )
      ]

  if filtered.empty:
      st.warning("⚠️ Nenhum dado com os filtros selecionados.")
      st.stop()

  st.caption(
      f"📊 {len(filtered):,} linhas filtradas de {len(df):,} total"
      .replace(",", ".")
  )

  # ── 13F: DEDUPLICAÇÃO ─────────────────────────────────────────────
  ff  = add_dedup_flags(filtered)
  _lt = ff[ff["_lt_first"]]   # LineTotal / Quantity: 1× por (NF, Item)
  _ar = ff[ff["_ar_first"]]   # AmountReceived:       1× por (NF, Recibo)

  # ── 13G: AGGREGATIONS ─────────────────────────────────────────────
  # Por Vendedor
  _vl = _lt.groupby("SlpName").agg(Vendas=("LineTotal", "sum"),
                                     Itens=("Quantity", "sum"))
  _va = _ar.groupby("SlpName").agg(Recebido=("AmountReceived", "sum"))
  _vb = ff.groupby("SlpName").agg(
      NFs=("InvDocNum", "nunique"), Comissao=("CommissionValue", "sum"),
      BasePagamento=("PaymentBase", "sum"), PctMedio=("CommissionPct", "mean"),
      Clientes=("CardCode", "nunique"),
  )
  resumo_vend = (
      _vb.join(_vl, how="left").join(_va, how="left")
      .fillna(0).reset_index()
      .rename(columns={"SlpName": "Vendedor"})
      .sort_values("Comissao", ascending=False)
  )
  resumo_vend["TicketMedioNF"] = (
      resumo_vend["Vendas"] / resumo_vend["NFs"].replace(0, np.nan)
  ).fillna(0)
  resumo_vend["ComissaoSobreVendaPct"] = (
      resumo_vend["Comissao"] / resumo_vend["Vendas"].replace(0, np.nan) * 100
  ).fillna(0)

  # Por Filial
  _fl = _lt.groupby("BranchName").agg(Vendas=("LineTotal", "sum"),
                                        Itens=("Quantity", "sum"))
  _fa = _ar.groupby("BranchName").agg(Recebido=("AmountReceived", "sum"))
  _fb = ff.groupby("BranchName").agg(NFs=("InvDocNum", "nunique"),
                                      Comissao=("CommissionValue", "sum"))
  resumo_filial = (
      _fb.join(_fl, how="left").join(_fa, how="left")
      .fillna(0).reset_index()
      .rename(columns={"BranchName": "Filial"})
      .sort_values("Comissao", ascending=False)
  )

  # Por Item
  _il = _lt.groupby("ItemCode").agg(
      Descricao=("ItemDescription", _get_first_mode),
      Vendas=("LineTotal", "sum"), Itens=("Quantity", "sum"),
  )
  _ia = _ar.groupby("ItemCode").agg(Recebido=("AmountReceived", "sum"))
  _ib = ff.groupby("ItemCode").agg(NFs=("InvDocNum", "nunique"),
                                    Comissao=("CommissionValue", "sum"))
  resumo_item = (
      _ib.join(_il, how="left").join(_ia, how="left")
      .fillna(0).reset_index()
      .sort_values("Comissao", ascending=False)
  )

  # Por Cliente
  _cl = _lt.groupby("CardName").agg(Vendas=("LineTotal", "sum"),
                                      Itens=("Quantity", "sum"))
  _ca = _ar.groupby("CardName").agg(Recebido=("AmountReceived", "sum"))
  _cb = ff.groupby("CardName").agg(NFs=("InvDocNum", "nunique"),
                                    Comissao=("CommissionValue", "sum"))
  resumo_cliente = (
      _cb.join(_cl, how="left").join(_ca, how="left")
      .fillna(0).reset_index()
      .rename(columns={"CardName": "Cliente"})
      .sort_values("Comissao", ascending=False)
  )

  # Por Mês
  resumo_mes = pd.DataFrame()
  if ff["ReceiveMonth"].ne("N/D").any():
      _ml = _lt.groupby(["ReceiveMonth", "SlpName"]).agg(
          Vendas=("LineTotal", "sum"), Itens=("Quantity", "sum"))
      _ma = _ar.groupby(["ReceiveMonth", "SlpName"]).agg(
          Recebido=("AmountReceived", "sum"))
      _mb = ff.groupby(["ReceiveMonth", "SlpName"]).agg(
          NFs=("InvDocNum", "nunique"), Comissao=("CommissionValue", "sum"))
      resumo_mes = (
          _mb.join(_ml, how="left").join(_ma, how="left")
          .fillna(0).reset_index()
          .rename(columns={"SlpName": "Vendedor"})
      )

  # ── 13H: KPI CARDS (Novo Design System) ────────────────────────────
  total_vendas   = _lt["LineTotal"].sum()
  total_itens    = _lt["Quantity"].sum()
  total_nfs      = ff["InvDocNum"].nunique()
  total_comissao = ff["CommissionValue"].sum()
  total_recebido = _ar["AmountReceived"].sum()
  media_pct      = ff["CommissionPct"].mean() if len(ff) else 0
  n_vendedores   = ff["SlpName"].nunique()

  # KPIs com design system (com delta dinamico)
  kpis_comm = [
      {
          "label": "Vendas",
          "value": fmt_brl(total_vendas),
          "icon": "💼",
          "prefix": "R$",
          "delta": None,
          "color": "primary",
      },
      {
          "label": "Itens",
          "value": f"{int(total_itens):,}".replace(",","."),
          "icon": "📦",
          "prefix": "",
          "color": "info",
      },
      {
          "label": "NFs",
          "value": f"{total_nfs}",
          "icon": "📄",
          "prefix": "",
          "color": "warning",
      },
      {
          "label": "Recebido",
          "value": fmt_brl(total_recebido),
          "icon": "💳",
          "prefix": "R$",
          "color": "success",
      },
      {
          "label": "Comissão",
          "value": fmt_brl(total_comissao),
          "icon": "💰",
          "prefix": "R$",
          "color": "primary",
      },
      {
          "label": "% Médio",
          "value": pct_fmt(media_pct),
          "icon": "📊",
          "prefix": "",
          "color": "info",
      },
  ]
  render_kpi_row(kpis_comm, layout=[2, 1.5, 1.5, 2, 2, 1.5])

  render_separator()

  # ── 13I: TABS ─────────────────────────────────────────────────────
  t_dash, t_vend, t_fil, t_item, t_cli, t_det, t_exp = st.tabs([
      "📊 Dashboard", "👤 Vendedores", "🏢 Filiais",
      "📦 Itens", "🏥 Clientes", "📋 Detalhado", "📥 Exportar",
  ])

  # ── TAB: DASHBOARD ────────────────────────────────────────────────
  with t_dash:
      c1, c2 = st.columns(2)

      cv = resumo_vend.head(top_n).sort_values("Comissao")
      fig_v = px.bar(
          cv, x="Comissao", y="Vendedor", orientation="h",
          title=f"💰 Top {top_n} vendedores por comissão",
          text=cv["Comissao"].apply(fmt_brl),
          color="Comissao", color_continuous_scale=CHART_COLORS[:2],
          labels={"Comissao":"R$","Vendedor":""},
      )
      fig_v.update_traces(textposition="outside")
      fig_v = apply_chart_style(fig_v, title=f"💰 Top {top_n} vendedores por comissão", height=420)
      fig_v.update_layout(coloraxis_showscale=False, margin=dict(r=80), showlegend=False)
      c1.plotly_chart(fig_v, use_container_width=True)

      pie_data = resumo_vend[resumo_vend["Comissao"] > 0].head(top_n)
      fig_pie = px.pie(
          pie_data, values="Comissao", names="Vendedor", hole=0.52,
          title="🥧 Participação da comissão por vendedor",
          color_discrete_sequence=CHART_COLORS,
      )
      fig_pie.update_traces(textinfo="percent+label")
      fig_pie = apply_chart_style(fig_pie, title="🥧 Participação da comissão por vendedor", height=420)
      fig_pie.update_layout(showlegend=False)
      c2.plotly_chart(fig_pie, use_container_width=True)

      if not resumo_mes.empty:
          mes_tot = resumo_mes.groupby("ReceiveMonth")[
              ["Vendas","Recebido","Comissao"]
          ].sum().reset_index()
          fig_mes = px.line(
              mes_tot, x="ReceiveMonth", y=["Vendas","Recebido","Comissao"],
              markers=True, title="📈 Evolução mensal",
              labels={"value":"R$","variable":"Indicador","ReceiveMonth":"Mês"},
          )
          fig_mes = apply_chart_style(fig_mes, title="📈 Evolução mensal", height=340)
          st.plotly_chart(fig_mes, use_container_width=True)

      d1, d2 = st.columns(2)
      top_items = resumo_item.head(top_n).sort_values("Comissao")
      fig_items = px.bar(
          top_items, x="Comissao", y="ItemCode", orientation="h",
          title=f"🏆 Top {top_n} itens por comissão",
          text=top_items["Comissao"].apply(fmt_brl),
          hover_data={"Descricao": True},
          color="Comissao", color_continuous_scale=CHART_COLORS[:2],
          labels={"Comissao":"R$","ItemCode":""},
      )
      fig_items.update_traces(textposition="outside")
      fig_items = apply_chart_style(fig_items, title=f"🏆 Top {top_n} itens por comissão", height=400)
      fig_items.update_layout(coloraxis_showscale=False, showlegend=False)
      d1.plotly_chart(fig_items, use_container_width=True)

      if len(resumo_vend) > 1:
          fig_sc = px.scatter(
              resumo_vend, x="Vendas", y="Comissao", size="NFs", color="Vendedor",
              hover_data=["Itens","Recebido","Clientes"],
              title="🎯 Vendas × Comissão por vendedor",
              labels={"Vendas":"Vendas (R$)","Comissao":"Comissão (R$)"},
          )
          fig_sc = apply_chart_style(fig_sc, title="🎯 Vendas × Comissão por vendedor", height=400)
          fig_sc.update_layout(showlegend=False)
          d2.plotly_chart(fig_sc, use_container_width=True)

  # ── TAB: VENDEDORES ───────────────────────────────────────────────
  with t_vend:
      st.caption(f"{len(resumo_vend)} vendedores no período filtrado")
      disp_v = resumo_vend.copy()
      for cn in ["Vendas","Recebido","BasePagamento","Comissao","TicketMedioNF"]:
          if cn in disp_v.columns:
              disp_v[cn] = disp_v[cn].apply(fmt_brl)
      disp_v["PctMedio"]              = disp_v["PctMedio"].apply(pct_fmt)
      disp_v["ComissaoSobreVendaPct"] = disp_v["ComissaoSobreVendaPct"].apply(pct_fmt)
      st.dataframe(disp_v, use_container_width=True, height=320)

      st.markdown("---")
      st.subheader("🔎 Deep dive por vendedor")
      vendedor_sel = st.selectbox(
          "Selecione o vendedor",
          resumo_vend["Vendedor"].tolist(),
          key="comm_vend_dd"
      )
      if vendedor_sel:
          dv_ff  = ff[ff["SlpName"] == vendedor_sel]
          _dv_lt = dv_ff[dv_ff["_lt_first"]]
          _dv_ar = dv_ff[dv_ff["_ar_first"]]

          m1, m2, m3, m4 = st.columns(4)
          m1.metric("Vendas",   fmt_brl(_dv_lt["LineTotal"].sum()))
          m2.metric("Itens",    f"{int(_dv_lt['Quantity'].sum()):,}".replace(",","."))
          m3.metric("NFs",      int(dv_ff["InvDocNum"].nunique()))
          m4.metric("Comissão", fmt_brl(dv_ff["CommissionValue"].sum()))

          drill = (
              _dv_lt.groupby(["ItemCode","CommissionPct"])
              .agg(Descricao=("ItemDescription",_get_first_mode),
                   Vendas=("LineTotal","sum"), Itens=("Quantity","sum"),
                   NFs=("InvDocNum","nunique"))
              .reset_index()
          )
          drill_comm = (
              dv_ff.groupby(["ItemCode","CommissionPct"])
              .agg(Comissao=("CommissionValue","sum")).reset_index()
          )
          drill_recv = (
              _dv_ar.groupby("ItemCode")
              .agg(Recebido=("AmountReceived","sum")).reset_index()
          )
          drill = (
              drill
              .merge(drill_comm, on=["ItemCode","CommissionPct"], how="left")
              .merge(drill_recv, on="ItemCode", how="left")
              .fillna(0)
              .sort_values("Comissao", ascending=False)
          )

          si = st.text_input("Buscar item do vendedor", key="comm_si")
          if si:
              mask = (
                  drill["ItemCode"].astype(str).str.contains(si, case=False, na=False) |
                  drill["Descricao"].astype(str).str.contains(si, case=False, na=False)
              )
              drill = drill[mask]

          dd = drill.copy()
          # Rename ItemCode to show code + description
          if "ItemCode" in dd.columns and "Descricao" in dd.columns:
              dd["Item"] = dd["ItemCode"].astype(str) + " — " + dd["Descricao"].astype(str)
              dd = dd.drop(columns=["ItemCode"])
              dd = dd[["Item"] + [col for col in dd.columns if col != "Item"]]
          for cn in ["Vendas","Recebido","Comissao"]:
              dd[cn] = dd[cn].apply(fmt_brl)
          dd["CommissionPct"] = dd["CommissionPct"].apply(pct_fmt)
          st.dataframe(dd, use_container_width=True, height=380)

  # ── TAB: FILIAIS ──────────────────────────────────────────────────
  with t_fil:
      chart_f = resumo_filial.sort_values("Comissao")
      fig_f = px.bar(
          chart_f, x="Comissao", y="Filial", orientation="h",
          title="💰 Comissão por filial",
          text=chart_f["Comissao"].apply(fmt_brl),
          color="Comissao", color_continuous_scale=CHART_COLORS[:2],
          labels={"Comissao":"R$","Filial":""},
      )
      fig_f.update_traces(textposition="outside")
      fig_f = apply_chart_style(fig_f, title="💰 Comissão por filial", 
                                 height=max(320, len(chart_f)*60))
      fig_f.update_layout(coloraxis_showscale=False, showlegend=False)
      st.plotly_chart(fig_f, use_container_width=True)

      filial_vendor = (
          ff.groupby(["BranchName","SlpName"])
          .agg(Comissao=("CommissionValue","sum")).reset_index()
      )
      fig_stack = px.bar(
          filial_vendor, x="BranchName", y="Comissao", color="SlpName",
          barmode="stack", title="💼 Comissão por filial × vendedor",
          labels={"BranchName":"Filial","Comissao":"R$","SlpName":"Vendedor"},
      )
      fig_stack = apply_chart_style(fig_stack, title="💼 Comissão por filial × vendedor", height=380)
      st.plotly_chart(fig_stack, use_container_width=True)

      disp_f = resumo_filial.copy()
      for cn in ["Vendas","Recebido","Comissao"]:
          if cn in disp_f.columns: disp_f[cn] = disp_f[cn].apply(fmt_brl)
      st.dataframe(disp_f, use_container_width=True, height=280)

  # ── TAB: ITENS ────────────────────────────────────────────────────
  with t_item:
      sgi = st.text_input("🔍 Buscar item por código ou descrição",
                           key="comm_item_g")
      di = resumo_item.copy()
      if sgi:
          mask = (
              di["ItemCode"].astype(str).str.contains(sgi, case=False, na=False) |
              di["Descricao"].astype(str).str.contains(sgi, case=False, na=False)
          )
          di = di[mask]
      di_d = di.copy()
      # Rename ItemCode to show code + description
      if "ItemCode" in di_d.columns and "Descricao" in di_d.columns:
          di_d["Item"] = di_d["ItemCode"].astype(str) + " — " + di_d["Descricao"].astype(str)
          di_d = di_d.drop(columns=["ItemCode"])
          di_d = di_d[["Item"] + [col for col in di_d.columns if col != "Item"]]
      for cn in ["Vendas","Recebido","Comissao"]:
          if cn in di_d.columns: di_d[cn] = di_d[cn].apply(fmt_brl)
      st.caption(f"{len(di)} itens distintos")
      st.dataframe(di_d, use_container_width=True, height=500)

  # ── TAB: CLIENTES ─────────────────────────────────────────────────
  with t_cli:
      top_cli = resumo_cliente.head(top_n).sort_values("Comissao")
      fig_cli = px.bar(
          top_cli, x="Comissao", y="Cliente", orientation="h",
          title=f"🏥 Top {top_n} clientes por comissão",
          text=top_cli["Comissao"].apply(fmt_brl),
          color="Comissao", color_continuous_scale=CHART_COLORS[:2],
          labels={"Comissao":"R$","Cliente":""},
      )
      fig_cli.update_traces(textposition="outside")
      fig_cli = apply_chart_style(fig_cli, title=f"🏥 Top {top_n} clientes por comissão", height=420)
      fig_cli.update_layout(coloraxis_showscale=False, showlegend=False)
      st.plotly_chart(fig_cli, use_container_width=True)

      cli_d = resumo_cliente.copy()
      for cn in ["Vendas","Recebido","Comissao"]:
          if cn in cli_d.columns: cli_d[cn] = cli_d[cn].apply(fmt_brl)
      st.dataframe(cli_d, use_container_width=True, height=350)

  # ── TAB: DETALHADO ────────────────────────────────────────────────
  with t_det:
      show_cols = [c for c in [
          "ReceiveDate","ReceiveMonth","BranchName","ReceiptNumber","NumeroNC",
          "EventType","InvDocNum","CardCode","CardName","SlpCode","SlpName",
          "ItemCode","ItemDescription","Installment","Quantity","Currency",
          "LineTotal","AmountReceived","AllocatedExpenses","PaymentBase",
          "CommissionPct","CommissionValue","GLAccount","GLAccountName",
      ] if c in filtered.columns]

      detail = filtered[show_cols].copy()

      ca, cb, cc = st.columns([3, 2, 2])
      sa = ca.text_input("🔍 Buscar em todos os campos", key="comm_det_sa")
      vd = cb.selectbox("Vendedor", ["Todos"] + vend_opts, key="comm_det_vd")
      bd = cc.selectbox("Filial",   ["Todos"] + branch_opts, key="comm_det_bd")

      if sa:
          mask = detail.astype(str).apply(
              lambda col: col.str.contains(sa, case=False, na=False)
          ).any(axis=1)
          detail = detail[mask]
      if vd != "Todos": detail = detail[detail["SlpName"]    == vd]
      if bd != "Todos": detail = detail[detail["BranchName"] == bd]

      det_d = detail.copy()
      for cn in ["LineTotal","AmountReceived","AllocatedExpenses",
                 "PaymentBase","CommissionValue"]:
          if cn in det_d.columns: det_d[cn] = det_d[cn].apply(fmt_brl)
      if "CommissionPct" in det_d.columns:
          det_d["CommissionPct"] = det_d["CommissionPct"].apply(pct_fmt)

      st.caption(f"{len(det_d):,} linhas exibidas".replace(",","."))
      st.dataframe(det_d, use_container_width=True, height=580)

  # ── TAB: EXPORTAR ─────────────────────────────────────────────────
  with t_exp:
      ts_file = datetime.now().strftime("%Y%m%d_%H%M")
      st.subheader("📥 Exportar relatórios de Comissão")
      st.caption(f"Exportando {len(filtered):,} linhas filtradas".replace(",","."))

      e1, e2, e3 = st.columns(3)
      with e1:
          st.download_button(
              "📊 Excel completo",
              data=to_excel({
                  "Resumo_Vendedor": resumo_vend,
                  "Resumo_Filial":   resumo_filial,
                  "Resumo_Item":     resumo_item,
                  "Resumo_Cliente":  resumo_cliente,
                  "Detalhado":       filtered,
              }),
              file_name=f"comissoes_analitico_{ts_file}.xlsx",
              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              use_container_width=True,
          )
      with e2:
          st.download_button(
              "📄 Resumo vendedores CSV",
              data=resumo_vend.to_csv(index=False, sep=";", decimal=",")
                   .encode("utf-8-sig"),
              file_name=f"resumo_vendedores_{ts_file}.csv",
              mime="text/csv", use_container_width=True,
          )
      with e3:
          st.download_button(
              "📋 Detalhado CSV",
              data=filtered.to_csv(index=False, sep=";", decimal=",")
                   .encode("utf-8-sig"),
              file_name=f"detalhado_{ts_file}.csv",
              mime="text/csv", use_container_width=True,
          )

      prev = resumo_vend.copy()
      for cn in ["Vendas","Recebido","BasePagamento","Comissao","TicketMedioNF"]:
          if cn in prev.columns: prev[cn] = prev[cn].apply(fmt_brl)
      prev["PctMedio"]              = prev["PctMedio"].apply(pct_fmt)
      prev["ComissaoSobreVendaPct"] = prev["ComissaoSobreVendaPct"].apply(pct_fmt)
      st.markdown("---")
      st.subheader("📊 Prévia — resumo por vendedor")
      st.dataframe(prev, use_container_width=True, height=340)

elif model_selected == "VENDAS":

  # ── Instanciar + Load ─────────────────────────────────────────────
  model_v = VendasModel(df_raw)

  with st.spinner("🔄 Normalizando colunas de Vendas..."):
      model_v.load()

  # ── Validar ───────────────────────────────────────────────────────
  is_valid_v, missing_v = model_v.validate()
  if not is_valid_v:
      st.error(f"❌ Modelo **VENDAS** incompatível com este arquivo.")
      c1, c2 = st.columns(2)
      with c1:
          st.markdown("**Colunas necessárias não encontradas:**")
          for col in missing_v:
              aliases = VendasModel.COL_MAP.get(col, [col])
              st.markdown(f"- `{col}` → espera: `{' | '.join(aliases[:3])}`")
      with c2:
          st.markdown("**Primeiras colunas do arquivo:**")
          for col in list(df_raw.columns)[:12]:
              st.markdown(f"- `{col}`")
      st.info("💡 Este arquivo pode ser de **COMISSÃO**. Troque o modelo na sidebar.")
      st.stop()

  # ── Filtros dinâmicos VENDAS (NOVO - Fase 1) ─────────────────────
  df_v = model_v.df
  
  # Usar os novos filtros compactos da sidebar
  filtros_v = render_filtros_sidebar_vendas(df_v)
  
  # Aplicar filtros
  filtered_v = df_v.copy()
  
  # Data
  if "__date__" in filtros_v:
      d0, d1 = filtros_v["__date__"]
      if "SaleDate" in filtered_v.columns:
          filtered_v = filtered_v[
              filtered_v["SaleDate"].dt.date.between(d0, d1)
          ]
  
  # Dimensões (SlpName, State, ItemGroup, UsageType)
  for col in ["SlpName", "State", "ItemGroup", "UsageType"]:
      if col in filtros_v and col in filtered_v.columns:
          sel = filtros_v[col]
          if sel and len(sel) < len(df_v[col].dropna().unique()):
              filtered_v = filtered_v[filtered_v[col].isin(sel)]

  if filtered_v.empty:
      st.warning("⚠️ Nenhum dado com os filtros selecionados.")
      st.stop()

  # Barra de status dos filtros (Fase 1)
  render_filtros_ativos_bar(filtros_v, df_v, filtered_v)

  # ── FIX #5 + #6: passa filtered_df + aggs corretos → render_tabs ─
  model_v._filtered_df = filtered_v
  aggs_v = model_v.get_aggregations(filtered_v)
  model_v.render_tabs(aggs_v, {})


# ══════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("📊 Power BI Automático © 2026 — Scientific PRD")