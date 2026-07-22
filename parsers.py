# parsers.py - Parsers para diferentes formatos de arquivo de treino
from fitparse import FitFile
from tcxparser import TCXParser
import gpxpy
from datetime import datetime
import os
import csv
from datetime import datetime
import json

def parse_fit(caminho_arquivo):
    """Parser para arquivos .fit (Garmin e outros smartwatches)"""
    treinos = []
    fitfile = FitFile(caminho_arquivo)
    
    for record in fitfile.get_messages('session'):
        data = record.get_value('start_time')
        duracao = record.get_value('total_timer_time')
        tipo = record.get_value('sport')
        calorias = record.get_value('total_calories')
        distancia = record.get_value('total_distance')
        
        if duracao:
            duracao = duracao / 60
        if distancia:
            distancia = distancia / 1000
        if data:
            data = data.strftime('%Y-%m-%d %H:%M:%S')
        
        treino = {
            'data': str(data) if data else None,
            'duracao': duracao,
            'tipo': tipo,
            'calorias': calorias,
            'distancia': distancia
        }
        treinos.append(treino)
    
    return treinos


def parse_tcx(caminho_arquivo):
    """Parser para arquivos .tcx (Nike, Strava, Polar, Garmin antigo)"""
    treinos = []
    
    try:
        tcx = TCXParser(caminho_arquivo)
        
        data = tcx.started_at
        duracao = tcx.duration
        distancia = tcx.distance
        calorias = tcx.calories
        tipo = tcx.activity_type
        
        if duracao:
            duracao = duracao / 60
        if distancia:
            distancia = distancia / 1000
        if data:
            data = data.strftime('%Y-%m-%d %H:%M:%S') if hasattr(data, 'strftime') else str(data)
        
        treino = {
            'data': str(data) if data else None,
            'duracao': duracao,
            'tipo': tipo,
            'calorias': calorias,
            'distancia': distancia
        }
        treinos.append(treino)
    
    except Exception:
        pass
    
    return treinos


def parse_gpx(caminho_arquivo):
    """Parser para arquivos .gpx (GPS genérico e Samsung Health)"""
    treinos = []
    
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
        
        for track in gpx.tracks:
            for segment in track.segments:
                if len(segment.points) < 2:
                    continue
                
                # Agrupar pontos por treino (quebra > 30 min = novo treino)
                treinos_segmento = []
                treino_atual = []
                
                for i, point in enumerate(segment.points):
                    if i == 0:
                        treino_atual.append(point)
                    else:
                        # Verificar intervalo de tempo
                        tempo_anterior = segment.points[i-1].time
                        tempo_atual = point.time
                        
                        if tempo_anterior and tempo_atual:
                            intervalo = (tempo_atual - tempo_anterior).total_seconds() / 60
                        else:
                            intervalo = 0
                        
                        # Se intervalo > 30 minutos, novo treino
                        if intervalo > 30:
                            treinos_segmento.append(treino_atual)
                            treino_atual = [point]
                        else:
                            treino_atual.append(point)
                
                # Adicionar último treino
                if treino_atual:
                    treinos_segmento.append(treino_atual)
                
                # Criar dicionário para cada treino
                for pontos in treinos_segmento:
                    if len(pontos) < 2:
                        continue
                    
                    inicio = pontos[0].time
                    fim = pontos[-1].time
                    
                    duracao = (fim - inicio).total_seconds() / 60 if inicio and fim else 0
                    
                    # Calcular distância para este grupo de pontos
                    from gpxpy.gpx import GPXTrackSegment
                    segmento_temp = GPXTrackSegment(pontos)
                    distancia = segmento_temp.length_3d() / 1000
                    
                    tipo = 'running'  # padrão
                    
                    treino = {
                        'data': inicio.strftime('%Y-%m-%d %H:%M:%S') if inicio else None,
                        'duracao': duracao,
                        'tipo': tipo,
                        'calorias': None,
                        'distancia': distancia
                    }
                    treinos.append(treino)
    
    except Exception as e:
        print(f"Aviso: erro ao processar GPX - {e}")
    
    return treinos
# Mapeamento de códigos de exercício da Samsung para nomes
MAPA_TIPOS_SAMSUNG = {
    '1001': 'running',
    '1002': 'walking',
    '2001': 'cycling',
    '15002': 'running',      # Treadmill running
    '15003': 'walking',      # Treadmill walking
    '0': 'other',
}


def parse_samsung_csv(caminho_arquivo):
    """Parser para arquivo CSV exportado do Samsung Health (com.samsung.health.exercise)"""
    treinos = []
    
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            # A primeira linha é o cabeçalho com muitos campos
            cabecalho = f.readline().strip()
            
            # Pular a segunda linha (metadados)
            f.readline()
            
            # Ler as linhas de dados
            reader = csv.reader(f)
            
            for linha in reader:
                if not linha or len(linha) < 2:
                    continue
                
                try:
                    # Extrair campos relevantes
                    start_time = linha[14].strip()  # com.samsung.health.exercise.start_time
                    end_time = linha[77].strip()    # com.samsung.health.exercise.end_time
                    duration_ms = linha[13].strip() # com.samsung.health.exercise.duration
                    distance = linha[43].strip()    # com.samsung.health.exercise.distance
                    calories = linha[46].strip()    # com.samsung.health.exercise.calorie
                    tipo_codigo = linha[16].strip() # com.samsung.health.exercise.exercise_type
                    
                    if not start_time or not end_time:
                        continue
                    
                    # Converter data
                    try:
                        data = datetime.strptime(start_time[:19], '%Y-%m-%d %H:%M:%S')
                        data_str = data.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        continue
                    
                    # Converter duração (milissegundos → minutos)
                    duracao = float(duration_ms) / 60000 if duration_ms else 0
                    
                    # Converter distância (metros → km)
                    distancia = float(distance) / 1000 if distance else 0
                    
                    # Calorias
                    calorias = float(calories) if calories else None
                    
                    # Traduzir tipo
                    tipo = MAPA_TIPOS_SAMSUNG.get(tipo_codigo, 'other')
                    
                    # Pular treinos muito curtos (< 1 minuto)
                    if duracao < 1:
                        continue
                    
                    treino = {
                        'data': data_str,
                        'duracao': duracao,
                        'tipo': tipo,
                        'calorias': calorias,
                        'distancia': distancia
                    }
                    treinos.append(treino)
                    
                except (ValueError, IndexError):
                    continue
    
    except Exception as e:
        print(f"Aviso: erro ao processar CSV Samsung - {e}")
    
    return treinos


def parse_arquivo(caminho_arquivo):
    """Parser universal"""
    nome = os.path.basename(caminho_arquivo).lower()
    
    if nome.endswith('.fit'):
        return parse_fit(caminho_arquivo)
    elif nome.endswith('.tcx'):
        return parse_tcx(caminho_arquivo)
    elif nome.endswith('.gpx'):
        return parse_gpx(caminho_arquivo)
    elif 'samsung' in nome and '.csv' in nome:
        return parse_samsung_csv(caminho_arquivo)
    else:
        raise ValueError(f"Formato não suportado: {caminho_arquivo}")
    
def parse_samsung_json(caminho_arquivo):
    """Parser para arquivos JSON de exercício do Samsung Health"""
    treinos = []
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # A estrutura pode variar; tentamos extrair os campos comuns
        start = data.get('start_time')
        end = data.get('end_time')
        distance = data.get('distance')  # em metros
        calories = data.get('calorie')
        duration_sec = data.get('duration')
        exercise_type = data.get('exercise_type')
        
        if not start or not end:
            return treinos
        
        # Converter duração para minutos
        if duration_sec:
            duracao = duration_sec / 60
        else:
            # Calcular pela diferença de tempo
            from datetime import datetime
            try:
                s = datetime.fromisoformat(start)
                e = datetime.fromisoformat(end)
                duracao = (e - s).total_seconds() / 60
            except:
                duracao = 0
        
        # Distância para km
        distancia = distance / 1000 if distance else 0
        
        # Mapear tipo
        tipo = str(exercise_type) if exercise_type else 'other'
        
        treino = {
            'data': start[:19] if start else None,
            'duracao': duracao,
            'tipo': tipo,
            'calorias': calories,
            'distancia': distancia
        }
        treinos.append(treino)
    
    except Exception:
        pass
    
    return treinos