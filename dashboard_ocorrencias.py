import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Ocorrências ProFarma")

# --- Paleta de Cores baseada no Logotipo ProFarma ---
# Verde principal do logo
COR_PRINCIPAL_VERDE = "#70C247" 
# Verde mais escuro para contrastar, ou um tom de cinza neutro
COR_CONTRASTE = "#4CAF50" # Um verde ligeiramente diferente para faltas ou um cinza: #6c757d

# --- Cabeçalho com Logotipo e Título ---
col_logo, col_title = st.columns([1, 4]) # Ajuste as proporções conforme necessário

with col_logo:
    try:
        st.image("logo_profarma.png", width=150) # Certifique-se que o logo está na mesma pasta
    except FileNotFoundError:
        st.warning("Logotipo 'logo_profarma.png' não encontrado. Verifique o caminho.")

with col_title:
    st.title('Dashboard de Ocorrências no Ponto')

st.markdown('---')

# --- Carregamento de Dados ---
try:
    df = pd.read_excel('Relatorio_OcorrenciasNoPonto.xlsx')
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
    
except FileNotFoundError:
    st.error("Erro: O arquivo 'Relatorio_OcorrenciasNoPonto.xlsx' não foi encontrado.")
    st.info("Por favor, verifique se o nome do arquivo está exatamente igual e se ele está na mesma pasta que o script.")
    st.stop()
except Exception as e:
    st.error(f"Ocorreu um erro ao carregar o arquivo: {e}")
    st.info("Por favor, verifique se o arquivo está no formato .xlsx e se a planilha contém a coluna 'Data'.")
    st.stop()

# --- Funções de Processamento de Dados ---
def e_marcacoes_impar(marcacoes):
    if pd.isna(marcacoes):
        return False
    return len(str(marcacoes).strip().split()) % 2 != 0

# Crie um DataFrame para armazenar os resultados por estabelecimento
resultados = pd.DataFrame(columns=['Estabelecimento', 'ContagemFaltas', 'ContagemMarcacoesImpares'])

grupos = df.groupby('Estabelecimento')
for estabelecimento, grupo in grupos:
    filtro_falta = (grupo['Ocorrencia'] == 'Falta') & (grupo['Justificativa'] == 'Falta')
    contagem_falta = filtro_falta.sum()
    marcacoes_impares = grupo['Marcacoes'].apply(e_marcacoes_impar)
    contagem_impares_base = marcacoes_impares.sum()
    filtro_sem_marcacao = (grupo['Ocorrencia'].isin(['Sem marcação de entrada', 'Sem marcação de saída']))
    contagem_sem_marcacao = filtro_sem_marcacao.sum()
    contagem_marcacoes_impares = contagem_impares_base + contagem_sem_marcacao
    resultados.loc[len(resultados)] = [estabelecimento, contagem_falta, contagem_marcacoes_impares]

# Ordene os resultados
resultados_faltas = resultados.sort_values(by='ContagemFaltas', ascending=True)
resultados_impares = resultados.sort_values(by='ContagemMarcacoesImpares', ascending=True)

# --- Gráficos Principais ---
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
        color_discrete_sequence=[COR_CONTRASTE] # Usando a cor de contraste
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
        labels={'ContagemMarcacoesImpares': 'Total de Ocorrências (Marcações Ímpares)'},
        color_discrete_sequence=[COR_PRINCIPAL_VERDE] # Usando o verde principal
    )
    fig_impares.update_traces(texttemplate='%{x}', textposition='outside')
    st.plotly_chart(fig_impares, use_container_width=True)

# --- Detalhes por Estabelecimento ---
st.markdown('---')
st.subheader('Detalhes por Estabelecimento')

# Crie uma lista de estabelecimentos para o filtro
lista_estabelecimentos = resultados['Estabelecimento'].tolist()
lista_estabelecimentos.insert(0, 'Selecione um Estabelecimento')
selected_estabelecimento = st.selectbox(
    'Selecione um estabelecimento para ver o detalhamento de faltas e marcações ímpares:',
    options=lista_estabelecimentos
)

# Lógica para mostrar os detalhes ao selecionar no seletor
if selected_estabelecimento != 'Selecione um Estabelecimento':
    st.write(f"### Detalhamento para: **{selected_estabelecimento}**")
    
    # Filtra os dados originais pelo estabelecimento selecionado
    df_filtrado = df[df['Estabelecimento'] == selected_estabelecimento].copy()

    # Processamento para Faltas
    faltas_df = df_filtrado[(df_filtrado['Ocorrencia'] == 'Falta') & (df_filtrado['Justificativa'] == 'Falta')]
    faltas_df = faltas_df[['Nome', 'Data']]
    faltas_df.columns = ['Nome do Funcionário', 'Data da Falta']
    faltas_df = faltas_df.sort_values(by=['Nome do Funcionário', 'Data da Falta']).reset_index(drop=True)
    faltas_df['Data da Falta'] = faltas_df['Data da Falta'].dt.strftime('%d/%m/%Y')
    
    # Processamento para Marcações Ímpares
    df_filtrado['is_impar'] = df_filtrado['Marcacoes'].apply(e_marcacoes_impar)
    df_filtrado['is_sem_marcacao'] = df_filtrado['Ocorrencia'].isin(['Sem marcação de entrada', 'Sem marcação de saída'])
    
    impares_df = df_filtrado[df_filtrado['is_impar'] | df_filtrado['is_sem_marcacao']]
    impares_df = impares_df[['Nome', 'Data']]
    impares_df.columns = ['Nome do Funcionário', 'Data da Marcação Ímpar']
    impares_df = impares_df.sort_values(by=['Nome do Funcionário', 'Data da Marcação Ímpar']).reset_index(drop=True)
    impares_df['Data da Marcação Ímpar'] = impares_df['Data da Marcação Ímpar'].dt.strftime('%d/%m/%Y')

    # Exibe os dois detalhes lado a lado
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

else:
    st.info("Use o menu acima para filtrar os nomes e datas por estabelecimento.")