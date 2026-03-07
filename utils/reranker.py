from typing import Callable, Optional

from sentence_transformers import CrossEncoder
from tqdm import tqdm

from utils.ai import PesquisaPrompt
from utils.domain import QueryMatch

reranker_model_name = "BAAI/bge-reranker-v2-m3"
reranker = CrossEncoder(reranker_model_name, max_length=512)


def rerank_items(
    matches: list[QueryMatch],
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> list[QueryMatch]:
    """Rerank each QueryMatch's candidates using a Cross-Encoder model.

    Args:
        matches: List of QueryMatch objects to rerank.
        progress_callback: Optional callback function(current, total) for progress tracking.

    Returns:
        New list of QueryMatch objects with candidates sorted by score (descending).
    """
    reranked: list[QueryMatch] = []
    total = len(matches)
    iterator = matches if progress_callback else tqdm(matches, total=total, desc="Reranking")

    for idx, match in enumerate(iterator, start=1):
        pairs = [[match.query, c.description] for c in match.candidates]
        scores = reranker.predict(pairs)

        scored_candidates = [
            PesquisaPrompt.Item(
                description=c.description,
                distance=c.distance,
                score=float(score),
                value=c.value,
            )
            for c, score in zip(match.candidates, scores)
        ]
        reranked.append(
            QueryMatch(
                query=match.query,
                candidates=sorted(scored_candidates, key=lambda c: c.score, reverse=True),
            )
        )

        if progress_callback:
            progress_callback(idx, total)

    return reranked


def filter_items_by_score(
    matches: list[QueryMatch], threshold: float = 0.5
) -> list[QueryMatch]:
    """Keep only candidates whose score >= *threshold* in each QueryMatch.

    Args:
        matches: List of QueryMatch objects.
        threshold: Minimum score threshold (default: 0.5).

    Returns:
        New list of QueryMatch objects with low-scoring candidates removed.
    """
    return [
        QueryMatch(
            query=match.query,
            candidates=[c for c in match.candidates if c.score >= threshold],
        )
        for match in matches
    ]


def filter_items_by_score_gap(
    matches: list[QueryMatch], gap_threshold: float = 0.1
) -> list[QueryMatch]:
    """Keep only candidates within *gap_threshold* of the best score in each QueryMatch.

    Args:
        matches: List of QueryMatch objects.
        gap_threshold: Maximum allowed score gap from the best candidate (default: 0.1).

    Returns:
        New list of QueryMatch objects with out-of-range candidates removed.
    """
    result: list[QueryMatch] = []
    for match in matches:
        if not match.candidates:
            result.append(QueryMatch(query=match.query))
            continue
        max_score = max(c.score for c in match.candidates)
        result.append(
            QueryMatch(
                query=match.query,
                candidates=[
                    c for c in match.candidates if (max_score - c.score) <= gap_threshold
                ],
            )
        )
    return result