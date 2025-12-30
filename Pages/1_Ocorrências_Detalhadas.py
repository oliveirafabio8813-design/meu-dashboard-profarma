# pages/1_Ocorrências_Detalhadas.py

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io

# --- Constantes e Configurações ---
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Ocorrências")
COR_PRINCIPAL_VERDE = "#70C247"
COR_CONTRASTE = "#4CAF50" 

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
    # Divide as marcações por espaços e conta se é ímpar
    return len(str(marcacoes).strip().split()) % 2 != 0

@st.cache_data
def load_data():
    df_ocorrencias = load_data_from_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
    df_banco_horas = load_data_from_github(URL_BANCO_HORAS_RESUMO, SHEET_BANCO_HORAS)
    
    if df_ocorrencias.empty:
        st.error("Falha ao carregar o DataFrame de Ocorrências.")
        st.stop()
        
    try:
        # AJUSTE NA DATA: O arquivo usa formato ISO (YYYY-MM-DD)
        df_ocorrencias['Data'] = pd.to_datetime(df_ocorrencias['Data'], errors='coerce')
        
        # Identificação de ocorrências
        df_ocorrencias['is_impar'] = df_ocorrencias['Marcacoes'].apply(e_marcacoes_impar)
        df_ocorrencias['is_sem_marcacao'] = df_ocorrencias['Ocorrencia'].isin(['Sem marcação de entrada', 'Sem marcação de saída'])
        df_ocorrencias['is_falta_nao_justificada'] = df_ocorrencias.apply(
            lambda row: 1 if row['Ocorrencia'] == 'Falta' and row['Justificativa'] == 'Falta' else 0, axis=1
        )
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        st.stop()

    return df_ocorrencias, df_banco_horas

df_ocorrencias, df_banco_horas = load_data()

# --- TÍTULO ---
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

with col_filter_button:
    st.write("") ; st.write("")
    if st.button('Limpar Filtros', use_container_width=True):
        st.session_state['selected_establishment_ocorrencias'] = []
        st.session_state['selected_department_ocorrencias'] = []
        st.rerun()

with col_filter_est:
    selected_establishments = st.multiselect('Estabelecimento:', 
                                             options=sorted(df_ocorrencias['Estabelecimento'].unique()), 
                                             key='selected_establishment_ocorrencias')

df_filtrado = df_ocorrencias.copy()
if selected_establishments:
    df_filtrado = df_filtrado[df_filtrado['Estabelecimento'].isin(selected_establishments)]

with col_filter_dep:
    selected_departments = st.multiselect('Departamento:', 
                                          options=sorted(df_filtrado['Departamento'].unique()), 
                                          key='selected_department_ocorrencias')

if selected_departments:
    df_filtrado = df_filtrado[df_filtrado['Departamento'].isin(selected_departments)]

# --- KPIs ---
st.markdown('---')
c1, c2 = st.columns(2)
total_faltas = df_filtrado['is_falta_nao_justificada'].sum()
total_impares = df_filtrado['is_impar'].sum() + df_filtrado['is_sem_marcacao'].sum()

c1.metric("Faltas Não Justificadas", int(total_faltas))
c2.metric("Marcações Ímpares/Ausentes", int(total_impares))

# --- GRÁFICO 1: POR DEPARTAMENTO ---
st.markdown('---')
st.subheader('Ocorrências por Departamento')
df_chart_dep = df_filtrado.groupby('Departamento').agg(
    Faltas=('is_falta_nao_justificada', 'sum'),
    Impares=('is_impar', 'sum'),
    Sem_Marcacao=('is_sem_marcacao', 'sum')
).reset_index()
df_chart_dep['Total'] = df_chart_dep['Faltas'] + df_chart_dep['Impares'] + df_chart_dep['Sem_Marcacao']
df_chart_dep = df_chart_dep[df_chart_dep['Total'] > 0].sort_values('Total', ascending=True)

if not df_chart_dep.empty:
    fig_dep = px.bar(df_chart_dep, y='Departamento', x=['Faltas', 'Impares', 'Sem_Marcacao'],
                     orientation='h', color_discrete_sequence=[COR_CONTRASTE, '#ffc107', '#17a2b8'],
                     template='plotly_white', height=min(len(df_chart_dep)*35+100, 600))
    st.plotly_chart(fig_dep, use_container_width=True)

# --- GRÁFICO 3: POR DATA (O QUE VOCÊ PEDIU) ---
st.markdown('---')
st.subheader('Ocorrências por Data')

# Garantir que não existam datas nulas antes de agrupar
df_data = df_filtrado.dropna(subset=['Data']).copy()

df_chart_data = df_data.groupby('Data').agg(
    Faltas=('is_falta_nao_justificada', 'sum'),
    Impares=('is_impar', 'sum'),
    Sem_Marcacao=('is_sem_marcacao', 'sum')
).reset_index()

# Ordenar por data cronológica
df_chart_data = df_chart_data.sort_values('Data')

# Criar coluna formatada para o eixo do gráfico
df_chart_data['Data Exibição'] = df_chart_data['Data'].dt.strftime('%d/%m/%Y')

if not df_chart_data.empty:
    fig_data = px.bar(df_chart_data, 
                      y='Data Exibição', 
                      x=['Faltas', 'Impares', 'Sem_Marcacao'],
                      orientation='h',
                      color_discrete_sequence=[COR_CONTRASTE, '#ffc107', '#17a2b8'],
                      labels={'value': 'Qtd Ocorrências', 'variable': 'Tipo'},
                      template='plotly_white', 
                      height=min(len(df_chart_data)*35+100, 500))
    
    # Isso garante que o gráfico siga a ordem das datas e não a ordem alfabética
    fig_data.update_layout(yaxis={'categoryorder':'trace'})
    st.plotly_chart(fig_data, use_container_width=True)
else:
    st.info("Nenhuma ocorrência encontrada nas datas deste arquivo.")

# --- TABELAS ---
st.markdown('---')
det_c1, det_c2 = st.columns(2)
with det_c1:
    st.markdown("**Faltas Detalhadas**")
    f_tab = df_filtrado[df_filtrado['is_falta_nao_justificada'] == 1][['Matricula', 'Nome', 'Data', 'Departamento']].copy()
    if not f_tab.empty:
        f_tab['Data'] = f_tab['Data'].dt.strftime('%d/%m/%Y')
        st.dataframe(f_tab, use_container_width=True, hide_index=True)
with det_c2:
    st.markdown("**Marcações Ímpares Detalhadas**")
    i_tab = df_filtrado[df_filtrado['is_impar'] | df_filtrado['is_sem_marcacao']][['Matricula', 'Nome', 'Data', 'Departamento', 'Marcacoes']].copy()
    if not i_tab.empty:
        i_tab['Data'] = i_tab['Data'].dt.strftime('%d/%m/%Y')
        st.dataframe(i_tab, use_container_width=True, hide_index=True)
