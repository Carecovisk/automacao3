from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Any

app = FastAPI()

# 1. Monta a pasta 'static' para servir o HTML e scripts
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. Rota para acessar a página inicial
@app.get("/")
async def read_index():
    return FileResponse('static/html/home.html')

# 3. Rota API para receber os dados
# Aceita uma lista de listas (matriz) ou lista de objetos, dependendo de como o JS enviar
@app.post("/api/salvar-tabela")
async def receber_tabela(dados: List[List[Any]]):
    """
    Recebe o JSON já parseado pelo frontend.
    Exemplo de entrada: [ ["Nome", "Idade"], ["João", 30], ["Maria", 25] ]
    """
    print(f"Recebidas {len(dados)} linhas de dados.")
    
    # Exemplo: Imprimindo a primeira linha (cabeçalho) e a primeira linha de dados
    if dados:
        print("Cabeçalho:", dados[0])
    
    # AQUI VOCÊ COLOCA SUA LÓGICA (Salvar no banco, criar CSV, processar regras)
    
    return {"status": "sucesso", "mensagem": f"{len(dados)} linhas processadas com sucesso."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)