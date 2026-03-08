import uuid
import threading
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pandas as pd

from services.matching import run_matching_pipeline
from utils.config import load_config, save_config
from web.schemas import PastedData, ExcelData, TaskStatus, MatchResult, MatchedItem, ConfigSchema
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Global state for data and tasks
_pasted_df: pd.DataFrame | None = None
_excel_df: pd.DataFrame | None = None
_pasted_context: str | None = None
_pasted_description_column: str | None = None
_task_store: Dict[str, Dict[str, Any]] = {}
_task_lock = threading.Lock()
_last_task_id: str | None = None


def _update_task_status(task_id: str, **updates):
    """Thread-safe task status update. Accepts arbitrary keyword arguments (e.g. message='...') to store alongside the standard fields."""
    with _task_lock:
        if task_id in _task_store:
            _task_store[task_id].update(updates)


# Rota para acessar a página inicial
@router.get("/")
async def read_index(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "active_page": "home"})


@router.get("/results")
async def read_results():
    """Start background task to process matching and redirect to results page with task ID."""
    global _pasted_df, _excel_df, _pasted_context, _pasted_description_column
    
    # Validate data exists
    if _pasted_df is None or _excel_df is None:
        raise HTTPException(status_code=400, detail="Dados não carregados. Por favor, envie os dados colados e o arquivo Excel primeiro.")
    
    if _pasted_description_column is None or _pasted_description_column not in _pasted_df.columns:
        raise HTTPException(status_code=400, detail=f"Coluna de descrição inválida: {_pasted_description_column}")
    
    # Extract queries, documents and their associated values
    queries = _pasted_df[_pasted_description_column].tolist()
    documents = _excel_df['description'].tolist()
    values = _excel_df['mean_value'].tolist()
    context = _pasted_context or "product matching"
    
    # Create task
    task_id = str(uuid.uuid4())
    global _last_task_id
    _last_task_id = task_id
    with _task_lock:
        _task_store[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "context": context,
            "progress": 0,
            "total": len(queries),
            "percentage": 0.0,
            "results": None,
            "error": None,
            "stage": "initializing",
            "message": None,
        }
    
    # Start background thread
    thread = threading.Thread(
        target=run_matching_pipeline,
        args=(task_id, queries, documents, values, context, _update_task_status),
        daemon=True,
    )
    thread.start()
    
    # Redirect to results view with task ID
    return RedirectResponse(url=f"/results-view?taskId={task_id}", status_code=303)


@router.get("/results-view")
async def results_view(request: Request, taskId: Optional[str] = Query(default=None)):
    """Serve the results HTML page. If no taskId is given, redirect to the last task."""
    if not taskId:
        if _last_task_id is None:
            raise HTTPException(status_code=404, detail="Nenhuma tarefa encontrada.")
        return RedirectResponse(url=f"/results-view?taskId={_last_task_id}", status_code=302)
    return templates.TemplateResponse("results.html", {"request": request, "active_page": "results"})


@router.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Poll endpoint to check task progress and results."""
    with _task_lock:
        task = _task_store.get(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    return JSONResponse(content=task)


# Rota para acessar a página de upload
@router.get("/upload")
async def read_upload(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "active_page": "upload"})


# Rota para acessar a página de configurações
@router.get("/config")
async def read_config(request: Request):
    return templates.TemplateResponse("config.html", {"request": request, "active_page": "config"})


@router.get("/api/config")
async def get_config():
    """Return current config; mask gemini_api_key so the key is never sent to the browser."""
    cfg = load_config()
    data = {
        "use_llm": cfg.use_llm,
        "gemini_api_key": "***" if cfg.gemini_api_key else "",
        "use_llm_abbreviation_expansion": cfg.use_llm_abbreviation_expansion,
        "use_llm_judge": cfg.use_llm_judge,
        "high_confidence_threshold": cfg.high_confidence_threshold,
    }
    return JSONResponse(content=data)


@router.post("/api/config")
async def post_config(payload: ConfigSchema):
    """Persist config settings. If gemini_api_key equals '***', keep the stored key unchanged."""
    cfg = load_config()
    if payload.use_llm is not None:
        cfg.use_llm = payload.use_llm
    if payload.gemini_api_key is not None and payload.gemini_api_key != "***":
        cfg.gemini_api_key = payload.gemini_api_key
    if payload.use_llm_abbreviation_expansion is not None:
        cfg.use_llm_abbreviation_expansion = payload.use_llm_abbreviation_expansion
    if payload.use_llm_judge is not None:
        cfg.use_llm_judge = payload.use_llm_judge
    if payload.high_confidence_threshold is not None:
        cfg.high_confidence_threshold = payload.high_confidence_threshold
    save_config(cfg)
    return JSONResponse(content={"ok": True})


# Rota para confirmar e processar dados
@router.post("/api/confirm-data")
async def receive_pasted_data(payload: PastedData):
    """
    Recebe os dados extraídos e a descrição para processamento.
    """
    header = payload.data[0][:3] # Sempre tem tamanho fixo de 3 colunas
    body_data = payload.data[2:]
    global _pasted_df, _pasted_context, _pasted_description_column
    _pasted_df = pd.DataFrame(body_data, columns=header)
    _pasted_context = payload.description
    _pasted_description_column = payload.description_column
    
    return {
        "status": "success",
        "message": "Dados recebidos com sucesso",
        "rows_count": len(payload.data),
        "header": header
    }


# Rota para processar arquivo Excel
@router.post("/api/process-excel")
async def receive_excel_data(payload: ExcelData):
    """
    Recebe os dados do arquivo Excel com as colunas selecionadas.
    """
    # TODO: Adicionar lógica de processamento do Excel
    global _excel_df
    _excel_df = pd.DataFrame([row.model_dump() for row in payload.data])
    
    # Apply filter if provided
    if payload.filterText:
        initial_count = len(_excel_df)
        try:
            _excel_df = _excel_df[_excel_df["description"].str.contains(payload.filterText, case=False, na=False, regex=payload.isRegex)]
            filtered_count = len(_excel_df)
            filter_type = "regex" if payload.isRegex else "text"
            print(f"Filtered from {initial_count} to {filtered_count} rows based on {filter_type} filter: '{payload.filterText}'")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro no filtro: {str(e)}. Verifique se a expressão regular está correta.")
    
    _excel_df = (
        _excel_df
        .groupby("description", as_index=False)
        .agg(
            quantity=("quantity", "sum"),
            total_value=("value", "sum"),
        )
    )
    _excel_df["mean_value"] = _excel_df["total_value"] / _excel_df["quantity"]
    _excel_df = _excel_df.drop(columns=["total_value", "quantity"])
    _excel_df = _excel_df.dropna()

    return {
        "status": "success",
        "message": "Arquivo Excel processado com sucesso",
        "fileName": payload.fileName,
        "skipRows": payload.skipRows,
        "filterText": payload.filterText,
        "isRegex": payload.isRegex,
        "rows_count": len(payload.data),
        "filtered_rows_count": len(_excel_df),
        "columns": payload.columns,
        "sample_data": payload.data[:5] if len(payload.data) > 5 else payload.data
    }

