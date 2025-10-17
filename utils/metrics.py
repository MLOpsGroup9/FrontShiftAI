"""
Retrieval evaluation metrics.
Parametric functions to reduce code duplication.
"""

import numpy as np
from typing import List, Dict, Tuple


def calculate_recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Calculate Recall@K metric."""
    if not relevant_ids:
        return 0.0
    retrieved_k = set(retrieved_ids[:k])
    relevant = set(relevant_ids)
    return len(retrieved_k & relevant) / len(relevant)


def calculate_precision_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Calculate Precision@K metric."""
    if not retrieved_ids or k == 0:
        return 0.0
    retrieved_k = set(retrieved_ids[:k])
    relevant = set(relevant_ids)
    return len(retrieved_k & relevant) / k


def calculate_mrr(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """Calculate Mean Reciprocal Rank."""
    relevant = set(relevant_ids)
    for i, doc_id in enumerate(retrieved_ids, 1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def calculate_hit_rate(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Calculate Hit Rate@K (1 if any relevant in top-k, else 0)."""
    retrieved_k = set(retrieved_ids[:k])
    relevant = set(relevant_ids)
    return 1.0 if (retrieved_k & relevant) else 0.0


def calculate_all_metrics(retrieved_ids: List[str], relevant_ids: List[str], 
                          k_values: List[int]) -> Dict[str, float]:
    """Calculate all metrics for given k values in one pass."""
    metrics = {}
    retrieved_set = set(retrieved_ids)
    relevant_set = set(relevant_ids)
    
    # MRR (independent of k)
    metrics['mrr'] = calculate_mrr(retrieved_ids, relevant_ids)
    
    # K-dependent metrics
    for k in k_values:
        retrieved_k = set(retrieved_ids[:k])
        overlap = len(retrieved_k & relevant_set)
        
        metrics[f'recall@{k}'] = overlap / len(relevant_set) if relevant_set else 0.0
        metrics[f'precision@{k}'] = overlap / k if k > 0 else 0.0
        metrics[f'hit_rate@{k}'] = 1.0 if overlap > 0 else 0.0
    
    return metrics


def calculate_batch_metrics(results: List[Tuple[List[str], List[str]]], 
                            k_values: List[int]) -> Dict[str, float]:
    """Calculate average metrics across multiple queries."""
    all_metrics = [calculate_all_metrics(retr, rel, k_values) for retr, rel in results]
    
    # Average all metrics
    averaged = {}
    for key in all_metrics[0].keys():
        values = [m[key] for m in all_metrics]
        averaged[key] = np.mean(values)
        averaged[f'{key}_std'] = np.std(values)
    
    return averaged

