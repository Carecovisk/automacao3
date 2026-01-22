from pathlib import Path
import textwrap
import chromadb
import hashlib
import numpy as np
import pandas as pd
import csv
from utils.ai import PesquisaPrompt, get_candidates
from utils.input import filter_and_calculate_mean_loja, get_product_descriptions
from chromadb import Documents,Embeddings
from utils.embeddings import GeminiEmbeddingFunction

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
    chroma_client = chromadb.PersistentClient(path="./chromadb_storage")
    db = chroma_client.get_or_create_collection(
        name=name,
        # embedding_function=GeminiEmbeddingFunction()
    )

    db.upsert(
        documents=documents,
        ids=[hashlib.md5(doc.encode()).hexdigest() for doc in documents]
    )
    return db

# Set up the DB
print("Creating ChromaDB...")
db = create_chroma_db(documents, "pesquisa_products")


def get_relevant_results(queries :list[str], db : chromadb.Collection) -> list[list]:
  results = db.query(query_texts=queries, n_results=5)
  docs = results.get('documents') or []
  distances = results.get('distances') or []
  print("Query results (docs with distances):")
  for i, (doc_list, dist_list) in enumerate(zip(docs, distances)):
      print(f"Query {queries[i]}:")
      for doc, dist in zip(doc_list, dist_list):
          print(f"  doc: {doc} | distance: {dist}")
  return docs


descriptions = df_descricoes_pesquisa['DESCRIÇÃO'].tolist()

# Query all descriptions at once
print("Querying relevant documents from ChromaDB...")
all_relevant_docs = get_relevant_results(descriptions, db)

if not all_relevant_docs:
    raise ValueError("No relevant documents found for the given descriptions.")

def build_prompts(df_descricoes_pesquisa : pd.DataFrame, all_relevant_docs : list[list[str]]) -> list[PesquisaPrompt]:
    prompts = []
    for position, (idx, row) in enumerate(df_descricoes_pesquisa.iterrows()):
        description = row['DESCRIÇÃO']
        relevant_docs = all_relevant_docs[position]
        prompt = PesquisaPrompt(
            id=idx,
            item_description=description,
            items=relevant_docs
        )
        prompts.append(prompt)
    return prompts


print("Building prompts...")
prompts = build_prompts(df_descricoes_pesquisa, all_relevant_docs)


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
