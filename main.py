import xml.etree.ElementTree as ET
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime


def carregar_treinos_apple_health(caminho_arquivo):
    tree = ET.parse(caminho_arquivo)
    root = tree.getroot()
    treinos = []

    for workout in root.findall('Workout'):
        data = workout.attrib['startDate']
        duracao = workout.attrib['duration']
        tipo = workout.attrib['workoutActivityType']
        calorias = None
        distancia = None

        for child in workout:
            if child.tag == 'WorkoutStatistics':
                tipo_estatistica = child.attrib.get('type')
                if tipo_estatistica == 'HKQuantityTypeIdentifierActiveEnergyBurned':
                    calorias = child.attrib.get('sum')
                elif tipo_estatistica == 'HKQuantityTypeIdentifierDistanceWalkingRunning':
                    distancia = child.attrib.get('sum')

        treino = {
            'data': data,
            'duracao': float(duracao) if duracao else 0.0,
            'tipo': tipo,
            'calorias': float(calorias) if calorias else None,
            'distancia': float(distancia) if distancia else None
        }
        treinos.append(treino)
    return treinos


def filtrar_por_ano(lista_de_treinos, ano):
    treinos_filtrados = []
    for treino in lista_de_treinos:
        if treino['data'].startswith(str(ano)):
            treinos_filtrados.append(treino)
    return treinos_filtrados


def resumo_por_tipo(lista_de_treinos):
    resultado = {}
    for treino in lista_de_treinos:
        tipo = treino['tipo']
        if tipo not in resultado:
            resultado[tipo] = {
                'quantidade': 0,
                'distancia_total': 0.0,
                'duracao_total': 0.0,
                'calorias_total': 0.0,
                'distancia_media': 0.0,
                'duracao_media': 0.0,
                'calorias_media': 0.0
            }
        resultado[tipo]['quantidade'] += 1
        resultado[tipo]['distancia_total'] += treino['distancia'] if treino['distancia'] else 0.0
        resultado[tipo]['duracao_total'] += treino['duracao']if treino['duracao'] else 0.0
        resultado[tipo]['calorias_total'] += treino['calorias'] if treino['calorias'] else 0.0

    for tipo, dados in resultado.items():
        qtd = dados['quantidade']
        dados['distancia_media'] = dados['distancia_total'] / qtd
        dados['duracao_media'] = dados['duracao_total'] / qtd
        dados['calorias_media'] = dados['calorias_total'] / qtd
    return resultado


def encontrar_recordes(lista_de_treinos):
    melhor_duracao_atual = 0
    melhor_distancia_atual = 0
    maior_caloria_atual = 0
    treino_recorde_distancia = {}
    treino_recorde_duracao = {}
    treino_recorde_calorias = {}

    for treino in lista_de_treinos:
        distancia = treino['distancia']
        duracao = treino['duracao']
        calorias = treino['calorias']

        if distancia is not None:
            distancia_atual = distancia
            if distancia_atual > melhor_distancia_atual:
                melhor_distancia_atual = distancia_atual
                treino_recorde_distancia = treino
        if duracao is not None:
            duracao_atual = duracao
            if duracao_atual > melhor_duracao_atual:
                melhor_duracao_atual = duracao_atual
                treino_recorde_duracao = treino
        if calorias is not None:
            calorias_atual = calorias
            if calorias_atual > maior_caloria_atual:
                maior_caloria_atual = calorias_atual
                treino_recorde_calorias = treino

    return {
        'maior_distancia': treino_recorde_distancia,
        'maior_duracao': treino_recorde_duracao,
        'mais_calorias': treino_recorde_calorias
    }
def distancia_por_semana(treinos):
    semanas = {}

    for treino in treinos:
        if treino['distancia'] is None or treino['distancia'] == 0:
            continue  # pula treinos sem distância

        data = datetime.strptime(treino['data'][:10], '%Y-%m-%d')
        numero_semana = data.isocalendar()[1]

        if numero_semana not in semanas:
            semanas[numero_semana] = 0

        semanas[numero_semana] += treino['distancia']

    return semanas

def projetar_evolucao(treinos, semanas_futuras=4):
    
    semanas_dict = distancia_por_semana(treinos)
    
    semanas_ordenadas = sorted(semanas_dict.items())
    x= [] #semanas
    y = []#distancia
    
    for semana,distancia in semanas_ordenadas:
        x.append(semana)
        y.append(distancia)    
    
    if len(x) < 2:
        return None
    
    x_np = np.array(x).reshape(-1,1)
    y_np = np.array(y)
    
    modelo = LinearRegression()
    modelo.fit(x_np,y_np)
    
    ultima_semana = max(x)
    proximas_semanas =list(range(ultima_semana +1,ultima_semana +1 +semanas_futuras))
    
    x_futuro = np.array(proximas_semanas).reshape(-1,1)
    y_futuro = modelo.predict(x_futuro)
    
    resultado = {}
    for semana, distancia in zip(proximas_semanas, y_futuro):
        resultado[int(semana)] = round(float(distancia), 2)
    
    return resultado

def filtrar_por_tipo (lista_de_treinos,tipo ):
    treinos_filtrados = []
    for treino in lista_de_treinos :
        if treino['tipo']== tipo:
            treinos_filtrados.append(treino)
    return treinos_filtrados

if __name__ == "__main__":
    dados = carregar_treinos_apple_health('apple_health_export/exportar.xml')
    treinos_2026 = filtrar_por_ano(dados, 2026)
    resumo = resumo_por_tipo(treinos_2026)
    recordes = encontrar_recordes(treinos_2026)

    print("Resumo:", resumo)
    print("Recordes:", recordes)
