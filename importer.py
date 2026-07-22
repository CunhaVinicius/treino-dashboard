import csv
import json
import os
import zipfile
import tempfile
from datetime import datetime
import xml.etree.ElementTree as ET

# ============================================================
# MAPEAMENTO SEMÂNTICO UNIVERSAL
# ============================================================
CAMPOS_DATA = [
    "start_time", "start_date", "startdate", "date_start", "begin_time",
    "end_time", "end_date", "enddate", "date_end", "time", "date"
]
CAMPOS_DISTANCIA = [
    "distance", "distancia", "total_distance", "distance_km", "km", "dist"
]
CAMPOS_DURACAO = [
    "duration", "duracao", "duration_sec", "duration_seconds", "elapsed_time",
    "timer_time", "total_timer_time", "moving_time"
]
CAMPOS_CALORIAS = [
    "calories", "calorie", "calorias", "energy", "kcal", "active_energy"
]
CAMPOS_TIPO = [
    "activity", "activity_type", "sport", "sport_type", "workout_type",
    "exercise_type", "type", "workoutactivitytype"
]

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def _extrair_arquivos(caminho_zip):
    """Extrai um ZIP e retorna lista de caminhos de arquivos"""
    arquivos = []
    tmpdir = tempfile.mkdtemp()
    with zipfile.ZipFile(caminho_zip, 'r') as zf:
        zf.extractall(tmpdir)
    for root, _, files in os.walk(tmpdir):
        for f in files:
            arquivos.append(os.path.join(root, f))
    return arquivos


def _normalizar_nome(nome):
    """Remove caracteres especiais e coloca em minúsculas"""
    return nome.strip().lower().replace(" ", "_").replace("-", "_")


def _encontrar_coluna(colunas, candidatos):
    """Procura por uma coluna que corresponda a qualquer candidato"""
    for col in colunas:
        col_norm = _normalizar_nome(col)
        for cand in candidatos:
            if cand in col_norm or col_norm in cand:
                return col
    return None


def _converter_valor(valor, tipo="float"):
    """Converte string para número, tratando vírgulas e None"""
    if valor is None or valor == "":
        return None
    try:
        if isinstance(valor, str):
            valor = valor.replace(",", ".")
        if tipo == "float":
            return float(valor)
        elif tipo == "int":
            return int(float(valor))
    except (ValueError, TypeError):
        return None
    return valor


def _parse_data(valor):
    """Converte qualquer formato de data para string ISO"""
    if not valor:
        return None

    # Se for número (timestamp Unix)
    if isinstance(valor, (int, float)):
        try:
            if valor > 1e10:          # milissegundos
                valor = valor / 1000
            return datetime.fromtimestamp(valor).strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass

    # Tentar strings com formatos conhecidos
    formatos = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y %H:%M:%S",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(str(valor)[:19], fmt).strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    return str(valor)[:19]


# ============================================================
# INSPETOR DE ARQUIVO
# ============================================================
def inspecionar_arquivo(caminho):
    """
    Analisa qualquer arquivo e retorna:
    - formato detectado
    - colunas/chaves encontradas
    - registros brutos
    """
    ext = os.path.splitext(caminho)[1].lower()
    resultado = {"formato": ext, "colunas": [], "registros": [], "erro": None}
    
    try:
        if ext == ".csv":
            with open(caminho, "r", encoding="utf-8-sig") as f:
                leitor = csv.reader(f)
                cabecalho = next(leitor, [])
                resultado["colunas"] = [c.strip() for c in cabecalho]
                resultado["registros"] = list(leitor)
        
        elif ext == ".json":
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                resultado["registros"] = dados
                if dados:
                    resultado["colunas"] = list(dados[0].keys())
            elif isinstance(dados, dict):
                resultado["registros"] = [dados]
                resultado["colunas"] = list(dados.keys())
        
        elif ext == ".xml":
            tree = ET.parse(caminho)
            root = tree.getroot()
            elementos = []
            for elem in root.iter():
                if elem.attrib:
                    elementos.append(elem.attrib)
            resultado["registros"] = elementos
            if elementos:
                resultado["colunas"] = list(elementos[0].keys())
        
        elif ext == ".gpx":
            import gpxpy
            with open(caminho, "r") as f:
                gpx = gpxpy.parse(f)
            pontos = []
            for track in gpx.tracks:
                for seg in track.segments:
                    for pt in seg.points:
                        pontos.append({
                            "latitude": pt.latitude,
                            "longitude": pt.longitude,
                            "elevation": pt.elevation,
                            "time": pt.time.isoformat() if pt.time else None
                        })
            resultado["registros"] = pontos
            if pontos:
                resultado["colunas"] = list(pontos[0].keys())
            resultado["formato"] = "gpx"
        
        elif ext == ".fit":
            from fitparse import FitFile
            fit = FitFile(caminho)
            registros = []
            for record in fit.get_messages("session"):
                reg = {}
                for field in record.fields:
                    reg[field.name] = field.value
                registros.append(reg)
            resultado["registros"] = registros
            if registros:
                resultado["colunas"] = list(registros[0].keys())
            resultado["formato"] = "fit"
        
        elif ext == ".tcx":
            from tcxparser import TCXParser
            tcx = TCXParser(caminho)
            reg = {
                "start_time": str(tcx.started_at),
                "distance": tcx.distance,
                "duration": tcx.duration,
                "calories": tcx.calories,
                "activity_type": tcx.activity_type,
            }
            resultado["registros"] = [reg]
            resultado["colunas"] = list(reg.keys())
            resultado["formato"] = "tcx"
    
    except Exception as e:
        resultado["erro"] = str(e)
    
    return resultado


# ============================================================
# MAPEADOR SEMÂNTICO + NORMALIZADOR (COM CONVERSÃO DE UNIDADES)
# ============================================================
def importar_treinos(caminho_arquivo):
    """
    Função universal: recebe qualquer arquivo e retorna lista de treinos padronizados.
    Aceita: .csv, .json, .xml, .gpx, .tcx, .fit, .zip (procura dentro)
    """
    if caminho_arquivo.endswith(".zip"):
        todos_treinos = []
        arquivos = _extrair_arquivos(caminho_arquivo)
        for arq in arquivos:
            treinos = importar_treinos(arq)
            todos_treinos.extend(treinos)
        return todos_treinos
    
    info = inspecionar_arquivo(caminho_arquivo)
    if not info["colunas"]:
        return []
    
    colunas = info["colunas"]
    
    col_data_inicio = _encontrar_coluna(colunas, CAMPOS_DATA)
    col_distancia = _encontrar_coluna(colunas, CAMPOS_DISTANCIA)
    col_duracao = _encontrar_coluna(colunas, CAMPOS_DURACAO)
    col_calorias = _encontrar_coluna(colunas, CAMPOS_CALORIAS)
    col_tipo = _encontrar_coluna(colunas, CAMPOS_TIPO)
    
    treinos = []
    for reg in info["registros"]:
        # Se for CSV, transformar linha em dicionário
        if isinstance(reg, (list, tuple)):
            reg_dict = {}
            for i, val in enumerate(reg):
                if i < len(colunas):
                    reg_dict[colunas[i]] = val
            reg = reg_dict
        
        if not isinstance(reg, dict):
            continue
        
        # Data
        data_inicio = _parse_data(reg.get(col_data_inicio)) if col_data_inicio else None
        if not data_inicio:
            continue
        
        # Distância (assumir metros, converter para km)
        distancia = _converter_valor(reg.get(col_distancia)) if col_distancia else None
        if distancia is not None and distancia > 0:
            if distancia > 100:   # mais de 100 km em um treino → está em metros
                distancia = distancia / 1000
        
        # Duração (assumir segundos ou milissegundos, converter para minutos)
        duracao = _converter_valor(reg.get(col_duracao)) if col_duracao else None
        if duracao is not None and duracao > 0:
            if duracao > 86400:           # mais de 1 dia em segundos → milissegundos
                duracao = duracao / 60000 # ms → min
            else:
                duracao = duracao / 60    # s → min
        
        # Calorias e tipo
        calorias = _converter_valor(reg.get(col_calorias)) if col_calorias else None
        tipo = str(reg.get(col_tipo, "")).lower() if col_tipo else "other"
        
        # Só adiciona se tiver distância ou duração
        if (distancia and distancia > 0) or (duracao and duracao > 0):
            treino = {
                "data": data_inicio,
                "duracao": duracao if duracao else 0,
                "tipo": tipo,
                "calorias": calorias,
                "distancia": distancia if distancia else 0,
            }
            treinos.append(treino)
    
    return treinos