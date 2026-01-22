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


def get_relevant_results(query, db) -> list[str]:
  passage = db.query(query_texts=[query], n_results=5)['documents'][0]
  return passage



print("Building prompts...")
prompts = []
for idx, row in df_descricoes_pesquisa.iterrows():
    description = row['DESCRIÇÃO']
    relevant_docs = get_relevant_results(description, db)
    prompt = PesquisaPrompt(
        id=idx,
        item_description=description,
        items=relevant_docs
    )
    prompts.append(prompt)


print("Getting candidates from LLM...")
# Call get_candidates and write results to CSV as they come
with open('./data/output/candidates_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['id','item', 'candidate', 'confidence']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    
    for result in get_candidates(prompts):
        for candidate in result.candidates:
            writer.writerow({
                'id': result.prompt.id,
                'item': result.prompt.item_description,
                'candidate': candidate.description,
                'confidence': candidate.confidence
            })
        print('Rows written for item:', result.prompt.item_description)
        csvfile.flush()  # Flush after each batch to ensure data is written
