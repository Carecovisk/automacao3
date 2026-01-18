import textwrap
import chromadb
import numpy as np
import pandas as pd
from utils.input import filter_and_calculate_mean_loja, get_product_descriptions
from chromadb import Documents,Embeddings
from my_embeddings import GeminiEmbeddingFunction

df_loja = filter_and_calculate_mean_loja(
  './data/loja.xlsx',
  description_filter=r"^PNEU",
  sheet_name='nfeitem'
)

df_descricoes_pesquisa = get_product_descriptions('./data/pesquisa.xlsx')

documents = df_descricoes_pesquisa['DESCRIÇÃO'].tolist()


def create_chroma_db(documents, name) -> chromadb.Collection:
    chroma_client = chromadb.PersistentClient(path="./chromadb_storage")
    db = chroma_client.get_or_create_collection(
        name=name,
        # embedding_function=GeminiEmbeddingFunction()
    )

    db.upsert(
        documents=documents,
        ids=[str(i) for i in range(len(documents))]
    )
    return db

# Set up the DB
db = create_chroma_db(documents, "google-car-db")


sample_data = db.get(include=['documents', 'embeddings'])

df_pesquisa = pd.DataFrame({
    "IDs": sample_data['ids'],
    "Documents": sample_data['documents'],
    "Embeddings": [str(emb)[:50] + "..." for emb in sample_data['embeddings']]  # Truncate embeddings
})

print("Embeddings DataFrame Info:")
print(df_pesquisa.info())
print(df_pesquisa.head())


def get_relevant_results(query, db) -> list[list[str]]:
  passage = db.query(query_texts=[query], n_results=5)['documents']
  return passage

search = input("Enter your search query: ")

results = get_relevant_results(search, db)
print("Relevant results:")

for result in results:
  print("\n".join(result))


# def make_prompt(query, relevant_passage):
#   escaped = relevant_passage.replace("'", "").replace('"', "").replace("\n", " ")
#   prompt = ("""
#     You are a helpful and informative bot that answers questions using
#     text from the reference passage included below.
#     Be sure to respond in a complete sentence, being comprehensive,
#     including all relevant background information.
#     However, you are talking to a non-technical audience, so be sure to
#     break down complicated concepts and strike a friendly
#     and converstional tone. If the passage is irrelevant to the answer,
#     you may ignore it.
#     QUESTION: '{query}'
#     PASSAGE: '{relevant_passage}'

#     ANSWER:
#   """).format(query=query, relevant_passage=escaped)

#   return prompt

# query = "How do you use the touchscreen in the Google car?"
# prompt = make_prompt(query, passage)
# print(prompt)


# MODEL_ID = "gemini-2.5-flash" # @param ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-preview", "gemini-3-pro-preview"] {"allow-input":true, isTemplate: true}
# answer = client.models.generate_content(
#     model = MODEL_ID,
#     contents = prompt
# )
# print("Answer:", answer.text)
