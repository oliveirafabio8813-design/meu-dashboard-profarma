
# Dashboard_Ocorrencias.py (Página Principal - Resumo Profissional com Head Count Global)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io
import zipfile
import unicodedata  # >>> normalizar nomes de abas e evitar problemas com acentos/espacos

# --- Constantes e Configurações ---
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Resumo",
                   initial_sidebar_state="expanded")

# Cores
COR_PRINCIPAL_VERDE = "#70C247"
COR_ALERTA_VERMELHO = "#dc3545"

# --- URLs BRUTAS DO GITHUB (XLSX) ---
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'

URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx'
SHEET_OCORRENCIAS = 'OcorrênciasnoPonto'  # confere com a sua planilha
URL_BANCO_HORAS_RESUMO = REPO_URL_BASE + 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx'
SHEET_BANCO_HORAS = 'ContaCorrenteBancodeHorasResum'  # confere com a sua planilha

# --------------------------------------
# Utilidades
# --------------------------------------
def _normalize(s: str) -> str:
    """Remove acentos e espaços para facilitar comparações."""
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    return s.replace(" ", "").lower()

def _is_html(b: bytes) -> bool:
    head = b[:4096].lower()
    return (b"<html" in head) or (b"<table" in head and b"</table" in head)

def _is_xlsx_zip(b: bytes) -> bool:
    # .xlsx/.xlsm são ZIP com entradas características
    try:
        with zipfile.ZipFile(io.BytesIO(b)) as zf:
            names = set(zf.namelist())
            return {"[Content_Types].xml", "xl/workbook.xml"} <= names
    except zipfile.BadZipFile:
        return False

# --------------------------------------
# Leitura robusta (XLSX do GitHub Raw)
# --------------------------------------
@st.cache_data(show_spinner=True, ttl=3600)  # >>> cache com TTL para aliviar GitHub
def load_data_from_github(url: str, sheet_name: str) -> pd.DataFrame:
    """
    Baixa bytes de um XLSX via GitHub Raw e lê a aba indicada com engine=openpyxl.
    - Se vier HTML/CSV disfarçado, avisa claramente.
    - Se a aba não for encontrada, tenta a 1ª aba e alerta.
    """
    headers = {
        "User-Agent": "Profarma-Streamlit/1.0 (+https://github.com/oliveirafabio8813-design)",
        "Accept": "*/*",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        raw = resp.content
        if not raw:
            raise ValueError("Arquivo vazio recebido do GitHub.")

        # 1) HTML retornado (erro/limite do GitHub)
        if _is_html(raw):
            raise ValueError("O GitHub retornou HTML (provável 404/limite de taxa). Verifique a URL ou tente novamente.")

        # 2) Confirma estrutura ZIP de XLSX
        if not _is_xlsx_zip(raw):
            # pode ser CSV ou texto plano
            text = raw.decode("utf-8", errors="ignore")
            if ";" in text or "," in text:
                raise ValueError("O link retornou CSV/TEXTO, não XLSX. Baixe o arquivo correto ou troque o parser.")
            raise ValueError("O link não parece um XLSX válido (não é um ZIP de Excel).")

        # 3) Lê a planilha com openpyxl
        bio = io.BytesIO(raw)
        with pd.ExcelFile(bio, engine="openpyxl") as xls:
            # sanity check da aba
            sn_target = _normalize(sheet_name)
            sheet_found = None
            for sn in xls.sheet_names:
                if _normalize(sn) == sn_target:
                    sheet_found = sn
                    break

            if sheet_found is None:
                # tenta a primeira aba e avisa
                sheet_found = xls.sheet_names[0]
                st.warning(
                    f"Aba '{sheet_name}' não encontrada em '{url}'. "
                    f"Usando a primeira aba do arquivo: '{sheet_found}'."
                )

            df = pd.read_excel(xls, sheet_name=sheet_found, engine="openpyxl")
            return df

    except Exception as e:
        st.error(f"⚠️ Erro ao carregar dados do GitHub ({url}, Aba: {sheet_name}): {e}")
        return pd.DataFrame()

# --------------------------------------
# Conversão de horas (evita float)
# --------------------------------------
def hhmm_to_min(time_str):
    """Converte 'HH:MM' (com sinal opcional '-') em minutos inteiros."""
    if pd.isna(time_str):
        return 0
    s = str(time_str).strip()
    if s in ("", "00:00", "00:00:00"):
        return 0
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    parts = s.split(":")
    try:
        h, m = int(parts[0]), int(parts[1])
    except Exception:
        return 0
    total = h * 60 + m
    return -total if neg else total

def min_to_hhmm(total_min: int) -> str:
    """Converte minutos inteiros em 'HH:MM' com sinal."""
    if total_min == 0 or pd.isna(total_min):
        return "00:00"
    neg = total_min < 0
    a = abs(int(total_min))
    h, m = divmod(a, 60)
    sign = "-" if neg else ""
    return f"{sign}{h:02d}:{m:02d}"

# --------------------------------------
# Checks auxiliares
# --------------------------------------
def e_marcacoes_impar(marcacoes):
    if pd.isna(marcacoes):
        return False
    return len(str(marcacoes).strip().split()) % 2 != 0

# --------------------------------------
# Carregamento + Processamento
# --------------------------------------
@st.cache_data(show_spinner=True, ttl=3600)
def load_data():
    df_ocorrencias = load_data_from_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
    df_banco_horas = load_data_from_github(URL_BANCO_HORAS_RESUMO, SHEET_BANCO_HORAS)

    if df_ocorrencias.empty or df_banco_horas.empty:
        st.error("Falha ao carregar um ou ambos os DataFrames do GitHub.")
        st.stop()

    # Ocorrências
    if "Data" in df_ocorrencias.columns:
        # dayfirst=True lida com dd/mm/yyyy; coerção evita crash em formatos mistos
        df_ocorrencias["Data"] = pd.to_datetime(df_ocorrencias["Data"], errors="coerce", dayfirst=True)
    else:
        st.warning("Coluna 'Data' não encontrada em Ocorrências.")

    df_ocorrencias["is_impar"] = df_ocorrencias["Marcacoes"].apply(e_marcacoes_impar) if "Marcacoes" in df_ocorrencias.columns else False
    df_ocorrencias["is_sem_marcacao"] = df_ocorrencias["Ocorrencia"].isin(
        ["Sem marcação de entrada", "Sem marcação de saída"]
    ) if "Ocorrencia" in df_ocorrencias.columns else False

    # Banco de Horas: trabalhar em minutos (evita erro de arredondamento)
    if all(c in df_banco_horas.columns for c in ["SaldoFinal", "Pagamentos", "Descontos"]):
        df_banco_horas["SaldoFinal_Min"]   = df_banco_horas["SaldoFinal"].apply(hhmm_to_min)
        df_banco_horas["Pagamentos_Min"]   = df_banco_horas["Pagamentos"].apply(hhmm_to_min).abs()
        df_banco_horas["Descontos_Min"]    = -df_banco_horas["Descontos"].apply(hhmm_to_min).abs()
    else:
        st.error("Colunas de horas ('SaldoFinal', 'Pagamentos', 'Descontos') não encontradas no Banco de Horas.")
        st.stop()

    return df_ocorrencias, df_banco_horas

# ---------- INÍCIO APP ----------
df_ocorrencias, df_banco_horas = load_data()

st.title("📊 Dashboard de Recursos Humanos Profarma")
st.markdown('---')

# KPIs Globais
total_head_count = df_banco_horas["Matricula"].nunique() if "Matricula" in df_banco_horas.columns else 0

df_ocorrencias["is_falta_nao_justificada"] = df_ocorrencias.apply(
    lambda row: 1 if row.get("Ocorrencia") == "Falta" and row.get("Justificativa") == "Falta" else 0, axis=1
)

total_faltas = int(df_ocorrencias["is_falta_nao_justificada"].sum())
total_impares = int(df_ocorrencias["is_impar"].sum())
total_sem_marcacao = int(df_ocorrencias["is_sem_marcacao"].sum())
total_marcacoes_impares = int(total_impares + total_sem_marcacao)

total_bh_positivo_min = int(df_banco_horas.loc[df_banco_horas["SaldoFinal_Min"] > 0, "SaldoFinal_Min"].sum())
total_bh_negativo_min = int(df_banco_horas.loc[df_banco_horas["SaldoFinal_Min"] < 0, "SaldoFinal_Min"].sum())

total_pagamentos_min = int(df_banco_horas.loc[df_banco_horas["Pagamentos_Min"] > 0, "Pagamentos_Min"].sum())
total_descontos_min  = int(df_banco_horas.loc[df_banco_horas["Descontos_Min"]  < 0, "Descontos_Min"].sum())

bh_positivo_formatado = min_to_hhmm(total_bh_positivo_min)
bh_negativo_formatado = min_to_hhmm(total_bh_negativo_min)
pagamentos_formatado  = min_to_hhmm(total_pagamentos_min)
descontos_formatado   = min_to_hhmm(total_descontos_min)

# Cabeçalho
col_logo, col_title, col_info = st.columns([1, 3, 1])
with col_logo:
    try:
        st.image("image_ccccb7.png", width=120)
    except FileNotFoundError:
        st.warning("Logotipo não encontrado.")

with col_title:
    st.markdown(f'<h1 style="color: {COR_PRINCIPAL_VERDE}; margin-bottom: 0px;">Dashboard Profarma - Visão Geral</h1>', unsafe_allow_html=True)
    st.markdown('Resumo Profissional de Ocorrências e Banco de Horas')

with col_info:
    st.metric(label="Total de Colaboradores (Head Count)", value=f"{total_head_count}")

st.markdown('---')

# KPIs
st.subheader('Indicadores Chave (KPIs)')
col_kpi_1, col_kpi_2, col_kpi_3, col_kpi_4 = st.columns(4)

with col_kpi_1:
    st.metric("Total de Faltas Não Justificadas (Período)", value=f"{total_faltas}", delta_color="off")

with col_kpi_2:
    st.metric("Total de Marcações Ímpares/Ausentes", value=f"{total_marcacoes_impares}", delta_color="off")

with col_kpi_3:
    st.metric("Banco de Horas Positivo (Crédito Total)", value=f"**{bh_positivo_formatado}**",
              help="Soma total das horas em saldo positivo de todos os colaboradores.", delta_color="off")

with col_kpi_4:
    delta_color = "normal" if total_bh_negativo_min < 0 else "off"
    st.metric("Banco de Horas Negativo (Débito Total)", value=f"**{bh_negativo_formatado}**",
              help="Soma total das horas em saldo negativo de todos os colaboradores.", delta_color=delta_color)

st.markdown('---')

# Análise por Estabelecimento
st.subheader('Análise de Distribuição por Estabelecimento')
col_chart_1, col_chart_2 = st.columns(2)

# Coluna 1 — Ocorrências
with col_chart_1:
    st.markdown('#### Top Estabelecimentos por Ocorrências')
    if all(c in df_ocorrencias.columns for c in ["Estabelecimento", "is_falta_nao_justificada", "is_impar", "is_sem_marcacao"]):
        df_ranking_ocorrencias = df_ocorrencias.groupby('Estabelecimento', as_index=False).agg(
            Total_Faltas=('is_falta_nao_justificada', 'sum'),
            Total_Impares=('is_impar', 'sum'),
            Total_Sem_Marcacao=('is_sem_marcacao', 'sum')
        )
        df_ranking_ocorrencias['Total_Ocorrencias'] = (
            df_ranking_ocorrencias['Total_Faltas'] +
            df_ranking_ocorrencias['Total_Impares'] +
            df_ranking_ocorrencias['Total_Sem_Marcacao']
        )
        df_ranking_ocorrencias = df_ranking_ocorrencias.sort_values('Total_Ocorrencias', ascending=True).tail(10)

        if not df_ranking_ocorrencias.empty:
            fig_oc = px.bar(
                df_ranking_ocorrencias,
                y='Estabelecimento',
                x=['Total_Faltas', 'Total_Impares', 'Total_Sem_Marcacao'],
                orientation='h',
                text='Total_Ocorrencias',
                color_discrete_sequence=[COR_ALERTA_VERMELHO, '#ffc107', '#17a2b8'],
                labels={'value': 'Total de Ocorrências', 'Estabelecimento': 'Estabelecimento', 'variable': 'Tipo de Ocorrência'},
                template='plotly_white'
            )
            fig_oc.update_traces(textposition='outside', cliponaxis=False)
            fig_oc.update_layout(xaxis_title=None, legend_title_text='Tipo', height=400, uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig_oc, use_container_width=True)
        else:
            st.info("Nenhuma ocorrência encontrada para exibição no ranking.")
    else:
        st.info("Colunas necessárias não encontradas para o ranking de ocorrências.")

# Coluna 2 — BH Negativo
with col_chart_2:
    st.markdown('#### Ranking de Débito (Saldo Negativo) no Banco de Horas')
    if all(c in df_banco_horas.columns for c in ["Estabelecimento", "SaldoFinal_Min"]):
        df_ranking_bh_neg = (
            df_banco_horas.loc[df_banco_horas['SaldoFinal_Min'] < 0]
            .groupby('Estabelecimento', as_index=False)['SaldoFinal_Min'].sum()
            .rename(columns={'SaldoFinal_Min': 'Total Saldo Negativo (Minutos)'})
            .sort_values('Total Saldo Negativo (Minutos)', ascending=True)
            .head(10)
        )
        if not df_ranking_bh_neg.empty:
            df_ranking_bh_neg['Saldo Negativo (HH:MM)'] = df_ranking_bh_neg['Total Saldo Negativo (Minutos)'].apply(min_to_hhmm)
            fig_bh_neg = px.bar(
                df_ranking_bh_neg, y='Estabelecimento', x='Total Saldo Negativo (Minutos)',
                orientation='h', text='Saldo Negativo (HH:MM)',
                color='Total Saldo Negativo (Minutos)', color_continuous_scale=px.colors.sequential.Reds_r,
                labels={'Total Saldo Negativo (Minutos)': 'Total de Horas Negativas (min)'},
                template='plotly_white',
                category_orders={'Estabelecimento': df_ranking_bh_neg['Estabelecimento'].tolist()}
            )
            fig_bh_neg.update_traces(textposition='outside', cliponaxis=False)
            fig_bh_neg.update_layout(xaxis_title=None, height=400, uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig_bh_neg, use_container_width=True)
        else:
            st.info("Nenhum saldo negativo encontrado para exibição no ranking.")
    else:
        st.info("Colunas necessárias não encontradas para o ranking de saldo negativo.")

st.markdown('---')

# Pagamentos e Descontos
st.subheader('Análise de Movimentações (Pagamentos e Descontos)')
col_mov_1, col_mov_2 = st.columns(2)

with col_mov_1:
    st.markdown('#### Ranking de Pagamentos de Horas')
    if all(c in df_banco_horas.columns for c in ["Estabelecimento", "Pagamentos_Min"]):
        df_pag = (
            df_banco_horas.loc[df_banco_horas["Pagamentos_Min"] > 0]
            .groupby('Estabelecimento', as_index=False)["Pagamentos_Min"].sum()
            .rename(columns={"Pagamentos_Min": "Total Pagamentos (Minutos)"})
            .sort_values("Total Pagamentos (Minutos)", ascending=False)
            .head(10)
        )
        if not df_pag.empty:
            df_pag["Pagamentos (HH:MM)"] = df_pag["Total Pagamentos (Minutos)"].apply(min_to_hhmm)
            fig_pag = px.bar(
                df_pag, y='Estabelecimento', x='Total Pagamentos (Minutos)',
                orientation='h', text='Pagamentos (HH:MM)',
                color='Total Pagamentos (Minutos)', color_continuous_scale=px.colors.sequential.Greens,
                labels={'Total Pagamentos (Minutos)': 'Total de Horas Pagas (min)'},
                template='plotly_white',
                category_orders={'Estabelecimento': df_pag['Estabelecimento'].tolist()}
            )
            fig_pag.update_traces(textposition='outside', cliponaxis=False)
            fig_pag.update_layout(xaxis_title=None, height=400, uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig_pag, use_container_width=True)
        else:
            st.info("Nenhum pagamento de horas encontrado para exibição no ranking.")
    else:
        st.info("Colunas necessárias não encontradas para o ranking de pagamentos.")

with col_mov_2:
    st.markdown('#### Ranking de Descontos de Horas')
    if all(c in df_banco_horas.columns for c in ["Estabelecimento", "Descontos_Min"]):
        df_desc = (
            df_banco_horas.loc[df_banco_horas["Descontos_Min"] < 0]
            .groupby('Estabelecimento', as_index=False)["Descontos_Min"].sum()
            .rename(columns={"Descontos_Min": "Total Descontos (Minutos)"})
            .sort_values("Total Descontos (Minutos)", ascending=True)
            .head(10)
        )
        if not df_desc.empty:
            df_desc["Descontos (HH:MM)"] = df_desc["Total Descontos (Minutos)"].apply(min_to_hhmm)
            fig_desc = px.bar(
                df_desc, y='Estabelecimento', x='Total Descontos (Minutos)',
                orientation='h', text='Descontos (HH:MM)',
                color='Total Descontos (Minutos)', color_continuous_scale=px.colors.sequential.Reds_r,
                labels={'Total Descontos (Minutos)': 'Total de Horas Descontadas (min)'},
                template='plotly_white',
                category_orders={'Estabelecimento': df_desc['Estabelecimento'].tolist()}
            )
            fig_desc.update_traces(textposition='outside', cliponaxis=False)
            fig_desc.update_layout(xaxis_title=None, height=400, uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig_desc, use_container_width=True)
        else:
            st.info("Nenhum desconto de horas encontrado para exibição no ranking.")
    else:
        st.info("Colunas necessárias não encontradas para o ranking de descontos.")


