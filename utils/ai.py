from collections.abc import Generator
from dataclasses import dataclass
from typing import Hashable
from pydantic import BaseModel

@dataclass
class PesquisaPrompt:
  id: Hashable
  item_description: str
  items: list[str]
  limit: int = 3

  def build(self) -> str:
    items_str = '\n'.join(self.items)
    return f"""
    Preciso saber quais dos seguintes itens correspondem a este "{self.item_description}".
    Dê-me uma lista de até {self.limit} melhores candidatos junto com uma porcentagem de confiança, a porcentagem deve estar entre 0 e 1.
    Se as marcas dos itens, modelos, tamanhos, ou outras características não corresponderem, desconsidere-os. Seja crítico, se não houver correspondência retorne uma lista vazia.
    Aqui estão os itens para escolher:

    {items_str}
    """

class Candidate(BaseModel):
  id: int
  description: str
  confidence: float

class Candidates(BaseModel):
  candidates: list[Candidate] = []

@dataclass
class PromptResult:
  prompt: PesquisaPrompt
  candidates: list['Candidate']

def get_candidates(prompts: list[PesquisaPrompt], provider : str) -> Generator[PromptResult, None, None]:
  """Fetch candidates using Gemini Batch API (50% cost reduction)."""
  if provider == 'gemini':
    from models.gemini import get_candidates_gemini
    yield from get_candidates_gemini(prompts)
  elif provider == 'ollama':
    from models.ollama import get_candidates_ollama
    yield from get_candidates_ollama(prompts)
  else:
    raise ValueError(f"Unknown provider: {provider}")