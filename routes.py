from typing import Any, List

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()


class DataConfirmation(BaseModel):
    data: list
    description: str


# Rota para acessar a página inicial
@router.get("/")
async def read_index():
    return FileResponse("static/html/home.html")


# Rota para confirmar e processar dados
@router.post("/api/confirm-data")
async def confirm_data(payload: DataConfirmation):
    """
    Recebe os dados extraídos e a descrição para processamento.
    """
    # TODO: Adicionar lógica de processamento dos dados
    header = payload.data[0][:-1] + payload.data[1][4:]
    return {
        "status": "success",
        "message": "Dados recebidos com sucesso",
        "rows_count": len(payload.data),
        "header": header
    }

