# pages/1_Ocorrências_Detalhadas.py

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io

# --- Configurações Iniciais ---
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Ocorrências")
COR_PRINCIPAL_VERDE = "#70C247"
COR_FALTAS = "#4CAF50" # Verde para Faltas
COR_IMPARES = "#ffc107" # Amarelo para Ímpares
COR_SEM_MARC = "#17a2b8" # Azul para Sem Marcação

# --- URLs GITHUB ---
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'
URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx'
SHEET_OCORRENCIAS = 'OcorrênciasnoPonto'

@st.cache_data(show_spinner="Sincronizando com GitHub...")
def load_data():
    try:
        response = requests.get(URL_OCORRENCIAS, timeout=30)
        df = pd.read_excel(io.BytesIO(response.content), sheet_name=SHEET_OCORRENCIAS)
        
        # 1. Tratamento da Data (Coluna J)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        
        # 2. Identificação de Marcações Ímpares
        def checar_impar(m):
            if pd.isna(m) or str(m).strip() == "": return False
            return len(str(m).strip().split()) % 2 != 0
        
        df['is_impar'] = df['Marcacoes'].apply(checar_impar)
        
        # 3. Identificação de Sem Marcação
        df['is_sem_marcacao'] = df['Ocorrencia'].str.contains('Sem marcação', case=False, na=False)
        
        # 4. Identificação de Faltas
        df['is_falta'] = df['Ocorrencia'].str.contains('Falta', case=False, na=False)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()

df_raw = load_data()

# --- Filtros ---
st.title("Dashboard Profarma - Ocorrências")
st.markdown("---")

col_f1, col_f2 = st.columns(2)
with col_f1:
    estabs = sorted(df_raw['Estabelecimento'].unique())
    sel_estabs = st.multiselect("Filtrar Estabelecimento", estabs)

df_filtered = df_raw.copy()
if sel_estabs:
    df_filtered = df_filtered[df_filtered['Estabelecimento'].isin(sel_estabs)]

with col_f2:
    deps = sorted(df_filtered['Departamento'].unique())
    sel_deps = st.multiselect("Filtrar Departamento", deps)

if sel_deps:
    df_filtered = df_filtered[df_filtered['Departamento'].isin(sel_deps)]

# --- GRÁFICO 1: POR DEPARTAMENTO ---
st.subheader("1. Ocorrências por Departamento")
df_dep = df_filtered.groupby('Departamento').agg(
    Faltas=('is_falta', 'sum'),
    Impares=('is_impar', 'sum'),
    Sem_Marcacao=('is_sem_marcacao', 'sum')
).reset_index()
df_dep['Total'] = df_dep['Faltas'] + df_dep['Impares'] + df_dep['Sem_Marcacao']
df_dep = df_dep[df_dep['Total'] > 0].sort_values('Total', ascending=True)

fig_dep = px.bar(df_dep, y='Departamento', x=['Faltas', 'Impares', 'Sem_Marcacao'],
                 orientation='h', color_discrete_sequence=[COR_FALTAS, COR_IMPARES, COR_SEM_MARC],
                 template='plotly_white', height=400)
st.plotly_chart(fig_dep, use_container_width=True)

# --- GRÁFICO 2: POR DATA (O NOVO) ---
st.markdown("---")
st.subheader("2. Evolução Diária de Ocorrências (O NOVO)")

# Agrupando por Data
df_data = df_filtered.groupby('Data').agg(
    Faltas=('is_falta', 'sum'),
    Impares=('is_impar', 'sum'),
    Sem_Marcacao=('is_sem_marcacao', 'sum')
).reset_index()

# Criar rótulo de data legível
df_data['Data_Formatada'] = df_data['Data'].dt.strftime('%d/%m/%Y')
df_data = df_data.sort_values('Data', ascending=True)

if not df_data.empty and (df_data[['Faltas', 'Impares', 'Sem_Marcacao']].sum().sum() > 0):
    fig_data = px.bar(df_data, 
                      y='Data_Formatada', 
                      x=['Faltas', 'Impares', 'Sem_Marcacao'],
                      orientation='h',
                      title="Volume de Ocorrências por Dia",
                      color_discrete_sequence=[COR_FALTAS, COR_IMPARES, COR_SEM_MARC],
                      labels={'value': 'Quantidade', 'Data_Formatada': 'Dia', 'variable': 'Tipo'},
                      template='plotly_white',
                      height=500)
    
    # Força a ordenação cronológica correta no eixo Y
    fig_data.update_layout(yaxis={'categoryorder':'array', 'categoryarray': df_data['Data_Formatada']})
    st.plotly_chart(fig_data, use_container_width=True)
else:
    st.warning("Aguardando dados ou filtros para gerar o gráfico de datas.")

# --- TABELA DE DETALHES ---
st.markdown("---")
st.subheader("3. Detalhamento Individual")
st.dataframe(df_filtered[['Matricula', 'Nome', 'Data', 'Departamento', 'Ocorrencia', 'Marcacoes']], use_container_width=True)

