import hashlib
from pathlib import Path
from typing import Callable, Dict

import chromadb
from slugify import slugify

from utils.ai import PesquisaPrompt
from utils.config import load_config
from utils.domain import QueryMatch
from utils.embeddings import emb_fn_bge_m3
from utils.preprocesssing import apply_replacements, get_replacements_from_llm, split_by_confidence
from utils.reranker import filter_items_by_score, filter_items_by_score_gap, rerank_items
from web.schemas import MatchedItem, MatchResult

TaskUpdater = Callable[..., None]

_OUTPUT_PATH = Path("./data/output")


def _insert_documents_in_batches(
    db,
    processed_documents: list[str],
    original_documents: list[str],
    batch_size: int = 5000,
    message_callback: Callable[[str], None] | None = None,
) -> None:
    """Insert documents into ChromaDB in batches to avoid memory issues."""
    total_docs = len(processed_documents)
    total_batches = (total_docs + batch_size - 1) // batch_size

    for i in range(0, total_docs, batch_size):
        batch_docs = processed_documents[i : i + batch_size]
        batch_originals = original_documents[i : i + batch_size]
        # ID is derived from the original text — stable across replacement changes
        batch_ids = [hashlib.md5(doc.encode()).hexdigest() for doc in batch_originals]
        db.upsert(documents=batch_docs, ids=batch_ids)

        current_batch = i // batch_size + 1
        msg = f"Inserindo batch {current_batch}/{total_batches} ({len(batch_docs)} documentos)"
        print(msg)
        if message_callback:
            message_callback(msg)


def run_matching_pipeline(
    task_id: str,
    queries: list[str],
    documents: list[str],
    values: list[float],
    context: str,
    task_updater: TaskUpdater,
) -> None:
    """Execute the full document-matching pipeline for *task_id*.

    Updates the task store via *task_updater* at each stage.
    Designed to be called from a background thread.

    Pipeline stages:
      1. LLM replacements — expand abbreviations in documents
      2. Vector DB — create collection and insert processed documents
      3. Query — retrieve top-N candidates per query
      4. Rerank → filter by score → filter by score gap
      5. Confidence split — only high-confidence matches are returned
    """
    try:
        task_updater(task_id, status="running", progress=0, total=len(queries))

        config = load_config()

        # --- Stage 1: LLM replacements ---------------------------------------
        task_updater(task_id, stage="llm_replacements", message="Obtendo replacements do LLM...")

        def _llm_status(msg: str) -> None:
            task_updater(task_id, message=msg)

        if config.use_llm and config.use_llm_abbreviation_expansion:
            replacements = get_replacements_from_llm(documents, context=context, status_callback=_llm_status)
        else:
            replacements = []

        task_updater(task_id, stage="preprocessing", message="Aplicando replacements aos documentos...")
        processed_documents = apply_replacements(documents, replacements)

        # Map each processed description back to its source value so we can
        # annotate candidates retrieved from the vector DB.
        doc_value_map: Dict[str, float] = {
            processed: value for processed, value in zip(processed_documents, values)
        }

        # --- Stage 2: Vector DB ----------------------------------------------
        task_updater(task_id, stage="creating_db", message="Criando coleção vetorial...")
        DB_STORAGE_PATH = _OUTPUT_PATH / "chromadb_storage"
        DB_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

        chroma_client = chromadb.PersistentClient(path=DB_STORAGE_PATH)
        db = chroma_client.get_or_create_collection(
            name=slugify(context), embedding_function=emb_fn_bge_m3  # type: ignore
        )

        task_updater(task_id, stage="inserting_db", message="Inserindo documentos no banco vetorial...")
        _insert_documents_in_batches(
            db,
            processed_documents,
            documents,
            message_callback=lambda msg: task_updater(task_id, message=msg),
        )

        # --- Stage 3: Query --------------------------------------------------
        task_updater(task_id, stage="querying_db", message="Consultando documentos relevantes...")
        raw = db.query(query_texts=queries, n_results=5)
        docs = raw.get("documents") or []
        distances = raw.get("distances") or []

        matches: list[QueryMatch] = [
            QueryMatch(
                query=query,
                candidates=[
                    PesquisaPrompt.Item(
                        description=doc,
                        distance=dist,
                        score=0.0,
                        value=doc_value_map.get(doc, 0.0),
                    )
                    for doc, dist in zip(doc_list, dist_list)
                    if dist <= 0.955
                ],
            )
            for query, doc_list, dist_list in zip(queries, docs, distances)
        ]

        if not any(m.has_candidates for m in matches):
            raise ValueError("Nenhum documento relevante encontrado para as descrições fornecidas.")

        # --- Stage 4: Rerank + filter ----------------------------------------
        task_updater(task_id, stage="reranking", message="Reordenando e filtrando resultados...")

        def _progress(current: int, total: int) -> None:
            task_updater(
                task_id,
                progress=current,
                total=total,
                percentage=round((current / total) * 100, 2),
            )

        matches = rerank_items(matches, progress_callback=_progress)
        matches = filter_items_by_score(matches, threshold=0.8)
        matches = filter_items_by_score_gap(matches, gap_threshold=0.1)

        # --- Stage 5: Confidence split ---------------------------------------
        _, high_confidence = split_by_confidence(matches, max_score_threshold=config.high_confidence_threshold)

        # --- LLM judge stub (gated on config) --------------------------------
        if config.use_llm and config.use_llm_judge:
            # TODO: implement execution logic for LLM judge on low-confidence candidates
            pass

        # --- Serialise results -----------------------------------------------
        match_results = [
            MatchResult(
                query=match.query,
                matched_items=[
                    MatchedItem(
                        description=c.description,
                        distance=c.distance,
                        score=c.score,
                        value=c.value,
                    )
                    for c in match.candidates
                ],
            )
            for match in high_confidence
        ]

        task_updater(
            task_id,
            status="completed",
            progress=len(queries),
            total=len(queries),
            percentage=100.0,
            results=[r.model_dump() for r in match_results],
        )

    except Exception as e:
        task_updater(task_id, status="failed", error=str(e))
