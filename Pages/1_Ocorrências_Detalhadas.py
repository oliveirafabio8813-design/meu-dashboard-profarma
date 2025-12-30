# pages/1_Ocorrências_Detalhadas.py (ATUALIZADO)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io

# --- Constantes e Configurações ---
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Ocorrências")
COR_PRINCIPAL_VERDE = "#70C247"
COR_CONTRASTE = "#4CAF50" # Cor usada para contrastes (Marcações Ímpares)

# --- URLs BRUTAS DO GITHUB ---
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'
URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx'
SHEET_OCORRENCIAS = 'OcorrênciasnoPonto'
URL_BANCO_HORAS_RESUMO = REPO_URL_BASE + 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx'
SHEET_BANCO_HORAS = 'ContaCorrenteBancodeHorasResum'

# --- Funções de Processamento de Dados ---

@st.cache_data(show_spinner="Carregando dados do GitHub...")
def load_data_from_github(url, sheet_name):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content), sheet_name=sheet_name)
    except Exception as e:
        st.error(f"⚠️ Erro ao carregar dados do GitHub: {e}")
        return pd.DataFrame()

def e_marcacoes_impar(marcacoes):
    if pd.isna(marcacoes):
        return False
    return len(str(marcacoes).strip().split()) % 2 != 0

def convert_to_hours(time_str):
    if pd.isna(time_str) or time_str == '00:00':
        return 0.0
    try:
        is_negative = str(time_str).startswith('-')
        if is_negative:
            time_str = str(time_str)[1:]
        parts = str(time_str).split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        total_hours = hours + minutes / 60
        return -total_hours if is_negative else total_hours
    except (ValueError, IndexError):
        return 0.0

@st.cache_data
def load_data():
    df_ocorrencias = load_data_from_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
    df_banco_horas = load_data_from_github(URL_BANCO_HORAS_RESUMO, SHEET_BANCO_HORAS)
    
    if df_ocorrencias.empty:
        st.error("Falha ao carregar o DataFrame de Ocorrências.")
        st.stop()
        
    try:
        df_ocorrencias['Data'] = pd.to_datetime(df_ocorrencias['Data'], errors='coerce', dayfirst=True)
        df_ocorrencias['is_impar'] = df_ocorrencias['Marcacoes'].apply(e_marcacoes_impar)
        df_ocorrencias['is_sem_marcacao'] = df_ocorrencias['Ocorrencia'].isin(['Sem marcação de entrada', 'Sem marcação de saída'])
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        st.stop()

    return df_ocorrencias, df_banco_horas

df_ocorrencias, df_banco_horas = load_data()

# --- TÍTULO DA PÁGINA ---
col_logo, col_title, _ = st.columns([1, 4, 1])
with col_logo:
    try:
        st.image("image_ccccb7.png", width=120)
    except:
        st.warning("Logo não encontrado.")

with col_title:
    st.markdown(f'<h1 style="color: {COR_PRINCIPAL_VERDE}; margin-bottom: 0px;">Dashboard Profarma - Ocorrências</h1>', unsafe_allow_html=True)
    st.markdown('Relatório e Detalhamento de Ocorrências no Ponto')

st.markdown('---')

# --- FILTROS ---
st.subheader('Filtros')
col_filter_est, col_filter_dep, col_filter_button = st.columns([1, 1, 0.5])

if 'selected_establishment_ocorrencias' not in st.session_state:
    st.session_state['selected_establishment_ocorrencias'] = []
if 'selected_department_ocorrencias' not in st.session_state:
    st.session_state['selected_department_ocorrencias'] = []

def reset_filters():
    st.session_state['selected_establishment_ocorrencias'] = []
    st.session_state['selected_department_ocorrencias'] = []

with col_filter_button:
    st.write("") ; st.write("")
    st.button('Limpar Filtros', on_click=reset_filters, use_container_width=True)

with col_filter_est:
    todos_estabelecimentos = sorted(list(df_ocorrencias['Estabelecimento'].unique()))
    selected_establishments = st.multiselect('Estabelecimento:', options=todos_estabelecimentos, key='selected_establishment_ocorrencias')

if selected_establishments:
    df_ocorrencias_filtrado = df_ocorrencias[df_ocorrencias['Estabelecimento'].isin(selected_establishments)].copy()
else:
    df_ocorrencias_filtrado = df_ocorrencias.copy()

with col_filter_dep:
    todos_departamentos = sorted(list(df_ocorrencias_filtrado['Departamento'].unique()))
    selected_departments = st.multiselect('Departamento:', options=todos_departamentos, key='selected_department_ocorrencias')

if selected_departments:
    df_ocorrencias_filtrado = df_ocorrencias_filtrado[df_ocorrencias_filtrado['Departamento'].isin(selected_departments)].copy()

# --- KPIs ---
st.markdown('---')
st.subheader('Resumo das Ocorrências')

df_ocorrencias_filtrado['is_falta_nao_justificada'] = df_ocorrencias_filtrado.apply(
    lambda row: 1 if row['Ocorrencia'] == 'Falta' and row['Justificativa'] == 'Falta' else 0, axis=1)

total_faltas = df_ocorrencias_filtrado['is_falta_nao_justificada'].sum()
total_impares = df_ocorrencias_filtrado['is_impar'].sum()
total_sem_marcacao = df_ocorrencias_filtrado['is_sem_marcacao'].sum()
total_geral_impares = int(total_impares + total_sem_marcacao)

c1, c2, c3 = st.columns(3)
c1.metric("Faltas Não Justificadas", int(total_faltas))
c2.metric("Marcações Ímpares/Ausentes", total_geral_impares)

# --- GRÁFICO 1: POR DEPARTAMENTO ---
st.markdown('---')
st.subheader('Ocorrências por Departamento')

df_chart_dep = df_ocorrencias_filtrado.groupby('Departamento').agg(
    Faltas=('is_falta_nao_justificada', 'sum'),
    Impares=('is_impar', 'sum'),
    Sem_Marcacao=('is_sem_marcacao', 'sum')
).reset_index()
df_chart_dep['Total'] = df_chart_dep['Faltas'] + df_chart_dep['Impares'] + df_chart_dep['Sem_Marcacao']
df_chart_dep = df_chart_dep[df_chart_dep['Total'] > 0].sort_values('Total', ascending=True)

if not df_chart_dep.empty:
    h_dep = min(len(df_chart_dep) * 40 + 80, 700)
    fig_dep = px.bar(df_chart_dep, y='Departamento', x=['Faltas', 'Impares', 'Sem_Marcacao'],
                     orientation='h', color_discrete_sequence=[COR_CONTRASTE, '#ffc107', '#17a2b8'],
                     template='plotly_white', height=h_dep)
    st.plotly_chart(fig_dep, use_container_width=True)

# --- NOVO GRÁFICO 3: POR DATA (ABAIXO DO DE DEP.) ---
st.markdown('---')
st.subheader('Ocorrências por Data')

df_chart_data = df_ocorrencias_filtrado.groupby('Data').agg(
    Faltas=('is_falta_nao_justificada', 'sum'),
    Impares=('is_impar', 'sum'),
    Sem_Marcacao=('is_sem_marcacao', 'sum')
).reset_index()

df_chart_data['Data_Formatada'] = df_chart_data['Data'].dt.strftime('%d/%m/%Y')
df_chart_data['Total_Dia'] = df_chart_data['Faltas'] + df_chart_data['Impares'] + df_chart_data['Sem_Marcacao']
df_chart_data = df_chart_data[df_chart_data['Total_Dia'] > 0].sort_values('Data', ascending=True)

if not df_chart_data.empty:
    h_data = min(len(df_chart_data) * 35 + 80, 500)
    fig_data = px.bar(df_chart_data, y='Data_Formatada', x=['Faltas', 'Impares', 'Sem_Marcacao'],
                      orientation='h', color_discrete_sequence=[COR_CONTRASTE, '#ffc107', '#17a2b8'],
                      labels={'value': 'Qtd Ocorrências', 'Data_Formatada': 'Data', 'variable': 'Tipo'},
                      template='plotly_white', height=h_data)
    fig_data.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_data, use_container_width=True)
else:
    st.info("Sem dados cronológicos para exibir.")

# --- TABELAS DETALHADAS ---
st.markdown('---')
st.subheader('Detalhamento por Colaborador')

# Preparação das tabelas (Faltas e Ímpares)
faltas_df = df_ocorrencias_filtrado[df_ocorrencias_filtrado['is_falta_nao_justificada'] == 1].copy()
if not faltas_df.empty:
    faltas_df['Data'] = faltas_df['Data'].dt.strftime('%d/%m/%Y')
    faltas_df = faltas_df[['Matricula', 'Nome', 'Data', 'Departamento']].sort_values(['Nome', 'Data'])

impares_df = df_ocorrencias_filtrado[df_ocorrencias_filtrado['is_impar'] | df_ocorrencias_filtrado['is_sem_marcacao']].copy()
if not impares_df.empty:
    impares_df['Data'] = impares_df['Data'].dt.strftime('%d/%m/%Y')
    impares_df = impares_df[['Matricula', 'Nome', 'Data', 'Departamento', 'Marcacoes']].sort_values(['Nome', 'Data'])

detalhe_col1, detalhe_col2 = st.columns(2)
with detalhe_col1:
    st.markdown("**Faltas Detalhadas**")
    if not faltas_df.empty:
        st.dataframe(faltas_df, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("Nenhuma falta encontrada.")

with detalhe_col2:
    st.markdown("**Marcações Ímpares Detalhadas**")
    if not impares_df.empty:
        st.dataframe(impares_df, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("Nenhuma marcação ímpar encontrada.")
