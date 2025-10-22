# Dashboard_Ocorrencias.py (Página Principal - Resumo Profissional com Head Count Global)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- Constantes e Configurações ---
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Resumo",
                   initial_sidebar_state="expanded")

# Cores
COR_PRINCIPAL_VERDE = "#70C247"  # Cor principal da marca
# Para saldos negativos (débito) ou ocorrências (mantido apenas para KPIs)
COR_ALERTA_VERMELHO = "#dc3545"

# --- Funções de Processamento de Dados ---


def e_marcacoes_impar(marcacoes):
    if pd.isna(marcacoes):
        return False
    return len(str(marcacoes).strip().split()) % 2 != 0


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


# --- Carregamento de Dados e Cache ---
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
    except FileNotFoundError:
        st.error(
            "Erro: O arquivo 'Relatorio_OcorrenciasNoPonto.xlsx' não foi encontrado.")
        st.stop()
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar o arquivo de ocorrências: {e}")
        st.stop()

    try:
        df_banco_horas = pd.read_excel(
            'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx')

        # Converte Saldo Final (mantém o sinal original)
        df_banco_horas['SaldoFinal_Horas'] = df_banco_horas['SaldoFinal'].apply(
            convert_to_hours)

        # Pagamentos (deve ser positivo - Garante que é um crédito)
        df_banco_horas['Pagamentos_Horas'] = df_banco_horas['Pagamentos'].apply(
            convert_to_hours).abs()

        # Descontos (deve ser negativo - Força o sinal para débito)
        df_banco_horas['Descontos_Horas'] = - \
            df_banco_horas['Descontos'].apply(convert_to_hours).abs()

    except FileNotFoundError:
        st.error(
            "Erro: O arquivo 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx' não foi encontrado.")
        st.stop()
    except Exception as e:
        st.error(
            f"Ocorreu um erro ao carregar o arquivo de banco de horas: {e}")
        st.stop()

    return df_ocorrencias, df_banco_horas


df_ocorrencias, df_banco_horas = load_data()


# --- CÁLCULOS DOS TOTAIS GLOBAIS ---

# CÁLCULOS EXISTENTES
total_head_count = df_banco_horas['Matricula'].nunique()

df_ocorrencias['is_falta_nao_justificada'] = df_ocorrencias.apply(
    lambda row: 1 if row['Ocorrencia'] == 'Falta' and row['Justificativa'] == 'Falta' else 0,
    axis=1
)

total_faltas = df_ocorrencias['is_falta_nao_justificada'].sum()
total_impares = df_ocorrencias['is_impar'].sum()
total_sem_marcacao = df_ocorrencias['is_sem_marcacao'].sum()
total_marcacoes_impares = int(total_impares + total_sem_marcacao)

total_bh_positivo_horas = df_banco_horas[df_banco_horas['SaldoFinal_Horas']
                                         > 0]['SaldoFinal_Horas'].sum()
total_bh_negativo_horas = df_banco_horas[df_banco_horas['SaldoFinal_Horas']
                                         < 0]['SaldoFinal_Horas'].sum()

# CÁLCULO DE PAGAMENTOS E DESCONTOS
total_pagamentos_horas = df_banco_horas[df_banco_horas['Pagamentos_Horas']
                                        > 0]['Pagamentos_Horas'].sum()
total_descontos_horas = df_banco_horas[df_banco_horas['Descontos_Horas']
                                       < 0]['Descontos_Horas'].sum()

# Formatação para exibição nos KPIs
bh_positivo_formatado = format_decimal_to_hhmm(total_bh_positivo_horas)
bh_negativo_formatado = format_decimal_to_hhmm(total_bh_negativo_horas)
pagamentos_formatado = format_decimal_to_hhmm(total_pagamentos_horas)
descontos_formatado = format_decimal_to_hhmm(total_descontos_horas)


# --- LAYOUT PROFISSIONAL ---

# 1. Cabeçalho com Logotipo e Título
col_logo, col_title, col_info = st.columns([1, 3, 1])

with col_logo:
    try:
        st.image("image_ccccb7.png", width=120)
    except FileNotFoundError:
        st.warning("Logotipo não encontrado.")

with col_title:
    st.markdown(
        f'<h1 style="color: {COR_PRINCIPAL_VERDE}; margin-bottom: 0px;">Dashboard de Gestão de Ponto</h1>', unsafe_allow_html=True)
    st.markdown('Visão Gerencial e Resumo dos Indicadores Chave (KPIs)')

st.markdown('---')


# 2. Seção de KPIs (st.metric)
st.subheader('Indicadores Chave Globais')

# Usando 7 colunas para todos os KPIs
colunas_kpis = st.columns(7)
col_hc, col1, col2, col3, col4, col5, col6 = colunas_kpis

# KPI 1: HEAD COUNT
with col_hc:
    st.metric(
        label="Total de Funcionários",
        value=total_head_count,
        delta_color="off"
    )

# KPI 2: FALTAS
with col1:
    st.metric(
        label="Total de Faltas (Não Justificadas)",
        value=total_faltas,
        delta_color="off"
    )

# KPI 3: MARCAÇÕES IMPARES
with col2:
    st.metric(
        label="Total de Marcações Ímpares / Sem Registro",
        value=total_marcacoes_impares,
        delta_color="off"
    )

# KPI 4: BH POSITIVO
with col3:
    st.metric(
        label="BH - Saldo POSITIVO (HH:MM)",
        value=bh_positivo_formatado,
        delta=f"+{total_bh_positivo_horas:.2f} Horas Decimais",
        delta_color="normal"
    )

# KPI 5: BH NEGATIVO
with col4:
    st.metric(
        label="BH - Saldo NEGATIVO (HH:MM)",
        value=bh_negativo_formatado,
        delta=f"{total_bh_negativo_horas:.2f} Horas Decimais",
        delta_color="inverse"
    )

# KPI 6: TOTAL A PAGAR (Pagamentos)
with col5:
    st.metric(
        label="BH - Total a PAGAR (HH:MM)",
        value=pagamentos_formatado,
        delta=f"+{total_pagamentos_horas:.2f} Horas Decimais",
        delta_color="normal"
    )

# KPI 7: TOTAL A DESCONTAR (Descontos)
with col6:
    st.metric(
        label="BH - Total a DESCONTAR (HH:MM)",
        value=descontos_formatado,
        delta=f"{total_descontos_horas:.2f} Horas Decimais",
        delta_color="inverse"
    )

st.markdown('---')


# 3. Análise Comparativa (Gráfico)
st.subheader('Análise Comparativa Geral por Estabelecimento')

# 3.1 Agrupamento de dados para comparação
# DataFrame de Ocorrências
df_resumo_ocorrencias = df_ocorrencias.groupby('Estabelecimento').agg(
    Total_Faltas=('is_falta_nao_justificada', 'sum'),
    Total_Impares=('is_impar', 'sum'),
    Total_Sem_Marcacao=('is_sem_marcacao', 'sum')
).reset_index()

df_resumo_ocorrencias['Total Ocorrências (Faltas + Ímpares)'] = (
    df_resumo_ocorrencias['Total_Faltas'] +
    df_resumo_ocorrencias['Total_Impares'] +
    df_resumo_ocorrencias['Total_Sem_Marcacao']
)

# DataFrame de Banco de Horas e merge (Usando Saldo Final)
df_resumo_bh = df_banco_horas.groupby('Estabelecimento')[
    'SaldoFinal_Horas'].sum().reset_index()
df_resumo_bh.columns = ['Estabelecimento', 'Saldo Total BH (Horas Decimais)']

# NOVO AGRUPAMENTO: Pagamentos (Horas a Pagar)
df_resumo_pagamentos = df_banco_horas[df_banco_horas['Pagamentos_Horas'] > 0].groupby(
    'Estabelecimento')['Pagamentos_Horas'].sum().reset_index()
df_resumo_pagamentos.columns = [
    'Estabelecimento', 'Total Pagamentos (Horas Decimais)']

# Merge para o dataframe comparativo (apenas usando SaldoFinal neste momento)
df_comparativo = pd.merge(df_resumo_ocorrencias, df_resumo_bh,
                          on='Estabelecimento', how='outer').fillna(0)


# 3.2 Gráfico de Barras Combinado (Ocorrências)
st.markdown('<h5 style="color: gray;">1. Estabelecimentos com Mais Ocorrências (Soma de Faltas + Ímpares/Sem Registro)</h5>', unsafe_allow_html=True)

df_ocorrencias_filtrado = df_comparativo[
    df_comparativo['Total Ocorrências (Faltas + Ímpares)'] > 1
].sort_values(
    'Total Ocorrências (Faltas + Ímpares)',
    ascending=False
)

if not df_ocorrencias_filtrado.empty:
    fig_comparativo_ocorrencias = px.bar(
        df_ocorrencias_filtrado.head(10),
        x='Estabelecimento',
        y='Total Ocorrências (Faltas + Ímpares)',
        color='Total Ocorrências (Faltas + Ímpares)',
        color_continuous_scale=px.colors.sequential.Greens,
        labels={
            'Total Ocorrências (Faltas + Ímpares)': 'Total de Ocorrências'},
        template='plotly_white'
    )
    fig_comparativo_ocorrencias.update_traces(
        texttemplate='%{y}',
        textposition='outside'
    )
    fig_comparativo_ocorrencias.update_layout(showlegend=False)
    st.plotly_chart(fig_comparativo_ocorrencias, use_container_width=True)
else:
    st.info("Nenhum estabelecimento encontrado com mais de 1 ocorrência total (Faltas + Marcações Ímpares).")


# 3.3 Gráfico de Saldo de BH (Somente Positivo)
st.markdown('<h5 style="color: gray; margin-top: 20px;">2. Saldo Positivo do Banco de Horas por Estabelecimento (Melhores Desempenhos)</h5>', unsafe_allow_html=True)

# 1. Filtrar somente saldos positivos
df_positivo_bh = df_comparativo[df_comparativo['Saldo Total BH (Horas Decimais)'] > 0].copy(
)

# 2. Criar a coluna de texto formatada (HH:MM)
df_positivo_bh['Saldo (HH:MM)'] = df_positivo_bh['Saldo Total BH (Horas Decimais)'].apply(
    format_decimal_to_hhmm)

# 3. Ordenar do maior para o menor saldo positivo
df_positivo_bh = df_positivo_bh.sort_values(
    'Saldo Total BH (Horas Decimais)',
    ascending=False
)

if not df_positivo_bh.empty:
    fig_bh_positivo = px.bar(
        df_positivo_bh,
        y='Estabelecimento',
        x='Saldo Total BH (Horas Decimais)',
        orientation='h',
        text='Saldo (HH:MM)',
        color='Saldo Total BH (Horas Decimais)',
        color_continuous_scale=px.colors.sequential.Greens,
        labels={'Saldo Total BH (Horas Decimais)': 'Saldo Positivo Líquido'},
        template='plotly_white',
        category_orders={
            'Estabelecimento': df_positivo_bh['Estabelecimento'].tolist()}
    )

    fig_bh_positivo.update_traces(
        textposition='outside',
        cliponaxis=False
    )
    fig_bh_positivo.update_layout(
        xaxis_title=None,
        xaxis={'showticklabels': False, 'visible': False},
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )

    st.plotly_chart(fig_bh_positivo, use_container_width=True)
else:
    st.info("Nenhum saldo positivo de Banco de Horas encontrado nos estabelecimentos para comparação.")


# 3.4 NOVO GRÁFICO: Ranking de Pagamentos (Horas a Pagar)
st.markdown('<h5 style="color: gray; margin-top: 20px;">3. Horas a Pagar (Pagamentos) por Estabelecimento (Maior Crédito)</h5>', unsafe_allow_html=True)

# 1. Filtrar somente pagamentos (já agrupado em df_resumo_pagamentos)
df_ranking_pagamentos_bh = df_resumo_pagamentos[
    df_resumo_pagamentos['Total Pagamentos (Horas Decimais)'] > 0
].copy()

# 2. Criar a coluna de texto formatada (HH:MM)
df_ranking_pagamentos_bh['Pagamentos (HH:MM)'] = df_ranking_pagamentos_bh['Total Pagamentos (Horas Decimais)'].apply(
    format_decimal_to_hhmm)

# 3. Ordenar do maior para o menor pagamento
df_ranking_pagamentos_bh = df_ranking_pagamentos_bh.sort_values(
    'Total Pagamentos (Horas Decimais)',
    ascending=False
)

if not df_ranking_pagamentos_bh.empty:
    fig_bh_pagamentos = px.bar(
        df_ranking_pagamentos_bh,
        y='Estabelecimento',
        x='Total Pagamentos (Horas Decimais)',
        orientation='h',
        text='Pagamentos (HH:MM)',
        # Usando a cor principal para Pagamentos (Verde)
        color='Total Pagamentos (Horas Decimais)',
        color_continuous_scale=px.colors.sequential.Greens,
        labels={'Total Pagamentos (Horas Decimais)': 'Total de Horas Pagas'},
        template='plotly_white',
        category_orders={
            'Estabelecimento': df_ranking_pagamentos_bh['Estabelecimento'].tolist()}
    )

    # AJUSTES PARA TEXTO NO TOPO E OCULTAR EIXO DECIMAL
    fig_bh_pagamentos.update_traces(
        textposition='outside',
        cliponaxis=False
    )
    fig_bh_pagamentos.update_layout(
        xaxis_title=None,
        xaxis={'showticklabels': False, 'visible': False},
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )

    st.plotly_chart(fig_bh_pagamentos, use_container_width=True)
else:
    st.info("Nenhum registro de Pagamento de Banco de Horas encontrado nos estabelecimentos para comparação.")
