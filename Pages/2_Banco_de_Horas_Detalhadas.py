# pages/2_Banco_de_Horas_Detalhadas.py (COM ORDEM DEPARTAMENTO antes de NOME)

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests             # Necessário para buscar URLs do GitHub
import io                   # NOVO: Necessário para lidar com dados binários do Excel (BytesIO)

# --- Constantes e Configurações ---
st.set_page_config(
    layout="wide", page_title="Dashboard Profarma - Banco de Horas")
COR_PRINCIPAL_VERDE = "#70C247"  # Cor para Crédito/Pagamentos
COR_CONTRASTE = "#dc3545"  # Cor para Débito/Descontos

# --- URLs BRUTAS DO GITHUB (AJUSTE CRÍTICO PARA XLSX) ---
REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'

# Arquivos XLSX e suas abas
URL_BANCO_HORAS_RESUMO = REPO_URL_BASE + 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx'
SHEET_BANCO_HORAS = 'ContaCorrenteBancodeHorasResum'

URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx' # Mantido para carregar na load_data, se necessário
SHEET_OCORRENCIAS = 'OcorrênciasnoPonto'


# --- Funções e Carregamento de Dados ---

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
    # CHAMA A FUNÇÃO CORRIGIDA PARA XLSX
    df_ocorrencias = load_data_from_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
    df_banco_horas = load_data_from_github(URL_BANCO_HORAS_RESUMO, SHEET_BANCO_HORAS)
    
    if df_banco_horas.empty:
        st.error("Falha ao carregar o DataFrame de Banco de Horas do GitHub.")
        st.stop()
        
    if not df_ocorrencias.empty:
        try:
            # Tenta processar Ocorrências (Mantido do original)
            df_ocorrencias['Data'] = pd.to_datetime(
                df_ocorrencias['Data'], errors='coerce', dayfirst=True)
        except Exception:
             # Se der erro no processamento, segue sem o df_ocorrencias
             df_ocorrencias = pd.DataFrame()

    try:
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
        st.error(f"Erro ao processar dados de Banco de Horas: {e}")
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
