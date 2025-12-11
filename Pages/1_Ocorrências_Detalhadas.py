# pages/1_Ocorrências_Detalhadas.py (AJUSTADO PARA GITHUB e XLSX)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests             # Necessário para buscar URLs do GitHub
import io                   # NOVO: Necessário para lidar com dados binários do Excel (BytesIO)

# --- Constantes e Configurações ---
st.set_page_config(
    layout="wide", page_title="Dashboard Profarma - Ocorrências")
COR_PRINCIPAL_VERDE = "#70C247"
COR_CONTRASTE = "#4CAF50" # Cor usada para contrastes (Marcações Ímpares)
COR_ALERTA_VERMELHO = "#dc3545" # Adicionado para o ranking de faltas

# --- URLs BRUTAS DO GITHUB (AJUSTE CRÍTICO PARA XLSX) ---
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'

# Arquivos XLSX e suas abas
URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx'
SHEET_OCORRENCIAS = 'OcorrênciasnoPonto' # Nome da aba no Excel

URL_BANCO_HORAS_RESUMO = REPO_URL_BASE + 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx' # Mantido para carregar Estabelecimento/Departamento
SHEET_BANCO_HORAS = 'ContaCorrenteBancodeHorasResum'

# --- Funções de Processamento de Dados ---

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
    # CHAMA A FUNÇÃO CORRIGIDA PARA XLSX
    df_ocorrencias = load_data_from_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
    df_banco_horas = load_data_from_github(URL_BANCO_HORAS_RESUMO, SHEET_BANCO_HORAS)
    
    if df_ocorrencias.empty:
        st.error("Falha ao carregar o DataFrame de Ocorrências do GitHub.")
        st.stop()
        
    try:
        # Processamento de Ocorrências (Mantido do original)
        df_ocorrencias['Data'] = pd.to_datetime(
            df_ocorrencias['Data'], errors='coerce', dayfirst=True)
        df_ocorrencias['is_impar'] = df_ocorrencias['Marcacoes'].apply(
            e_marcacoes_impar)
        df_ocorrencias['is_sem_marcacao'] = df_ocorrencias['Ocorrencia'].isin(
            ['Sem marcação de entrada', 'Sem marcação de saída'])
    except Exception as e:
        st.error(f"Erro ao processar dados de Ocorrências: {e}")
        st.stop()

    if not df_banco_horas.empty:
        # Processamento de Banco de Horas (Mantido o necessário para filtros)
        df_banco_horas['SaldoFinal_Horas'] = df_banco_horas['SaldoFinal'].apply(
            convert_to_hours)
    
    return df_ocorrencias, df_banco_horas


df_ocorrencias, df_banco_horas = load_data()


# --- TÍTULO DA PÁGINA COM LOGO ---
col_logo, col_title, _ = st.columns([1, 4, 1])

with col_logo:
    try:
        # Usando o nome de arquivo referenciado
        st.image("image_ccccb7.png", width=120)
    except FileNotFoundError:
        st.warning("Logotipo não encontrado.")

with col_title:
    # Título H1 ajustado para "Dashboard Profarma - Ocorrências"
    st.markdown(
        f'<h1 style="color: {COR_PRINCIPAL_VERDE}; margin-bottom: 0px;">Dashboard Profarma - Ocorrências</h1>', unsafe_allow_html=True)
    st.markdown('Relatório e Detalhamento de Ocorrências no Ponto')
st.markdown('---')


# --- FILTROS DE ESTABELECIMENTO E DEPARTAMENTO ---

st.subheader('Filtros')
col_filter_est, col_filter_dep, col_filter_button = st.columns(
    [1, 1, 0.5])  # Adiciona coluna para o botão

# Inicializa o estado dos filtros para poder resetar (usando listas)
if 'selected_establishment_ocorrencias' not in st.session_state:
    st.session_state['selected_establishment_ocorrencias'] = []
if 'selected_department_ocorrencias' not in st.session_state:
    st.session_state['selected_department_ocorrencias'] = []


def reset_filters():
    # Limpa as listas de seleção
    st.session_state['selected_establishment_ocorrencias'] = []
    st.session_state['selected_department_ocorrencias'] = []


# Botão de Limpar Filtros
with col_filter_button:
    st.write("")  # Espaçador para alinhar o botão
    st.write("")  # Espaçador adicional
    st.button('Limpar Filtros', on_click=reset_filters,
              use_container_width=True)


# 1. Filtro de Estabelecimento (Multiselect)
with col_filter_est:
    todos_estabelecimentos = sorted(
        list(df_ocorrencias['Estabelecimento'].unique()))
    selected_establishments = st.multiselect(
        # MUDANÇA PARA MULTISELECT
        'Estabelecimento:',
        options=todos_estabelecimentos,
        # Usa o estado atual
        default=st.session_state['selected_establishment_ocorrencias'],
        # Adiciona chave para controle de estado
        key='selected_establishment_ocorrencias'
    )

# 2. Filtragem Inicial por Estabelecimento
if selected_establishments:
    # Se a lista não estiver vazia
    df_ocorrencias_filtrado = df_ocorrencias[df_ocorrencias['Estabelecimento'].isin(
        selected_establishments)].copy()
else:
    # Se a lista estiver vazia, usa o DataFrame completo
    df_ocorrencias_filtrado = df_ocorrencias.copy()

# 3. Filtro de Departamento (Multiselect, depende do Estabelecimento)
with col_filter_dep:
    # Opções de departamento são baseadas no df filtrado pelo estabelecimento
    todos_departamentos = sorted(
        list(df_ocorrencias_filtrado['Departamento'].unique()))

    # --- LÓGICA DE LIMPEZA DE DEPARTAMENTO ---
    # Verifica se algum departamento selecionado não existe mais no escopo atual
    current_selection_dep = st.session_state['selected_department_ocorrencias']
    new_selection_dep = [
        dep for dep in current_selection_dep if dep in todos_departamentos]
    if set(current_selection_dep) != set(new_selection_dep):
        st.session_state['selected_department_ocorrencias'] = new_selection_dep

    selected_departments = st.multiselect(
        'Departamento:',
        options=todos_departamentos,
        default=st.session_state['selected_department_ocorrencias'],
        key='selected_department_ocorrencias'
    )

# 4. Filtragem Final por Departamento
if selected_departments:
    df_ocorrencias_filtrado = df_ocorrencias_filtrado[df_ocorrencias_filtrado['Departamento'].isin(
        selected_departments)].copy()


# --- ANÁLISE GERAL DOS DADOS FILTRADOS ---
st.markdown('---')
st.subheader('Resumo das Ocorrências (Filtros Aplicados)')

# Cálculos de KPIs
df_ocorrencias_filtrado['is_falta_nao_justificada'] = df_ocorrencias_filtrado.apply(
    lambda row: 1 if row['Ocorrencia'] == 'Falta' and row['Justificativa'] == 'Falta' else 0,
    axis=1
)
total_faltas_filtrado = df_ocorrencias_filtrado['is_falta_nao_justificada'].sum()
total_impares_filtrado = df_ocorrencias_filtrado['is_impar'].sum()
total_sem_marcacao_filtrado = df_ocorrencias_filtrado['is_sem_marcacao'].sum()
total_marcacoes_impares_filtrado = int(
    total_impares_filtrado + total_sem_marcacao_filtrado)


col_kpi_1, col_kpi_2, col_kpi_3, _ = st.columns(4)

with col_kpi_1:
    st.metric(
        label="Total de Faltas Não Justificadas",
        value=f"{int(total_faltas_filtrado)}",
        delta_color="off"
    )

with col_kpi_2:
    st.metric(
        label="Total de Marcações Ímpares/Ausentes",
        value=f"{total_marcacoes_impares_filtrado}",
        delta_color="off"
    )


# --- GRÁFICO DE BARRAS DE OCORRÊNCIAS POR DEPARTAMENTO ---
st.markdown('---')
st.subheader('Ocorrências por Departamento (Detalhe)')


# 1. Agrupamento por Departamento (Faltas e Ímpares)
df_chart = df_ocorrencias_filtrado.groupby('Departamento').agg(
    Total_Faltas=('is_falta_nao_justificada', 'sum'),
    Total_Impares=('is_impar', 'sum'),
    Total_Sem_Marcacao=('is_sem_marcacao', 'sum')
).reset_index()

df_chart['Total_Ocorrencias'] = df_chart['Total_Faltas'] + \
    df_chart['Total_Impares'] + df_chart['Total_Sem_Marcacao']

# 2. Remover departamentos sem ocorrências no filtro
df_chart = df_chart[df_chart['Total_Ocorrencias'] > 0].sort_values(
    'Total_Ocorrencias', ascending=True
)

if not df_chart.empty:
    # CÁLCULO DA ALTURA DINÂMICA
    num_departamentos = len(df_chart)
    # 40px por barra + 80px de margem, limitado a 700px
    chart_height = min(num_departamentos * 40 + 80, 700)

    fig_departamento = px.bar(
        df_chart,
        y='Departamento',
        x=['Total_Faltas', 'Total_Impares', 'Total_Sem_Marcacao'],
        orientation='h',
        color_discrete_sequence=[
            COR_CONTRASTE, '#ffc107', '#17a2b8'],
        labels={'value': 'Total de Ocorrências',
                'Departamento': 'Departamento',
                'variable': 'Tipo de Ocorrência'},
        template='plotly_white',
        height=chart_height
    )

    # Adiciona a soma total como texto no final de cada barra
    fig_departamento.update_traces(
        # text=df_chart['Total_Ocorrencias'], # Apenas se usar a soma total
        textposition='outside',
        cliponaxis=False
    )
    # Configurações de layout
    fig_departamento.update_layout(
        xaxis_title="Total de Ocorrências",
        legend_title_text='Tipo',
        uniformtext_minsize=8,
        uniformtext_mode='hide',
    )
    st.plotly_chart(fig_departamento, use_container_width=True)
else:
    st.info("Nenhuma ocorrência encontrada para os filtros aplicados.")


# --- DETALHE DE OCORRÊNCIAS (TABELA) ---
st.markdown('---')
st.subheader('Detalhamento por Colaborador')


# 1. Tabela de Faltas
faltas_df = df_ocorrencias_filtrado[
    df_ocorrencias_filtrado['is_falta_nao_justificada'] == 1
].copy()

# A coluna 'Cargo' não estava sendo incluída aqui, mas é essencial para o ranking, 
# então será incluída no DataFrame de ranking mais abaixo.

faltas_df_detalhe = faltas_df[[
    'Matricula', 'Nome', 'Data', 'Departamento', 'Ocorrencia'
]]
faltas_df_detalhe.columns = ['Matrícula', 'Nome do Funcionário',
                     'Data da Falta', 'Departamento', 'Tipo']
faltas_df_detalhe['Data da Falta'] = faltas_df_detalhe['Data da Falta'].dt.strftime(
    '%d/%m/%Y')
# Ordenação
faltas_df_detalhe = faltas_df_detalhe.sort_values(
    by=['Nome do Funcionário', 'Data da Falta']).reset_index(drop=True)


# 2. Tabela de Marcações Ímpares/Ausentes
impares_df = df_ocorrencias_filtrado[
    df_ocorrencias_filtrado['is_impar'] | df_ocorrencias_filtrado['is_sem_marcacao']
].copy()

impares_df = impares_df[[
    'Matricula', 'Nome', 'Data', 'Departamento', 'Marcacoes'
]]
impares_df.columns = ['Matrícula', 'Nome do Funcionário',
                      'Data da Marcação Ímpar', 'Departamento', 'Marcações Registradas']

impares_df = impares_df.sort_values(
    by=['Nome do Funcionário', 'Data da Marcação Ímpar']).reset_index(drop=True)
impares_df['Data da Marcação Ímpar'] = impares_df['Data da Marcação Ímpar'].dt.strftime(
    '%d/%m/%Y')

detalhe_col1, detalhe_col2 = st.columns(2)

# --- Coluna 1: Faltas ---
with detalhe_col1:
    st.subheader("Faltas Detalhadas")
    if not faltas_df_detalhe.empty:
        # CÁLCULO DA ALTURA DINÂMICA PARA FALTAS
        num_rows = len(faltas_df_detalhe)
        dynamic_height = min(num_rows * 35 + 40, 500)

        st.dataframe(
            faltas_df_detalhe,
            use_container_width=True,
            hide_index=True,
            height=dynamic_height
        )
    else:
        st.info("Nenhuma falta encontrada para este filtro.")

# --- Coluna 2: Marcações Ímpares ---
with detalhe_col2:
    st.subheader("Marcações Ímpares Detalhadas")
    if not impares_df.empty:
        # CÁLCULO DA ALTURA DINÂMICA PARA MARCAÇÕES ÍMPARES
        num_rows = len(impares_df)
        dynamic_height = min(num_rows * 35 + 40, 500)

        st.dataframe(
            impares_df,
            use_container_width=True,
            hide_index=True,
            height=dynamic_height
        )
    else:
        st.info("Nenhuma marcação ímpar/ausente encontrada para este filtro.")


# ----------------------------------------------------------------------
# 🌟 NOVA SEÇÃO: RANKING DE FALTAS POR COLABORADOR
# ----------------------------------------------------------------------

st.markdown('---')
st.header('🏆 Ranking de Faltas por Colaborador (Não Justificadas)')
st.markdown('Tabela com os colaboradores que acumulam o maior número de faltas não justificadas no período filtrado.')

# --- 1. Agrupar Faltas por Colaborador ---
if not faltas_df.empty:
    # Agrupamento para obter a soma de faltas por colaborador
    # O DataFrame 'faltas_df' foi criado a partir do 'df_ocorrencias_filtrado'
    df_ranking_faltas = faltas_df.groupby(
        ['Estabelecimento', 'Nome', 'Cargo']
    ).agg(
        Soma_de_Faltas=('is_falta_nao_justificada', 'sum')
    ).reset_index()

    # Ordenar pelo número de faltas (do maior para o menor)
    df_ranking_faltas = df_ranking_faltas.sort_values(
        'Soma_de_Faltas', ascending=False
    ).rename(columns={
        'Estabelecimento': 'Unidade',
        'Nome': 'Colaborador',
        'Soma_de_Faltas': 'Total Faltas'
    })

    # Criar coluna de ranking (opcional, mas útil)
    df_ranking_faltas['Rank'] = np.arange(1, len(df_ranking_faltas) + 1)
    
    # Reordenar colunas para exibição
    df_ranking_faltas = df_ranking_faltas[['Rank', 'Unidade', 'Colaborador', 'Cargo', 'Total Faltas']]

    # CÁLCULO DA ALTURA DINÂMICA PARA O RANKING
    num_rows_ranking = len(df_ranking_faltas)
    dynamic_height_ranking = min(num_rows_ranking * 35 + 40, 600)


    st.dataframe(
        df_ranking_faltas,
        use_container_width=True,
        hide_index=True,
        height=dynamic_height_ranking,
        column_config={
            "Total Faltas": st.column_config.NumberColumn(
                "Total Faltas",
                format="%d",
                help="Soma total das faltas não justificadas (ocorrência 'Falta' com justificativa 'Falta')."
            )
        }
    )

    # Adicionando um pequeno gráfico de barras para o Top 10 (Melhor visualização)
    st.markdown('#### Top 10 Visualização')
    df_ranking_top_10 = df_ranking_faltas.head(10).copy()

    if not df_ranking_top_10.empty:
        df_ranking_top_10 = df_ranking_top_10.sort_values('Total Faltas', ascending=True)

        fig_ranking = px.bar(
            df_ranking_top_10,
            y='Colaborador',
            x='Total Faltas',
            orientation='h',
            text='Total Faltas',
            color='Total Faltas', 
            color_continuous_scale=[COR_ALERTA_VERMELHO],
            labels={'Total Faltas': 'Total de Faltas', 'Colaborador': 'Colaborador'},
            template='plotly_white'
        )
        
        fig_ranking.update_traces(
            texttemplate='%{text}',
            textposition='outside',
        )
        
        fig_ranking.update_layout(
            xaxis_title=None,
            height=400,
            coloraxis_showscale=False # Oculta a barra de cores
        )
        
        st.plotly_chart(fig_ranking, use_container_width=True)
    
else:
    st.info("Nenhuma falta não justificada encontrada para criar o ranking com os filtros atuais.")
