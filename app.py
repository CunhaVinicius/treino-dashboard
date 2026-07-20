import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
from main import (carregar_treinos_apple_health, filtrar_por_ano,
                  resumo_por_tipo, encontrar_recordes, distancia_por_semana,
                  projetar_evolucao, filtrar_por_tipo)

st.set_page_config(page_title="Treinos Dashboard", page_icon="🏃", layout="wide")
st.title('🏃 Dashboard de Treinos')

# ============================================================
# UPLOAD DE ARQUIVOS
# ============================================================
st.subheader('📤 Upload de Arquivos')

arquivos_upload = st.file_uploader(
    "Faça upload dos seus arquivos de treino",
    type=['fit', 'tcx', 'gpx', 'xml','csv','zip'],
    accept_multiple_files=True,
    help="Formatos aceitos: .fit (Garmin), .tcx (Nike/Strava), .gpx (GPS), .xml (Apple Health)"
)

if arquivos_upload:
    todos_treinos = []
    
    for arquivo in arquivos_upload:
        with open(f"temp_{arquivo.name}", "wb") as f:
            f.write(arquivo.getbuffer())
        
        # Se for ZIP, extrair e processar todos os arquivos dentro
        if arquivo.name.endswith('.zip'):
            import zipfile
            import tempfile
            
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(f"temp_{arquivo.name}", 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                
                # Procurar automaticamente por arquivos de treino
                for root, dirs, files in os.walk(tmpdir):
                    for file in files:
                        caminho_completo = os.path.join(root, file)
                        
                        if file.endswith('.xml'):
                            treinos_arquivo = carregar_treinos_apple_health(caminho_completo)
                        elif file.endswith('.gpx'):
                            from parsers import parse_gpx
                            treinos_arquivo = parse_gpx(caminho_completo)
                        elif file.endswith('.fit'):
                            from parsers import parse_fit
                            treinos_arquivo = parse_fit(caminho_completo)
                        elif file.endswith('.tcx'):
                            from parsers import parse_tcx
                            treinos_arquivo = parse_tcx(caminho_completo)
                        else:
                            continue
                        
                        if treinos_arquivo:
                            todos_treinos.extend(treinos_arquivo)
        
        # Se for XML individual
        elif arquivo.name.endswith('.xml'):
            treinos_arquivo = carregar_treinos_apple_health(f"temp_{arquivo.name}")
            if treinos_arquivo:
                todos_treinos.extend(treinos_arquivo)
        
        # Outros formatos
        else:
            from parsers import parse_arquivo
            treinos_arquivo = parse_arquivo(f"temp_{arquivo.name}")
            if treinos_arquivo:
                todos_treinos.extend(treinos_arquivo)
    
    dados = todos_treinos
    st.success(f"✅ {len(arquivos_upload)} arquivo(s) processados — {len(dados)} treinos carregados!")
else:
    st.info("👆 Faça upload de pelo menos um arquivo para começar.")
    st.stop()
st.caption(f"📁 {len(dados)} treinos disponíveis para análise")

st.subheader('🔎 Filtros')
ano_escolhido = st.selectbox('Escolha um ano:', [2023, 2024, 2025, 2026])
treinos = filtrar_por_ano(dados, ano_escolhido)

traducao_tipo = {
    'HKWorkoutActivityTypeRunning': 'Corrida',
    'HKWorkoutActivityTypeWalking': 'Caminhada',
    'HKWorkoutActivityTypeCycling': 'Ciclismo',
    'HKWorkoutActivityTypeTraditionalStrengthTraining': 'Musculação',
    'HKWorkoutActivityTypeFunctionalStrengthTraining': 'Treino Funcional'
}

traducao_recordes = {
    'maior_distancia': 'Recorde de Distância',
    'maior_duracao': 'Recorde de Tempo',
    'mais_calorias': 'Recorde de Calorias'
}

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

st.subheader('📊 Métricas')
col1, col2, col3 = st.columns(3)
col1.metric('Total de Treinos', len(treinos))
col2.metric('Distância Total (km)', round(soma_distancia, 2))
col3.metric('Total de Calorias', round(soma_calorias, 2))
st.divider()

st.subheader('🏃 Análise por Tipo de Atividade')
col_tabela, col_grafico = st.columns([1, 1])
with col_tabela:
    st.dataframe(tabela, width='stretch')
with col_grafico:
    dados_grafico = {k: v['distancia_total'] for k, v in resumo_traduzido.items()}
    st.bar_chart(dados_grafico)
st.divider()

st.subheader('📊 Projeção de Evolução - Corrida')
treinos_corrida = filtrar_por_tipo(treinos, 'HKWorkoutActivityTypeRunning')

if len(treinos_corrida) < 2:
    st.warning("⚠️ Poucos treinos de corrida para gerar projeção.")
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