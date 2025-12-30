import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# --- Configurações de Layout ---
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Análise Diária")
COR_FALTA = "#E74C3C"  # Vermelho para Faltas
COR_MARCACAO = "#3498DB" # Azul para Marcações Ímpares

# --- URLs GITHUB ---
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'
URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx'
SHEET_NAME = 'OcorrênciasnoPonto'

@st.cache_data(ttl=60) # Cache de 1 minuto para forçar atualização
def load_data():
    try:
        response = requests.get(URL_OCORRENCIAS, timeout=30)
        df = pd.read_excel(io.BytesIO(response.content), sheet_name=SHEET_NAME)
        
        # 1. Tratamento Rigoroso da Data
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        
        # 2. Lógica Solicitada: Faltas
        # Ocorrencia == 'Falta' E Justificativa == 'Falta'
        df['is_falta'] = df.apply(
            lambda x: 1 if (str(x['Ocorrencia']).strip() == 'Falta' and 
                            str(x['Justificativa']).strip() == 'Falta') else 0, axis=1
        )
        
        # 3. Lógica Solicitada: Marcação Ímpar
        # Ocorrencia contém 'Sem marcação' OU Justificativa == 'Falta de Marcação'
        termos_sem_marcacao = ['Sem marcação de entrada', 'Sem marcação de saída']
        df['is_impar'] = df.apply(
            lambda x: 1 if (str(x['Ocorrencia']).strip() in termos_sem_marcacao or 
                            str(x['Justificativa']).strip() == 'Falta de Marcação') else 0, axis=1
        )
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df_raw = load_data()

# --- Título e Filtros ---
st.title("📊 Análise Diária de Ocorrências")
st.markdown("---")

# Filtros Laterais ou em Colunas
col_f1, col_f2 = st.columns(2)
with col_f1:
    lista_estab = sorted(df_raw['Estabelecimento'].unique().tolist())
    sel_estab = st.multiselect("Selecione o Estabelecimento:", lista_estab)

df_filtrado = df_raw.copy()
if sel_estab:
    df_filtrado = df_filtrado[df_filtrado['Estabelecimento'].isin(sel_estab)]

with col_f2:
    lista_dep = sorted(df_filtrado['Departamento'].unique().tolist())
    sel_dep = st.multiselect("Selecione o Departamento:", lista_dep)

if sel_dep:
    df_filtrado = df_filtrado[df_filtrado['Departamento'].isin(sel_dep)]

# --- Processamento para o Gráfico ---
# Agrupar por data e somar os contadores
df_diario = df_filtrado.groupby('Data').agg(
    Total_Faltas=('is_falta', 'sum'),
    Marcacoes_Impares=('is_impar', 'sum')
).reset_index()

# Ordenar por data e formatar para o eixo X
df_diario = df_diario.sort_values('Data')
df_diario['Data_Texto'] = df_diario['Data'].dt.strftime('%d/%m/%Y')

# --- GRÁFICO DE BARRAS VERTICAIS ---
st.subheader("Comparativo Diário: Faltas vs Marcações Ímpares")

if not df_diario.empty and (df_diario['Total_Faltas'].sum() + df_diario['Marcacoes_Impares'].sum() > 0):
    fig = px.bar(
        df_diario,
        x='Data_Texto',
        y=['Total_Faltas', 'Marcacoes_Impares'],
        barmode='group', # Barras lado a lado para comparação
        labels={'value': 'Total de Ocorrências', 'Data_Texto': 'Data da Ocorrência', 'variable': 'Legenda'},
        color_discrete_map={'Total_Faltas': COR_FALTA, 'Marcacoes_Impares': COR_MARCACAO},
        template='plotly_white',
        text_auto=True # Mostra o número em cima da barra
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        legend_title="Tipo de Ocorrência",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado encontrado para os critérios de Falta ou Marcação Ímpar nos filtros selecionados.")

# --- Detalhamento Final ---
st.markdown("---")
with st.expander("Ver dados brutos da seleção"):
    st.write(df_filtrado[df_filtrado['is_falta'] + df_filtrado['is_impar'] > 0][
        ['Matricula', 'Nome', 'Data', 'Ocorrencia', 'Justificativa', 'Marcacoes']
    ])


