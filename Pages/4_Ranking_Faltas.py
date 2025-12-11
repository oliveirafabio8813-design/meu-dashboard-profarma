# Arquivo: pages/4_Ranking_Faltas.py

import streamlit as st
import pandas as pd
import plotly.express as px

# 🚨 IMPORTANTE: No ambiente real com Multi-Page, você teria que
# carregar os dados aqui ou de um arquivo de utilitário compartilhado.
# Para este exemplo, usaremos as variáveis globais df_ocorrencias e 
# as constantes de cor que assumimos estarem definidas no módulo principal.

# Se você não puder acessar as variáveis globais, precisará copiar/importar:
# from Dashboard_Ocorrencias import load_data, COR_PRINCIPAL_VERDE, COR_ALERTA_VERMELHO
# df_ocorrencias, _ = load_data()


# ----------------------------------------------------------------------
# ⚠️ ADAPTAÇÃO: Se você está rodando tudo em um único arquivo temporariamente, 
# COPIE e COLE a função `page_ranking_faltas()` no final do seu script.
# Para que funcione, o código deve usar as variáveis globais já carregadas 
# (df_ocorrencias, COR_ALERTA_VERMELHO)
# ----------------------------------------------------------------------

# Definições de constantes (se não vierem do módulo principal)
try:
    COR_ALERTA_VERMELHO = st.session_state.get('COR_ALERTA_VERMELHO', "#dc3545")
except:
    # Se estiver rodando como script único, defina-as
    COR_ALERTA_VERMELHO = "#dc3545"

def page_ranking_faltas(df_ocorrencias):
    st.title("🏆 Ranking de Faltas Não Justificadas por Colaborador")
    st.markdown('---')
    
    # --- 1. Filtrar e Agrupar os Dados ---
    
    # O filtro 'is_falta_nao_justificada' já foi calculado no script principal:
    # is_falta_nao_justificada = (Ocorrencia == 'Falta' AND Justificativa == 'Falta')
    
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

    # Exibe a tabela completa (ou o top 100 para evitar sobrecarga)
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
            color_continuous_scale=px.colors.sequential.Reds,
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
# ⚠️ SE VOCÊ ESTIVER RODANDO EM UM ÚNICO ARQUIVO, adicione a chamada no 
# FINAL do seu script principal (após o bloco '4. Gráficos de Pagamentos e Descontos')
# ----------------------------------------------------------------------
# page_ranking_faltas(df_ocorrencias)
