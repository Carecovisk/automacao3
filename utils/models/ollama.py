# Import from parent module
import sys
from collections.abc import Generator
from pathlib import Path

from ollama import chat

sys.path.append(str(Path(__file__).parent.parent))
from ai import Candidates, PesquisaPrompt, PromptResult


def get_candidates_ollama(queries: list[str], results: list[list[PesquisaPrompt.Item]]):
    """
    Fetch candidates using Ollama API.
    Processes queries sequentially and yields (queries, results) tuples.

    Args:
      queries: List of query strings
      results: List of lists of PesquisaPrompt.Item objects

    Yields:
      Tuples of (list[str], list[list[PesquisaPrompt.Item]]) representing processed queries and their results
    """
    # Build prompts from queries and results
    prompts = []
    for i, (query, result_items) in enumerate(zip(queries, results)):
        prompt = PesquisaPrompt(id=i, item_description=query, items=result_items)
        prompts.append(prompt)

    # Process results and reconstruct as (queries, results) tuples
    processed_queries = []
    processed_results = []

    for i, prompt in enumerate(prompts):
        response = chat(
            model="gemma3:4b-it-qat",
            messages=[{"role": "user", "content": prompt.build()}],
            format=Candidates.model_json_schema(),
        )
        candidates = Candidates.model_validate_json(response.message.content)

        # Extract the candidates and convert back to PesquisaPrompt.Item format
        result_items = []
        for candidate in candidates.candidates:
            # Find the matching item from original results based on description
            original_items = results[i]
            matching_item = next(
                (
                    item
                    for item in original_items
                    if item.description == candidate.description
                ),
                None,
            )
            if matching_item:
                result_items.append(matching_item)

        processed_queries.append(queries[i])
        processed_results.append(result_items)

    # Yield as a single tuple
    yield (processed_queries, processed_results)
