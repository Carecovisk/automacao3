import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder
import numpy as np

# --- CONFIGURAÇÃO ---

# 1. Configurar o Modelo de Embedding (Bi-Encoder) para o ChromaDB
# O BGE-M3 é excelente para criar a representação vetorial inicial.
embedding_model_name = "BAAI/bge-m3"
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=embedding_model_name
)

# 2. Configurar o Modelo de Reranking (Cross-Encoder)
# Este modelo é mais pesado e "lê" o par (query + documento) para dar uma nota precisa.
# Se estiver sem GPU, pode tentar um modelo menor como 'BAAI/bge-reranker-base'
reranker_model_name = "BAAI/bge-reranker-v2-m3"
reranker = CrossEncoder(reranker_model_name, max_length=512)

# --- PREPARAÇÃO DOS DADOS ---

# Inicializar ChromaDB (em memória para este exemplo)
client = chromadb.Client()
collection = client.create_collection(
    name="produtos_db",
    embedding_function=emb_fn  # Usa o BGE para vetores
)

# Simulando uma lista de produtos (Note como alguns são muito parecidos)
docs = [
    "Samsung Galaxy S23 Ultra 256GB Preto",      # Alvo correto
    "Samsung Galaxy S23 128GB Preto",            # Quase igual, mas modelo diferente
    "Capa para Samsung Galaxy S23 Ultra",        # Acessório, semanticamente próximo
    "Samsung Galaxy S22 Ultra 256GB Usado",      # Modelo antigo
    "iPhone 14 Pro Max 256GB",                   # Concorrente
    "Carregador Samsung Tipo C 25W"              # Acessório
]
ids = [f"id_{i}" for i in range(len(docs))]

print("Indexando produtos...")
collection.add(documents=docs, ids=ids)

# --- EXECUÇÃO DO MATCHING ---

query_text = "Smartphone Samsung S23 Ultra 256gb"

print(f"\n--- Buscando por: '{query_text}' ---\n")

# ETAPA 1: Recuperação (Retrieval) com ChromaDB
# Pedimos mais resultados do que precisamos (ex: Top 10) para dar margem ao Reranker trabalhar.
results = collection.query(
    query_texts=[query_text],
    n_results=5
)

retrieved_docs = results['documents'][0]
print(">> Resultados Originais do ChromaDB (Bi-Encoder):")
for i, doc in enumerate(retrieved_docs):
    print(f"{i+1}. {doc}")

# ETAPA 2: Reranking (Refinamento)
# O Reranker precisa de pares: [Query, Documento]
pairs = [[query_text, doc] for doc in retrieved_docs]

# O modelo calcula a pontuação de similaridade para cada par
scores = reranker.predict(pairs)

# Combinar documentos com suas novas pontuações e ordenar
reranked_results = sorted(
    list(zip(retrieved_docs, scores)), 
    key=lambda x: x[1], 
    reverse=True
)

print("\n>> Resultados Após Reranking (Cross-Encoder):")
for i, (doc, score) in enumerate(reranked_results):
    # Cross-Encoders costumam dar scores negativos ou positivos (logits). 
    # Quanto maior, melhor.
    print(f"{i+1}. {doc} (Score: {score:.4f})")