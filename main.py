import csv
import hashlib
from pathlib import Path
from typing import Callable

import chromadb
import pandas as pd
from slugify import slugify

from utils.ai import PesquisaPrompt, get_candidates
from utils.embeddings import emb_fn_bge_m3
from utils.input import get_notas_fiscais, get_pesquisa
from utils.preprocesssing import apply_replacements, get_replacements_from_llm
from utils.reranker import (
    filter_items_by_score,
    filter_items_by_score_gap,
    rerank_items,
)

OUTPUT_PATH = Path("./data/output")
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


def create_chroma_db(documents, name) -> chromadb.Collection:
    chroma_client = chromadb.PersistentClient(path=OUTPUT_PATH / "chromadb_storage")
    db = chroma_client.get_or_create_collection(
        name=name, embedding_function=emb_fn_bge_m3
    )

    db.upsert(
        documents=documents,
        ids=[hashlib.md5(doc.encode()).hexdigest() for doc in documents],
    )
    return db


def split_queries_by_confidence(
    queries: list[str],
    relevant_results: list[list[PesquisaPrompt.Item]],
    max_score_threshold: float = 0.9,
) -> tuple[
    tuple[list[str], list[list[PesquisaPrompt.Item]]],
    tuple[list[str], list[list[PesquisaPrompt.Item]]],
]:
    """Split queries into low and high confidence based on maximum score threshold.

    Args:
        queries: List of query strings
        relevant_results: List of lists containing PesquisaPrompt.Item objects
        max_score_threshold: Maximum score threshold (default: 0.9)

    Returns:
        Tuple of two tuples:
        - First tuple: (low_confidence_queries, low_confidence_results)
          where max score < threshold
        - Second tuple: (high_confidence_queries, high_confidence_results)
          where max score >= threshold
    """
    low_confidence_queries = []
    low_confidence_results = []
    high_confidence_queries = []
    high_confidence_results = []

    for query, results in zip(queries, relevant_results):
        # Check if results list is empty or get max score
        if not results:
            continue
        else:
            max_score_item = max(results, key=lambda item: item.score)
            if max_score_item.score < max_score_threshold:
                low_confidence_queries.append(query)
                low_confidence_results.append(results)
            else:
                max_score_item.matched = (
                    True  # Mark the item with the highest score as matched
                )
                high_confidence_queries.append(query)
                high_confidence_results.append(results)

    return (low_confidence_queries, low_confidence_results), (
        high_confidence_queries,
        high_confidence_results,
    )


def filter_by_distance(
    docs: list[str], distances: list[float], threshold: float = 0.955
) -> list[PesquisaPrompt.Item]:
    """Filter documents that have a distance less than or equal to the threshold.

    Args:
        docs: List of document strings
        distances: List of distance values corresponding to docs
        threshold: Maximum distance threshold (default: 0.955)

    Returns:
        List of filtered PesquisaPrompt.Item objects
    """
    filtered_items = []

    for doc, distance in zip(docs, distances):
        if distance <= threshold:
            filtered_items.append(
                PesquisaPrompt.Item(description=doc, distance=distance)
            )

    return filtered_items


def get_relevant_results(
    queries: list[str], db: chromadb.Collection, n_results=5
) -> list[list[PesquisaPrompt.Item]]:
    results = db.query(query_texts=queries, n_results=n_results)
    docs = results.get("documents") or []
    distances = results.get("distances") or []

    filtered_docs_list = []

    for doc_list, dist_list in zip(docs, distances):
        # Filter documents by distance threshold
        filtered_docs = filter_by_distance(doc_list, dist_list)
        filtered_docs_list.append(filtered_docs)

    return filtered_docs_list


def build_prompts(
    descricoes_pesquisa: list[str], relevant_results: list[list[PesquisaPrompt.Item]]
) -> list[PesquisaPrompt]:
    prompts = []
    for position, description in enumerate(descricoes_pesquisa):
        relevant_docs = relevant_results[position]
        if relevant_docs:
            prompt = PesquisaPrompt(
                id=position + 1, item_description=description, items=relevant_docs
            )
            prompts.append(prompt)
    return prompts


def write_with_stdout_redirect(path_output: Path, writer: Callable) -> None:
    import sys

    original_stdout = sys.stdout
    with open(path_output, "w", encoding="utf-8") as f:
        sys.stdout = f
        writer()
    sys.stdout = original_stdout


def print_prompts(prompts: list[PesquisaPrompt]) -> None:
    for idx, prompt in enumerate(prompts, start=1):
        print(f"\n--- Prompt {idx} ---")
        print(f"ID: {prompt.id}")
        print(f"Description: {prompt.item_description}")
        print(f"Items ({len(prompt.items)}):")
        for item in prompt.items:
            print(
                f"  - {item.description} (Distance: {item.distance}) (Score: {item.score})"
            )


def print_replaced_descricoes(descricoes: list[str]) -> None:
    for idx, descr in enumerate(descricoes, start=1):
        print(f"{idx}. {descr}")


def print_confidence_results(
    queries: list[str],
    results: list[list[PesquisaPrompt.Item]],
    confidence_type: str = "Results",
) -> None:
    """Print confidence results showing queries and their matched items.

    Args:
        queries: List of query strings
        results: List of lists containing PesquisaPrompt.Item objects
        confidence_type: Type label for the output (e.g., "High Confidence", "Low Confidence")
    """
    print(f"\n{'=' * 80}")
    print(f"{confidence_type}")
    print(f"{'=' * 80}")

    for idx, (query, items) in enumerate(zip(queries, results), start=1):
        print(f"\n[{idx}] Query: {query}")

        if not items:
            print("  No items found")
        else:
            print(f"  Items ({len(items)}):")
            for item in items:
                matched_indicator = "✓" if item.matched else " "
                print(
                    f"    [{matched_indicator}] {item.description}"
                    f"\n        Score: {item.score:.4f}, Distance: {item.distance:.4f}"
                )


def get_descricoes_notas(df_notas_fiscais: pd.DataFrame) -> list[str]:
    """Extract 'descr_compl' column from DataFrame as a list of strings."""
    return df_notas_fiscais["descr_compl"].tolist()


def get_descricoes_pesquisa(df_pesquisa: pd.DataFrame) -> list[str]:
    """Extract 'DESCRIÇÃO' column from DataFrame as a list of strings."""
    return df_pesquisa["DESCRIÇÃO"].tolist()


def process_queries(
    queries: list[str],
    documents: list[str],
    context: str,
    provider: str = "gemini",
):
    """
    Process a list of queries against a list of documents with optional preprocessing.

    Args:
        queries: List of search queries to match against documents
        documents: List of document strings to search through
        context: Context string for LLM replacement preprocessing
        provider: LLM provider to use for candidate selection ('gemini' or 'ollama')

    Yields:
        Tuples of (queries, results) for high confidence and processed low confidence results
    """
    # Get replacements from LLM and apply them to documents
    replacements = get_replacements_from_llm(documents, context=context)

    print(
        "Replacements:",
        "\n".join([f"{r.regex} -> {r.replacement}" for r in replacements]),
    )

    print("Applying replacements to documents...")
    processed_documents = apply_replacements(documents, replacements)

    write_with_stdout_redirect(
        OUTPUT_PATH / "descricoes_replaced.txt",
        lambda: print_replaced_descricoes(processed_documents),
    )

    # Set up the DB
    print("Creating ChromaDB...")
    db = create_chroma_db(processed_documents, slugify(context))

    print("Querying relevant documents from ChromaDB...")
    relevant_results = get_relevant_results(queries, db, n_results=5)

    if not relevant_results:
        raise ValueError("No relevant documents found for the given descriptions.")

    print("Reranking results...")
    reranked = rerank_items(queries, relevant_results)
    relevant_results = filter_items_by_score(reranked, threshold=0.8)
    relevant_results = filter_items_by_score_gap(relevant_results, gap_threshold=0.1)

    low_confidence, high_confidence = split_queries_by_confidence(
        queries, relevant_results
    )

    print(f"High confidence queries: {len(high_confidence[0])}")
    print(f"Low confidence queries: {len(low_confidence[0])}")

    # Print high confidence results
    write_with_stdout_redirect(
        OUTPUT_PATH / "high_confidence_results.txt",
        lambda: print_confidence_results(
            *high_confidence, "High Confidence Results"
        ),
    )

    # Print low confidence results
    if low_confidence[0]:
        write_with_stdout_redirect(
            OUTPUT_PATH / "low_confidence_results.txt",
            lambda: print_confidence_results(
                *low_confidence, "Low Confidence Results"
            ),
        )

    # Yield high confidence results first
    yield high_confidence

    # Process low confidence queries with LLM
    if low_confidence[0]:  # If there are low confidence queries
        print(
            f"Processing {len(low_confidence[0])} low confidence queries with {provider}..."
        )
        for processed_queries, processed_results in get_candidates(
            *low_confidence, provider=provider
        ):
            print(f"Processed {len(processed_queries)} queries through LLM")
            yield (processed_queries, processed_results)
    else:
        print("No low confidence queries to process")


def main():
    df_pesquisa = get_pesquisa("./data/pesquisa.xlsx")
    descricoes_pesquisa = get_descricoes_pesquisa(df_pesquisa)

    df_notas_fiscais = get_notas_fiscais(
        "./data/loja.xlsx", description_filter=r"^PNEU MOTO", sheet_name="nfeitem"
    )
    descricoes_notas = get_descricoes_notas(df_notas_fiscais)

    for queries, results in process_queries(descricoes_pesquisa, descricoes_notas, context="pneus moto"):
        print(f"Yielded {len(queries)} queries with their results")
        # Here you can add any additional processing for the yielded results


if __name__ == "__main__":
    main()
