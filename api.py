from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from main import carregar_treinos_apple_health
from parsers import parse_arquivo

app = FastAPI(title="Treino Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_treino(arquivo: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo.filename)[1]) as tmp:
        tmp.write(await arquivo.read())
        caminho = tmp.name
    
    if arquivo.filename.endswith('.xml'):
        treinos = carregar_treinos_apple_health(caminho)
    else:
        treinos = parse_arquivo(caminho)
    
    os.remove(caminho)
    
    return {"status": "ok", "arquivo": arquivo.filename, "quantidade": len(treinos), "treinos": treinos}
