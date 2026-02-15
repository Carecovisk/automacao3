from typing import Any, List

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


# Rota para acessar a página inicial
@router.get("/")
async def read_index():
    return FileResponse("static/html/home.html")


# Rota API para receber os dados
# Aceita uma lista de listas (matriz) ou lista de objetos, dependendo de como o JS enviar
@router.post("/api/salvar-tabela")
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

    return {
        "status": "sucesso",
        "mensagem": f"{len(dados)} linhas processadas com sucesso.",
    }
