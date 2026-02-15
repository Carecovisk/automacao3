from collections.abc import Generator
from dataclasses import dataclass
from typing import Hashable
from pydantic import BaseModel


@dataclass
class BasePrompt:
    id: Hashable

    class PromptResult(BaseModel):
        pass

    def build(self) -> str:
        raise NotImplementedError("Subclasses must implement build method")


@dataclass
class PesquisaPrompt(BasePrompt):
    item_description: str
    items: list["PesquisaPrompt.Item"]
    limit: int = 3

    @dataclass
    class Item:
        description: str
        distance: float
        score: float = 0.0
        matched: bool = False

    def build(self) -> str:
        items_str = "\n".join(item.description for item in self.items)
        return f"""
    Preciso saber quais dos seguintes itens correspondem a este "{self.item_description}".
    Dê-me uma lista de até {self.limit} melhores candidatos junto com o seu rank.
    Se as marcas dos itens, modelos, tamanhos, ou outras características não corresponderem, desconsidere-os. Seja crítico, se não houver correspondência retorne uma lista vazia.
    Aqui estão os itens para escolher:

    {items_str}
    """


class Candidate(BaseModel):
    id: int
    description: str
    rank: int


class Candidates(BaseModel):
    candidates: list[Candidate] = []


@dataclass
class PromptResult:
    prompt: PesquisaPrompt
    candidates: list["Candidate"]


def get_candidates(
    queries: list[str], results: list[list["PesquisaPrompt.Item"]], provider: str
) -> Generator[tuple[list[str], list[list["PesquisaPrompt.Item"]]], None, None]:
    """Fetch candidates from the specified provider.

    Args:
      queries: List of query strings
      results: List of lists of PesquisaPrompt.Item objects
      provider: Provider name ('gemini' or 'ollama')

    Yields:
      Tuples of (queries, results) representing processed queries and their filtered results
    """
    if provider == "gemini":
        from .models.gemini import get_candidates_gemini

        yield from get_candidates_gemini(queries, results)
    elif provider == "ollama":
        from .models.ollama import get_candidates_ollama

        yield from get_candidates_ollama(queries, results)
    else:
        raise ValueError(f"Unknown provider: {provider}")
