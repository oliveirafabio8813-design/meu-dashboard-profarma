# Dashboard_Ocorrencias.py (Código Atualizado)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests             # Necessário para buscar URLs do GitHub
import io                   # NOVO: Necessário para lidar com dados binários do Excel (BytesIO)

# --- Constantes e Configurações ---
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Resumo",
                   initial_sidebar_state="expanded")

# Cores
COR_PRINCIPAL_VERDE = "#70C247"
COR_ALERTA_VERMELHO = "#dc3545"

# --- URLs BRUTAS DO GITHUB (AJUSTE CRÍTICO PARA XLSX) ---
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'

# Arquivos XLSX (Nomes completos do arquivo no GitHub)
URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx'
SHEET_OCORRENCIAS = 'OcorrênciasnoPonto' # Nome da aba no Excel

URL_BANCO_HORAS_RESUMO = REPO_URL_BASE + 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx'
SHEET_BANCO_HORAS = 'ContaCorrenteBancodeHorasResum' # Nome da aba no Excel

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


# --- Carregamento de Dados e Cache (AJUSTADO PARA XLSX) ---
@st.cache_data
def load_data():
    # CHAMA A FUNÇÃO CORRIGIDA PARA XLSX
    df_ocorrencias = load_data_from_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
    df_banco_horas = load_data_from_github(URL_BANCO_HORAS_RESUMO, SHEET_BANCO_HORAS)

    if df_ocorrencias.empty or df_banco_horas.empty:
        st.error("Falha ao carregar um ou ambos os DataFrames do GitHub.")
        st.stop()

    # --- Processamento de Ocorrências (Mantido do original) ---
    df_ocorrencias['Data'] = pd.to_datetime(
        df_ocorrencias['Data'], errors='coerce', dayfirst=True)
    df_ocorrencias['is_impar'] = df_ocorrencias['Marcacoes'].apply(
        e_marcacoes_impar)
    df_ocorrencias['is_sem_marcacao'] = df_ocorrencias['Ocorrencia'].isin(
        ['Sem marcação de entrada', 'Sem marcação de saída'])
    
    # CRIAÇÃO DA COLUNA DE FALTA NÃO JUSTIFICADA (NECESSÁRIA PARA O RANKING)
    df_ocorrencias['is_falta_nao_justificada'] = df_ocorrencias.apply(
        lambda row: 1 if row['Ocorrencia'] == 'Falta' and row['Justificativa'] == 'Falta' else 0,
        axis=1
    )


    # --- Processamento de Banco de Horas (Mantido do original) ---
    # Converte Saldo Final (mantém o sinal original)
    df_banco_horas['SaldoFinal_Horas'] = df_banco_horas['SaldoFinal'].apply(
        convert_to_hours)
    # Pagamentos (deve ser positivo - Garante que é um crédito)
    df_banco_horas['Pagamentos_Horas'] = df_banco_horas['Pagamentos'].apply(
        convert_to_hours).abs()
    # Descontos (deve ser negativo - Força o sinal para débito)
    df_banco_horas['Descontos_Horas'] = - \
        df_banco_horas['Descontos'].apply(convert_to_hours).abs()

    return df_ocorrencias, df_banco_horas


df_ocorrencias, df_banco_horas = load_data()


# --- INÍCIO DO STREAMLIT APP ---
st.title("📊 Dashboard de Recursos Humanos Profarma")
st.markdown('---')


# --- CÁLCULOS DOS TOTAIS GLOBAIS (EXISTENTES) ---
total_head_count = df_banco_horas['Matricula'].nunique()

# O cálculo desta coluna foi movido para a função load_data para garantir o cache
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
        # Assumindo que a imagem 'image_ccccb7.png' está no repositório
        st.image("image_ccccb7.png", width=120)
    except FileNotFoundError:
        st.warning("Logotipo não encontrado.")

with col_title:
    st.markdown(
        f'<h1 style="color: {COR_PRINCIPAL_VERDE}; margin-bottom: 0px;">Dashboard Profarma - Visão Geral</h1>', unsafe_allow_html=True)
    st.markdown('Resumo Profissional de Ocorrências e Banco de Horas')

with col_info:
    st.metric(label="Total de Colaboradores (Head Count)",
              value=f"{total_head_count}")

st.markdown('---')


# 2. KPIs de Ocorrências e Saldo de Horas
st.subheader('Indicadores Chave (KPIs)')

col_kpi_1, col_kpi_2, col_kpi_3, col_kpi_4 = st.columns(4)

with col_kpi_1:
    st.metric(
        label="Total de Faltas Não Justificadas (Período)",
        value=f"{int(total_faltas)}",
        delta_color="off"
    )

with col_kpi_2:
    st.metric(
        label="Total de Marcações Ímpares/Ausentes",
        value=f"{total_marcacoes_impares}",
        delta_color="off"
    )

with col_kpi_3:
    st.metric(
        label="Banco de Horas Positivo (Crédito Total)",
        value=f"**{bh_positivo_formatado}**",
        help="Soma total das horas em saldo positivo de todos os colaboradores.",
        delta_color="off",
    )

with col_kpi_4:
    # Se o saldo negativo for 0, usa a cor verde, senão usa a cor de alerta
    delta_color = "normal" if total_bh_negativo_horas < 0 else "off"
    st.metric(
        label="Banco de Horas Negativo (Débito Total)",
        value=f"**{bh_negativo_formatado}**",
        help="Soma total das horas em saldo negativo de todos os colaboradores.",
        delta_color=delta_color
    )

st.markdown('---')


# 3. Gráficos de Ranking (Ocorrências, Saldo Negativo, Pagamentos/Descontos)
st.subheader('Análise de Distribuição por Estabelecimento')

col_chart_1, col_chart_2 = st.columns(2)

# --- Coluna 1: Ocorrências (Faltas e Ímpares) ---
with col_chart_1:
    st.markdown('#### Top Estabelecimentos por Ocorrências')

    # 1. Agrupamento por Estabelecimento (Faltas e Ímpares)
    df_ranking_ocorrencias = df_ocorrencias.groupby('Estabelecimento').agg(
        Total_Faltas=('is_falta_nao_justificada', 'sum'),
        Total_Impares=('is_impar', 'sum'),
        Total_Sem_Marcacao=('is_sem_marcacao', 'sum')
    ).reset_index()

    df_ranking_ocorrencias['Total_Ocorrencias'] = df_ranking_ocorrencias['Total_Faltas'] + \
        df_ranking_ocorrencias['Total_Impares'] + \
        df_ranking_ocorrencias['Total_Sem_Marcacao']

    # 2. Ordenar do maior para o menor
    df_ranking_ocorrencias = df_ranking_ocorrencias.sort_values(
        'Total_Ocorrencias', ascending=True
    ).tail(10)

    if not df_ranking_ocorrencias.empty:
        fig_ocorrencias = px.bar(
            df_ranking_ocorrencias,
            y='Estabelecimento',
            x=['Total_Faltas', 'Total_Impares', 'Total_Sem_Marcacao'],
            orientation='h',
            # Usa o Total_Ocorrencias como texto
            text='Total_Ocorrencias',
            color_discrete_sequence=[
                COR_ALERTA_VERMELHO, '#ffc107', '#17a2b8'],  # Cores para as categorias
            labels={'value': 'Total de Ocorrências',
                    'Estabelecimento': 'Estabelecimento',
                    'variable': 'Tipo de Ocorrência'},
            template='plotly_white'
        )

        fig_ocorrencias.update_traces(
            textposition='outside',
            cliponaxis=False
        )

        # Atualiza o layout para melhor visualização
        fig_ocorrencias.update_layout(
            xaxis_title=None,
            legend_title_text='Tipo',
            height=400,
            uniformtext_minsize=8,
            uniformtext_mode='hide'
        )

        st.plotly_chart(fig_ocorrencias, use_container_width=True)
    else:
        st.info("Nenhuma ocorrência encontrada para exibição no ranking.")


# --- Coluna 2: Saldo Negativo (Débito) ---
with col_chart_2:
    st.markdown('#### Ranking de Débito (Saldo Negativo) no Banco de Horas')

    # 1. Filtrar saldos negativos e agrupar
    df_ranking_bh_negativo = df_banco_horas[df_banco_horas['SaldoFinal_Horas'] < 0].groupby(
        'Estabelecimento')['SaldoFinal_Horas'].sum().reset_index(name='Total Saldo Negativo (Horas Decimais)')

    # 2. Criar coluna formatada para o texto
    df_ranking_bh_negativo['Saldo Negativo (HH:MM)'] = df_ranking_bh_negativo['Total Saldo Negativo (Horas Decimais)'].apply(
        format_decimal_to_hhmm)

    # 3. Ordenar do maior débito (mais negativo) para o menor
    df_ranking_bh_negativo = df_ranking_bh_negativo.sort_values(
        'Total Saldo Negativo (Horas Decimais)',
        ascending=True
    ).head(10)

    if not df_ranking_bh_negativo.empty:
        # A cor será mais intensa quanto mais negativo for o saldo
        fig_bh_negativo = px.bar(
            df_ranking_bh_negativo,
            y='Estabelecimento',
            x='Total Saldo Negativo (Horas Decimais)',
            orientation='h',
            text='Saldo Negativo (HH:MM)',
            color='Total Saldo Negativo (Horas Decimais)',
            color_continuous_scale=px.colors.sequential.Reds_r,
            labels={'Total Saldo Negativo (Horas Decimais)': 'Total de Horas Negativas'},
            template='plotly_white',
            category_orders={
                'Estabelecimento': df_ranking_bh_negativo['Estabelecimento'].tolist()}
        )

        # Ajustes para texto no topo e ocultar eixo decimal
        fig_bh_negativo.update_traces(
            textposition='outside',
            cliponaxis=False
        )
        fig_bh_negativo.update_layout(
            xaxis_title=None,
            height=400,
            uniformtext_minsize=8,
            uniformtext_mode='hide'
        )

        st.plotly_chart(fig_bh_negativo, use_container_width=True)
    else:
        st.info("Nenhum saldo negativo encontrado para exibição no ranking.")

st.markdown('---')

# 4. Gráficos de Pagamentos e Descontos
st.subheader('Análise de Movimentações (Pagamentos e Descontos)')
col_mov_1, col_mov_2 = st.columns(2)

# --- Coluna 1: Pagamentos (Crédito) ---
with col_mov_1:
    st.markdown('#### Ranking de Pagamentos de Horas')

    # 1. Filtrar pagamentos e agrupar (Pagamentos_Horas é sempre positivo)
    df_ranking_pagamentos_bh = df_banco_horas[df_banco_horas['Pagamentos_Horas'] > 0].groupby(
        'Estabelecimento')['Pagamentos_Horas'].sum().reset_index(name='Total Pagamentos (Horas Decimais)')

    # 2. Criar coluna formatada para o texto
    df_ranking_pagamentos_bh['Pagamentos (HH:MM)'] = df_ranking_pagamentos_bh['Total Pagamentos (Horas Decimais)'].apply(
        format_decimal_to_hhmm)

    # 3. Ordenar do maior para o menor pagamento
    df_ranking_pagamentos_bh = df_ranking_pagamentos_bh.sort_values(
        'Total Pagamentos (Horas Decimais)',
        ascending=False
    ).head(10)

    if not df_ranking_pagamentos_bh.empty:
        fig_bh_pagamentos = px.bar(
            df_ranking_pagamentos_bh,
            y='Estabelecimento',
            x='Total Pagamentos (Horas Decimais)',
            orientation='h',
            text='Pagamentos (HH:MM)',
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
            height=400,
            uniformtext_minsize=8,
            uniformtext_mode='hide'
        )

        st.plotly_chart(fig_bh_pagamentos, use_container_width=True)
    else:
        st.info("Nenhum pagamento de horas encontrado para exibição no ranking.")


# --- Coluna 2: Descontos (Débito) ---
with col_mov_2:
    st.markdown('#### Ranking de Descontos de Horas')

    # 1. Filtrar descontos e agrupar (Descontos_Horas é sempre negativo)
    df_ranking_descontos_bh = df_banco_horas[df_banco_horas['Descontos_Horas'] < 0].groupby(
        'Estabelecimento')['Descontos_Horas'].sum().reset_index(name='Total Descontos (Horas Decimais)')

    # 2. Criar coluna formatada para o texto
    df_ranking_descontos_bh['Descontos (HH:MM)'] = df_ranking_descontos_bh['Total Descontos (Horas Decimais)'].apply(
        format_decimal_to_hhmm)

    # 3. Ordenar do maior débito (mais negativo) para o menor
    df_ranking_descontos_bh = df_ranking_descontos_bh.sort_values(
        'Total Descontos (Horas Decimais)',
        ascending=True
    ).head(10)

    if not df_ranking_descontos_bh.empty:
        # A cor será mais intensa quanto mais negativo for o saldo
        fig_bh_descontos = px.bar(
            df_ranking_descontos_bh,
            y='Estabelecimento',
            x='Total Descontos (Horas Decimais)',
            orientation='h',
            text='Descontos (HH:MM)',
            color='Total Descontos (Horas Decimais)',
            color_continuous_scale=px.colors.sequential.Reds_r,
            labels={'Total Descontos (Horas Decimais)': 'Total de Horas Descontadas'},
            template='plotly_white',
            category_orders={
                'Estabelecimento': df_ranking_descontos_bh['Estabelecimento'].tolist()}
        )

        # AJUSTES PARA TEXTO NO TOPO E OCULTAR EIXO DECIMAL
        fig_bh_descontos.update_traces(
            textposition='outside',
            cliponaxis=False
        )
        fig_bh_descontos.update_layout(
            xaxis_title=None,
            height=400,
            uniformtext_minsize=8,
            uniformtext_mode='hide'
        )

        st.plotly_chart(fig_bh_descontos, use_container_width=True)
    else:
        st.info("Nenhum desconto de horas encontrado para exibição no ranking.")


# ----------------------------------------------------------------------
# 🌟 NOVA FUNÇÃO: RANKING DE FALTAS POR COLABORADOR
# ----------------------------------------------------------------------

def page_ranking_faltas(df_ocorrencias):
    st.title("🏆 Ranking de Faltas Não Justificadas por Colaborador")
    st.markdown('---')
    
    # --- 1. Filtrar e Agrupar os Dados ---
    # is_falta_nao_justificada é a coluna binária (1 ou 0) criada no load_data
    df_faltas = df_ocorrencias[df_ocorrencias['is_falta_nao_justificada'] == 1].copy()
    
    # Agrupamento para obter a soma de faltas por colaborador
    # Assume que as colunas 'Estabelecimento', 'Nome', 'Cargo' existem no df_ocorrencias
    df_ranking_faltas = df_faltas.groupby(
        ['Estabelecimento', 'Nome', 'Cargo']
    ).agg(
        Soma_de_Faltas=('is_falta_nao_justificada', 'sum')
    ).reset_index()

    # Ordenar pelo número de faltas (do maior para o menor)
    df_ranking_faltas = df_ranking_faltas.sort_values(
        'Soma_de_Faltas', ascending=False
    )
    
    total_faltas = df_ranking_faltas['Soma_de_Faltas'].sum()

    st.info(f"O número total de faltas não justificadas neste período é de **{int(total_faltas)}**.")
    st.markdown('---')
    
    # --- 2. Exibição da Tabela de Ranking ---
    st.subheader('Tabela Detalhada (Top 100 Colaboradores)')

    # Renomeia colunas para exibição amigável
    df_exibicao = df_ranking_faltas.head(100).rename(columns={
        'Estabelecimento': 'Unidade',
        'Nome': 'Colaborador',
        'Soma_de_Faltas': 'Total Faltas'
    })
    
    st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        column_order=['Unidade', 'Colaborador', 'Cargo', 'Total Faltas']
    )

    st.markdown('---')
    
    # --- 3. Gráfico de Ranking (Top 10) ---
    st.subheader('Gráfico: Top 10 Colaboradores com Mais Faltas')
    
    df_ranking_top_10 = df_ranking_faltas.head(10).copy()

    if not df_ranking_top_10.empty:
        # Cria uma coluna de rótulo combinando nome e total para o texto do gráfico
        df_ranking_top_10['Colaborador_Label'] = df_ranking_top_10['Nome'] + ' (' + df_ranking_top_10['Soma_de_Faltas'].astype(int).astype(str) + ')'
        
        fig_ranking = px.bar(
            df_ranking_top_10.sort_values('Soma_de_Faltas', ascending=True),
            y='Colaborador_Label',
            x='Soma_de_Faltas',
            orientation='h',
            text='Soma_de_Faltas',
            color='Soma_de_Faltas', # Cor baseada na quantidade de faltas
            color_continuous_scale=[COR_ALERTA_VERMELHO], # Usa a cor de alerta
            labels={'Soma_de_Faltas': 'Total de Faltas', 'Colaborador_Label': 'Colaborador'},
            template='plotly_white'
        )
        
        fig_ranking.update_traces(
            texttemplate='%{text}',
            textposition='outside',
            marker_color=COR_ALERTA_VERMELHO # Força a cor vermelha de alerta
        )
        
        fig_ranking.update_layout(
            xaxis_title=None,
            height=500
        )
        
        st.plotly_chart(fig_ranking, use_container_width=True)
    else:
        st.info("Nenhuma falta não justificada encontrada para criar o ranking.")


# ----------------------------------------------------------------------
# ➡️ CHAMADA DA NOVA PÁGINA/SEÇÃO
# ----------------------------------------------------------------------
st.markdown('# ----------------------------------------------------------------------')
st.markdown('## 📄 Seção Extra: Ranking de Faltas por Colaborador')
page_ranking_faltas(df_ocorrencias)
st.markdown('# ----------------------------------------------------------------------')

