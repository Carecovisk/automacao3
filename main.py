from pathlib import Path
import chromadb
import sqlite3
import pandas as pd
from utils.ai import PesquisaPrompt, get_candidates
from utils.input import filter_and_calculate_mean_loja, get_product_descriptions
from utils.db import init_sqlite_db, store_query_results

OUTPUT_PATH = Path('./data/output')
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

df_loja = filter_and_calculate_mean_loja(
  './data/loja.xlsx',
  description_filter=r"^PNEU MOTO",
  sheet_name='nfeitem'
)

df_descricoes_pesquisa = get_product_descriptions('./data/pesquisa.xlsx')
documents = df_loja['descr_compl'].tolist()


def create_chroma_db(documents, name) -> chromadb.Collection:
    chroma_client = chromadb.PersistentClient(path="./data/output/chromadb_storage")
    db = chroma_client.get_or_create_collection(
        name=name,
        # embedding_function=GeminiEmbeddingFunction()
    )

    # db.upsert(
    #     documents=documents,
    #     ids=[hashlib.md5(doc.encode()).hexdigest() for doc in documents]
    # )
    return db

def filter_by_distance(docs: list[str], distances: list[float], threshold: float = 0.955) -> tuple[list[str], list[float]]:
    """Filter documents that have a distance less than or equal to the threshold.
    
    Args:
        docs: List of document strings
        distances: List of distance values corresponding to docs
        threshold: Maximum distance threshold (default: 0.955)
    
    Returns:
        Tuple of (filtered_docs, filtered_distances)
    """
    filtered_docs = []
    filtered_distances = []
    
    for doc, distance in zip(docs, distances):
        if distance <= threshold:
            filtered_docs.append(doc)
            filtered_distances.append(distance)
    
    return filtered_docs, filtered_distances


# Set up the DB
print("Creating ChromaDB...")
db = create_chroma_db(documents, "pesquisa_products")

# Initialize SQLite database
print("Initializing SQLite database...")
sqlite_conn = init_sqlite_db()


def get_relevant_results(queries: list[str], db: chromadb.Collection, sqlite_conn: sqlite3.Connection) -> list[list]:
    results = db.query(query_texts=queries, n_results=5)
    docs = results.get('documents') or []
    distances = results.get('distances') or []
    
    filtered_docs_list = []
    
    for i, (doc_list, dist_list) in enumerate(zip(docs, distances)):
        query_text = queries[i]

        store_query_results(sqlite_conn, query_text, doc_list, dist_list)
        
        # Filter documents by distance threshold
        filtered_docs, filtered_distances = filter_by_distance(doc_list, dist_list)
        filtered_docs_list.append(filtered_docs)
    
    return filtered_docs_list


descriptions = df_descricoes_pesquisa['DESCRIÇÃO'].tolist()

print("Querying relevant documents from ChromaDB...")
all_relevant_docs = get_relevant_results(descriptions, db, sqlite_conn)

if not all_relevant_docs:
    raise ValueError("No relevant documents found for the given descriptions.")

def build_prompts(df_descricoes_pesquisa : pd.DataFrame, all_relevant_docs : list[list[str]]) -> list[PesquisaPrompt]:
    prompts = []
    for position, (idx, row) in enumerate(df_descricoes_pesquisa.iterrows()):
        description = row['DESCRIÇÃO']
        relevant_docs = all_relevant_docs[position]
        if relevant_docs:
            prompt = PesquisaPrompt(
                id=idx,
                item_description=description,
                items=relevant_docs
            )
            prompts.append(prompt)
    return prompts


print("Building prompts...")
prompts = build_prompts(df_descricoes_pesquisa, all_relevant_docs)


def print_prompts(prompts: list[PesquisaPrompt]) -> None:
    """Print a list of PesquisaPrompt objects with their details."""
    for idx, prompt in enumerate(prompts, start=1):
        print(f"\n--- Prompt {idx} ---")
        print(f"ID: {prompt.id}")
        print(f"Description: {prompt.item_description}")
        print(f"Items ({len(prompt.items)}):")
        for item in prompt.items:
            print(f"  - {item}")


print_prompts(prompts)

# Close SQLite connection when done
sqlite_conn.close()
print("SQLite database connection closed.")

# print("Getting candidates from LLM...")
# # Call get_candidates and write results to CSV as they come
# with open(OUTPUT_PATH / 'candidates_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
#     fieldnames = ['id','item', 'candidate', 'confidence']
#     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#     writer.writeheader()
    
#     for result in get_candidates(prompts, provider='ollama'):
#         for candidate in result.candidates:
#             writer.writerow({
#                 'id': result.prompt.id,
#                 'item': result.prompt.item_description,
#                 'candidate': candidate.description,
#                 'confidence': candidate.confidence
#             })
#         print('Rows written for item:', result.prompt.item_description)
#         csvfile.flush()  # Flush after each batch to ensure data is written
