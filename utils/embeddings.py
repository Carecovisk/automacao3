from google import genai
from google.genai import types
from chromadb import EmbeddingFunction, Documents, Embeddings
from chromadb.utils import embedding_functions
from utils.config import load_config

emb_fn_bge_m3 = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-m3"
)