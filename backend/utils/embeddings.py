from google import genai
from google.genai import types
from chromadb import EmbeddingFunction, Documents, Embeddings

client = genai.Client()

class GeminiEmbeddingFunction(EmbeddingFunction):
  def __call__(self, input: Documents) -> Embeddings:
    EMBEDDING_MODEL_ID = "gemini-embedding-001"
    title = "Custom query"
    batch_size = 100
    all_embeddings = []
    
    # Process documents in batches
    for i in range(0, len(input), batch_size):
      print(f"Processing batch {i // batch_size + 1}...")
      batch = input[i:i + batch_size]
      response = client.models.embed_content(
          model=EMBEDDING_MODEL_ID,
          contents=batch,
          config=types.EmbedContentConfig(
            task_type="retrieval_document",
            title=title
          )
      )
      all_embeddings.extend([embedding.values for embedding in response.embeddings])
    
    return all_embeddings