import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
from main import (filtrar_por_ano, resumo_por_tipo, encontrar_recordes,
                  distancia_por_semana, projetar_evolucao, filtrar_por_tipo)
from importer import importar_treinos

st.set_page_config(page_title="Treinos Dashboard", page_icon="🏃", layout="wide")
st.title('🏃 Dashboard de Treinos')

# ============================================================
# UPLOAD UNIVERSAL
# ============================================================
st.subheader('📤 Upload de Arquivos')

arquivos_upload = st.file_uploader(
    "Faça upload dos seus arquivos de treino (qualquer formato)",
    type=['fit', 'tcx', 'gpx', 'xml', 'csv', 'zip', 'json'],
    accept_multiple_files=True,
    help="Arraste arquivos de qualquer app de saúde (Samsung, Apple, Garmin, Strava, etc.)"
)

if arquivos_upload:
    todos_treinos = []

    for arquivo in arquivos_upload:
        with open(f"temp_{arquivo.name}", "wb") as f:
            f.write(arquivo.getbuffer())

        treinos_arquivo = importar_treinos(f"temp_{arquivo.name}")
        if treinos_arquivo:
            todos_treinos.extend(treinos_arquivo)

    # -------------------------------------------------------
    # FILTRO DE REGISTROS INVÁLIDOS (resumos diários, etc.)
    # -------------------------------------------------------
    dados_filtrados = []
    for t in todos_treinos:
        distancia = t.get('distancia', 0) or 0
        duracao = t.get('duracao', 0) or 0

        if distancia > 0 or duracao > 0:
            if distancia == 0 and duracao < 1:
                continue
            dados_filtrados.append(t)

    dados = dados_filtrados
    st.success(f"✅ {len(arquivos_upload)} arquivo(s) processados — {len(dados)} treinos válidos carregados!")
else:
    st.info("👆 Faça upload de qualquer arquivo de saúde (ZIP, CSV, JSON, XML, GPX, FIT, TCX).")
    st.stop()

st.caption(f"📁 {len(dados)} treinos disponíveis para análise")

# ============================================================
# FILTROS E TRADUÇÕES (COM ANOS DINÂMICOS E DIAGNÓSTICO)
# ============================================================
st.subheader('🔎 Filtros')

# Extrair anos reais dos dados
anos_disponiveis = sorted({t['data'][:4] for t in dados if t.get('data')})
if not anos_disponiveis:
    st.warning("Nenhum treino com data encontrada nos arquivos enviados.")
    st.stop()

ano_escolhido = st.selectbox('Escolha um ano:', anos_disponiveis)
treinos = filtrar_por_ano(dados, ano_escolhido)

# Diagnóstico temporário: mostrar tipos únicos encontrados
tipos_unicos = {t.get('tipo', 'N/A') for t in treinos}
st.info(f"🔍 Tipos de atividade encontrados no ano selecionado: {tipos_unicos}")

# Dicionário de tradução atualizado (pode ser ajustado conforme diagnóstico)
traducao_tipo = {
    'running': 'Corrida',
    'walking': 'Caminhada',
    'cycling': 'Ciclismo',
    'hiking': 'Caminhada',
    'run': 'Corrida',
    'walk': 'Caminhada',
    'bike': 'Ciclismo',
    'swim': 'Natação',
    'weight_training': 'Musculação',
    'strength_training': 'Musculação',
    'functional_training': 'Treino Funcional',
    'yoga': 'Yoga',
    'other': 'Outro',
    '1001': 'Corrida',
    '1002': 'Caminhada',
    '2001': 'Ciclismo',
    '15002': 'Corrida',
    '15003': 'Caminhada',
    '15005': 'Corrida',
}

traducao_recordes = {
    'maior_distancia': 'Recorde de Distância',
    'maior_duracao': 'Recorde de Tempo',
    'mais_calorias': 'Recorde de Calorias'
}

# ============================================================
# PROCESSAMENTO DOS DADOS
# ============================================================
resumo_treinos = resumo_por_tipo(treinos)

soma_distancia = sum(d['distancia_total'] for d in resumo_treinos.values())
soma_calorias = sum(d['calorias_total'] for d in resumo_treinos.values())

resumo_traduzido = {traducao_tipo.get(k, k): v for k, v in resumo_treinos.items()}

recorde = encontrar_recordes(treinos)
recorde_traduzido = {traducao_recordes.get(k, k): v for k, v in recorde.items()}

tabela = pd.DataFrame.from_dict(resumo_traduzido, orient='index')
tabela_recordes = pd.DataFrame.from_dict(recorde_traduzido, orient='index')
tabela_recordes.rename(columns={
    'data': 'Data', 'duracao': 'Duração (min)', 'tipo': 'Atividade',
    'calorias': 'Calorias', 'distancia': 'Distância (km)'
}, inplace=True)
tabela_recordes = tabela_recordes.astype(str)

# ============================================================
# MÉTRICAS PRINCIPAIS
# ============================================================
st.subheader('📊 Métricas')
col1, col2, col3 = st.columns(3)
col1.metric('Total de Treinos', len(treinos))
col2.metric('Distância Total (km)', round(soma_distancia, 2))
col3.metric('Total de Calorias', round(soma_calorias, 2))
st.divider()

# ============================================================
# ANÁLISE POR TIPO DE ATIVIDADE
# ============================================================
st.subheader('🏃 Análise por Tipo de Atividade')
col_tabela, col_grafico = st.columns([1, 1])
with col_tabela:
    st.dataframe(tabela, width='stretch')
with col_grafico:
    dados_grafico = {k: v['distancia_total'] for k, v in resumo_traduzido.items()}
    st.bar_chart(dados_grafico)
st.divider()

# ============================================================
# PROJEÇÃO DE EVOLUÇÃO - CORRIDA (usando o tipo correto 'running')
# ============================================================
st.subheader('📊 Projeção de Evolução - Corrida')
treinos_corrida = filtrar_por_tipo(treinos, 'running')

if len(treinos_corrida) < 2:
    st.warning("⚠️ Poucos treinos de corrida para gerar projeção. Verifique se há treinos do tipo 'running' nos dados.")
else:
    dados_real = distancia_por_semana(treinos_corrida)
    dados_projecao = projetar_evolucao(treinos_corrida)

    if dados_projecao is None or len(dados_projecao) < 2:
        st.warning("⚠️ Dados insuficientes para projetar evolução.")
    else:
        semanas_reais = list(dados_real.keys())
        distancias_reais = list(dados_real.values())
        semanas_projecao = list(dados_projecao.keys())
        distancias_projecao = list(dados_projecao.values())

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(semanas_reais, distancias_reais, 'b-o', label='Real', linewidth=2, markersize=6)
        ax.plot(semanas_projecao, distancias_projecao, '--o', color='orange', label='Projeção', linewidth=2, markersize=6)
        if semanas_reais and semanas_projecao:
            ax.axvline(x=max(semanas_reais), color='gray', linestyle=':', alpha=0.7, label='Hoje')
        ax.set_xlabel('Semana do Ano')
        ax.set_ylabel('Distância (km)')
        ax.set_title('Evolução da Distância Semanal - Corrida')
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

        if len(distancias_projecao) >= 2:
            primeiro = distancias_projecao[0]
            ultimo = distancias_projecao[-1]
            variacao = ((ultimo - primeiro) / primeiro) * 100

            if variacao > 5:
                st.markdown(f"📈 **Variação: {variacao:.1f}%** — Seus treinos estão crescendo. Continue assim!")
            elif variacao < -5:
                st.markdown(f"📉 **Variação: {variacao:.1f}%** — Seu volume está caindo. Considere revisar seu plano de treinos.")
            else:
                st.markdown(f"➡️ **Variação: {variacao:.1f}%** — Seus treinos estão estáveis. Que tal aumentar o desafio?")
            
            st.caption(f"Projeção: de {primeiro:.1f} km para {ultimo:.1f} km em 4 semanas")

st.divider()
st.subheader('🏆 Recordes')
st.dataframe(tabela_recordes, width='stretch')