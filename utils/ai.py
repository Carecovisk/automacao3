from dataclasses import dataclass
from email import message
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from typing import Hashable
import uuid
from ollama import chat
from pydantic import BaseModel
from google import genai
import os

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
    Dê-me uma lista dos {self.limit} melhores candidatos junto com uma porcentagem de confiança, a porcentagem deve estar entre 0 e 1.
    Se as marcas dos itens, modelos, tamanhos, ou outras características não corresponderem, desconsidere-os. Seja crítico, se não houver correspondência retorne uma lista vazia.
    Aqui estão os itens para escolher:

    {items_str}
    """

class Candidate(BaseModel):
  id: int
  item_description: str
  confidence: float

class Candidates(BaseModel):
  candidates: list[Candidate] = []

@dataclass
class PromptResult:
  prompt: PesquisaPrompt
  candidates: list['Candidate']

def get_candidates(prompts: list[PesquisaPrompt], max_workers: int = 3):
  """Make parallel requests to Ollama for multiple prompts, yielding results as they complete."""
  with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(fetch_candidates_gemini, prompt): prompt for prompt in prompts}
    for future in concurrent.futures.as_completed(futures):
      yield future.result()

def fetch_candidates_ollama(prompt: PesquisaPrompt) -> PromptResult:
  response = chat(
    model='gemma3:4b-it-qat',
    messages=[{'role': 'user', 'content': prompt.build()}],
    format=Candidates.model_json_schema()
  )
  candidates = Candidates.model_validate_json(response.message.content)
  return PromptResult(prompt=prompt, candidates=candidates.candidates)


client = genai.Client()
def fetch_candidates_gemini(prompt: PesquisaPrompt) -> PromptResult:
  """Fetch candidates using Google Gemini API."""
  
  response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt.build(),
    config={
        "response_mime_type": "application/json",
        "response_json_schema": Candidates.model_json_schema(),
    },
  )
  candidates = Candidates.model_validate_json(response.text)
  print(f"Received {len(candidates.candidates)} candidates for prompt ID {prompt.id}")
  return PromptResult(prompt=prompt, candidates=candidates.candidates)