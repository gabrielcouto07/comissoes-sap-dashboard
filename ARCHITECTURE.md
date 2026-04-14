# 🏗️ ARCHITECTURE.md — Power BI Automático Multi-Modelos

## Visão Geral

Este documento descreve a arquitetura modular do Power BI Automático, suas decisões de design, padrões utilizados, e guias para extensão.

## 📐 Decisões Arquiteturais

### 1. **Padrão Strategy**

Cada modelo de análise implementa a interface `BaseModel`, permitindo:
- ✅ Múltiplas estratégias de processamento coexistirem
- ✅ Seleção em tempo de execução (sidebar)
- ✅ Adição de novos modelos sem modificar código existing

**Alternativas consideradas:**
- ❌ Inheritance simples: Rígida, difícil generalizar comportamentos
- ❌ Conditional logic no app.py: Monolítico, difícil de manter
- ✅ **Strategy (padrão escolhido)**: Flexível, extensível

### 2. **Separação em Camadas**

```
app.py              (Orquestração — 170 linhas)
    ↓
models/             (Lógica de negócio — ~120 linhas/modelo)
    ↓
templates/          (Renderização UI — genérica ~100 linhas)
    ↓
utils/              (Funções puras — ~50 linhas/módulo)
```

**Benefícios:**
- Testabilidade: Utils e models sem Streamlit
- Reusabilidade: Templates usadas por múltiplos modelos
- Manutenibilidade: Separação clara de responsabilidades

### 3. **Funções Genéricas com Parâmetros**

❌ **Antes:**
```python
def normalize_columns(df):
    # Usa global COL_MAP — hardcoded
    rev = {alias.upper(): col for col, aliases in COL_MAP.items() for alias in aliases}
```

✅ **Depois:**
```python
def normalize_columns(df, col_map, numeric_cols=None, text_cols=None):
    # Recebe col_map como parâmetro — genérico
    rev = {alias.upper(): col for col, aliases in col_map.items() for alias in aliases}
```

**Vantagem:** Sem dependências globais, reutilizável em qualquer modelo.

### 4. **Deduplicação Condicional**

Nem todo modelo precisa dedup. Solução:

```python
class BaseModel:
    DEDUP_ENABLED: bool = False
    DEDUP_LT_COLS: list = None
    DEDUP_AR_COLS: list = None
    
    def load(self):
        if self.DEDUP_ENABLED:
            self.df = add_dedup_flags(self.df, ...)
```

ComissaoModel:
```python
DEDUP_ENABLED = True
DEDUP_LT_COLS = ["InvDocNum", "ItemCode"]
DEDUP_AR_COLS = ["InvDocNum", "ReceiptNumber"]
```

VendasModel:
```python
DEDUP_ENABLED = False  # Sem dedup
```

## 📊 Fluxo de Dados

```
Upload
  ↓
Load genérico (file_loader)
  ├→ Detecta formato (xlsx/csv)
  ├→ Tenta múltiplos encodings
  └→ Retorna DataFrame bruto
  ↓
Instanciar modelo
model = ModelClass(df_raw)
  ↓
Load modelo
model.load()
  ├→ Normaliza colunas (normalize_columns)
  ├→ Converte tipos numéricos (parse_num)
  ├→ Parse datas (smart_date)
  ├→ Adiciona dedup flags (se habilitado)
  └→ Cria derivadas (ex: período)
  ↓
Validar
ok, missing = model.validate()
  ├→ Verifica REQUIRED_COLS existem
  └→ Retorna lista de colunas faltando
  ↓
Aplicar filtros
filtered = model.apply_filters(filters_dict)
  ├→ Itera sobre cada coluna
  └→ Filtra por valores selecionados
  ↓
Agregar dados
aggs = model.get_aggregations(filtered)
  ├→ Calcula resumos por perspectiva
  ├→ Usa subsets dedup (se aplicável)
  └→ Retorna dict com agregações
  ↓
Calcular KPIs
kpis = model.get_kpis(filtered)
  ├→ Retorna list[(label, value, color, sub), ...]
  └→ Renderiza com render_kpis()
  ↓
Renderizar UI
model.render_tabs(aggs, filters)
render_export_tab(model, filtered)
```

## 🧩 Componentes

### BaseModel (`models/base_model.py`)

**Responsabilidades:**
- Interface comum para todos os modelos
- Pipeline: load → validate → apply_filters
- Defaults inteligentes (DEDUP_ENABLED=False, etc.)
- Métodos abstratos obrigatórios

**Métodos abstratos (implementar em subclasses):**
- `get_kpis(df)` → list[tuple] KPIs
- `get_aggregations(df)` → dict agregações
- `get_charts_config()` → list[dict] config gráficos
- `render_tabs(aggs, filters)` → None (renderiza Streamlit)

**Métodos com defaults (pode sobrescrever):**
- `load()` → pipeline normalização
- `validate()` → verifica colunas obrigatórias
- `apply_filters(filters_dict)` → DataFrame filtrado
- `get_export_sheets(df)` → dict para Excel

### ComissaoModel (`models/comissao_model.py`)

**Especialidades:**
- Deduplicação de vendas (LineTotal) e recebimentos (AmountReceived)
- 5 agregações (vendedor, filial, item, cliente, mês)
- 6 KPIs específicos
- Tratamentos especiais (InvDocNum NaN, SlpName fallback)

**Código:**
```python
class ComissaoModel(BaseModel):
    MODEL_NAME = "COMISSAO"
    DEDUP_ENABLED = True
    DEDUP_LT_COLS = ["InvDocNum", "ItemCode"]
    DEDUP_AR_COLS = ["InvDocNum", "ReceiptNumber"]
    
    def load(self) -> ComissaoModel:
        super().load()
        # Lógica customizada aqui
        return self
```

### VendasModel (`models/vendas_model.py`)

**Especialidades:**
- Sem deduplicação (vendas são únicas por linha)
- Simples: 3 KPIs (Total, Ticket Médio, Transações)
- 2 agregações (vendedor, cliente)
- Modelo exemplo de quão rápido é criar novo

**Times:**
- ComissaoModel: ~600 linhas (complexo)
- VendasModel: ~120 linhas (simples)
- Ratio: 5x menos código!

### Utils (`utils/*.py`)

**formatters.py:**
- `fmt_brl(v)` → "R$ 1.234,56"
- `pct_fmt(v)` → "15,00%"
- `fmt_date(v)` → "01/01/2023"
- `fmt_int(v)` → "1.234"

**parsers.py:**
- `parse_num(v)` → float robusta (Excel serials, locales, NaN)
- `smart_date(v)` → pd.Timestamp (formatos variados)
- `_get_first_mode(x)` → modo de série (para agregações text)

**normalizers.py:**
- `normalize_columns(df, col_map, numeric_cols, text_cols, date_cols)` → DataFrame normalizado
- `validate_required_columns(df, required)` → list colunas faltando

**deduplicators.py:**
- `add_dedup_flags(df, lt_key_cols, ar_key_cols)` → DataFrame com flags _lt_first, _ar_first
- `get_dedup_subset(df, flag_col)` → DataFrame filtrado por flag

**file_loader.py:**
- `load_file(f, col_map)` → (DataFrame, error_msg) com detecção automática
- `to_excel(sheets)` → bytes do arquivo Excel

### Templates (`templates/*.py`)

**dashboard_template.py:**
- `render_header(model, filtered_df)` → header customizado
- `render_kpis(model_kpis)` → KPI cards bonitas
- `render_filters(df, filter_cols)` → filtros dinâmicos + multiselect
- `render_dataframe_display(df, numeric_cols, percent_cols)` → table formatada
- `render_search_filter(df, search_key)` → busca global

**export_template.py:**
- `render_export_tab(model, filtered_df)` → downloads Excel/CSV + preview

## 🔄 Como Adicionar Novo Modelo

### Passo 1: Criar classe

```python
# models/meu_modelo.py
from models.base_model import BaseModel
import pandas as pd

class MeuModel(BaseModel):
    MODEL_NAME = "MEU_MODELO"
    MODEL_ICON = "🆕"
    
    COL_MAP = {
        "ColA": ["Alias1", "Alias2"],
        "ColB": ["Alias3", "Alias4"],
    }
    
    REQUIRED_COLS = ["ColA", "ColB"]
    NUMERIC_COLS = ["ColA"]
    TEXT_COLS = ["ColB"]
    DATE_COLS = []
    
    DEDUP_ENABLED = False
    
    TABS = ["📊 Dashboard", "📋 Detalhado", "📥 Exportar"]
    FILTER_COLS = ["ColA", "ColB"]
    
    def get_kpis(self, df=None):
        if df is None: df = self.df
        total_a = df["ColA"].sum()
        return [
            ("📊 Total", f"{total_a:,.0f}".replace(",", "."), "blue", "resumo"),
        ]
    
    def get_aggregations(self, df=None):
        if df is None: df = self.df
        resumo = df.groupby("ColB").agg(Total=("ColA", "sum")).reset_index()
        return {"por_categoria": resumo}
    
    def get_charts_config(self):
        return [{"name": "Chart 1", "type": "bar"}]
    
    def render_tabs(self, aggs=None, filters=None):
        st.info("✅ Modelo renderizado")
```

### Passo 2: Registrar no app.py

```python
from models.meu_modelo import MeuModel

MODELS = {
    "💰 Comissões": ComissaoModel,
    "📈 Vendas": VendasModel,
    "🆕 Meu Modelo": MeuModel,  # ← adicionar aqui
}
```

### Passo 3: Test

```bash
streamlit run app.py
# Sidebar: escolha "🆕 Meu Modelo"
# Upload dados com colunas correspondentes
```

## 🧪 Testabilidade

**Models são testáveis sem Streamlit:**

```python
import pandas as pd
from models.comissao_model import ComissaoModel

# Teste unitário (sem st.*)
df = pd.DataFrame({
    "ReceiveDate": ["2024-01-01"],
    "SlpName": ["João"],
    "LineTotal": [1000.0],
    # ... etc
})

model = ComissaoModel(df).load()
assert model.validate()[0]

kpis = model.get_kpis()
assert len(kpis) == 6
```

## 📈 Performance

### Caching
```python
@st.cache_data(show_spinner=False)
def _cached_load(file_bytes, filename):
    # Evita reprocessar arquivo a cada interação
```

### Dedup Subsets
```python
# ComissaoModel mantém _lt e _ar pré-filtrados
# Agregações usam subsets, não recomputa a cada vez
```

## 🚀 Possíveis Extensões

1. **Mais modelos**: Compras, Despesas, Receitas, Faturamento, Estoque
2. **Temas por modelo**: Cores, ícones, layouts customizados
3. **Alertas contextuais**: "Margem baixa", "Falta giro", etc.
4. **Modelos customizáveis**: YAML com config de col_map, KPIs, etc.
5. **Caching em BD**: Armazenar agregações para acesso rápido
6. **Webhooks**: Integrar com Slack, Email, etc.

## 📝 Convenções de Código

- **PEP 8**: Seguir convenções Python
- **Docstrings**: Toda função/classe tem docstring
- **Type hints**: Usar `def func(x: int) -> str:` onde possível
- **Nomes**: `get_*()` para métodos que retornam dados, `render_*()` para UI

## 🔗 Relacionados

- `README.md` — Guia de uso
- `PROMPT_TRANSFORMACAO_POWERBI.md` — Visão estratégica da transformação
- `app.py` — Aplicação principal (~170 linhas)
- `models/` — Implementações de modelos
- `utils/` — Funções compartilhadas

---

**Última atualização:** 14 de abril de 2026  
**Versão:** 7.0 (Arquitetura Modular)
