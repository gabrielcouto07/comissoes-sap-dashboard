# � Power BI Automático Multi-Modelos

Dashboard em **Streamlit** com arquitetura modular para múltiplos tipos de análise: Comissões, Vendas, Compras, Despesas, Receitas.

## ✨ Funcionalidades

- **🎯 Multi-Modelos**: Escolha o tipo de análise (Comissões, Vendas, etc.)
- 📤 Upload de dados (CSV/XLSX) com detecção automática
- 🔄 Normalização inteligente de colunas (com/sem acento)
- 📊 Agregações por perspectiva (vendedor, filial, item, cliente, período)
- 📈 Gráficos interativos (Plotly)
- 🔀 Deduplicação automática de vendas/recebimentos (modelo Comissões)
- 🎛️ Filtros dinâmicos multi-seleção
- 📥 Exportação em Excel e CSV
- ✅ Validação de colunas obrigatórias

## 🏗️ Arquitetura

### Estrutura de Pastas

```
projeto/
├── app.py                          # Main app (170 linhas — pura orquestração)
├── app_backup.py                   # Backup da versão anterior
│
├── utils/                          # Funções genéricas reutilizáveis
│   ├── formatters.py              # fmt_brl, pct_fmt, fmt_date, fmt_int
│   ├── parsers.py                 # parse_num, smart_date, _get_first_mode
│   ├── normalizers.py             # normalize_columns, validate_required_columns
│   ├── deduplicators.py           # add_dedup_flags, get_dedup_subset
│   ├── file_loader.py             # load_file, to_excel
│   └── __init__.py                # re-exports
│
├── models/                         # Modelos de análise
│   ├── base_model.py              # Classe abstrata (interface comum)
│   ├── comissao_model.py          # Modelo: Comissões (refactor)
│   ├── vendas_model.py            # Modelo: Vendas (exemplo novo)
│   └── __init__.py
│
├── templates/                      # Templates Streamlit reutilizáveis
│   ├── dashboard_template.py      # render_header, render_kpis, render_filters
│   ├── export_template.py         # render_export_tab
│   └── __init__.py
│
├── comissoes.csv                   # Tabela de dados de exemplo
└── README.md
```

### Fluxo de Execução

```
Sidebar: Upload arquivo + Selecionar modelo
    ↓
Load genérico (detect cols, encoding, separator)
    ↓
Instanciar modelo escolhido
    ↓
Pipeline: normalize → validate → deduplicate (se necessário)
    ↓
Filtros dinâmicos
    ↓
Agregações (por_vendedor, por_filial, por_item, etc.)
    ↓
KPIs + Charts (delegado ao modelo)
    ↓
Exportação genérica (Excel, CSV)
```

## 🎯 Modelos Disponíveis

### 💰 COMISSÃO (refactor)
- **Dedup**: Sim (LineTotal, AmountReceived)
- **Agregações**: 5 (vendedor, filial, item, cliente, mês)
- **KPIs**: 6 (Vendas, Itens, NFs, Recebido, Comissão, % Médio)
- **Colunas**: ~25 campos mapeados

### 📈 VENDAS (novo)
- **Dedup**: Não
- **Agregações**: 2 (vendedor, cliente)
- **KPIs**: 3 (Total Vendas, Ticket Médio, Transações)
- **Colunas**: 6 campos essenciais

## 📋 Modelo Comissões — Colunas Esperadas

### Obrigatórias (REQUIRED_COLS)
```
ReceiveDate, InvDocNum, SlpName, ItemCode,
LineTotal, AmountReceived, CommissionPct, CommissionValue
```

### Mapeadas (COL_MAP) — Aliases aceitos
```ini
[ReceiveDate]
  - Data do Recebimento, ReceiveDate, Data Recebimento

[SlpName]
  - Nome do Vendedor, Nome do vendedor, SlpName

[LineTotal]
  - Valor Total da Linha NF, LineTotal, Valor Linha

[CommissionValue]
  - Comissao Final, Comissão Final, CommissionValue, Valor Comissão

... e mais 20 campos com múltiplos aliases
```

## 🚀 Setup & Uso

```bash
# Clone ou entre no diretório
cd "Treinin/New folder (2)"

# Instale dependências
pip install -r requirements.txt

# Run
streamlit run app.py
```

### Requirements.txt
```
streamlit>=1.28
pandas>=2.0
numpy>=1.24
plotly>=5.0
openpyxl>=3.0
```

## 🔄 Padrão de Design

### Strategy Pattern
- **BaseModel**: Classe abstrata que define interface comum
- **ComissaoModel**, **VendasModel**, etc.: Implementações específicas

### Reutilização
- **90%+** do código compartilhado
- Novo modelo = ~30 minutos (vs. horas antes)
- Sem duplicação de: normalização, formatação, filtros, export

### Extensibilidade
```python
# Adicionar novo modelo é trivial:
from models.base_model import BaseModel

class MeuModel(BaseModel):
    MODEL_NAME = "MEU_MODELO"
    COL_MAP = {...}
    REQUIRED_COLS = [...]
    
    def get_kpis(self, df):
        return [...]
    
    def get_aggregations(self, df):
        return {...}
    
    # ... etc
```

Depois registrar no app.py:
```python
MODELS = {
    "💰 Comissões": ComissaoModel,
    "📈 Vendas": VendasModel,
    "🆕 Meu Modelo": MeuModel,
}
```

## 📊 Que Mudou na Refatoração

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Linhas app.py** | 938 | 170 |
| **Modelos** | 1 (Comissão) | 2+ (Comissão, Vendas, ...) |
| **Reutilização** | 0% | 90%+ |
| **Tempo novo modelo** | N/A | ~30 min |
| **Testabilidade** | Monolítica | Modular |
| **Manutenção** | Difícil | Fácil |

## 🐛 Correções & Melhorias

### Versão Refatorada (Agora)
- ✅ **Arquitetura modular**: Fácil adicionar novos modelos
- ✅ **Genérica**: COL_MAP, numeric_cols, etc. recebem como parâmetros
- ✅ **Sem globals hardcoded**: Cada modelo auto-contido
- ✅ **Reutilização de componentes**: templates, utils, formatters
- ✅ **Validação centralizada**: validate_required_columns, normalize_columns

### Versão Anterior (v6.3)
- ✅ FIX #1: pd.read_excel com io.BytesIO
- ✅ FIX #2: Cache data genérico
- ✅ FIX #3: Tratamento robusto de NaN
- ✅ FIX #4: Deduplicação inteligente (LineTotal vs AmountReceived)

## 📝 Próximos Passos

1. **Testar** com dados reais do comissoes.csv
2. **Deploy** na Vercel (estrutura já compatível)
3. **Adicionar** modelos: Compras, Despesas, Receitas
4. **Customização** avançada: temas por modelo, alertas contextuais

## 📞 Desenvolvido

- **Stack**: Python 3.10+, Streamlit, Pandas, Plotly
- **Versão**: v7.0 (Refatoração Modular)
- **Última atualização**: 14 de abril de 2026
- **Autor**: Gabriel Cardoso

## 📄 Licença

© 2025 Scientific PRD

