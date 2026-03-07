import json
import random
import re
import uuid
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from utils.ai import BasePrompt, PesquisaPrompt
from utils.domain import QueryMatch
from utils.cache import CacheManager
from utils.models.gemini import make_prompt


class Replacement(BaseModel):
    regex: str = Field(
        description="Regular expression pattern to match. python regex syntax"
    )
    replacement: str = Field(description="Replacement string")


@dataclass
class PreprocessingPrompt(BasePrompt):
    id: Hashable
    sample: list[str]
    context: str

    class PromptResult(BaseModel):
        replacements: list[Replacement] = []

    def build(self) -> str:
        return f"""
    Você é um especialista em Regex e dados de varejo.

    CONTEXTO:
      {self.context}

    TAREFA:
      Crie uma lista de 'replacements' para expandir abreviações e minemonicos comuns encontrados nos dados de varejo.

    DADOS DE AMOSTRA:
    {json.dumps(self.sample, indent=2, ensure_ascii=False)}

    """


# Initialize cache manager for replacements
_replacement_cache = CacheManager(
    cache_dir=Path("cache/llm_replacements"), result_type=Replacement
)


def get_replacements_from_llm(
    strings: list[str],
    context: str = "Dados de varejo contendo abreviações e variações",
    use_cache: bool = True,
    status_callback: Callable[[str], None] | None = None,
) -> list[Replacement]:
    """
    Create a PreprocessingPrompt from a list of strings and get replacements using Gemini API.
    Results are cached based on the context string to avoid redundant API calls.

    Args:
        strings: List of strings to analyze for common abbreviations and patterns
        context: Context description for the prompt (default: retail data context)
        use_cache: Whether to use cached results if available (default: True)
        status_callback: Optional callback to report status messages (receives a message string)

    Returns:
        List of Replacement objects containing regex patterns and replacements
    """

    # Try to load from cache first
    if use_cache:
        if status_callback:
            status_callback("Verificando cache de replacements...")
        cached_result = _replacement_cache.load(context)
        if cached_result is not None:
            print(f"✓ Loaded {len(cached_result)} replacements from cache")
            if status_callback:
                status_callback(f"✓ {len(cached_result)} replacements carregados do cache")
            return cached_result

    # Cache miss or cache disabled - call the LLM
    print("calling LLM API...")
    if status_callback:
        status_callback("Chamando LLM para gerar replacements...")
    sample = random.sample(strings, min(len(strings), 50))

    prompt = PreprocessingPrompt(id=uuid.uuid4(), sample=sample, context=context)

    result = make_prompt(prompt)
    replacements = result.replacements  # type: ignore

    # Save to cache
    if use_cache:
        _replacement_cache.save(context, replacements)

    if status_callback:
        status_callback(f"✓ {len(replacements)} replacements gerados pelo LLM")

    return replacements


def clear_replacement_cache(context: str | None = None) -> None:
    """
    Clear cached replacement results.

    Args:
        context: Specific context to clear. If None, clears all cached replacements.
    """
    _replacement_cache.clear(context)


def get_cache_info(context: str) -> dict | None:
    """
    Get information about cached replacements for a given context.

    Args:
        context: Context string to check

    Returns:
        Dictionary with cache metadata or None if not cached
    """
    return _replacement_cache.get_cache_info(context)


def apply_replacements(
    strings: list[str], replacements: list[Replacement]
) -> list[str]:
    """
    Apply regex replacements to a list of strings.

    Args:
      strings: List of strings to process
      replacements: List of Replacement objects with regex patterns and replacements

    Returns:
      List of strings with all replacements applied
    """
    result = []
    for string in strings:
        processed = string
        for replacement in replacements:
            try:
                processed = re.sub(
                    replacement.regex, replacement.replacement, processed
                )
            except re.error as e:
                print(f"Invalid regex pattern '{replacement.regex}': {e}")
                continue
        result.append(processed)
    return result

    
def split_by_confidence(
    matches: list[QueryMatch],
    max_score_threshold: float = 0.9,
) -> tuple[list[QueryMatch], list[QueryMatch]]:
    """Split QueryMatch objects into low and high confidence groups.

    A match is considered high confidence when its best candidate's score
    meets or exceeds *max_score_threshold*. The winning candidate is marked
    as ``matched = True``.

    Args:
        matches: List of QueryMatch objects to classify.
        max_score_threshold: Score threshold for high confidence (default: 0.9).

    Returns:
        ``(low_confidence, high_confidence)`` — two lists of QueryMatch.
    """
    low_confidence: list[QueryMatch] = []
    high_confidence: list[QueryMatch] = []

    for match in matches:
        if not match.has_candidates:
            continue
        best = match.best_candidate
        if best is not None and best.score >= max_score_threshold:
            best.matched = True
            high_confidence.append(match)
        else:
            low_confidence.append(match)

    return low_confidence, high_confidence


def split_queries_by_confidence(
    queries: list[str],
    relevant_results: list[list[PesquisaPrompt.Item]],
    max_score_threshold: float = 0.9,
) -> tuple[
    tuple[list[str], list[list[PesquisaPrompt.Item]]],
    tuple[list[str], list[list[PesquisaPrompt.Item]]],
]:
    """Deprecated: use ``split_by_confidence`` with ``list[QueryMatch]`` instead.

    Kept for backward compatibility with code that has not yet been migrated.
    """
    matches = [
        QueryMatch(query=q, candidates=items)
        for q, items in zip(queries, relevant_results)
    ]
    low, high = split_by_confidence(matches, max_score_threshold)
    return (
        ([m.query for m in low], [m.candidates for m in low]),
        ([m.query for m in high], [m.candidates for m in high]),
    )