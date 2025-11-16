#!/usr/bin/env python3
"""
Quality Gate Checker for LLM-as-a-Judge Evaluation System

Reads summary.json from chat_pipeline/evaluation/eval_results/<timestamp>/
Compares LLM judge metrics (0-5 scale) against thresholds from quality_gates.yml
Returns PASS/FAIL/PASS_WITH_WARNINGS
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from chat_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


def find_latest_evaluation_result(results_base_dir: str) -> Optional[Path]:
    """Find the most recent evaluation result directory"""
    results_path = Path(results_base_dir)
    
    if not results_path.exists():
        logger.error(f"Results directory not found: {results_base_dir}")
        return None
    
    timestamp_dirs = [d for d in results_path.iterdir() if d.is_dir()]
    
    if not timestamp_dirs:
        logger.error(f"No evaluation results found in {results_base_dir}")
        return None
    
    latest_dir = max(timestamp_dirs, key=lambda d: d.stat().st_mtime)
    
    logger.info(f"Found latest evaluation results: {latest_dir.name}")
    return latest_dir


def load_summary_json(eval_result_dir: Path) -> Optional[Dict]:
    """Load summary.json from evaluation result directory"""
    summary_path = eval_result_dir / "summary.json"
    
    if not summary_path.exists():
        logger.error(f"summary.json not found in {eval_result_dir}")
        return None
    
    try:
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        logger.info("Loaded summary.json successfully")
        return summary
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse summary.json: {e}")
        return None


def load_quality_gates(
    config_path: str, 
    environment: str
) -> Optional[Tuple[Dict, Dict]]:
    """Load quality gate thresholds for environment"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if environment not in config.get('environments', {}):
            logger.error(
                f"Environment '{environment}' not found in quality_gates.yml"
            )
            return None
        
        env_config = config['environments'][environment]
        metric_mapping = config.get('metric_mapping', {})
        
        logger.info(f"Loaded quality gates for environment: {environment}")
        return env_config, metric_mapping
    
    except Exception as e:
        logger.error(f"Failed to load quality gates: {e}")
        return None


def get_nested_value(data: Dict, path: str) -> Optional[float]:
    """Get value from nested dict using dot notation"""
    keys = path.split('.')
    value = data
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    
    return value


def check_thresholds(
    summary: Dict,
    thresholds: Dict,
    metric_mapping: Dict,
    threshold_type: str
) -> Tuple[bool, List[Dict]]:
    """Check if metrics pass thresholds"""
    results = []
    all_passed = True
    
    for metric_key, threshold_config in thresholds.items():
        json_path = metric_mapping.get(metric_key, metric_key)
        actual_value = get_nested_value(summary, json_path)
        
        if actual_value is None:
            logger.warning(
                f"Metric '{metric_key}' not found at path '{json_path}'"
            )
            results.append({
                'metric': metric_key,
                'threshold_config': threshold_config,
                'actual': None,
                'passed': False,
                'reason': 'Metric not found in summary.json'
            })
            all_passed = False
            continue
        
        passed = True
        operator = None
        threshold_value = None
        
        if 'min' in threshold_config:
            threshold_value = threshold_config['min']
            operator = '>='
            passed = actual_value >= threshold_value
        elif 'max' in threshold_config:
            threshold_value = threshold_config['max']
            operator = '<='
            passed = actual_value <= threshold_value
        else:
            logger.warning(f"No min/max defined for '{metric_key}'")
            continue
        
        status_icon = "PASS" if passed else "FAIL"
        logger.info(
            f"{status_icon} {metric_key}: {actual_value:.3f} {operator} "
            f"{threshold_value} [{threshold_type}]"
        )
        
        results.append({
            'metric': metric_key,
            'threshold_value': threshold_value,
            'actual_value': actual_value,
            'passed': passed,
            'operator': operator,
            'description': threshold_config.get('description', '')
        })
        
        if not passed:
            all_passed = False
    
    return all_passed, results


def main():
    parser = argparse.ArgumentParser(
        description='Check quality gates against LLM judge evaluation results'
    )
    parser.add_argument(
        '--environment',
        type=str,
        default='development',
        choices=['development', 'staging', 'production'],
        help='Environment to check thresholds for'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='chat_pipeline/configs/quality_gates.yml',
        help='Path to quality gates config'
    )
    parser.add_argument(
        '--results-dir',
        type=str,
        default='chat_pipeline/evaluation/eval_results',
        help='Base directory for evaluation results'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='chat_pipeline/evaluation/eval_results/quality_gate_result.json',
        help='Output file for quality gate result'
    )
    
    args = parser.parse_args()
    
    logger.info("Quality Gate Checker - LLM Judge Evaluation")
    logger.info(f"Environment: {args.environment}")
    
    latest_eval_dir = find_latest_evaluation_result(args.results_dir)
    if not latest_eval_dir:
        logger.error("No evaluation results found")
        sys.exit(1)
    
    summary = load_summary_json(latest_eval_dir)
    if not summary:
        logger.error("Failed to load summary.json")
        sys.exit(1)
    
    gate_config = load_quality_gates(args.config, args.environment)
    if not gate_config:
        logger.error("Failed to load quality gates")
        sys.exit(1)
    
    env_config, metric_mapping = gate_config
    
    logger.info("Checking CRITICAL thresholds...")
    critical_passed, critical_results = check_thresholds(
        summary,
        env_config.get('critical_thresholds', {}),
        metric_mapping,
        'CRITICAL'
    )
    
    logger.info("Checking WARNING thresholds...")
    warning_passed, warning_results = check_thresholds(
        summary,
        env_config.get('warning_thresholds', {}),
        metric_mapping,
        'WARNING'
    )
    
    deployment_decision = env_config.get('deployment_decision', {})
    require_all_critical = deployment_decision.get('require_all_critical', True)
    allow_warnings = deployment_decision.get('allow_warnings', True)
    
    if critical_passed and warning_passed:
        status = "PASS"
        deployment_approved = True
        logger.info("Quality Gate: PASS - All thresholds met")
    elif critical_passed and allow_warnings:
        status = "PASS_WITH_WARNINGS"
        deployment_approved = True
        logger.warning("Quality Gate: PASS WITH WARNINGS")
    elif critical_passed and not allow_warnings:
        status = "FAIL"
        deployment_approved = False
        logger.error("Quality Gate: FAIL - Warnings not allowed")
    else:
        status = "FAIL"
        deployment_approved = False
        logger.error("Quality Gate: FAIL - Critical thresholds not met")
    
    result = {
        'status': status,
        'deployment_approved': deployment_approved,
        'environment': args.environment,
        'timestamp': datetime.now().isoformat(),
        'evaluation_dir': str(latest_eval_dir),
        'critical_checks': critical_results,
        'warning_checks': warning_results,
        'summary': {
            'critical_passed': critical_passed,
            'warning_passed': warning_passed,
            'total_critical_checks': len(critical_results),
            'critical_failures': sum(
                1 for r in critical_results if not r['passed']
            ),
            'total_warning_checks': len(warning_results),
            'warning_failures': sum(
                1 for r in warning_results if not r['passed']
            )
        }
    }
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Quality gate result saved to: {output_path}")
    
    if deployment_approved:
        logger.info("Deployment APPROVED")
        sys.exit(0)
    else:
        logger.error("Deployment BLOCKED")
        sys.exit(1)


if __name__ == '__main__':
    main()
