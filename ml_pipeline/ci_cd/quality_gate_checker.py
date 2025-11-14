#!/usr/bin/env python3
"""
Quality Gate Checker for FrontShiftAI ML Pipeline

Loads evaluation metrics from unified_summary.json and compares them against
thresholds defined in quality_gates.yml. Returns deployment decision based on
environment-specific quality gates.

Usage:
    python ml_pipeline/ci_cd/quality_gate_checker.py --environment production
    python ml_pipeline/ci_cd/quality_gate_checker.py --environment staging --summary-path custom/path.json
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import yaml

# Ensure project root is on sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ml_pipeline.utils.logger import get_logger

logger = get_logger("quality_gate_checker")


class QualityGateResult:
    """Container for quality gate check results"""
    def __init__(self, status: str, deployment_approved: bool, checks: List[Dict], warnings: List[str] = None):
        self.status = status  # "PASS", "PASS_WITH_WARNINGS", "FAIL"
        self.deployment_approved = deployment_approved
        self.checks = checks  # List of check results
        self.warnings = warnings or []


def load_quality_gates(environment: str = "production") -> Dict:
    """Load quality gate thresholds from config file"""
    config_path = project_root / "ml_pipeline" / "configs" / "quality_gates.yml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Quality gates config not found: {config_path}")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Get environment config or use default
    env_config = config.get("environments", {}).get(environment)
    if not env_config:
        default_env = config.get("default_environment", "production")
        logger.warning(f"Environment '{environment}' not found, using '{default_env}'")
        env_config = config.get("environments", {}).get(default_env)
    
    if not env_config:
        raise ValueError(f"No quality gate configuration found for environment: {environment}")
    
    return {
        "critical": env_config.get("critical", {}),
        "warning": env_config.get("warning", {}),
        "performance": env_config.get("performance", {}),
        "deployment_decision": env_config.get("deployment_decision", {}),
        "metric_mapping": config.get("metric_mapping", {})
    }


def load_evaluation_metrics(summary_path: Optional[Path] = None) -> Dict:
    """Load evaluation metrics from unified_summary.json"""
    if summary_path is None:
        summary_path = project_root / "ml_pipeline" / "evaluation" / "eval_results" / "unified_summary.json"
    
    if not summary_path.exists():
        raise FileNotFoundError(f"Evaluation summary not found: {summary_path}")
    
    with open(summary_path, "r") as f:
        metrics = json.load(f)
    
    return metrics


def get_metric_value(metrics: Dict, metric_key: str, metric_mapping: Dict) -> Optional[float]:
    """Extract metric value from nested metrics dict using mapping"""
    # Handle mapped keys like "rag.mean_semantic_sim"
    if metric_key in metric_mapping:
        path = metric_mapping[metric_key].split(".")
        value = metrics
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return float(value) if value is not None else None
    
    # Direct lookup
    if metric_key in metrics:
        return float(metrics[metric_key])
    
    # Try nested lookup
    for section in ["rag", "bias", "sensitivity"]:
        if section in metrics and metric_key in metrics[section]:
            return float(metrics[section][metric_key])
    
    return None


def calculate_bias_gap(metrics: Dict) -> Optional[float]:
    """Calculate maximum bias gap from bias report"""
    try:
        bias_report_path = project_root / "ml_pipeline" / "evaluation" / "eval_results" / "bias_report.csv"
        if bias_report_path.exists():
            import pandas as pd
            df = pd.read_csv(bias_report_path)
            if "sim_gap_vs_mean" in df.columns:
                max_gap = abs(df["sim_gap_vs_mean"].max())
                return float(max_gap)
    except Exception as e:
        logger.warning(f"Could not calculate bias gap: {e}")
    
    return None


def calculate_sensitivity_variance(metrics: Dict) -> Optional[float]:
    """Calculate variance in sensitivity analysis"""
    try:
        sensitivity_path = project_root / "ml_pipeline" / "evaluation" / "eval_results" / "sensitivity_report.csv"
        if sensitivity_path.exists():
            import pandas as pd
            df = pd.read_csv(sensitivity_path)
            if "context_similarity" in df.columns:
                variance = df["context_similarity"].var()
                return float(variance)
    except Exception as e:
        logger.warning(f"Could not calculate sensitivity variance: {e}")
    
    return None


def check_threshold(metric_value: Optional[float], threshold: Dict, check_type: str) -> Tuple[bool, str]:
    """Check if metric value meets threshold"""
    if metric_value is None:
        return False, f"Metric value not found"
    
    if "min" in threshold:
        min_val = threshold["min"]
        if metric_value < min_val:
            return False, f"{check_type}: {metric_value:.4f} < {min_val:.4f} (min required)"
        return True, f"{check_type}: {metric_value:.4f} >= {min_val:.4f} [PASS]"
    
    if "max" in threshold:
        max_val = threshold["max"]
        if metric_value > max_val:
            return False, f"{check_type}: {metric_value:.4f} > {max_val:.4f} (max allowed)"
        return True, f"{check_type}: {metric_value:.4f} <= {max_val:.4f} [PASS]"
    
    return True, f"{check_type}: No threshold defined"


def check_quality_gates(metrics: Dict, gates_config: Dict, environment: str) -> QualityGateResult:
    """Check all quality gates against metrics"""
    critical_thresholds = gates_config["critical"]
    warning_thresholds = gates_config["warning"]
    metric_mapping = gates_config["metric_mapping"]
    deployment_decision = gates_config["deployment_decision"]
    
    checks = []
    critical_failures = []
    warnings = []
    
    # Check critical thresholds
    for metric_key, threshold in critical_thresholds.items():
        if metric_key == "max_bias_gap":
            metric_value = calculate_bias_gap(metrics)
        elif metric_key == "sensitivity_variance":
            metric_value = calculate_sensitivity_variance(metrics)
        else:
            metric_value = get_metric_value(metrics, metric_key, metric_mapping)
        
        passed, message = check_threshold(metric_value, threshold, "CRITICAL")
        checks.append({
            "metric": metric_key,
            "type": "critical",
            "passed": passed,
            "value": metric_value,
            "threshold": threshold,
            "message": message
        })
        
        if not passed:
            critical_failures.append(metric_key)
    
    # Check warning thresholds
    for metric_key, threshold in warning_thresholds.items():
        if metric_key == "sensitivity_variance":
            metric_value = calculate_sensitivity_variance(metrics)
        else:
            metric_value = get_metric_value(metrics, metric_key, metric_mapping)
        
        passed, message = check_threshold(metric_value, threshold, "WARNING")
        checks.append({
            "metric": metric_key,
            "type": "warning",
            "passed": passed,
            "value": metric_value,
            "threshold": threshold,
            "message": message
        })
        
        if not passed:
            warnings.append(metric_key)
    
    # Determine status
    require_all_critical = deployment_decision.get("require_all_critical", True)
    allow_warnings = deployment_decision.get("allow_warnings", True)
    
    if critical_failures:
        status = "FAIL"
        deployment_approved = False
    elif warnings and not allow_warnings:
        status = "PASS_WITH_WARNINGS"
        deployment_approved = False
    elif warnings:
        status = "PASS_WITH_WARNINGS"
        deployment_approved = True
    else:
        status = "PASS"
        deployment_approved = True
    
    return QualityGateResult(status, deployment_approved, checks, warnings)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Check quality gates for ML pipeline")
    parser.add_argument(
        "--environment", 
        "-e",
        type=str,
        default="production",
        choices=["development", "staging", "production"],
        help="Environment for quality gate thresholds"
    )
    parser.add_argument(
        "--summary-path",
        type=str,
        default=None,
        help="Path to unified_summary.json (default: ml_pipeline/evaluation/eval_results/unified_summary.json)"
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output results as JSON"
    )
    args = parser.parse_args()
    
    try:
        # Load configuration and metrics
        logger.info(f"Loading quality gates for environment: {args.environment}")
        gates_config = load_quality_gates(args.environment)
        
        summary_path = Path(args.summary_path) if args.summary_path else None
        logger.info(f"Loading evaluation metrics from: {summary_path or 'default path'}")
        metrics = load_evaluation_metrics(summary_path)
        
        # Check quality gates
        logger.info("Checking quality gates...")
        result = check_quality_gates(metrics, gates_config, args.environment)
        
        # Output results
        if args.output_json:
            output = {
                "status": result.status,
                "deployment_approved": result.deployment_approved,
                "environment": args.environment,
                "checks": result.checks,
                "warnings": result.warnings
            }
            print(json.dumps(output, indent=2))
        else:
            logger.info("=" * 60)
            logger.info("Quality Gate Results")
            logger.info("=" * 60)
            logger.info(f"Status: {result.status}")
            logger.info(f"Deployment Approved: {result.deployment_approved}")
            logger.info("")
            
            for check in result.checks:
                status_icon = "[PASS]" if check["passed"] else "[FAIL]"
                logger.info(f"{status_icon} {check['metric']} ({check['type']}): {check['message']}")
            
            if result.warnings:
                logger.info("")
                logger.warning(f"Warnings: {', '.join(result.warnings)}")
        
        # Set GitHub Actions output if in CI
        if os.environ.get("GITHUB_ACTIONS"):
            with open(os.environ.get("GITHUB_OUTPUT", "/dev/stdout"), "a") as f:
                f.write(f"deployment_approved={str(result.deployment_approved).lower()}\n")
                f.write(f"quality_gate_status={result.status}\n")
        
        # Exit with appropriate code
        sys.exit(0 if result.deployment_approved else 1)
        
    except Exception as e:
        logger.error(f"Quality gate check failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()

