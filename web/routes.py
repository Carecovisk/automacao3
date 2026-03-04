import uuid
import threading
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
import pandas as pd
from slugify import slugify

from web.schemas import PastedData, ExcelData, TaskStatus, MatchResult, MatchedItem
from main import process_queries

router = APIRouter()

# Global state for data and tasks
_pasted_df: pd.DataFrame | None = None
_excel_df: pd.DataFrame | None = None
_pasted_context: str | None = None
_pasted_description_column: str | None = None
_task_store: Dict[str, Dict[str, Any]] = {}
_task_lock = threading.Lock()


def _update_task_status(task_id: str, **updates):
    """Thread-safe task status update."""
    with _task_lock:
        if task_id in _task_store:
            _task_store[task_id].update(updates)


def _insert_documents_in_batches(db, processed_documents: list[str], batch_size: int = 1000):
    """Insert documents into ChromaDB in batches to avoid memory issues with large datasets."""
    import hashlib
    
    total_docs = len(processed_documents)
    for i in range(0, total_docs, batch_size):
        batch_docs = processed_documents[i:i + batch_size]
        batch_ids = [hashlib.md5(doc.encode()).hexdigest() for doc in batch_docs]
        db.upsert(
            documents=batch_docs,
            ids=batch_ids,
        )
        print(f"Inserted batch {i // batch_size + 1}/{(total_docs + batch_size - 1) // batch_size} ({len(batch_docs)} documents)")


def _process_matching_task(task_id: str, queries: list[str], documents: list[str], context: str):
    """Background task to process query matching with progress tracking."""
    try:
        _update_task_status(task_id, status="running", progress=0, total=len(queries))
        
        # Import dependencies
        from utils.reranker import rerank_items, filter_items_by_score, filter_items_by_score_gap
        from utils.embeddings import emb_fn_bge_m3
        from utils.preprocesssing import apply_replacements, get_replacements_from_llm
        from utils.ai import PesquisaPrompt
        from main import split_queries_by_confidence
        import chromadb
        import hashlib
        from pathlib import Path
        
        # Define progress callback
        def progress_callback(current: int, total: int):
            _update_task_status(task_id, progress=current, total=total, percentage=round((current / total) * 100, 2))
        
        # Run the processing pipeline (simplified version of process_queries with progress tracking)
        _update_task_status(task_id, status="running", stage="preprocessing")
        
        # Get replacements from LLM and apply them
        replacements = get_replacements_from_llm(documents, context=context)
        processed_documents = apply_replacements(documents, replacements)
        
        _update_task_status(task_id, stage="creating_db")
        
        # Set up the DB
        OUTPUT_PATH = Path("./data/output")
        OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
        
        chroma_client = chromadb.PersistentClient(path=str(OUTPUT_PATH / "chromadb_storage"))
        db = chroma_client.get_or_create_collection(
            name=slugify(context), embedding_function=emb_fn_bge_m3  # type: ignore
        )
        
        # Insert documents in batches
        _insert_documents_in_batches(db, processed_documents)
        
        _update_task_status(task_id, stage="querying_db")
        
        # Query relevant results
        results = db.query(query_texts=queries, n_results=5)
        docs = results.get("documents") or []
        distances = results.get("distances") or []
        
        relevant_results = []
        for doc_list, dist_list in zip(docs, distances):
            items = [
                PesquisaPrompt.Item(description=doc, distance=dist, score=0.0)
                for doc, dist in zip(doc_list, dist_list)
                if dist <= 0.955
            ]
            relevant_results.append(items)
        
        if not relevant_results:
            raise ValueError("Nenhum documento relevante encontrado para as descrições fornecidas.")
        
        _update_task_status(task_id, stage="reranking")
        
        # Rerank with progress tracking
        reranked = rerank_items(queries, relevant_results, progress_callback=progress_callback)
        relevant_results = filter_items_by_score(reranked, threshold=0.8)
        relevant_results = filter_items_by_score_gap(relevant_results, gap_threshold=0.1)
        
        # Split by confidence
        low_confidence, high_confidence = split_queries_by_confidence(queries, relevant_results)
        
        # Format results
        high_conf_queries, high_conf_results = high_confidence
        match_results = [
            MatchResult(
                query=query,
                matched_items=[
                    MatchedItem(description=item.description, distance=item.distance, score=item.score)
                    for item in items
                ]
            )
            for query, items in zip(high_conf_queries, high_conf_results)
        ]
        
        _update_task_status(
            task_id, 
            status="completed", 
            progress=len(queries), 
            total=len(queries),
            percentage=100.0,
            results=[r.model_dump() for r in match_results]
        )
        
    except Exception as e:
        _update_task_status(task_id, status="failed", error=str(e))

# Rota para acessar a página inicial
@router.get("/")
async def read_index():
    return FileResponse("static/html/home.html")


@router.get("/results")
async def read_results():
    """Start background task to process matching and redirect to results page with task ID."""
    global _pasted_df, _excel_df, _pasted_context, _pasted_description_column
    
    # Validate data exists
    if _pasted_df is None or _excel_df is None:
        raise HTTPException(status_code=400, detail="Dados não carregados. Por favor, envie os dados colados e o arquivo Excel primeiro.")
    
    if _pasted_description_column is None or _pasted_description_column not in _pasted_df.columns:
        raise HTTPException(status_code=400, detail=f"Coluna de descrição inválida: {_pasted_description_column}")
    
    # Extract queries and documents
    queries = _pasted_df[_pasted_description_column].tolist()
    documents = _excel_df['description'].tolist()
    context = _pasted_context or "product matching"
    
    # Create task
    task_id = str(uuid.uuid4())
    with _task_lock:
        _task_store[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "total": len(queries),
            "percentage": 0.0,
            "results": None,
            "error": None,
            "stage": "initializing"
        }
    
    # Start background thread
    thread = threading.Thread(target=_process_matching_task, args=(task_id, queries, documents, context), daemon=True)
    thread.start()
    
    # Redirect to results view with task ID
    return RedirectResponse(url=f"/results-view?taskId={task_id}", status_code=303)


@router.get("/results-view")
async def results_view():
    """Serve the results HTML page."""
    return FileResponse("static/html/results.html")


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
async def read_upload():
    return FileResponse("static/html/upload.html")


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
        .assign(total_value=_excel_df["value"] * _excel_df["quantity"])
        .groupby("description", as_index=False)
        .agg(
            quantity=("quantity", "sum"),
            total_value=("total_value", "sum"),
        )
    )
    _excel_df["value"] = _excel_df["total_value"] / _excel_df["quantity"]
    _excel_df = _excel_df.drop(columns=["total_value"])
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

