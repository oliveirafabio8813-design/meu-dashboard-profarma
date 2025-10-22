# pages/2_Banco_de_Horas_Detalhadas.py (Com a correção de sinal e NOVO GRÁFICO DE PAGAMENTOS/DESCONTOS)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- Constantes e Configurações ---
st.set_page_config(
    layout="wide", page_title="Dashboard Profarma - Banco de Horas")
COR_PRINCIPAL_VERDE = "#70C247"  # Cor para Crédito/Pagamentos
COR_CONTRASTE = "#dc3545"  # Cor para Débito/Descontos

# --- Funções e Carregamento de Dados ---


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
    try:
        df_ocorrencias = pd.read_excel('Relatorio_OcorrenciasNoPonto.xlsx')
        # Tenta carregar os dados
        df_ocorrencias['Data'] = pd.to_datetime(
            df_ocorrencias['Data'], errors='coerce', dayfirst=True)
    except Exception as e:
        # st.error(f"Erro ao carregar ou processar dados de Ocorrências: {e}")
        st.stop()

    try:
        df_banco_horas = pd.read_excel(
            'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx')

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
        # st.error(f"Erro ao carregar ou processar dados de Banco de Horas: {e}")
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

ranking_positivo = df_positivo.groupby('Estabelecimento')[
    'SaldoFinal_Horas'].sum().sort_values(ascending=False).reset_index()
ranking_negativo = df_negativo.groupby('Estabelecimento')[
    'SaldoFinal_Horas'].sum().sort_values(ascending=True).reset_index()

col_ranking_pos, col_ranking_neg = st.columns(2)

with col_ranking_pos:
    st.markdown('##### Ranking de Horas Positivas')
    if not ranking_positivo.empty:
        fig_pos = px.bar(
            ranking_positivo,
            x='SaldoFinal_Horas',
            y='Estabelecimento',
            orientation='h',
            title='Total de Horas Positivas no Escopo Selecionado',
            labels={'SaldoFinal_Horas': 'Total de Horas (Positivas)'},
            color_discrete_sequence=[COR_PRINCIPAL_VERDE],
            category_orders={
                'Estabelecimento': ranking_positivo['Estabelecimento'].tolist()},
            height=CHART_HEIGHT
        )
        fig_pos.update_traces(texttemplate='%{x:.2f}h', textposition='outside')
        st.plotly_chart(fig_pos, use_container_width=True)
    else:
        st.info("Nenhum saldo positivo para o filtro selecionado.")

with col_ranking_neg:
    st.markdown('##### Ranking de Horas Negativas')
    if not ranking_negativo.empty:
        fig_neg = px.bar(
            ranking_negativo,
            x='SaldoFinal_Horas',
            y='Estabelecimento',
            orientation='h',
            title='Total de Horas Negativas no Escopo Selecionado',
            labels={'SaldoFinal_Horas': 'Total de Horas (Negativas)'},
            color_discrete_sequence=[COR_CONTRASTE],
            category_orders={
                'Estabelecimento': ranking_negativo['Estabelecimento'].tolist()},
            height=CHART_HEIGHT
        )
        fig_neg.update_traces(texttemplate='%{x:.2f}h', textposition='outside')
        st.plotly_chart(fig_neg, use_container_width=True)
    else:
        st.info("Nenhum saldo negativo para o filtro selecionado.")


# --- GRÁFICOS DE PAGAMENTOS E DESCONTOS (Inalterado) ---
st.markdown('---')
st.subheader('Análise Gráfica por Movimentação (Pagamento/Desconto)')

# Agrupamento de Pagamentos (Positivos)
ranking_pagamentos = df_banco_horas_filtrado[df_banco_horas_filtrado['Pagamentos_Horas'] > 0] \
    .groupby('Estabelecimento')['Pagamentos_Horas'].sum().sort_values(ascending=False).reset_index()

# Agrupamento de Descontos (Negativos)
ranking_descontos_raw = df_banco_horas_filtrado[df_banco_horas_filtrado['Descontos_Horas'] < 0] \
    .groupby('Estabelecimento')['Descontos_Horas'].sum().sort_values(ascending=True).reset_index()

col_ranking_pag, col_ranking_desc = st.columns(2)

with col_ranking_pag:
    st.markdown('##### Ranking de Horas Pagas')
    if not ranking_pagamentos.empty:
        fig_pag = px.bar(
            ranking_pagamentos,
            x='Pagamentos_Horas',
            y='Estabelecimento',
            orientation='h',
            title='Total de Horas Pagas no Escopo Selecionado',
            labels={'Pagamentos_Horas': 'Total de Horas (Pagamentos)'},
            color_discrete_sequence=[COR_PRINCIPAL_VERDE],
            category_orders={
                'Estabelecimento': ranking_pagamentos['Estabelecimento'].tolist()},
            height=CHART_HEIGHT
        )
        fig_pag.update_traces(texttemplate='%{x:.2f}h', textposition='outside')
        st.plotly_chart(fig_pag, use_container_width=True)
    else:
        st.info("Nenhum pagamento de horas encontrado para o filtro selecionado.")

with col_ranking_desc:
    st.markdown('##### Ranking de Horas Descontadas')
    if not ranking_descontos_raw.empty:
        fig_desc = px.bar(
            ranking_descontos_raw,
            x='Descontos_Horas',
            y='Estabelecimento',
            orientation='h',
            title='Total de Horas Descontadas no Escopo Selecionado',
            labels={'Descontos_Horas': 'Total de Horas (Descontos)'},
            color_discrete_sequence=[COR_CONTRASTE],
            category_orders={
                'Estabelecimento': ranking_descontos_raw['Estabelecimento'].tolist()},
            height=CHART_HEIGHT
        )
        fig_desc.update_traces(
            texttemplate='%{x:.2f}h', textposition='outside')
        st.plotly_chart(fig_desc, use_container_width=True)
    else:
        st.info("Nenhum desconto de horas encontrado para o filtro selecionado.")

# --- DETALHAMENTO DO BANCO DE HORAS (AJUSTADO COM ESTABELECIMENTO E CARGO) ---

if filtros_ativos:
    st.markdown('---')

    estabs_title = ", ".join(
        selected_establishments) if selected_establishments else "Todos"
    deps_title = ", ".join(
        selected_departments) if selected_departments else "Todos"
    st.subheader(
        f'Detalhes do Banco de Horas e Movimentações para: **{estabs_title}** / **{deps_title}**')

    # DEFINIÇÃO DAS COLUNAS COM ESTABELECIMENTO E CARGO
    BASE_COLUMNS_SALDO = ['Estabelecimento', 'Nome',
                          'Cargo', 'SaldoFinal_Horas', 'Saldo Final (HH:MM)']
    BASE_COLUMNS_PAG_DESC = ['Estabelecimento',
                             'Nome', 'Cargo', 'Horas_Decimais', 'Horas_HHMM']

    # 1. Detalhes de Saldo Positivo
    detalhes_positivo_df = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] > 0][
        BASE_COLUMNS_SALDO
    ].copy()
    detalhes_positivo_df.columns = [
        'Estabelecimento', 'Nome do Funcionário', 'Cargo', 'Saldo (Horas Decimais)', 'Saldo (HH:MM)']
    detalhes_positivo_df = detalhes_positivo_df.sort_values(
        by='Saldo (Horas Decimais)', ascending=False).reset_index(drop=True)

    # 2. Detalhes de Saldo Negativo
    detalhes_negativo_df = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] < 0][
        BASE_COLUMNS_SALDO
    ].copy()
    detalhes_negativo_df.columns = [
        'Estabelecimento', 'Nome do Funcionário', 'Cargo', 'Saldo (Horas Decimais)', 'Saldo (HH:MM)']
    detalhes_negativo_df = detalhes_negativo_df.sort_values(
        by='Saldo (Horas Decimais)', ascending=True).reset_index(drop=True)

    # 3. Detalhes de Pagamentos
    # Mapeando Pagamentos para a estrutura de Pag/Desc
    detalhes_pagamentos_df_temp = df_banco_horas_filtrado[df_banco_horas_filtrado['Pagamentos_Horas'] > 0].copy(
    )
    detalhes_pagamentos_df_temp = detalhes_pagamentos_df_temp.rename(
        columns={'Pagamentos_Horas': 'Horas_Decimais', 'Pagamentos (HH:MM)': 'Horas_HHMM'})

    detalhes_pagamentos_df = detalhes_pagamentos_df_temp[BASE_COLUMNS_PAG_DESC].copy(
    )
    detalhes_pagamentos_df.columns = ['Estabelecimento', 'Nome do Funcionário',
                                      'Cargo', 'Pagamentos (Horas Decimais)', 'Pagamentos (HH:MM)']
    detalhes_pagamentos_df = detalhes_pagamentos_df.sort_values(
        by='Pagamentos (Horas Decimais)', ascending=False).reset_index(drop=True)

    # 4. Detalhes de Descontos
    # Mapeando Descontos para a estrutura de Pag/Desc
    detalhes_descontos_df_temp = df_banco_horas_filtrado[df_banco_horas_filtrado['Descontos_Horas'] < 0].copy(
    )
    detalhes_descontos_df_temp = detalhes_descontos_df_temp.rename(
        columns={'Descontos_Horas': 'Horas_Decimais', 'Descontos (HH:MM)': 'Horas_HHMM'})

    detalhes_descontos_df = detalhes_descontos_df_temp[BASE_COLUMNS_PAG_DESC].copy(
    )
    detalhes_descontos_df.columns = ['Estabelecimento', 'Nome do Funcionário',
                                     'Cargo', 'Descontos (Horas Decimais)', 'Descontos (HH:MM)']
    detalhes_descontos_df = detalhes_descontos_df.sort_values(
        by='Descontos (Horas Decimais)', ascending=True).reset_index(drop=True)

    # --- EXIBIÇÃO EM 2 LINHAS DE 2 COLUNAS CADA ---

    st.markdown('#### Resumo de Saldo Final')
    detalhe_banco_col1, detalhe_banco_col2 = st.columns(2)

    # Saldo Positivo
    with detalhe_banco_col1:
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
    with detalhe_banco_col2:
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
