"""
Model Detector — Detecção automática do modelo pelos dados

Analisa as colunas presentes em um DataFrame e sugere qual modelo
é mais apropriado (Comissão, Vendas, Compras, etc.)
"""

import pandas as pd
from typing import Tuple, List


def detect_model_by_columns(df: pd.DataFrame) -> Tuple[str, float, List[str]]:
    """
    Detecta automaticamente qual modelo usar baseado nas colunas presentes.
    
    Args:
        df: DataFrame com colunas a analisar
        
    Returns:
        (model_name, confidence_score, matching_columns)
        
    Example:
        >>> detect_model_by_columns(df_vendas)
        ('VENDAS', 0.94, ['SaleDate', 'SlpName', 'LineTotal', ...])
    """
    
    col_names = set([c.upper().strip() for c in df.columns])
    
    # Padrões de detecção para cada modelo
    patterns = {
        "COMISSAO": {
            "required": ["RECEIVDATE", "INVDOCNUM", "SLPNAME", "ITEMCODE", "LINETOTAL", "COMMISSIONVALUE"],
            "optional": ["AMOUNTRECEIVED", "COMMISSIONSORT", "BRANCHNAME", "PAYMENTBASE"],
        },
        "VENDAS": {
            "required": ["SALEDATE", "SLPNAME", "LINETOTAL"],
            "optional": ["ITEMCODE", "ITEMDESCRIPTION", "CARDNAME", "INVOICETOTAL", "STATE", "QUANTITY"],
        },
        "COMPRAS": {
            "required": ["PURCHASEDATE", "SUPPLIERNAME", "PURCHASEAMOUNT"],
            "optional": ["ITCODE", "CATEGORYCODE", "QUANTITY", "COST"],
        },
        "DESPESAS": {
            "required": ["EXPENSEDATE", "COSTCENTER", "EXPENSEAMOUNT"],
            "optional": ["CATEGORY", "DEPARTMENT", "DESCRIPTION"],
        },
    }
    
    scores = {}
    matches = {}
    
    for model, pattern in patterns.items():
        # Score = (required_match / total_required) * 0.7 + (optional_match / total_optional) * 0.3
        req_cols = pattern.get("required", [])
        opt_cols = pattern.get("optional", [])
        
        req_found = sum(1 for c in req_cols if c in col_names)
        opt_found = sum(1 for c in opt_cols if c in col_names)
        
        req_score = req_found / len(req_cols) if req_cols else 0
        opt_score = opt_found / len(opt_cols) if opt_cols else 0
        
        # Penalizar se faltam required columns
        if req_found == 0:
            score = 0
        elif req_score < 0.6:
            score = 0  # Rejeitar se faltam muchos required
        else:
            score = req_score * 0.7 + opt_score * 0.3
        
        scores[model] = score
        matches[model] = list(set(
            [c for c in req_cols if c in col_names] + 
            [c for c in opt_cols if c in col_names]
        ))
    
    # Encontrar melhor match
    best_model = max(scores, key=scores.get)
    best_score = scores[best_model]
    best_matches = matches[best_model]
    
    return best_model, best_score, best_matches


def format_detection_message(model: str, score: float, matches: List[str]) -> str:
    """
    Formata uma mensagem legível com o resultado da detecção.
    
    Args:
        model: nome do modelo detectado
        score: score de confiança (0-1)
        matches: lista de colunas que combinaram
        
    Returns:
        string formatada com emoji e informação
    """
    
    icons = {
        "COMISSAO": "💰",
        "VENDAS": "📈",
        "COMPRAS": "🛒",
        "DESPESAS": "💳",
    }
    
    icon = icons.get(model, "📊")
    conf_pct = int(score * 100)
    conf_bar = "█" * conf_pct + "░" * (100 - conf_pct)
    
    return f"""{icon} **{model}** — {conf_pct}% compatível

Colunas reconhecidas: {len(matches)} detectadas
Confiança: [{conf_bar}] {conf_pct}%

✅ Use este modelo para análise automática."""
