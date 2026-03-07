from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from utils.ai import PesquisaPrompt


@dataclass
class QueryMatch:
    """A query paired with its candidate document matches.

    Serves as the common data structure that flows through the entire
    matching pipeline — preprocessing, reranking, filtering and splitting.
    Each stage receives and returns ``list[QueryMatch]`` instead of
    the fragile parallel ``(queries, items_list)`` pattern.
    """

    query: str
    candidates: list[PesquisaPrompt.Item] = field(default_factory=list)

    @property
    def has_candidates(self) -> bool:
        """True when there is at least one candidate."""
        return bool(self.candidates)

    @property
    def best_candidate(self) -> Optional[PesquisaPrompt.Item]:
        """The candidate with the highest score, or None if there are no candidates."""
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.score)

    def is_high_confidence(self, threshold: float = 0.9) -> bool:
        """True when the best candidate's score meets or exceeds *threshold*."""
        best = self.best_candidate
        return best is not None and best.score >= threshold
