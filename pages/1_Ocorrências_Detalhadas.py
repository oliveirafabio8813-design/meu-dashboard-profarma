# pages/1_Ocorrências_Detalhadas.py (FINAL: Adição de Multiselect nos filtros e ajuste de altura)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- Constantes e Configurações ---
st.set_page_config(
    layout="wide", page_title="Dashboard Profarma - Ocorrências")
COR_PRINCIPAL_VERDE = "#70C247"
COR_CONTRASTE = "#4CAF50"

# --- Funções de Processamento de Dados ---


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
    try:
        df_ocorrencias = pd.read_excel('Relatorio_OcorrenciasNoPonto.xlsx')
        df_ocorrencias['Data'] = pd.to_datetime(
            df_ocorrencias['Data'], errors='coerce', dayfirst=True)
        df_ocorrencias['is_impar'] = df_ocorrencias['Marcacoes'].apply(
            e_marcacoes_impar)
        df_ocorrencias['is_sem_marcacao'] = df_ocorrencias['Ocorrencia'].isin(
            ['Sem marcação de entrada', 'Sem marcação de saída'])
    except Exception as e:
        st.error(f"Erro ao carregar ou processar dados de Ocorrências: {e}")
        st.stop()
    try:
        df_banco_horas = pd.read_excel(
            'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx')
        df_banco_horas['SaldoFinal_Horas'] = df_banco_horas['SaldoFinal'].apply(
            convert_to_hours)
    except Exception as e:
        st.error(f"Erro ao carregar ou processar dados de Banco de Horas: {e}")
        st.stop()

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
    [1, 1, 0.5])  # Adiciona coluna para o botão

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
    st.write("")  # Espaçador para alinhar o botão
    st.write("")  # Espaçador adicional
    st.button('Limpar Filtros', on_click=reset_filters,
              use_container_width=True)


# 1. Filtro de Estabelecimento (Multiselect)
with col_filter_est:
    todos_estabelecimentos = sorted(
        list(df_ocorrencias['Estabelecimento'].unique()))

    selected_establishments = st.multiselect(  # MUDANÇA PARA MULTISELECT
        'Estabelecimento:',
        options=todos_estabelecimentos,
        # Usa o estado atual
        default=st.session_state['selected_establishment_ocorrencias'],
        # Adiciona chave para controle de estado
        key='selected_establishment_ocorrencias'
    )

# 2. Filtragem Inicial por Estabelecimento
if selected_establishments:  # Se a lista não estiver vazia
    df_ocorrencias_filtrado = df_ocorrencias[df_ocorrencias['Estabelecimento'].isin(
        selected_establishments)].copy()
else:  # Se a lista estiver vazia, usa o DataFrame completo
    df_ocorrencias_filtrado = df_ocorrencias.copy()

# 3. Filtro de Departamento (Multiselect, depende do Estabelecimento)
with col_filter_dep:
    # Opções de departamento são baseadas no df filtrado pelo estabelecimento
    todos_departamentos = sorted(
        list(df_ocorrencias_filtrado['Departamento'].unique()))

    # --- LÓGICA DE LIMPEZA DE DEPARTAMENTO ---
    # Verifica se algum departamento selecionado não existe mais no escopo atual
    current_selection_dep = st.session_state['selected_department_ocorrencias']

    # Filtra a seleção atual para manter apenas os que estão disponíveis (em todos_departamentos)
    new_selection_dep = [
        dep for dep in current_selection_dep if dep in todos_departamentos]

    # Se houve mudança na seleção, atualiza o st.session_state
    if set(current_selection_dep) != set(new_selection_dep):
        st.session_state['selected_department_ocorrencias'] = new_selection_dep
    # --- FIM DA LÓGICA DE LIMPEZA ---

    selected_departments = st.multiselect(  # MUDANÇA PARA MULTISELECT
        'Departamento:',
        options=todos_departamentos,
        # Usa o estado atualizado (limpo) como default
        default=st.session_state['selected_department_ocorrencias'],
        key='selected_department_ocorrencias'  # Adiciona chave para controle de estado
    )

# 4. Filtragem Final por Departamento
if selected_departments:  # Se a lista não estiver vazia
    df_ocorrencias_filtrado = df_ocorrencias_filtrado[df_ocorrencias_filtrado['Departamento'].isin(
        selected_departments)].copy()

# --- LÓGICA DE TAMANHO DE GRÁFICO CONDICIONAL ---
# Filtros ativos se selected_establishments OU selected_departments não estiverem vazios
filtros_ativos = bool(selected_establishments or selected_departments)

# Define a altura base.
BASE_HEIGHT = 400
if filtros_ativos:
    # Se houver filtros, o gráfico detalha apenas um escopo menor.
    CHART_HEIGHT = 250
else:
    # Se não houver filtros, o gráfico mostra todos os estabelecimentos.
    CHART_HEIGHT = BASE_HEIGHT
# Fim da Lógica de Tamanho de Gráfico

# --- GRÁFICOS DE OCARRÊNCIAS (Dados agora filtrados por ESTAB e DEP) ---
st.markdown('---')
st.subheader('Análise Gráfica por Estabelecimento')

# Processamento de dados para gráficos (Continua a agrupar por Estabelecimento, mas com dados mais filtrados)
resultados = pd.DataFrame(
    columns=['Estabelecimento', 'ContagemFaltas', 'ContagemMarcacoesImpares'])

# Agrupa pelos estabelecimentos que estão no DF filtrado (serão os selecionados ou todos)
grupos = df_ocorrencias_filtrado.groupby('Estabelecimento')

for estabelecimento, grupo in grupos:
    filtro_falta = (grupo['Ocorrencia'] == 'Falta') & (
        grupo['Justificativa'] == 'Falta')
    contagem_falta = filtro_falta.sum()

    contagem_impares_base = grupo['is_impar'].sum()
    contagem_sem_marcacao = grupo['is_sem_marcacao'].sum()
    contagem_marcacoes_impares = contagem_impares_base + contagem_sem_marcacao

    resultados.loc[len(resultados)] = [estabelecimento,
                                       contagem_falta, contagem_marcacoes_impares]

resultados_faltas = resultados.sort_values(
    by='ContagemFaltas', ascending=False)
resultados_impares = resultados.sort_values(
    by='ContagemMarcacoesImpares', ascending=False)

col1, col2 = st.columns(2)
with col1:
    # Título simplificado, pois o filtro já indica o escopo
    st.subheader('Gráfico de Faltas')
    if not resultados_faltas.empty:
        fig_faltas = px.bar(
            resultados_faltas,
            y='Estabelecimento',
            x='ContagemFaltas',
            orientation='h',
            title='Total de Faltas no Escopo Selecionado',
            labels={'ContagemFaltas': 'Total de Ocorrências (Faltas)'},
            color_discrete_sequence=[COR_CONTRASTE],
            category_orders={
                'Estabelecimento': resultados_faltas['Estabelecimento'].tolist()},
            height=CHART_HEIGHT  # APLICAÇÃO DA ALTURA CONDICIONAL
        )
        fig_faltas.update_traces(texttemplate='%{x}', textposition='outside')
        st.plotly_chart(fig_faltas, use_container_width=True)
    else:
        st.info("Nenhuma ocorrência de Falta para os filtros selecionados.")


with col2:
    st.subheader('Gráfico de Marcações Ímpares')
    if not resultados_impares.empty:
        fig_impares = px.bar(
            resultados_impares,
            y='Estabelecimento',
            x='ContagemMarcacoesImpares',
            orientation='h',
            title='Total de Marcações Ímpares no Escopo Selecionado',
            labels={
                'ContagemMarcacoesImpares': 'Total de Ocorrências (Marcações Ímpar)'},
            color_discrete_sequence=[COR_PRINCIPAL_VERDE],
            category_orders={
                'Estabelecimento': resultados_impares['Estabelecimento'].tolist()},
            height=CHART_HEIGHT  # APLICAÇÃO DA ALTURA CONDICIONAL
        )
        fig_impares.update_traces(texttemplate='%{x}', textposition='outside')
        st.plotly_chart(fig_impares, use_container_width=True)
    else:
        st.info("Nenhuma ocorrência de Marcação Ímpar para os filtros selecionados.")


# --- DETALHAMENTO DE OCORRÊNCIAS (Com Altura Dinâmica e colunas ajustadas) ---

# O detalhamento só faz sentido se a filtragem resultou em um escopo menor (ou seja, filtros ativos)
if filtros_ativos:
    st.markdown('---')

    # Monta o título dinamicamente
    estabs_title = ", ".join(
        selected_establishments) if selected_establishments else "Todos"
    deps_title = ", ".join(
        selected_departments) if selected_departments else "Todos"
    st.subheader(
        f"Detalhes de Ocorrências para: **{estabs_title}** / **{deps_title}**")

    # Processamento para Faltas
    faltas_df = df_ocorrencias_filtrado[
        (df_ocorrencias_filtrado['Ocorrencia'] == 'Falta') &
        (df_ocorrencias_filtrado['Justificativa'] == 'Falta')
    ].copy()

    # Colunas: Nome do Funcionário e Data da Falta
    faltas_df = faltas_df[['Nome', 'Data']]
    faltas_df.columns = ['Nome do Funcionário', 'Data da Falta']

    faltas_df = faltas_df.sort_values(
        by=['Nome do Funcionário', 'Data da Falta']).reset_index(drop=True)
    faltas_df['Data da Falta'] = faltas_df['Data da Falta'].dt.strftime(
        '%d/%m/%Y')

    # Processamento para Marcações Ímpares
    impares_df = df_ocorrencias_filtrado[
        df_ocorrencias_filtrado['is_impar'] | df_ocorrencias_filtrado['is_sem_marcacao']
    ].copy()

    # Colunas: Nome do Funcionário e Data da Marcação Ímpar
    impares_df = impares_df[['Nome', 'Data']]
    impares_df.columns = ['Nome do Funcionário', 'Data da Marcação Ímpar']

    impares_df = impares_df.sort_values(
        by=['Nome do Funcionário', 'Data da Marcação Ímpar']).reset_index(drop=True)
    impares_df['Data da Marcação Ímpar'] = impares_df['Data da Marcação Ímpar'].dt.strftime(
        '%d/%m/%Y')

    detalhe_col1, detalhe_col2 = st.columns(2)

    # --- Coluna 1: Faltas ---
    with detalhe_col1:
        st.subheader("Faltas Detalhadas")
        if not faltas_df.empty:
            # CÁLCULO DA ALTURA DINÂMICA PARA FALTAS
            num_rows = len(faltas_df)
            dynamic_height = min(num_rows * 35 + 40, 500)

            st.dataframe(
                faltas_df,
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
            st.info("Nenhuma marcação ímpar encontrada para este filtro.")
