"""
VendasModel — Query SAP "Vendas por Item (Completo)"
Suporta 35 colunas da planilha exportada do SAP B1.
Modelo para análise de faturamento por representante, região e produto.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
from models.base_model import BaseModel
from utils.formatters import fmt_brl, pct_fmt
from utils.parsers import _get_first_mode
from utils.file_loader import to_excel
from datetime import datetime


class VendasModel(BaseModel):
    """
    Modelo de análise de VENDAS (Vendas por Item - Query SAP B1).
    
    Principais características:
    - Sem deduplicação (cada linha é única)
    - Foco em faturamento, ticket médio e distribuição geográfica
    - Agregações: vendedor, grupo, item, cliente, estado, mês
    """
    
    MODEL_NAME = "VENDAS"
    MODEL_ICON = "📈"
    DEDUP_ENABLED = False  # Vendas não precisa dedup
    
    COL_MAP = {
        # Datas
        "SaleDate": ["Data do Faturamento", "Data Faturamento", "SaleDate", "Data Emissao", "Data Emissão"],
        # Filial
        "BranchName": ["Nome da filial", "Filial Faturamento", "Filial", "BranchName"],
        # Documentos
        "InvDocNum": ["Nº NF", "Numero NF", "Número NF", "InvDocNum", "NF"],
        "DocNum": ["Nº do documento", "Numero do documento", "Número do documento", "DocNum"],
        "InternalNum": ["Nº interno", "Numero interno", "Número interno", "InternalNum"],
        "DocType": ["Documento", "Tipo Documento", "DocType"],
        # Item
        "ItemCode": ["Nº do item", "Numero do item", "Número do item", "ItemCode", "Cod. Item"],
        "ItemDescription": ["Descrição do item", "Descricao do item", "Descrição do Item", "ItemDescription"],
        "ItemGroup": ["Grupo de Itens", "Grupo de itens", "Grupo Itens", "ItemGroup", "Categoria"],
        # Cliente
        "CardCode": ["Código do cliente/fornecedor", "Codigo do cliente", "CardCode", "Cod. Cliente"],
        "CardName": ["Nome do cliente/fornecedor", "Nome do cliente", "CardName", "Cliente", "Nome PN"],
        # Vendedor / Localização
        "SlpName": ["Vendedor", "SlpName", "Nome do Vendedor", "Nome Vendedor"],
        "State": ["UF", "Estado", "State"],
        "UsageType": ["Utilização", "Utilizacao", "Uso", "UsageType"],
        # Quantidades e Valores
        "Quantity": ["Quantidade", "Quantity", "Qtd"],
        "UnitPrice": ["Valor Unitário", "Valor Unitario", "UnitPrice", "Preço Unitário"],
        "UnitPriceIPI": ["Valor unitário IPI", "Valor Unitario IPI", "UnitPriceIPI"],
        "LineTotal": ["Valor dos Itens", "Valor dos itens", "LineTotal", "Valor Itens"],
        "ItemSaleTotal": ["Valor Total da Venda por Itens", "Valor Total Venda por Itens", "Valor Venda Item", "ItemSaleTotal"],
        "AdditionalExpenses": ["Valor Total da Desp. Adicionais", "Desp. Adicionais", "Despesas Adicionais", "AdditionalExpenses"],
        "InvoiceTotal": ["Valor Total da Nota", "Valor Total Nota", "Valor NF", "InvoiceTotal"],
        "AmountReceivable": ["Valor Total a Receber", "Valor a Receber", "AmountReceivable"],
        # Impostos
        "TaxCode": ["Código de imposto", "Codigo Imposto", "TaxCode"],
        "ICMS": ["ICMS"],
        "AliqICMS": ["Aliq ICMS", "Aliquota ICMS", "% ICMS"],
        "IPI": ["IPI"],
        "AliqIPI": ["Aliq IPI", "Aliquota IPI", "% IPI"],
        "PIS": ["PIS"],
        "AliqPIS": ["Aliq PIS", "Aliquota PIS", "% PIS"],
        "COFINS": ["COFINS"],
        "AliqCOFINS": ["Aliq COFINS", "Aliquota COFINS", "% COFINS"],
        "CredPresumido": ["CRED. PRESUMIDO", "Cred. Presumido", "Cred Presumido", "CredPresumido"],
        "DIFAL": ["DIFAL"],
        "TotalTaxes": ["Valor dos Impostos", "Total Impostos", "Impostos", "TotalTaxes"],
        "Volumetria": ["Volumetria"],
    }
    
    REQUIRED_COLS = ["SaleDate", "SlpName", "LineTotal"]
    
    NUMERIC_COLS = [
        "Quantity", "UnitPrice", "UnitPriceIPI", "LineTotal", "ItemSaleTotal",
        "AdditionalExpenses", "InvoiceTotal", "AmountReceivable",
        "ICMS", "AliqICMS", "IPI", "AliqIPI", "PIS", "AliqPIS",
        "COFINS", "AliqCOFINS", "CredPresumido", "DIFAL", "TotalTaxes", "Volumetria",
    ]
    
    TEXT_COLS = [
        "BranchName", "InvDocNum", "DocNum", "InternalNum", "DocType",
        "ItemCode", "ItemDescription", "ItemGroup",
        "CardCode", "CardName", "SlpName", "State", "UsageType", "TaxCode",
    ]
    
    DATE_COLS = ["SaleDate"]
    
    TABS = [
        "📊 Dashboard", "👤 Vendedores", "📦 Itens & Grupos",
        "🏥 Clientes", "🗺️ Estados", "📋 Detalhado", "📥 Exportar",
    ]
    
    FILTER_COLS = ["SlpName", "BranchName", "State", "ItemGroup"]
    
    def __init__(self, df_raw: pd.DataFrame):
        super().__init__(df_raw)
        self.top_n = 10
    
    def load(self) -> "VendasModel":
        """Pipeline: normalize → colunas derivadas → pronto."""
        from utils.normalizers import normalize_columns
        self.df = normalize_columns(
            self.df_raw, self.COL_MAP, self.NUMERIC_COLS,
            self.TEXT_COLS, self.DATE_COLS, "SaleDate"
        )
        # Coluna derivada de mês
        if "SaleDate" in self.df.columns:
            self.df["SaleMonth"] = np.where(
                self.df["SaleDate"].notna(),
                self.df["SaleDate"].dt.to_period("M").astype(str),
                "N/D",
            )
        return self

def get_kpis(self, df: pd.DataFrame) -> list:
    total_fat = df["LineTotal"].sum() if "LineTotal" in df.columns else 0
    total_nota = df["InvoiceTotal"].sum() if "InvoiceTotal" in df.columns else 0
    total_rec = df["AmountReceivable"].sum() if "AmountReceivable" in df.columns else 0
    total_itens = df["Quantity"].sum() if "Quantity" in df.columns else 0
    n_nfs = df["InvDocNum"].nunique() if "InvDocNum" in df.columns else 0
    n_clientes = df["CardName"].nunique() if "CardName" in df.columns else 0
    n_vendedores = df["SlpName"].nunique() if "SlpName" in df.columns else 0
    ticket = total_nota / n_nfs if n_nfs > 0 else 0

    return [
        ("📦 Faturamento", fmt_brl(total_fat), "indigo", f"{int(total_itens):,} itens".replace(",", ".")),
        ("🧾 Total NF", fmt_brl(total_nota), "blue", f"{n_nfs} NFs emitidas"),
        ("💳 A Receber", fmt_brl(total_rec), "teal", "valor líquido"),
        ("🎯 Ticket Médio", fmt_brl(ticket), "purple", "por NF"),
        ("🏥 Clientes", f"{n_clientes}", "green", "ativos no período"),
        ("👤 Vendedores", f"{n_vendedores}", "amber", "em campo"),
    ]

def get_aggregations(self, df: pd.DataFrame) -> dict:
    aggs = {}

    # ── Por Vendedor ──────────────────────────────────────────
    if "SlpName" in df.columns:
        _vend = df.groupby("SlpName").agg(
            Faturamento=("LineTotal", "sum"),
            TotalNF=("InvoiceTotal", "sum"),
            AReceber=("AmountReceivable", "sum"),
            Itens=("Quantity", "sum"),
            NFs=("InvDocNum", "nunique"),
            Clientes=("CardName", "nunique"),
        ).reset_index().rename(columns={"SlpName": "Vendedor"})
        _vend["TicketMedio"] = (_vend["TotalNF"] / _vend["NFs"].replace(0, np.nan)).fillna(0)
        _vend["% AReceber"] = (_vend["AReceber"] / _vend["TotalNF"].replace(0, np.nan) * 100).fillna(0)
        aggs["por_vendedor"] = _vend.sort_values("Faturamento", ascending=False)

    # ── Por Item ─────────────────────────────────────────────
    if "ItemCode" in df.columns:
        _item = df.groupby("ItemCode").agg(
            Descricao=("ItemDescription", _get_first_mode),
            Grupo=("ItemGroup", _get_first_mode),
            Faturamento=("LineTotal", "sum"),
            Quantidade=("Quantity", "sum"),
            NFs=("InvDocNum", "nunique"),
            Clientes=("CardName", "nunique"),
        ).reset_index()
        _item["PrecoMedio"] = (_item["Faturamento"] / _item["Quantidade"].replace(0, np.nan)).fillna(0)
        aggs["por_item"] = _item.sort_values("Faturamento", ascending=False)

    # ── Por Grupo ────────────────────────────────────────────
    if "ItemGroup" in df.columns:
        aggs["por_grupo"] = df.groupby("ItemGroup").agg(
            Faturamento=("LineTotal", "sum"),
            Quantidade=("Quantity", "sum"),
            NFs=("InvDocNum", "nunique"),
            Itens_Distintos=("ItemCode", "nunique"),
        ).reset_index().sort_values("Faturamento", ascending=False)

    # ── Por Cliente ───────────────────────────────────────────
    if "CardName" in df.columns:
        _cli = df.groupby(["CardName", "CardCode"]).agg(
            Faturamento=("LineTotal", "sum"),
            TotalNota=("InvoiceTotal", "sum"),
            Quantidade=("Quantity", "sum"),
            NFs=("InvDocNum", "nunique"),
        ).reset_index().rename(columns={"CardName": "Cliente", "CardCode": "Codigo"})
        aggs["por_cliente"] = _cli.sort_values("Faturamento", ascending=False)

    # ── Por Estado ────────────────────────────────────────────
    if "State" in df.columns:
        aggs["por_estado"] = df.groupby("State").agg(
            Faturamento=("LineTotal", "sum"),
            TotalNota=("InvoiceTotal", "sum"),
            Clientes=("CardName", "nunique"),
            NFs=("InvDocNum", "nunique"),
        ).reset_index().sort_values("Faturamento", ascending=False)

    # ── Por Mês ───────────────────────────────────────────────
    if "SaleMonth" in df.columns and df["SaleMonth"].ne("N/D").any():
        aggs["por_mes"] = df.groupby(["SaleMonth", "SlpName"]).agg(
            Faturamento=("LineTotal", "sum"),
            NFs=("InvDocNum", "nunique"),
        ).reset_index()

    return aggs

def get_charts_config(self) -> list:
    return [
        {"name": "por_vendedor", "type": "bar_h", "x": "Faturamento", "y": "Vendedor"},
        {"name": "por_grupo", "type": "pie", "values": "Faturamento", "names": "ItemGroup"},
    ]

def render_tabs(self, aggs: dict, filters: dict) -> None:
    df = self.df if self.df is not None else pd.DataFrame()
    tabs = st.tabs(self.TABS)

    # ── DASHBOARD ─────────────────────────────────────────────
    with tabs[0]:
        c1, c2 = st.columns(2)

        if "por_vendedor" in aggs and not aggs["por_vendedor"].empty:
            cv = aggs["por_vendedor"].head(self.top_n).sort_values("Faturamento")
            fig = px.bar(cv, x="Faturamento", y="Vendedor", orientation="h",
                         title=f"📈 Top {self.top_n} vendedores",
                         text=cv["Faturamento"].apply(fmt_brl),
                         color="Faturamento",
                         color_continuous_scale=["#bfdbfe", "#1d4ed8"])
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, coloraxis_showscale=False,
                              height=420, plot_bgcolor="white", paper_bgcolor="white")
            c1.plotly_chart(fig, use_container_width=True)

        if "por_grupo" in aggs and not aggs["por_grupo"].empty:
            fig_pie = px.pie(aggs["por_grupo"], values="Faturamento", names="ItemGroup",
                             hole=0.52, title="🥧 Por grupo de item",
                             color_discrete_sequence=px.colors.qualitative.Set3)
            fig_pie.update_traces(textinfo="percent+label")
            fig_pie.update_layout(height=420, showlegend=False, paper_bgcolor="white")
            c2.plotly_chart(fig_pie, use_container_width=True)

        if "por_mes" in aggs and not aggs["por_mes"].empty:
            mes_tot = aggs["por_mes"].groupby("SaleMonth")["Faturamento"].sum().reset_index()
            fig_m = px.line(mes_tot, x="SaleMonth", y="Faturamento", markers=True,
                            title="📅 Evolução mensal",
                            labels={"SaleMonth": "Mês", "Faturamento": "R$"})
            fig_m.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_m, use_container_width=True)

        if "por_estado" in aggs and not aggs["por_estado"].empty:
            d1, d2 = st.columns(2)
            uf_data = aggs["por_estado"].head(15).sort_values("Faturamento")
            fig_uf = px.bar(uf_data, x="Faturamento", y="State", orientation="h",
                            title="🗺️ Faturamento por UF",
                            text=uf_data["Faturamento"].apply(fmt_brl),
                            color="Faturamento",
                            color_continuous_scale=["#d1fae5", "#059669"])
            fig_uf.update_traces(textposition="outside")
            fig_uf.update_layout(showlegend=False, coloraxis_showscale=False,
                                 height=400, plot_bgcolor="white", paper_bgcolor="white")
            d1.plotly_chart(fig_uf, use_container_width=True)

            if "por_vendedor" in aggs and len(aggs["por_vendedor"]) > 1:
                fig_sc = px.scatter(aggs["por_vendedor"], x="Faturamento", y="AReceber",
                                   size="NFs", color="Vendedor",
                                   title="🎯 Faturamento × A Receber",
                                   labels={"Faturamento": "R$", "AReceber": "A Receber (R$)"})
                fig_sc.update_layout(height=400, plot_bgcolor="white",
                                    paper_bgcolor="white", showlegend=False)
                d2.plotly_chart(fig_sc, use_container_width=True)

    # ── VENDEDORES ────────────────────────────────────────────
    with tabs[1]:
        if "por_vendedor" in aggs:
            st.caption(f"{len(aggs['por_vendedor'])} vendedores | período filtrado")
            disp = aggs["por_vendedor"].copy()
            for col in ["Faturamento", "TotalNF", "AReceber", "TicketMedio"]:
                if col in disp.columns:
                    disp[col] = disp[col].apply(fmt_brl)
            if "% AReceber" in disp.columns:
                disp["% AReceber"] = disp["% AReceber"].apply(lambda v: f"{v:.1f}%")
            st.dataframe(disp, use_container_width=True, height=380)

            st.subheader("🔎 Drill-down por vendedor")
            vend_sel = st.selectbox("Selecionar vendedor",
                                    aggs["por_vendedor"]["Vendedor"].tolist())
            if vend_sel and "SlpName" in df.columns:
                dv = df[df["SlpName"] == vend_sel]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Faturamento", fmt_brl(dv["LineTotal"].sum()))
                m2.metric("Qtd Itens", f"{int(dv['Quantity'].sum()):,}".replace(",", "."))
                m3.metric("NFs", int(dv["InvDocNum"].nunique()))
                m4.metric("Clientes", int(dv["CardName"].nunique()))

    # ── ITENS & GRUPOS ────────────────────────────────────────
    with tabs[2]:
        s1, s2 = st.columns([1, 2])
        if "por_grupo" in aggs:
            with s1:
                st.subheader("📊 Por Grupo")
                g = aggs["por_grupo"].copy()
                g["Faturamento"] = g["Faturamento"].apply(fmt_brl)
                st.dataframe(g, use_container_width=True, height=350)

        if "por_item" in aggs:
            with s2:
                st.subheader("📦 Por Item")
                search_item = st.text_input("🔍 Buscar item (código ou descrição)")
                di = aggs["por_item"].copy()
                if search_item:
                    mask = (
                        di["ItemCode"].astype(str).str.contains(search_item, case=False, na=False) |
                        di["Descricao"].astype(str).str.contains(search_item, case=False, na=False)
                    )
                    di = di[mask]
                di_disp = di.copy()
                for col in ["Faturamento", "PrecoMedio"]:
                    if col in di_disp.columns:
                        di_disp[col] = di_disp[col].apply(fmt_brl)
                st.caption(f"{len(di_disp)} itens")
                st.dataframe(di_disp, use_container_width=True, height=500)

    # ── CLIENTES ─────────────────────────────────────────────
    with tabs[3]:
        if "por_cliente" in aggs:
            top_cli = aggs["por_cliente"].head(self.top_n).sort_values("Faturamento")
            fig_cli = px.bar(top_cli, x="Faturamento", y="Cliente", orientation="h",
                             title=f"🏥 Top {self.top_n} clientes",
                             text=top_cli["Faturamento"].apply(fmt_brl),
                             color="Faturamento",
                             color_continuous_scale=["#fecaca", "#be123c"])
            fig_cli.update_traces(textposition="outside")
            fig_cli.update_layout(showlegend=False, coloraxis_showscale=False,
                                  height=420, plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_cli, use_container_width=True)
            cli_disp = aggs["por_cliente"].copy()
            for col in ["Faturamento", "TotalNota"]:
                if col in cli_disp.columns:
                    cli_disp[col] = cli_disp[col].apply(fmt_brl)
            st.dataframe(cli_disp, use_container_width=True, height=350)

    # ── ESTADOS ───────────────────────────────────────────────
    with tabs[4]:
        if "por_estado" in aggs:
            disp_uf = aggs["por_estado"].copy()
            for col in ["Faturamento", "TotalNota"]:
                if col in disp_uf.columns:
                    disp_uf[col] = disp_uf[col].apply(fmt_brl)
            st.dataframe(disp_uf, use_container_width=True, height=450)

    # ── DETALHADO ─────────────────────────────────────────────
    with tabs[5]:
        show_cols = [c for c in [
            "SaleDate", "SaleMonth", "BranchName", "InvDocNum", "DocType",
            "SlpName", "CardCode", "CardName", "State", "UsageType",
            "ItemCode", "ItemDescription", "ItemGroup",
            "Quantity", "UnitPrice", "LineTotal", "ItemSaleTotal",
            "InvoiceTotal", "AmountReceivable", "TotalTaxes",
        ] if c in df.columns]
        detail = df[show_cols].copy()
        col_a, col_b, col_c = st.columns([3, 2, 2])
        search_all = col_a.text_input("🔍 Buscar em todos os campos")
        vend_opts = sorted(df["SlpName"].dropna().unique().tolist()) if "SlpName" in df.columns else []
        uf_opts = sorted(df["State"].dropna().unique().tolist()) if "State" in df.columns else []
        vend_d = col_b.selectbox("Vendedor", ["Todos"] + vend_opts)
        uf_d = col_c.selectbox("UF", ["Todos"] + uf_opts)
        if search_all:
            mask = detail.astype(str).apply(
                lambda col: col.str.contains(search_all, case=False, na=False)
            ).any(axis=1)
            detail = detail[mask]
        if vend_d != "Todos" and "SlpName" in detail.columns:
            detail = detail[detail["SlpName"] == vend_d]
        if uf_d != "Todos" and "State" in detail.columns:
            detail = detail[detail["State"] == uf_d]
        det_disp = detail.copy()
        for col in ["UnitPrice", "LineTotal", "ItemSaleTotal", "InvoiceTotal",
                    "AmountReceivable", "TotalTaxes"]:
            if col in det_disp.columns:
                det_disp[col] = det_disp[col].apply(fmt_brl)
        st.caption(f"{len(det_disp):,} linhas".replace(",", "."))
        st.dataframe(det_disp, use_container_width=True, height=580)

    # ── EXPORTAR ─────────────────────────────────────────────
    with tabs[6]:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        st.subheader("📥 Exportar Vendas")
        sheets = {k: v for k, v in aggs.items()}
        sheets["Detalhado"] = df
        e1, e2 = st.columns(2)
        with e1:
            st.download_button(
                "📊 Excel completo",
                data=to_excel(sheets),
                file_name=f"vendas_{ts}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with e2:
            if "por_vendedor" in aggs:
                st.download_button(
                    "📄 Resumo vendedores CSV",
                    data=aggs["por_vendedor"].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                    file_name=f"vendedores_{ts}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

def get_export_sheets(self, df: pd.DataFrame) -> dict:
    sheets = self.get_aggregations(df)
    sheets["Detalhado"] = df
    return sheets