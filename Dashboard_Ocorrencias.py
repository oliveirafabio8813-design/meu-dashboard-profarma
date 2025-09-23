import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Ocorrências ProFarma")

# --- Paleta de Cores baseada no Logotipo ProFarma ---
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

# --- Carregamento de Dados ---
try:
    df_ocorrencias = pd.read_excel('Relatorio_OcorrenciasNoPonto.xlsx')
    df_ocorrencias['Data'] = pd.to_datetime(df_ocorrencias['Data'], errors='coerce', dayfirst=True)
except FileNotFoundError:
    st.error("Erro: O arquivo 'Relatorio_OcorrenciasNoPonto.xlsx' não foi encontrado.")
    st.stop()
except Exception as e:
    st.error(f"Ocorreu um erro ao carregar o arquivo de ocorrências: {e}")
    st.stop()

try:
    df_banco_horas = pd.read_excel('Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx')
    df_banco_horas['SaldoFinal_Horas'] = df_banco_horas['SaldoFinal'].apply(convert_to_hours)
except FileNotFoundError:
    st.error("Erro: O arquivo 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx' não foi encontrado.")
    st.stop()
except Exception as e:
    st.error(f"Ocorreu um erro ao carregar o arquivo de banco de horas: {e}")
    st.stop()

# --- Cabeçalho com Logotipo e Título ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        st.image("image_ccccb7.png", width=150)
    except FileNotFoundError:
        st.warning("Logotipo 'image_ccccb7.png' não encontrado. Verifique o caminho.")
with col_title:
    st.title('Dashboard de Ocorrências no Ponto')

st.markdown('---')

# --- Filtro Central por Estabelecimento ---
todos_estabelecimentos = sorted(list(set(df_ocorrencias['Estabelecimento'].unique()) | set(df_banco_horas['Estabelecimento'].unique())))
todos_estabelecimentos.insert(0, 'Todos os Estabelecimentos')
selected_establishment = st.selectbox(
    'Filtro por Estabelecimento:',
    options=todos_estabelecimentos
)

# --- Filtrar DataFrames com base na seleção ---
if selected_establishment != 'Todos os Estabelecimentos':
    df_ocorrencias_filtrado = df_ocorrencias[df_ocorrencias['Estabelecimento'] == selected_establishment].copy()
    df_banco_horas_filtrado = df_banco_horas[df_banco_horas['Estabelecimento'] == selected_establishment].copy()
else:
    df_ocorrencias_filtrado = df_ocorrencias.copy()
    df_banco_horas_filtrado = df_banco_horas.copy()

# --- Relatório de Ocorrências (Gráficos) ---
st.subheader('Relatório de Ocorrências')

# Processamento de dados para gráficos
resultados = pd.DataFrame(columns=['Estabelecimento', 'ContagemFaltas', 'ContagemMarcacoesImpares'])
grupos = df_ocorrencias_filtrado.groupby('Estabelecimento')
for estabelecimento, grupo in grupos:
    filtro_falta = (grupo['Ocorrencia'] == 'Falta') & (grupo['Justificativa'] == 'Falta')
    contagem_falta = filtro_falta.sum()
    marcacoes_impares = grupo['Marcacoes'].apply(e_marcacoes_impar)
    contagem_impares_base = marcacoes_impares.sum()
    filtro_sem_marcacao = (grupo['Ocorrencia'].isin(['Sem marcação de entrada', 'Sem marcação de saída']))
    contagem_sem_marcacao = filtro_sem_marcacao.sum()
    contagem_marcacoes_impares = contagem_impares_base + contagem_sem_marcacao
    resultados.loc[len(resultados)] = [estabelecimento, contagem_falta, contagem_sem_marcacao + contagem_impares_base]

resultados_faltas = resultados.sort_values(by='ContagemFaltas', ascending=False)
resultados_impares = resultados.sort_values(by='ContagemMarcacoesImpares', ascending=False)

col1, col2 = st.columns(2)
with col1:
    st.subheader('Gráfico de Faltas por Estabelecimento')
    fig_faltas = px.bar(
        resultados_faltas,
        y='Estabelecimento',
        x='ContagemFaltas',
        orientation='h',
        title='Total de Faltas por Estabelecimento',
        labels={'ContagemFaltas': 'Total de Ocorrências (Faltas)'},
        color_discrete_sequence=[COR_CONTRASTE],
        category_orders={'Estabelecimento': resultados_faltas['Estabelecimento'].tolist()}
    )
    fig_faltas.update_traces(texttemplate='%{x}', textposition='outside')
    st.plotly_chart(fig_faltas, use_container_width=True)

with col2:
    st.subheader('Gráfico de Marcações Ímpares')
    fig_impares = px.bar(
        resultados_impares,
        y='Estabelecimento',
        x='ContagemMarcacoesImpares',
        orientation='h',
        title='Total de Marcações Ímpares por Estabelecimento',
        labels={'ContagemMarcacoesImpares': 'Total de Ocorrências (Marcações Ímpar)'},
        color_discrete_sequence=[COR_PRINCIPAL_VERDE],
        category_orders={'Estabelecimento': resultados_impares['Estabelecimento'].tolist()}
    )
    fig_impares.update_traces(texttemplate='%{x}', textposition='outside')
    st.plotly_chart(fig_impares, use_container_width=True)

# --- Detalhamento de Ocorrências (se houver um filtro) ---
if selected_establishment != 'Todos os Estabelecimentos':
    st.markdown('---')
    st.subheader(f"Detalhes de Ocorrências para: **{selected_establishment}**")
    
    # Processamento para Faltas
    faltas_df = df_ocorrencias_filtrado[(df_ocorrencias_filtrado['Ocorrencia'] == 'Falta') & (df_ocorrencias_filtrado['Justificativa'] == 'Falta')]
    faltas_df = faltas_df[['Nome', 'Data']]
    faltas_df.columns = ['Nome do Funcionário', 'Data da Falta']
    faltas_df = faltas_df.sort_values(by=['Nome do Funcionário', 'Data da Falta']).reset_index(drop=True)
    faltas_df['Data da Falta'] = faltas_df['Data da Falta'].dt.strftime('%d/%m/%Y')
    
    # Processamento para Marcações Ímpares
    df_ocorrencias_filtrado['is_impar'] = df_ocorrencias_filtrado['Marcacoes'].apply(e_marcacoes_impar)
    df_ocorrencias_filtrado['is_sem_marcacao'] = df_ocorrencias_filtrado['Ocorrencia'].isin(['Sem marcação de entrada', 'Sem marcação de saída'])
    impares_df = df_ocorrencias_filtrado[df_ocorrencias_filtrado['is_impar'] | df_ocorrencias_filtrado['is_sem_marcacao']]
    impares_df = impares_df[['Nome', 'Data']]
    impares_df.columns = ['Nome do Funcionário', 'Data da Marcação Ímpar']
    impares_df = impares_df.sort_values(by=['Nome do Funcionário', 'Data da Marcação Ímpar']).reset_index(drop=True)
    impares_df['Data da Marcação Ímpar'] = impares_df['Data da Marcação Ímpar'].dt.strftime('%d/%m/%Y')
    
    detalhe_col1, detalhe_col2 = st.columns(2)
    with detalhe_col1:
        st.subheader("Faltas Detalhadas")
        if not faltas_df.empty:
            st.dataframe(faltas_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma falta encontrada para este estabelecimento.")
    with detalhe_col2:
        st.subheader("Marcações Ímpares Detalhadas")
        if not impares_df.empty:
            st.dataframe(impares_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma marcação ímpar encontrada para este estabelecimento.")

# --- Relatório de Banco de Horas (Gráficos) ---
st.markdown('---')
st.subheader('Relatório do Banco de Horas')

# Classificar e agrupar por estabelecimento
df_positivo = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] > 0]
df_negativo = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] < 0]

# Ordenação de horas negativas para a visualização desejada
ranking_positivo = df_positivo.groupby('Estabelecimento')['SaldoFinal_Horas'].sum().sort_values(ascending=False).reset_index()
ranking_negativo = df_negativo.groupby('Estabelecimento')['SaldoFinal_Horas'].sum().sort_values(ascending=True).reset_index()

col_ranking_pos, col_ranking_neg = st.columns(2)

with col_ranking_pos:
    st.subheader('Ranking de Horas Positivas')
    fig_pos = px.bar(
        ranking_positivo,
        x='SaldoFinal_Horas',
        y='Estabelecimento',
        orientation='h',
        title='Total de Horas Positivas por Estabelecimento',
        labels={'SaldoFinal_Horas': 'Total de Horas (Positivas)'},
        color_discrete_sequence=[COR_PRINCIPAL_VERDE],
        category_orders={'Estabelecimento': ranking_positivo['Estabelecimento'].tolist()}
    )
    fig_pos.update_traces(texttemplate='%{x:.2f}h', textposition='outside')
    st.plotly_chart(fig_pos, use_container_width=True)

with col_ranking_neg:
    st.subheader('Ranking de Horas Negativas')
    fig_neg = px.bar(
        ranking_negativo,
        x='SaldoFinal_Horas',
        y='Estabelecimento',
        orientation='h',
        title='Total de Horas Negativas por Estabelecimento',
        labels={'SaldoFinal_Horas': 'Total de Horas (Negativas)'},
        color_discrete_sequence=[COR_CONTRASTE],
        # CORRIGIDO: Invertendo a ordem das categorias para que o maior débito fique no topo
        category_orders={'Estabelecimento': ranking_negativo['Estabelecimento'].tolist()}
    )
    fig_neg.update_traces(texttemplate='%{x:.2f}h', textposition='outside')
    st.plotly_chart(fig_neg, use_container_width=True)

# --- Detalhamento do Banco de Horas (se houver um filtro) ---
if selected_establishment != 'Todos os Estabelecimentos':
    st.markdown('---')
    st.subheader(f'Detalhes do Banco de Horas para: **{selected_establishment}**')

    detalhes_positivo_df = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] > 0][['Nome', 'SaldoFinal_Horas', 'SaldoFinal']]
    detalhes_positivo_df.columns = ['Nome do Funcionário', 'Saldo (Horas Decimais)', 'Saldo (HH:MM)']
    detalhes_positivo_df = detalhes_positivo_df.sort_values(by='Saldo (Horas Decimais)', ascending=False).reset_index(drop=True)

    # Ordenação de horas negativas para a visualização desejada
    detalhes_negativo_df = df_banco_horas_filtrado[df_banco_horas_filtrado['SaldoFinal_Horas'] < 0][['Nome', 'SaldoFinal_Horas', 'SaldoFinal']]
    detalhes_negativo_df.columns = ['Nome do Funcionário', 'Saldo (Horas Decimais)', 'Saldo (HH:MM)']
    detalhes_negativo_df = detalhes_negativo_df.sort_values(by='Saldo (Horas Decimais)', ascending=True).reset_index(drop=True)

    detalhe_banco_col1, detalhe_banco_col2 = st.columns(2)

    with detalhe_banco_col1:
        st.subheader("Saldo Positivo Detalhado")
        if not detalhes_positivo_df.empty:
            st.dataframe(detalhes_positivo_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum saldo positivo encontrado para este estabelecimento.")

    with detalhe_banco_col2:
        st.subheader("Saldo Negativo Detalhado")
        if not detalhes_negativo_df.empty:
            st.dataframe(detalhes_negativo_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum saldo negativo encontrado para este estabelecimento.")