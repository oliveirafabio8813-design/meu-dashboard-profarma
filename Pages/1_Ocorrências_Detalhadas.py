import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# --- Configurações Iniciais ---
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Ocorrências")
COR_FALTA = "#E74C3C" 
COR_MARCACAO = "#3498DB"

# URLs do GitHub
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'
URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx'
SHEET_NAME = 'OcorrênciasnoPonto'

@st.cache_data(ttl=60)
def load_data():
    try:
        response = requests.get(URL_OCORRENCIAS, timeout=30)
        response.raise_for_status()
        
        # Carrega o Excel
        df = pd.read_excel(io.BytesIO(response.content), sheet_name=SHEET_NAME)
        
        # Limpa nomes das colunas (remove espaços e garante string)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 1. Tratamento da Data
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        
        # 2. Função de Normalização para comparação segura
        def normalize(val):
            return str(val).strip().lower()

        # 3. Lógica de Faltas (Ocorrencia == 'falta' e Justificativa == 'falta')
        df['is_falta'] = df.apply(
            lambda x: 1 if (normalize(x.get('Ocorrencia', '')) == 'falta' and 
                            normalize(x.get('Justificativa', '')) == 'falta') else 0, axis=1
        )
        
        # 4. Lógica de Marcação Ímpar
        # Verifica se a ocorrência contém "sem marcação" OU se a justificativa é "falta de marcação"
        df['is_impar'] = df.apply(
            lambda x: 1 if ('sem marcação' in normalize(x.get('Ocorrencia', '')) or 
                            normalize(x.get('Justificativa', '')) == 'falta de marcação') else 0, axis=1
        )
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df_raw = load_data()

# --- Título e Interface ---
st.title("📊 Análise Diária: Faltas e Marcações Ímpares")
st.markdown("---")

if not df_raw.empty:
    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sel_estab = st.multiselect("Filtrar Estabelecimento:", sorted(df_raw['Estabelecimento'].dropna().unique()))
    
    df_filtrado = df_raw.copy()
    if sel_estab:
        df_filtrado = df_filtrado[df_filtrado['Estabelecimento'].isin(sel_estab)]

    with col_f2:
        sel_dep = st.multiselect("Filtrar Departamento:", sorted(df_filtrado['Departamento'].dropna().unique()))
    
    if sel_dep:
        df_filtrado = df_filtrado[df_filtrado['Departamento'].isin(sel_dep)]

    # --- Processamento para o Gráfico ---
    # Remove datas nulas e agrupa
    df_diario = df_filtrado.dropna(subset=['Data']).groupby('Data').agg(
        Total_Faltas=('is_falta', 'sum'),
        Marcacoes_Impares=('is_impar', 'sum')
    ).reset_index()

    # Ordenação Cronológica
    df_diario = df_diario.sort_values('Data')
    df_diario['Data_Str'] = df_diario['Data'].dt.strftime('%d/%m/%Y')

    # --- Gráfico de Barras Verticais ---
    st.subheader("Comparativo por Data")
    
    # Verifica se há algo para mostrar
    if not df_diario.empty and (df_diario['Total_Faltas'].sum() + df_diario['Marcacoes_Impares'].sum() > 0):
        fig = px.bar(
            df_diario,
            x='Data_Str',
            y=['Total_Faltas', 'Marcacoes_Impares'],
            barmode='group',
            labels={'value': 'Quantidade', 'Data_Str': 'Data', 'variable': 'Tipo de Ocorrência'},
            color_discrete_map={'Total_Faltas': COR_FALTA, 'Marcacoes_Impares': COR_MARCACAO},
            template='plotly_white',
            text_auto=True
        )
        
        fig.update_layout(
            xaxis_title="Dias",
            yaxis_title="Total de Ocorrências",
            legend_title="Legenda",
            xaxis={'type': 'category'}, # Garante que as datas fiquem em ordem
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Nenhuma ocorrência encontrada para os critérios selecionados nos filtros.")

    # --- Tabela de Conferência (Abaixo do Gráfico) ---
    st.markdown("---")
    with st.expander("Clique para ver os dados detalhados da seleção"):
        st.dataframe(
            df_filtrado[df_filtrado['is_falta'] + df_filtrado['is_impar'] > 0][
                ['Matricula', 'Nome', 'Data', 'Ocorrencia', 'Justificativa']
            ].sort_values('Data'),
            use_container_width=True,
            hide_index=True
        )
else:
    st.error("O arquivo não pôde ser carregado. Verifique se o link no GitHub ainda é válido.")
