from typing import Any, List, Dict

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()


class DataConfirmation(BaseModel):
    data: list
    description: str


class ExcelData(BaseModel):
    fileName: str
    skipRows: int
    columns: "ExcelColumns"
    columnIndices: "ExcelColumnIndices"
    data: List["ExcelRow"]


class ExcelColumns(BaseModel):
    description: str
    quantity: str
    value: str


class ExcelColumnIndices(BaseModel):
    description: int
    quantity: int
    value: int


class ExcelRow(BaseModel):
    description: str
    quantity: int
    value: float


# Rota para acessar a página inicial
@router.get("/")
async def read_index():
    return FileResponse("static/html/home.html")


# Rota para acessar a página de upload
@router.get("/upload")
async def read_upload():
    return FileResponse("static/html/upload.html")


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


# Rota para processar arquivo Excel
@router.post("/api/process-excel")
async def process_excel(payload: ExcelData):
    """
    Recebe os dados do arquivo Excel com as colunas selecionadas.
    """
    # TODO: Adicionar lógica de processamento do Excel
    return {
        "status": "success",
        "message": "Arquivo Excel processado com sucesso",
        "fileName": payload.fileName,
        "skipRows": payload.skipRows,
        "rows_count": len(payload.data),
        "columns": payload.columns,
        "sample_data": payload.data[:5] if len(payload.data) > 5 else payload.data
    }

