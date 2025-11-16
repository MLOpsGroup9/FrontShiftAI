#!/usr/bin/env python3
"""
Model Deployment Script for FrontShiftAI ML Pipeline

Deploys evaluated model to the versioned registry. This script:
1. Validates model artifact exists
2. Loads metrics from unified_summary.json
3. Calls existing push_to_registry.py for versioning
4. Creates metadata with git commit hash and quality gate status
5. Updates symlink to latest version
6. Logs deployment to W&B

Usage:
    python ml_pipeline/ci_cd/deploy_model.py
    python ml_pipeline/ci_cd/deploy_model.py --model-path custom/path.gguf
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Ensure project root is on sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ml_pipeline.utils.logger import get_logger
from ml_pipeline.tracking.push_to_registry import push_to_registry
from ml_pipeline.tracking.exp_tracking import log_metrics

logger = get_logger("deploy_model")


def get_git_commit_hash() -> Optional[str]:
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()[:7]  # Short hash
    except Exception as e:
        logger.warning(f"Could not get git commit hash: {e}")
        return None


def get_git_branch() -> Optional[str]:
    """Get current git branch"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Could not get git branch: {e}")
        return None


def load_pipeline_config() -> Dict:
    """Load pipeline configuration"""
    try:
        import yaml
        config_path = project_root / "ml_pipeline" / "configs" / "pipeline_config.yml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Could not load pipeline config: {e}")
        return {}


def load_evaluation_metrics() -> Dict:
    """Load evaluation metrics from unified_summary.json"""
    summary_path = project_root / "ml_pipeline" / "evaluation" / "eval_results" / "unified_summary.json"
    
    if not summary_path.exists():
        raise FileNotFoundError(f"Evaluation summary not found: {summary_path}")
    
    with open(summary_path, "r") as f:
        return json.load(f)


def validate_model_file(model_path: Path) -> bool:
    """Validate model file exists and is accessible"""
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return False
    
    if not model_path.is_file():
        logger.error(f"Model path is not a file: {model_path}")
        return False
    
    size_mb = model_path.stat().st_size / (1024 * 1024)
    logger.info(f"Model file validated: {model_path.name} ({size_mb:.2f} MB)")
    return True


def update_metadata_with_deployment_info(metadata_path: Path, quality_gate_status: Optional[str] = None):
    """Update metadata.json with additional deployment information"""
    if not metadata_path.exists():
        logger.warning(f"Metadata file not found: {metadata_path}")
        return
    
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    # Add deployment info
    metadata["deployment"] = {
        "timestamp": datetime.now().isoformat(),
        "git_commit": get_git_commit_hash(),
        "git_branch": get_git_branch(),
        "quality_gate_status": quality_gate_status or "unknown",
        "deployed_by": os.environ.get("GITHUB_ACTOR", "unknown")
    }
    
    # Add GitHub Actions context if available
    if os.environ.get("GITHUB_RUN_ID"):
        metadata["deployment"]["github_run_id"] = os.environ.get("GITHUB_RUN_ID")
        metadata["deployment"]["github_run_url"] = (
            f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
        )
    
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    
    logger.info(f"Updated metadata with deployment information: {metadata_path}")


def create_latest_symlink(registry_dir: Path, model_name: str, version: str):
    """Create or update symlink to latest version"""
    latest_path = registry_dir / "latest"
    version_dir = registry_dir / f"{model_name}_{version}"
    
    try:
        # Remove existing symlink if it exists
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        
        # Create new symlink
        if sys.platform == "win32":
            # Windows doesn't support symlinks easily, create a text file with path
            with open(latest_path, "w") as f:
                f.write(str(version_dir))
            logger.info(f"Created latest pointer file: {latest_path}")
        else:
            latest_path.symlink_to(version_dir)
            logger.info(f"Created latest symlink: {latest_path} -> {version_dir}")
    except Exception as e:
        logger.warning(f"Could not create latest symlink: {e}")


def deploy_model(
    model_path: Optional[Path] = None,
    quality_gate_status: Optional[str] = None,
    dry_run: bool = False
) -> Dict:
    """Deploy model to registry"""
    config = load_pipeline_config()
    
    # Determine model path
    if model_path is None:
        model_path = project_root / config.get("model", {}).get("path", "models/Llama-3.2-3B-Instruct-Q4_K_S.gguf")
    else:
        model_path = Path(model_path)
    
    # Validate model file
    if not validate_model_file(model_path):
        raise FileNotFoundError(f"Model file validation failed: {model_path}")
    
    # Load evaluation metrics
    logger.info("Loading evaluation metrics...")
    metrics_dict = load_evaluation_metrics()
    
    # Extract metrics for registry
    rag_metrics = metrics_dict.get("rag", {})
    registry_metrics = {
        "mean_semantic_sim": rag_metrics.get("mean_semantic_sim", 0.0),
        "mean_precision_at_k": rag_metrics.get("mean_precision_at_k", 0.0)
    }
    
    # Get model name and file name
    model_name = config.get("model", {}).get("name", "llama_3b_instruct")
    model_file = model_path.name
    
    if dry_run:
        logger.info("DRY RUN: Would deploy model with the following:")
        logger.info(f"  Model: {model_name}")
        logger.info(f"  File: {model_file}")
        logger.info(f"  Metrics: {registry_metrics}")
        return {"status": "dry_run", "model_name": model_name, "metrics": registry_metrics}
    
    # Deploy to registry using existing function
    logger.info(f"Deploying model '{model_name}' to registry...")
    metadata = push_to_registry(model_name, model_file, registry_metrics)
    
    # Update metadata with deployment info
    registry_dir = project_root / config.get("registry", {}).get("path", "models_registry")
    version_dir = registry_dir / f"{model_name}_{metadata['version']}"
    metadata_path = version_dir / "metadata.json"
    
    update_metadata_with_deployment_info(metadata_path, quality_gate_status)
    
    # Create latest symlink
    create_latest_symlink(registry_dir, model_name, metadata['version'])
    
    # Log deployment to W&B
    try:
        deployment_metrics = {
            "deployment_version": metadata['version'],
            "deployment_timestamp": metadata['timestamp'],
            **registry_metrics
        }
        artifacts = {"model_metadata": metadata_path}
        log_metrics("Model_Deployment", model_name, deployment_metrics, artifacts)
        logger.info("Deployment logged to W&B")
    except Exception as e:
        logger.warning(f"Could not log deployment to W&B: {e}")
    
    logger.info(f"✅ Model deployed successfully: {model_name} {metadata['version']}")
    logger.info(f"📁 Registry location: {version_dir}")
    
    return {
        "status": "success",
        "model_name": model_name,
        "version": metadata['version'],
        "registry_path": str(version_dir),
        "metrics": registry_metrics
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Deploy model to registry")
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Path to model file (default: from pipeline_config.yml)"
    )
    parser.add_argument(
        "--quality-gate-status",
        type=str,
        default=None,
        choices=["PASS", "PASS_WITH_WARNINGS", "FAIL"],
        help="Quality gate status to include in metadata"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without actually deploying"
    )
    args = parser.parse_args()
    
    try:
        result = deploy_model(
            model_path=Path(args.model_path) if args.model_path else None,
            quality_gate_status=args.quality_gate_status,
            dry_run=args.dry_run
        )
        
        if args.dry_run:
            logger.info("Dry run completed successfully")
        else:
            logger.info(f"Deployment completed: {result['status']}")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()

