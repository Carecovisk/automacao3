import csv
import hashlib
from pathlib import Path
import chromadb
import sqlite3
import pandas as pd
from utils.ai import PesquisaPrompt, get_candidates
from utils.input import get_notas_fiscais, get_pesquisa
from utils.db import init_sqlite_db, store_query_results
from utils.reranker import rerank_items, filter_items_by_score
from utils.embeddings import emb_fn_bge_m3

OUTPUT_PATH = Path('./data/output')
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


def create_chroma_db(documents, name) -> chromadb.Collection:
    chroma_client = chromadb.PersistentClient(path=OUTPUT_PATH / "chromadb_storage")
    db = chroma_client.get_or_create_collection(
        name=name,
        embedding_function=emb_fn_bge_m3
    )

    db.upsert(
        documents=documents,
        ids=[hashlib.md5(doc.encode()).hexdigest() for doc in documents]
    )
    return db

def filter_by_distance(docs: list[str], distances: list[float], threshold: float = 0.955) -> list[PesquisaPrompt.Item]:
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
            filtered_items.append(PesquisaPrompt.Item(description=doc, distance=distance))
    
    return filtered_items

def get_relevant_results(queries: list[str], db: chromadb.Collection, sqlite_conn: sqlite3.Connection, n_results = 5) -> list[list[PesquisaPrompt.Item]]:
    results = db.query(query_texts=queries, n_results=n_results)
    docs = results.get('documents') or []
    distances = results.get('distances') or []
    
    filtered_docs_list = []
    
    for i, (doc_list, dist_list) in enumerate(zip(docs, distances)):
        query_text = queries[i]

        store_query_results(sqlite_conn, query_text, doc_list, dist_list)
        
        # Filter documents by distance threshold
        filtered_docs = filter_by_distance(doc_list, dist_list)
        filtered_docs_list.append(filtered_docs)
    
    return filtered_docs_list


def build_prompts(descricoes_pesquisa : list[str], all_relevant_docs : list[list[PesquisaPrompt.Item]]) -> list[PesquisaPrompt]:
    prompts = []
    for position, description in enumerate(descricoes_pesquisa):
        relevant_docs = all_relevant_docs[position]
        if relevant_docs:
            prompt = PesquisaPrompt(
                id=position + 1,
                item_description=description,
                items=relevant_docs
            )
            prompts.append(prompt)
    return prompts


def print_prompts_to_file(prompts: list[PesquisaPrompt], path_output: Path) -> None:
    """Print a list of PesquisaPrompt objects with their details."""
    import sys
    original_stdout = sys.stdout

    with open(path_output, 'w', encoding='utf-8') as f:
        sys.stdout = f
        for idx, prompt in enumerate(prompts, start=1):
            print(f"\n--- Prompt {idx} ---")
            print(f"ID: {prompt.id}")
            print(f"Description: {prompt.item_description}")
            print(f"Items ({len(prompt.items)}):")
            for item in prompt.items:
                print(f"  - {item.description} (Distance: {item.distance}) (Score: {item.score})")

    sys.stdout = original_stdout

def get_descricoes_notas(df_notas_fiscais: pd.DataFrame) -> list[str]:
    """Extract 'descr_compl' column from DataFrame as a list of strings."""
    return df_notas_fiscais['descr_compl'].tolist()

def get_descricoes_pesquisa(df_pesquisa: pd.DataFrame) -> list[str]:
    """Extract 'DESCRIÇÃO' column from DataFrame as a list of strings."""
    return df_pesquisa['DESCRIÇÃO'].tolist()

def main():
    df_pesquisa = get_pesquisa('./data/pesquisa.xlsx')
    descricoes_pesquisa = get_descricoes_pesquisa(df_pesquisa)

    df_notas_fiscais = get_notas_fiscais(
        './data/loja.xlsx',
        description_filter=r"^PNEU MOTO",
        sheet_name='nfeitem'
    )
    descricoes_notas = get_descricoes_notas(df_notas_fiscais)

    # Set up the DB
    print("Creating ChromaDB...")
    db = create_chroma_db(descricoes_notas, "pesquisa_products")

    # Initialize SQLite database
    print("Initializing SQLite database...")
    sqlite_conn = init_sqlite_db()


    print("Querying relevant documents from ChromaDB...")
    relevant_results = get_relevant_results(descricoes_pesquisa, db, sqlite_conn, n_results=10)

    if not relevant_results:
        raise ValueError("No relevant documents found for the given descriptions.")

    print("Reranking results...")
    reranked = rerank_items(descricoes_pesquisa, relevant_results)
    relevant_results = filter_items_by_score(reranked, threshold=0.5)

    print("Building prompts...")
    prompts = build_prompts(descricoes_pesquisa, relevant_results)

    print_prompts_to_file(prompts, OUTPUT_PATH / 'prompts_output.txt')

    # Close SQLite connection when done
    sqlite_conn.close()

    # print("Getting candidates from LLM...")
    # # Call get_candidates and write results to CSV as they come
    # with open(OUTPUT_PATH / 'candidates_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
    #     fieldnames = ['id','item', 'candidate', 'rank']
    #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    #     writer.writeheader()
        
    #     for result in get_candidates(prompts, provider='ollama'):
    #         for candidate in result.candidates:
    #             writer.writerow({
    #                 'id': result.prompt.id,
    #                 'item': result.prompt.item_description,
    #                 'candidate': candidate.description,
    #                 'rank': candidate.rank
    #             })
    #         print('Rows written for item:', result.prompt.item_description)
    #         csvfile.flush()  # Flush after each batch to ensure data is written
    print("Finished.")


if __name__ == "__main__":
    main()
