"""
Metrics calculation for agent evaluation
"""
from typing import Dict, List, Any
from collections import defaultdict
import numpy as np


class EvaluationMetrics:
    """Calculate and track evaluation metrics"""
    
    def __init__(self):
        self.results = defaultdict(list)
    
    def calculate_intent_accuracy(self, predictions: List[Dict]) -> Dict[str, float]:
        """
        Calculate intent classification accuracy
        
        Args:
            predictions: List of dicts with 'expected' and 'predicted' agents
            
        Returns:
            Dict with accuracy, precision, recall per class
        """
        correct = 0
        total = len(predictions)
        
        # Per-class metrics
        class_stats = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})
        
        for pred in predictions:
            expected = pred['expected']
            predicted = pred['predicted']
            
            if expected == predicted:
                correct += 1
                class_stats[expected]['tp'] += 1
            else:
                class_stats[expected]['fn'] += 1
                class_stats[predicted]['fp'] += 1
        
        # Calculate overall accuracy
        accuracy = correct / total if total > 0 else 0.0
        
        # Calculate per-class precision and recall
        class_metrics = {}
        for agent_class in class_stats:
            tp = class_stats[agent_class]['tp']
            fp = class_stats[agent_class]['fp']
            fn = class_stats[agent_class]['fn']
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            class_metrics[agent_class] = {
                'precision': precision,
                'recall': recall,
                'f1': f1
            }
        
        return {
            'accuracy': accuracy,
            'correct': correct,
            'total': total,
            'class_metrics': class_metrics
        }
    
    def calculate_response_quality(self, responses: List[Dict]) -> Dict[str, float]:
        """
        Calculate response quality metrics
        
        Args:
            responses: List of dicts with response and expected fields
            
        Returns:
            Dict with quality scores
        """
        completeness_scores = []
        
        for resp in responses:
            response_text = resp.get('response', '').lower()
            expected_contains = resp.get('expected_contains', [])
            
            if not expected_contains:
                continue
            
            # Check how many expected terms are present
            found = sum(1 for term in expected_contains if term.lower() in response_text)
            completeness = found / len(expected_contains)
            completeness_scores.append(completeness)
        
        return {
            'avg_completeness': np.mean(completeness_scores) if completeness_scores else 0.0,
            'min_completeness': np.min(completeness_scores) if completeness_scores else 0.0,
            'max_completeness': np.max(completeness_scores) if completeness_scores else 0.0
        }
    
    def calculate_latency_stats(self, latencies: List[float]) -> Dict[str, float]:
        """
        Calculate latency statistics
        
        Args:
            latencies: List of latency values in milliseconds
            
        Returns:
            Dict with latency stats
        """
        if not latencies:
            return {
                'avg_ms': 0.0,
                'p50_ms': 0.0,
                'p95_ms': 0.0,
                'p99_ms': 0.0,
                'min_ms': 0.0,
                'max_ms': 0.0
            }
        
        return {
            'avg_ms': np.mean(latencies),
            'p50_ms': np.percentile(latencies, 50),
            'p95_ms': np.percentile(latencies, 95),
            'p99_ms': np.percentile(latencies, 99),
            'min_ms': np.min(latencies),
            'max_ms': np.max(latencies)
        }
    
    def calculate_success_rate(self, results: List[Dict]) -> Dict[str, float]:
        """
        Calculate success/failure rates
        
        Args:
            results: List of dicts with 'success' boolean
            
        Returns:
            Dict with success metrics
        """
        total = len(results)
        if total == 0:
            return {'success_rate': 0.0, 'failure_rate': 0.0}
        
        successes = sum(1 for r in results if r.get('success', False))
        failures = total - successes
        
        return {
            'success_rate': successes / total,
            'failure_rate': failures / total,
            'total': total,
            'successes': successes,
            'failures': failures
        }
    
    def calculate_agent_metrics(self, agent_results: List[Dict]) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics for an agent
        
        Args:
            agent_results: List of agent execution results
            
        Returns:
            Dict with all metrics
        """
        latencies = [r['latency_ms'] for r in agent_results if 'latency_ms' in r]
        
        return {
            'latency': self.calculate_latency_stats(latencies),
            'success': self.calculate_success_rate(agent_results),
            'quality': self.calculate_response_quality(agent_results),
            'total_tests': len(agent_results)
        }


def generate_summary_report(all_metrics: Dict[str, Any]) -> str:
    """
    Generate human-readable summary report
    
    Args:
        all_metrics: Dict containing all evaluation metrics
        
    Returns:
        Formatted string report
    """
    report = []
    report.append("=" * 60)
    report.append("AGENT EVALUATION SUMMARY")
    report.append("=" * 60)
    report.append("")
    
    # Intent Classification
    if 'intent_classification' in all_metrics:
        ic = all_metrics['intent_classification']
        report.append("INTENT CLASSIFICATION:")
        report.append(f"  Accuracy: {ic['accuracy']:.1%} ({ic['correct']}/{ic['total']})")
        report.append("")
        
        if 'class_metrics' in ic:
            report.append("  Per-Agent Metrics:")
            for agent, metrics in ic['class_metrics'].items():
                report.append(f"    {agent}:")
                report.append(f"      Precision: {metrics['precision']:.1%}")
                report.append(f"      Recall: {metrics['recall']:.1%}")
                report.append(f"      F1: {metrics['f1']:.1%}")
            report.append("")
    
    # PTO Agent
    if 'pto_agent' in all_metrics:
        pto = all_metrics['pto_agent']
        report.append("PTO AGENT:")
        report.append(f"  Tests Run: {pto['total_tests']}")
        report.append(f"  Success Rate: {pto['success']['success_rate']:.1%}")
        report.append(f"  Avg Latency: {pto['latency']['avg_ms']:.0f}ms")
        report.append(f"  P95 Latency: {pto['latency']['p95_ms']:.0f}ms")
        report.append(f"  Response Quality: {pto['quality']['avg_completeness']:.1%}")
        report.append("")
    
    # HR Ticket Agent
    if 'hr_ticket_agent' in all_metrics:
        hr = all_metrics['hr_ticket_agent']
        report.append("HR TICKET AGENT:")
        report.append(f"  Tests Run: {hr['total_tests']}")
        report.append(f"  Success Rate: {hr['success']['success_rate']:.1%}")
        report.append(f"  Avg Latency: {hr['latency']['avg_ms']:.0f}ms")
        report.append(f"  P95 Latency: {hr['latency']['p95_ms']:.0f}ms")
        report.append(f"  Response Quality: {hr['quality']['avg_completeness']:.1%}")
        report.append("")
    
    # Website Extraction Agent
    if 'website_extraction_agent' in all_metrics:
        web = all_metrics['website_extraction_agent']
        report.append("WEBSITE EXTRACTION AGENT:")
        report.append(f"  Tests Run: {web['total_tests']}")
        report.append(f"  Success Rate: {web['success']['success_rate']:.1%}")
        report.append(f"  Avg Latency: {web['latency']['avg_ms']:.0f}ms")
        report.append(f"  P95 Latency: {web['latency']['p95_ms']:.0f}ms")
        report.append(f"  Response Quality: {web['quality']['avg_completeness']:.1%}")
        report.append("")
    
    # Performance Targets
    report.append("PERFORMANCE TARGETS:")
    
    # Check intent accuracy
    if 'intent_classification' in all_metrics:
        ic_acc = all_metrics['intent_classification']['accuracy']
        status = "✓ PASS" if ic_acc >= 0.85 else "✗ FAIL"
        report.append(f"  Intent Accuracy ≥ 85%: {status} ({ic_acc:.1%})")
    
    # Check latency for each agent
    for agent_key in ['pto_agent', 'hr_ticket_agent', 'website_extraction_agent']:
        if agent_key in all_metrics:
            p95 = all_metrics[agent_key]['latency']['p95_ms']
            status = "✓ PASS" if p95 < 5000 else "✗ FAIL"
            agent_name = agent_key.replace('_', ' ').title()
            report.append(f"  {agent_name} P95 < 5s: {status} ({p95:.0f}ms)")
    
    report.append("")
    report.append("=" * 60)
    
    return "\n".join(report)