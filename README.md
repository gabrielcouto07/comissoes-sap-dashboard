# 💰 Calculadora de Comissões — Scientific PRD v3.0

Dashboard interativo em **Streamlit** para cálculo e análise de comissões de vendas baseado em dados SAP.

## ✨ Funcionalidades

- 📤 Upload de dados (CSV/XLSX) do SAP
- 🔍 Filtros multi-seleção (vendedor, filial, UF, período, documento)
- 📊 Agregações por vendedor e item
- 📈 Gráficos interativos (Plotly)
- 📥 Exportação em Excel (3 abas) e CSV
- ⚠️ Diagnóstico de erros de coluna e % cadastrado

## 📋 Colunas Obrigatórias (SAP)

| Coluna | Tipo |
|--------|------|
| `Documento` | NF ou DEV NF |
| `Código Item` | Código SKU |
| `Vendedor` | Nome do vendedor |
| `Valor de Venda (Linha)` | Numérico |
| `Valor Recebido (Linha)` | Numérico |

### Opcionais
- Filial, UF, Grupo de Itens, Data Faturamento, Cliente, SlpCode

## 🚀 Setup

```bash
# Clone ou entre no diretório
cd "Treinin/New folder (2)"

# Instale dependências
pip install streamlit pandas plotly openpyxl numpy

# Run
streamlit run blank/app.py
```

## 📁 Arquivos

- `blank/app.py` — Aplicação Streamlit principal
- `comissoes.csv` — Tabela de % de comissão (formato: SlpCode;ItemCode;CommissionPct;SlpName)

## 🔧 Correções v3.0

- ✅ FIX #1: pd.read_excel com io.BytesIO — resolve "No columns to parse"
- ✅ FIX #2: remove @st.cache_data para evitar bugs com st.error
- ✅ FIX #3: Filtros sempre retornam listas
- ✅ FIX #4: Melhor detecção de colunas com aliases

## 📄 Licença

© 2025 Scientific PRD

