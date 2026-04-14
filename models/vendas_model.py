"""
VendasModel — Modelo de análise simples de vendas.

Exemplo de quão rápido é criar novo modelo com a arquitetura.
Diferenças vs. Comissão: sem dedup, sem comissão, estrutura +simples.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
from models.base_model import BaseModel
from utils import fmt_brl, pct_fmt, _get_first_mode


class VendasModel(BaseModel):
    """
    Modelo de análise de vendas por vendedor/cliente.
    
    Simples: faturamento, quantidade, ticket médio.
    """
    
    MODEL_NAME = "VENDAS"
    MODEL_ICON = "📈"
    
    COL_MAP = {
        "SaleDate":     ["Data Venda", "Data Emissao", "SaleDate", "Data"],
        "SlpName":      ["Vendedor", "Nome do Vendedor", "SlpName", "Sales Rep"],
        "CardName":     ["Cliente", "Nome do PN", "CardName", "Customer"],
        "LineTotal":    ["Valor", "Total", "LineTotal", "Amount"],
        "Quantity":     ["Quantidade", "Quantity", "Qtd"],
        "ItemCode":     ["Item", "Codigo Item", "ItemCode", "Product"],
        "ItemDescription": ["Descricao", "Descrição", "Description"],
        "BranchName":   ["Filial", "Branch", "BranchName"],
        "CommissionPct": ["Comissão %", "Commission %", "CommissionPct"],
    }
    
    REQUIRED_COLS = ["SaleDate", "SlpName", "LineTotal"]
    
    NUMERIC_COLS = ["LineTotal", "Quantity", "CommissionPct"]
    TEXT_COLS = ["SlpName", "CardName", "ItemCode", "ItemDescription", "BranchName"]
    DATE_COLS = ["SaleDate"]
    
    DEDUP_ENABLED = False  # Vendas não precisa dedup
    
    TABS = ["📊 Dashboard", "👤 Vendedores", "🏥 Clientes", "📥 Exportar"]
    FILTER_COLS = ["SlpName", "BranchName", "CardName"]
    
    def __init__(self, df_raw: pd.DataFrame):
        super().__init__(df_raw)
        self.top_n = 10
    
    def load(self) -> "VendasModel":
        """Carrega e normaliza dados específicos de Vendas."""
        super().load()
        
        # Derivadas
        if "SlpName" in self.df.columns and self.df["SlpName"].eq("").all():
            self.df["SlpName"] = "Vendedor"
        
        return self
    
    def get_kpis(self, df: pd.DataFrame = None) -> list[tuple]:
        """KPIs simplificados para Vendas."""
        if df is None:
            df = self.df
        
        total_sales = df["LineTotal"].sum() if "LineTotal" in df.columns else 0
        num_trans = len(df)
        ticket = total_sales / num_trans if num_trans > 0 else 0
        n_sellers = df["SlpName"].nunique() if "SlpName" in df.columns else 0
        
        return [
            ("📈 Total Vendas", fmt_brl(total_sales), "blue", f"{num_trans:,} transações".replace(",", ".")),
            ("🎯 Ticket Médio", fmt_brl(ticket), "emerald", f"{n_sellers} vendedores"),
            ("📊 Transações", f"{num_trans:,}".replace(",", "."), "teal", "sem dedup"),
        ]
    
    def get_aggregations(self, df: pd.DataFrame = None) -> dict:
        """Agregações: vendedor, cliente, itens."""
        if df is None:
            df = self.df
        
        aggs = {}
        
        # Por Vendedor
        if "SlpName" in df.columns:
            resumo_vend = df.groupby("SlpName").agg(
                Vendas=("LineTotal", "sum"),
                Transacoes=("LineTotal", "count"),
                Itens=("Quantity", "sum"),
                Clientes=("CardName", "nunique"),
            ).reset_index().sort_values("Vendas", ascending=False)
            resumo_vend["TicketMedio"] = resumo_vend["Vendas"] / resumo_vend["Transacoes"]
            aggs["por_vendedor"] = resumo_vend
        
        # Por Cliente
        if "CardName" in df.columns:
            resumo_cli = df.groupby("CardName").agg(
                Vendas=("LineTotal", "sum"),
                Compras=("LineTotal", "count"),
                Itens=("Quantity", "sum"),
            ).reset_index().sort_values("Vendas", ascending=False)
            aggs["por_cliente"] = resumo_cli
        
        self.aggs = aggs
        return aggs
    
    def get_charts_config(self) -> list[dict]:
        """Gráficos para Vendas."""
        return [
            {"name": "Top Vendedores", "type": "bar"},
            {"name": "Vendas por Cliente", "type": "pie"},
        ]
    
    def render_tabs(self, aggs: dict = None, filters: dict = None) -> None:
        """Renderiza tabs básicas (simplificado)."""
        if aggs is None:
            aggs = self.aggs or self.get_aggregations()
        
        st.info("✅ Modelo Vendas renderizado com sucesso!")
    
    def get_export_sheets(self, df: pd.DataFrame = None) -> dict:
        """Sheets para exportação."""
        aggs = self.aggs or self.get_aggregations()
        return {
            "Resumo_Vendedor": aggs.get("por_vendedor", pd.DataFrame()),
            "Resumo_Cliente": aggs.get("por_cliente", pd.DataFrame()),
            "Detalhado": df if df is not None else self.df,
        }
