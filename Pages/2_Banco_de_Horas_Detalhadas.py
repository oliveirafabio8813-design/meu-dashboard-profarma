# pages/2_Banco_de_Horas_Detalhadas.py (AJUSTADO PARA GITHUB e XLSX)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests             # Necessário para buscar URLs do GitHub
import io                   # NOVO: Necessário para lidar com dados binários do Excel (BytesIO)

# --- Constantes e Configurações ---
st.set_page_config(
    layout="wide", page_title="Dashboard Profarma - Banco de Horas")
COR_PRINCIPAL_VERDE = "#70C247"  # Cor para Crédito/Pagamentos
COR_CONTRASTE = "#dc3545"  # Cor para Débito/Descontos

# --- URLs BRUTAS DO GITHUB (AJUSTE CRÍTICO PARA XLSX) ---
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'

# Arquivos XLSX e suas abas
URL_BANCO_HORAS_RESUMO = REPO_URL_BASE + 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx'
SHEET_BANCO_HORAS = 'ContaCorrenteBancodeHorasResum'

URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx' # Mantido para carregar na load_data, se necessário
SHEET_OCORRENCIAS = 'OcorrênciasnoPonto'


# --- Funções e Carregamento de Dados ---

@st.cache_data(show_spinner="Carregando dados do GitHub...")
def load_data_from_github(url, sheet_name):
    """Carrega o arquivo Excel (XLSX) do link Raw do GitHub."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status() # Lança erro para códigos HTTP 4xx/5xx
        # Lê o conteúdo binário da resposta e usa pd.read_excel
        return pd.read_excel(io.BytesIO(response.content), sheet_name=sheet_name)
    except Exception as e:
        st.error(f"⚠️ Erro ao carregar dados do GitHub ({url}, Aba: {sheet_name}): {e}")
        return pd.DataFrame()


def convert_to_hours(time_str):
    """Converte strings HH:MM para horas decimais, respeitando o sinal '-' inicial."""
    if pd.isna(time_str) or str(time_str).strip() in ['00:00', '00:00:00']:
        return 0.0
    try:
        is_negative = str(time_str).startswith('-')
        if is_negative:
            time_str = str(time_str)[1:]
        parts = str(time_str).split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        total_hours = hours + minutes / 60
        # A função mantém o sinal original, se existir
        return -total_hours if is_negative else total_hours
    except (ValueError, IndexError):
        return 0.0


def format_decimal_to_hhmm(decimal_hours):
    """Converte horas decimais para HH:MM, respeitando o sinal."""
    if pd.isna(decimal_hours) or decimal_hours == 0:
        return '00:00'
    sinal = '-' if decimal_hours < 0 else ''
    abs_hours = abs(decimal_hours)
    horas = int(np.floor(abs_hours))
    minutos_decimais = abs_hours - horas
    minutos = int(round(minutos_decimais * 60))
    if minutos == 60:
        horas += 1
        minutos = 0
    return f"{sinal}{horas:02d}:{minutos:02d}"


@st.cache_data
def load_data():
    # CHAMA A FUNÇÃO CORRIGIDA PARA XLSX
    df_ocorrencias = load_data_from_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
    df_banco_horas = load_data_from_github(URL_BANCO_HORAS_RESUMO, SHEET_BANCO_HORAS)
    
    if df_banco_horas.empty:
        st.error("Falha ao carregar o DataFrame de Banco de Horas do GitHub.")
        st.stop()
        
    if not df_ocorrencias.empty:
        try:
            # Tenta processar Ocorrências (Mantido do original)
            df_ocorrencias['Data'] = pd.to_datetime(
                df_ocorrencias['Data'], errors='coerce', dayfirst=True)
        except Exception:
             # Se der erro no processamento, segue sem o df_ocorrencias
             df_ocorrencias = pd.DataFrame()

    try:
        # 1. Converte Saldo Final (mantém o sinal original)
        df_banco_horas['SaldoFinal_Horas'] = df_banco_horas['SaldoFinal'].apply(
            convert_to_hours)
        df_banco_horas['Saldo Final (HH:MM)'] = df_banco_horas['SaldoFinal_Horas'].apply(
            format_decimal_to_hhmm)

        # 2. Pagamentos (deve ser positivo - Garante que é um crédito)
        df_banco_horas['Pagamentos_Horas'] = df_banco_horas['Pagamentos'].apply(
            convert_to_hours).abs()
        df_banco_horas['Pagamentos (HH:MM)'] = df_banco_horas['Pagamentos_Horas'].apply(
            format_decimal_to_hhmm)

        # 3. Descontos (deve ser negativo - Força o sinal para débito)
        df_banco_horas['Descontos_Horas'] = - \
            df_banco_horas['Descontos'].apply(convert_to_hours).abs()
        df_banco_horas['Descontos (HH:MM)'] = df_banco_horas['Descontos_Horas'].apply(
            format_decimal_to_hhmm)

    except Exception as e:
        st.error(f"Erro ao processar dados de Banco de Horas: {e}")
        st.stop()

    return df_ocorrencias, df_banco_horas


df_ocorrencias, df_banco_horas = load_data()


# --- TÍTULO DA PÁGINA COM LOGO (Inalterado) ---
col_logo, col_title, _ = st.columns([1, 4, 1])

with col_logo:
    try:
        st.image("image_ccccb7.png", width=120)
    except FileNotFoundError:
        st.warning("Logotipo não encontrado.")

with col_title:
    st.markdown(
        f'<h1 style="color: {COR_PRINCIPAL_VERDE}; margin-bottom: 0px;">Dashboard Profarma - Banco de Horas</h1>', unsafe_allow_html=True)
    st.markdown('Relatório e Detalhamento do Banco de Horas')
st.markdown('---')


# --- FILTROS DE ESTABELECIMENTO E DEPARTAMENTO ---

st.subheader('Filtros')
col_filter_est, col_filter_dep, col_filter_button = st.columns([1, 1, 0.5])

# Inicializa o estado dos filtros
if 'selected_establishment_banco' not in st.session_state:
    st.session_state['selected_establishment_banco'] = []
if 'selected_department_banco' not in st.session_state:
    st.session_state['selected_department_banco'] = []


def reset_filters_banco():
    st.session_state['selected_establishment_banco'] = []
    st.session_state['selected_department_banco'] = []


# Botão de Limpar Filtros
with col_filter_button:
    st.write("")
    st.write("")
    st.button('Limpar Filtros', on_click=reset_filters_banco,
              use_container_width=True)


# 1. Filtro de Estabelecimento
with col_filter_est:
    todos_estabelecimentos = sorted(
        list(df_banco_horas['Estabelecimento'].unique()))

    selected_establishments = st.multiselect(
        'Estabelecimento:',
        options=todos_estabelecimentos,
        key='selected_establishment_banco'
    )

# 2. Filtragem Inicial por Estabelecimento
if selected_establishments:
    df_banco_horas_filtrado = df_banco_horas[df_banco_horas['Estabelecimento'].isin(
        selected_establishments)].copy()
else:
    df_banco_horas_filtrado = df_banco_horas.copy()

# 3. Filtro de Departamento
with col_filter_dep:
    todos_departamentos = sorted(
        list(df_banco_horas_filtrado['Departamento'].unique()))
    current_selection_dep = st.session_state['selected_department_banco']
    new_selection_dep = [
        dep for dep in current_selection_dep if dep in todos_departamentos]
    if set(current_selection_dep) != set(new_selection_dep):
        st.session_state['selected_department_banco'] = new_selection_dep
    selected_departments = st.multiselect(
        'Departamento:',
        options=todos_departamentos,
        key='selected_department_banco'
    )

# 4. Filtragem Final por Departamento
if selected_departments:
    df_banco_horas_filtrado = df_banco_horas_filtrado[df_banco_horas_filtrado['Departamento'].isin(
        selected_departments)].copy()

# --- LÓGICA DE TAMANHO DE GRÁFICO CONDICIONAL (Inalterado) ---
filtros_ativos = bool(selected_establishments or selected_departments)
BASE_HEIGHT = 400
if filtros_ativos:
    CHART_HEIGHT = 250
else:
    CHART_HEIGHT = BASE_HEIGHT

# --- GRÁFICOS DE SALDO FINAL (Inalterado) ---
st.markdown('---')
st.subheader('Análise Gráfica por Saldo Final (Acúmulo)')
df_positivo = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] > 0]
df_negativo = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] < 0]

# Gráfico de Saldo Positivo
df_chart_positivo = df_positivo.groupby('Estabelecimento')[
    'SaldoFinal_Horas'].sum().reset_index(name='Total Horas Positivas')
df_chart_positivo = df_chart_positivo.sort_values(
    'Total Horas Positivas', ascending=True)

df_chart_positivo['Total Horas Positivas (HH:MM)'] = df_chart_positivo['Total Horas Positivas'].apply(
    format_decimal_to_hhmm)

col_chart_pos, col_chart_neg = st.columns(2)

with col_chart_pos:
    st.markdown('#### Saldo Positivo por Estabelecimento (Crédito)')
    if not df_chart_positivo.empty:
        fig_positivo = px.bar(
            df_chart_positivo,
            y='Estabelecimento',
            x='Total Horas Positivas',
            orientation='h',
            text='Total Horas Positivas (HH:MM)',
            color='Total Horas Positivas',
            color_continuous_scale=px.colors.sequential.Greens,
            labels={'Total Horas Positivas': 'Total de Horas'},
            template='plotly_white',
            height=CHART_HEIGHT,
        )
        fig_positivo.update_traces(textposition='outside', cliponaxis=False)
        fig_positivo.update_layout(xaxis_title=None, showlegend=False)
        st.plotly_chart(fig_positivo, use_container_width=True)
    else:
        st.info("Nenhum saldo positivo encontrado para este filtro.")

# Gráfico de Saldo Negativo
df_chart_negativo = df_negativo.groupby('Estabelecimento')[
    'SaldoFinal_Horas'].sum().reset_index(name='Total Horas Negativas')
df_chart_negativo = df_chart_negativo.sort_values(
    'Total Horas Negativas', ascending=False)

df_chart_negativo['Total Horas Negativas (HH:MM)'] = df_chart_negativo['Total Horas Negativas'].apply(
    format_decimal_to_hhmm)

with col_chart_neg:
    st.markdown('#### Saldo Negativo por Estabelecimento (Débito)')
    if not df_chart_negativo.empty:
        fig_negativo = px.bar(
            df_chart_negativo,
            y='Estabelecimento',
            x='Total Horas Negativas',
            orientation='h',
            text='Total Horas Negativas (HH:MM)',
            color='Total Horas Negativas',
            color_continuous_scale=px.colors.sequential.Reds_r,
            labels={'Total Horas Negativas': 'Total de Horas'},
            template='plotly_white',
            height=CHART_HEIGHT,
        )
        fig_negativo.update_traces(textposition='outside', cliponaxis=False)
        fig_negativo.update_layout(xaxis_title=None, showlegend=False)
        st.plotly_chart(fig_negativo, use_container_width=True)
    else:
        st.info("Nenhum saldo negativo encontrado para este filtro.")


# --- GRÁFICOS DE PAGAMENTOS/DESCONTOS ---
st.markdown('---')
st.subheader('Análise Gráfica de Movimentações (Pagamentos e Descontos)')

# Pagamentos (Crédito)
df_chart_pagamentos = df_banco_horas_filtrado[df_banco_horas_filtrado['Pagamentos_Horas'] > 0].groupby(
    'Estabelecimento')['Pagamentos_Horas'].sum().reset_index(name='Total Pagamentos')
df_chart_pagamentos = df_chart_pagamentos.sort_values(
    'Total Pagamentos', ascending=True)

df_chart_pagamentos['Total Pagamentos (HH:MM)'] = df_chart_pagamentos['Total Pagamentos'].apply(
    format_decimal_to_hhmm)

col_chart_pag, col_chart_desc = st.columns(2)

with col_chart_pag:
    st.markdown('#### Pagamentos de Horas por Estabelecimento')
    if not df_chart_pagamentos.empty:
        fig_pagamentos = px.bar(
            df_chart_pagamentos,
            y='Estabelecimento',
            x='Total Pagamentos',
            orientation='h',
            text='Total Pagamentos (HH:MM)',
            color='Total Pagamentos',
            color_continuous_scale=px.colors.sequential.Greens,
            labels={'Total Pagamentos': 'Total de Horas Pagas'},
            template='plotly_white',
            height=CHART_HEIGHT,
        )
        fig_pagamentos.update_traces(textposition='outside', cliponaxis=False)
        fig_pagamentos.update_layout(xaxis_title=None, showlegend=False)
        st.plotly_chart(fig_pagamentos, use_container_width=True)
    else:
        st.info("Nenhum pagamento de horas encontrado para este filtro.")

# Descontos (Débito)
df_chart_descontos = df_banco_horas_filtrado[df_banco_horas_filtrado['Descontos_Horas'] < 0].groupby(
    'Estabelecimento')['Descontos_Horas'].sum().reset_index(name='Total Descontos')
df_chart_descontos = df_chart_descontos.sort_values(
    'Total Descontos', ascending=False)

df_chart_descontos['Total Descontos (HH:MM)'] = df_chart_descontos['Total Descontos'].apply(
    format_decimal_to_hhmm)

with col_chart_desc:
    st.markdown('#### Descontos de Horas por Estabelecimento')
    if not df_chart_descontos.empty:
        fig_descontos = px.bar(
            df_chart_descontos,
            y='Estabelecimento',
            x='Total Descontos',
            orientation='h',
            text='Total Descontos (HH:MM)',
            color='Total Descontos',
            color_continuous_scale=px.colors.sequential.Reds_r,
            labels={'Total Descontos': 'Total de Horas Descontadas'},
            template='plotly_white',
            height=CHART_HEIGHT,
        )
        fig_descontos.update_traces(textposition='outside', cliponaxis=False)
        fig_descontos.update_layout(xaxis_title=None, showlegend=False)
        st.plotly_chart(fig_descontos, use_container_width=True)
    else:
        st.info("Nenhum desconto de horas encontrado para este filtro.")


# --- DETALHE DO BANCO DE HORAS (TABELA) ---
st.markdown('---')
st.subheader('Detalhamento por Colaborador')

# 1. Tabela de Saldo Positivo (Crédito)
detalhes_positivo_df = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] > 0].copy()
detalhes_positivo_df = detalhes_positivo_df.sort_values(
    'SaldoFinal_Horas', ascending=False)
detalhes_positivo_df = detalhes_positivo_df[[
    'Matricula', 'Nome', 'Departamento', 'Saldo Final (HH:MM)'
]]
detalhes_positivo_df.columns = [
    'Matrícula', 'Nome do Funcionário', 'Departamento', 'Saldo Positivo'
]


# 2. Tabela de Saldo Negativo (Débito)
detalhes_negativo_df = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] < 0].copy()
detalhes_negativo_df = detalhes_negativo_df.sort_values(
    'SaldoFinal_Horas', ascending=True)
detalhes_negativo_df = detalhes_negativo_df[[
    'Matricula', 'Nome', 'Departamento', 'Saldo Final (HH:MM)'
]]
detalhes_negativo_df.columns = [
    'Matrícula', 'Nome do Funcionário', 'Departamento', 'Saldo Negativo'
]

# 3. Tabela de Pagamentos
detalhes_pagamentos_df = df_banco_horas_filtrado[df_banco_horas_filtrado['Pagamentos_Horas'] > 0].copy()
detalhes_pagamentos_df = detalhes_pagamentos_df.sort_values(
    'Pagamentos_Horas', ascending=False)
detalhes_pagamentos_df = detalhes_pagamentos_df[[
    'Matricula', 'Nome', 'Departamento', 'Pagamentos (HH:MM)'
]]
detalhes_pagamentos_df.columns = [
    'Matrícula', 'Nome do Funcionário', 'Departamento', 'Pagamentos'
]

# 4. Tabela de Descontos
detalhes_descontos_df = df_banco_horas_filtrado[df_banco_horas_filtrado['Descontos_Horas'] < 0].copy()
detalhes_descontos_df = detalhes_descontos_df.sort_values(
    'Descontos_Horas', ascending=True)
detalhes_descontos_df = detalhes_descontos_df[[
    'Matricula', 'Nome', 'Departamento', 'Descontos (HH:MM)'
]]
detalhes_descontos_df.columns = [
    'Matrícula', 'Nome do Funcionário', 'Departamento', 'Descontos'
]


# Exibição das Tabelas de Saldo
st.markdown('#### Saldo Final (Crédito vs. Débito)')
detalhe_col1, detalhe_col2 = st.columns(2)

# Saldo Positivo
with detalhe_col1:
    st.subheader("Saldo Positivo Detalhado")
    if not detalhes_positivo_df.empty:
        num_rows = len(detalhes_positivo_df)
        dynamic_height = min(num_rows * 35 + 40, 500)
        st.dataframe(
            detalhes_positivo_df,
            use_container_width=True,
            hide_index=True,
            height=dynamic_height
        )
    else:
        st.info("Nenhum saldo positivo encontrado para este filtro.")

# Saldo Negativo
with detalhe_col2:
    st.subheader("Saldo Negativo Detalhado")
    if not detalhes_negativo_df.empty:
        num_rows = len(detalhes_negativo_df)
        dynamic_height = min(num_rows * 35 + 40, 500)
        st.dataframe(
            detalhes_negativo_df,
            use_container_width=True,
            hide_index=True,
            height=dynamic_height
        )
    else:
        st.info("Nenhum saldo negativo encontrado para este filtro.")

st.markdown('---')
st.markdown('#### Movimentações (Pagamentos e Descontos)')
detalhe_mov_col1, detalhe_mov_col2 = st.columns(2)

# Pagamentos
with detalhe_mov_col1:
    st.subheader("Pagamentos de Horas Detalhados")
    if not detalhes_pagamentos_df.empty:
        num_rows = len(detalhes_pagamentos_df)
        dynamic_height = min(num_rows * 35 + 40, 500)
        st.dataframe(
            detalhes_pagamentos_df,
            use_container_width=True,
            hide_index=True,
            height=dynamic_height
        )
    else:
        st.info("Nenhum pagamento de horas encontrado para este filtro.")

# Descontos
with detalhe_mov_col2:
    st.subheader("Descontos de Horas Detalhados")
    if not detalhes_descontos_df.empty:
        num_rows = len(detalhes_descontos_df)
        dynamic_height = min(num_rows * 35 + 40, 500)
        st.dataframe(
            detalhes_descontos_df,
            use_container_width=True,
            hide_index=True,
            height=dynamic_height
        )
    else:
        st.info("Nenhum desconto de horas encontrado para este filtro.")


