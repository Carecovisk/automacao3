from sentence_transformers import CrossEncoder
from tqdm import tqdm
from utils.ai import PesquisaPrompt

reranker_model_name = "BAAI/bge-reranker-v2-m3"
reranker = CrossEncoder(reranker_model_name, max_length=512)


def rerank_items(queries: list[str], items_list: list[list[PesquisaPrompt.Item]]) -> list[list[PesquisaPrompt.Item]]:
    """Rerank PesquisaPrompt.Item objects using a Cross-Encoder model.
    
    Args:
        queries: List of query strings
        items_list: List of lists containing PesquisaPrompt.Item objects
    
    Returns:
        List of lists of PesquisaPrompt.Item objects sorted by score (descending)
    """
    reranked_items = []
    
    for query, items in tqdm(zip(queries, items_list), total=len(queries), desc="Reranking"):
        # Create pairs of [query, item description]
        pairs = [[query, item.description] for item in items]
        
        # Get scores from the reranker
        scores = reranker.predict(pairs)
        
        # Update items with reranker scores and sort
        items_with_scores = [
            PesquisaPrompt.Item(description=item.description, distance=item.distance, score=float(score))
            for item, score in zip(items, scores)
        ]
        ranked = sorted(items_with_scores, key=lambda x: x.score, reverse=True)
        reranked_items.append(ranked)
    
    return reranked_items


def filter_items_by_score(items_list: list[list[PesquisaPrompt.Item]], threshold: float = 0.5) -> list[list[PesquisaPrompt.Item]]:
    """Filter PesquisaPrompt.Item objects by score threshold.
    
    Args:
        items_list: List of lists containing PesquisaPrompt.Item objects
        threshold: Minimum score threshold (default: 0.5)
    
    Returns:
        List of lists with only items that meet or exceed the threshold
    """
    return [
        [item for item in items if item.score >= threshold]
        for items in items_list
    ]

def filter_items_by_score_gap(items_list: list[list[PesquisaPrompt.Item]], gap_threshold: float = 0.1) -> list[list[PesquisaPrompt.Item]]:
    """Filter PesquisaPrompt.Item objects by score gap threshold.
    
    Args:
        items_list: List of lists containing PesquisaPrompt.Item objects
        gap_threshold: Minimum score gap threshold (default: 0.1)
    
    Returns:
        List of lists with only items that have a score gap greater than or equal to the threshold
    """
    filtered_items = []
    
    for items in items_list:
        if not items:
            filtered_items.append([])
            continue
        
        # Get the highest score in the current list
        max_score = max(item.score for item in items)
        
        # Filter items based on the score gap
        filtered = [item for item in items if (max_score - item.score) <= gap_threshold]
        filtered_items.append(filtered)
    
    return filtered_items