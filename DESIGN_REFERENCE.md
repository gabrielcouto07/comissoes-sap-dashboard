# 🎨 Quick Reference — Design System

## Imports Rápidos

```python
# Cores
from config.colors import PALETTE, CHART_COLORS

# UI Components
from templates.ui import (
    load_theme,
    kpi_card,
    render_kpi_row,
    apply_chart_style,
    render_header,
    render_separator,
)
```

---

## Paleta de Cores

```python
PALETTE = {
    "bg": "#0f1117",          # Fundo
    "surface": "#1a1d27",     # Cards
    "primary": "#4f8ef7",     # Azul
    "success": "#34c97e",     # Verde
    "warning": "#f5a623",     # Amber
    "danger": "#e05c5c",      # Vermelho
    "info": "#22d3ee",        # Cyan
    "text": "#e8eaf0",        # Texto
    "muted": "#8b90a8",       # Texto fraco
}

CHART_COLORS = [
    "#4f8ef7",  # Blue
    "#34c97e",  # Green
    "#f5a623",  # Amber
    "#e05c5c",  # Red
    "#a78bfa",  # Purple
    "#22d3ee",  # Cyan
]
```

---

## Padrões de Uso

### 1. Gráfico Básico (Bar)

```python
import plotly.express as px
from templates.ui import apply_chart_style, CHART_COLORS

fig = px.bar(
    df, 
    x="Categoria", 
    y="Valor",
    color_discrete_sequence=CHART_COLORS,
)
fig = apply_chart_style(fig, title="Meu Gráfico", height=380)
st.plotly_chart(fig, use_container_width=True)
```

### 2. Gráfico com Cores Gradientes

```python
fig = px.bar(
    df,
    x="Categoria",
    y="Valor",
    color="Valor",
    color_continuous_scale=CHART_COLORS[:2],  # Gradient blue→green
)
fig = apply_chart_style(fig, title="Top Itens")
st.plotly_chart(fig, use_container_width=True)
```

### 3. KPI Individual

```python
from templates.ui import kpi_card

kpi_card(
    label="Faturamento",
    value="R$ 1.234.567",
    delta=+15.3,
    icon="💰",
    color="primary",  # primary, success, warning, danger, info
)
```

### 4. Linha de KPIs

```python
from templates.ui import render_kpi_row

kpis = [
    {
        "label": "Vendas",
        "value": "R$ 2.5M",
        "delta": +12.4,
        "icon": "💼",
        "color": "primary",
    },
    {
        "label": "Ticket",
        "value": "R$ 1.250",
        "delta": -3.2,
        "icon": "🎯",
        "color": "warning",
    },
    {
        "label": "Clientes",
        "value": "450",
        "icon": "👥",
        "color": "success",
    },
]

render_kpi_row(kpis, layout=[2, 2, 1])
```

### 5. Header Customizado

```python
from templates.ui import render_header

render_header(model, filtered_df)
```

### 6. Separador

```python
from templates.ui import render_separator

render_separator(title="Seção de Gráficos")
```

---

## Cores por Tipo de Dado

| IntençãoI | Cor | Variável |
|-----------|-----|----------|
| Principal | Azul | `PALETTE["primary"]` |
| Positivo | Verde | `PALETTE["success"]` |
| Aviso | Amber | `PALETTE["warning"]` |
| Negativo | Vermelho | `PALETTE["danger"]` |
| Info | Cyan | `PALETTE["info"]` |

---

## Exemplo Completo

```python
import streamlit as st
import pandas as pd
import plotly.express as px
from config.colors import PALETTE, CHART_COLORS
from templates.ui import (
    load_theme,
    kpi_card,
    render_kpi_row,
    apply_chart_style,
)

# 1. Carregar tema (executa uma vez)
load_theme()

# 2. Dados
data = {
    "Mês": ["Jan", "Fev", "Mar", "Abr"],
    "Vendas": [1000, 1200, 1100, 1500],
}
df = pd.DataFrame(data)

# 3. KPIs
st.subheader("📊 KPIs")
kpis = [
    {"label": "Total", "value": "R$ 4.8k", "icon": "💰", "delta": +12},
    {"label": "Média", "value": "R$ 1.2k", "icon": "📈", "delta": +5},
]
render_kpi_row(kpis, layout=[2, 2])

# 4. Gráfico
st.subheader("📈 Evolução")
fig = px.line(df, x="Mês", y="Vendas", markers=True)
fig.update_traces(line=dict(color=PALETTE["primary"], width=3))
fig = apply_chart_style(fig, title="Vendas por Mês", height=380)
st.plotly_chart(fig, use_container_width=True)
```

---

## Estrutura de Arquivos

```
config/
├── __init__.py
└── colors.py            # ← Paleta centralizada

templates/
├── __init__.py
├── ui.py                # ← Componentes (novo)
├── dashboard_template.py
└── export_template.py

theme.css               # ← Estilos CSS (novo)

app.py                  # ← Integrado (modificado)
```

---

## Notas

- ✅ `load_theme()` executa uma vez (cached)
- ✅ Tudo usa `PALETTE` e `CHART_COLORS` para coesão
- ✅ Dark mode por padrão
- ✅ Fonts: Inter (Streamlit) + Courier (números)
- ✅ Hover e transitions automáticos

---

## Troubleshooting

**P: Gráfico não está apparecendo em dark mode**  
R: Certifique-se de rodar `load_theme()` no início do app.

**P: Cores do gráfico não são CHART_COLORS**  
R: Use `color_discrete_sequence=CHART_COLORS` no `px.bar()`.

**P: KPI cards parecem estranhos**  
R: Verifique se CSS foi carregado com `load_theme()`.

**P: Quero mudar uma cor**  
R: Edite `config/colors.py` → tudo se atualiza sem mexer em outro lugar.
