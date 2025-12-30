import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

st.set_page_config(layout="wide", page_title="Dashboard Profarma")

# --- CONFIGURAÇÃO DE ACESSO ---
# Verifique se este link abre o download automático do arquivo no seu navegador
URL_EXCEL = "https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/Relatorio_OcorrenciasNoPonto.xlsx"
NOME_ABA_ESPERADO = "OcorrênciasnoPonto" 

@st.cache_data(ttl=30)
def carregar_dados_seguro():
    try:
        response = requests.get(URL_EXCEL, timeout=30)
        response.raise_for_status()
        
        # Abrir o arquivo para validar as abas existentes
        excel_file = pd.ExcelFile(io.BytesIO(response.content))
        abas_reais = excel_file.sheet_names
        
        # Se a aba esperada não estiver lá, tenta pegar a primeira aba disponível
        aba_para_usar = NOME_ABA_ESPERADO if NOME_ABA_ESPERADO in abas_reais else abas_reais[0]
        
        df = excel_file.parse(aba_para_usar)
        
        # Limpeza de colunas
        df.columns = [str(c).strip() for c in df.columns]
        
        # Diagnóstico para o usuário (ajuda a debugar se não funcionar)
        return df, abas_reais, aba_para_usar
    except Exception as e:
        st.error(f"Erro ao conectar com o GitHub: {e}")
        return pd.DataFrame(), [], ""

df_raw, lista_abas, aba_detectada = carregar_dados_seguro()

# --- TÍTULO ---
st.title("📊 Verificação de Ocorrências Diárias")

# Painel de Ajuda (Só aparece se houver erro ou para conferência)
with st.expander("🔍 Diagnóstico de Conexão (Clique aqui se o gráfico não aparecer)"):
    st.write(f"**Abas encontradas no arquivo:** {lista_abas}")
    st.write(f"**Aba sendo lida agora:** {aba_detectada}")
    if not df_raw.empty:
        st.write(f"**Colunas detectadas:** {list(df_raw.columns)}")

if not df_raw.empty:
    # Processamento de Dados (Normalização Forçada)
    df_raw['Data'] = pd.to_datetime(df_raw['Data'], errors='coerce')
    
    def check_falta(row):
        oc = str(row.get('Ocorrencia', '')).strip().lower()
        ju = str(row.get('Justificativa', '')).strip().lower()
        return 1 if (oc == 'falta' and ju == 'falta') else 0

    def check_impar(row):
        oc = str(row.get('Ocorrencia', '')).strip().lower()
        ju = str(row.get('Justificativa', '')).strip().lower()
        # Busca por termos parciais para ser mais flexível
        if 'sem marcação' in oc or ju == 'falta de marcação':
            return 1
        return 0

    df_raw['is_falta'] = df_raw.apply(check_falta, axis=1)
    df_raw['is_impar'] = df_raw.apply(check_impar, axis=1)

    # Gráfico Diário
    df_grafico = df_raw.dropna(subset=['Data']).groupby('Data').agg(
        Faltas=('is_falta', 'sum'),
        Impares=('is_impar', 'sum')
    ).reset_index()

    if not df_grafico.empty and (df_grafico['Faltas'].sum() + df_grafico['Impares'].sum() > 0):
        df_grafico = df_grafico.sort_values('Data')
        df_grafico['Dia'] = df_grafico['Data'].dt.strftime('%d/%m/%Y')

        fig = px.bar(
            df_grafico, x='Dia', y=['Faltas', 'Impares'],
            barmode='group',
            text_auto=True,
            title="Comparativo: Faltas vs Marcações Ímpares",
            color_discrete_map={'Faltas': '#E74C3C', 'Impares': '#3498DB'},
            template='plotly_white'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ O arquivo foi lido, mas nenhuma linha atende aos critérios: (Ocorrência=Falta + Justificativa=Falta) ou (Sem Marcação).")
        st.info("Dica: Verifique na tabela abaixo se os nomes das colunas e os textos estão escritos como o esperado.")

    # Tabela de Conferência
    st.markdown("---")
    st.subheader("Amostra dos Dados")
    st.dataframe(df_raw[['Estabelecimento', 'Data', 'Ocorrencia', 'Justificativa']].head(20))

