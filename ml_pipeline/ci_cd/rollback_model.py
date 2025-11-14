#!/usr/bin/env python3
"""
Model Rollback Script for FrontShiftAI ML Pipeline

Rolls back to a previous model version in the registry. This script:
1. Validates target version exists
2. Loads target version metadata
3. Verifies target metrics were acceptable
4. Backs up current version
5. Restores target version to active location
6. Updates symlinks
7. Creates rollback log
8. Sends notification

Usage:
    python ml_pipeline/ci_cd/rollback_model.py --target-version v5
    python ml_pipeline/ci_cd/rollback_model.py --previous
    python ml_pipeline/ci_cd/rollback_model.py --target-version v3 --reason "Performance degradation"
"""

import sys
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

# Ensure project root is on sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ml_pipeline.utils.logger import get_logger
from ml_pipeline.utils.email_notifier import send_email

logger = get_logger("rollback_model")


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


def get_available_versions(model_name: str, registry_dir: Path) -> List[str]:
    """Get list of available model versions"""
    versions = []
    for version_dir in registry_dir.glob(f"{model_name}_v*"):
        if version_dir.is_dir():
            versions.append(version_dir.name.split("_v")[-1])
    
    # Sort versions numerically
    versions.sort(key=lambda x: int(x) if x.isdigit() else 0)
    return versions


def get_current_version(registry_dir: Path, model_name: str) -> Optional[str]:
    """Get current active version from latest symlink or file"""
    latest_path = registry_dir / "latest"
    
    if latest_path.exists():
        if latest_path.is_symlink():
            target = latest_path.resolve()
        else:
            # Windows: read path from file
            try:
                with open(latest_path, "r") as f:
                    target = Path(f.read().strip())
            except:
                return None
        
        if target.exists() and target.is_dir():
            version = target.name.split("_v")[-1]
            return version
    
    # Fallback: get highest version number
    versions = get_available_versions(model_name, registry_dir)
    return versions[-1] if versions else None


def get_previous_version(model_name: str, registry_dir: Path) -> Optional[str]:
    """Get previous version (one before current)"""
    current = get_current_version(registry_dir, model_name)
    if not current:
        return None
    
    versions = get_available_versions(model_name, registry_dir)
    try:
        current_idx = versions.index(current)
        if current_idx > 0:
            return versions[current_idx - 1]
    except ValueError:
        pass
    
    return None


def load_version_metadata(version_dir: Path) -> Dict:
    """Load metadata.json from version directory"""
    metadata_path = version_dir / "metadata.json"
    
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")
    
    with open(metadata_path, "r") as f:
        return json.load(f)


def validate_rollback_target(version_dir: Path, metadata: Dict) -> bool:
    """Validate that target version has acceptable metrics"""
    metrics = metadata.get("metrics", {})
    
    # Check if metrics exist
    if not metrics:
        logger.warning("No metrics found in target version metadata")
        return True  # Allow rollback anyway
    
    # Check critical thresholds
    mean_sim = metrics.get("mean_semantic_sim", 0.0)
    mean_prec = metrics.get("mean_precision_at_k", 0.0)
    
    # Basic validation: metrics should be reasonable
    if mean_sim < 0.3 or mean_prec < 0.5:
        logger.warning(f"Target version has low metrics: sim={mean_sim}, prec={mean_prec}")
        response = input("Proceed with rollback anyway? (yes/no): ")
        return response.lower() == "yes"
    
    return True


def backup_current_version(registry_dir: Path, model_name: str, current_version: str):
    """Backup current version before rollback"""
    backup_dir = registry_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    current_dir = registry_dir / f"{model_name}_{current_version}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{model_name}_{current_version}_backup_{timestamp}"
    
    if current_dir.exists():
        shutil.copytree(current_dir, backup_path)
        logger.info(f"Backed up current version to: {backup_path}")
    else:
        logger.warning(f"Current version directory not found: {current_dir}")


def create_rollback_log(registry_dir: Path, rollback_info: Dict):
    """Create rollback log entry"""
    log_dir = registry_dir / "rollback_logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(log_file, "w") as f:
        json.dump(rollback_info, f, indent=4)
    
    logger.info(f"Rollback log created: {log_file}")


def rollback_model(
    target_version: Optional[str] = None,
    use_previous: bool = False,
    reason: Optional[str] = None,
    dry_run: bool = False
) -> Dict:
    """Rollback to target version"""
    config = load_pipeline_config()
    model_name = config.get("model", {}).get("name", "llama_3b_instruct")
    registry_dir = project_root / config.get("registry", {}).get("path", "models_registry")
    
    # Determine target version
    if use_previous:
        target_version = get_previous_version(model_name, registry_dir)
        if not target_version:
            raise ValueError("No previous version found")
        logger.info(f"Rolling back to previous version: {target_version}")
    elif not target_version:
        raise ValueError("Must specify --target-version or --previous")
    
    # Validate target version exists
    target_dir = registry_dir / f"{model_name}_{target_version}"
    if not target_dir.exists():
        raise FileNotFoundError(f"Target version directory not found: {target_dir}")
    
    # Load target metadata
    target_metadata = load_version_metadata(target_dir)
    logger.info(f"Target version metadata: {json.dumps(target_metadata, indent=2)}")
    
    # Validate target metrics
    if not validate_rollback_target(target_dir, target_metadata):
        raise ValueError("Target version validation failed")
    
    # Get current version
    current_version = get_current_version(registry_dir, model_name)
    
    if dry_run:
        logger.info("DRY RUN: Would rollback with the following:")
        logger.info(f"  Current version: {current_version}")
        logger.info(f"  Target version: {target_version}")
        logger.info(f"  Reason: {reason or 'Not specified'}")
        return {
            "status": "dry_run",
            "current_version": current_version,
            "target_version": target_version
        }
    
    # Backup current version
    if current_version:
        backup_current_version(registry_dir, model_name, current_version)
    
    # Update latest symlink
    latest_path = registry_dir / "latest"
    if latest_path.exists() or latest_path.is_symlink():
        latest_path.unlink()
    
    if sys.platform == "win32":
        # Windows: create pointer file
        with open(latest_path, "w") as f:
            f.write(str(target_dir))
    else:
        latest_path.symlink_to(target_dir)
    
    logger.info(f"Updated latest symlink to: {target_version}")
    
    # Create rollback log
    rollback_info = {
        "timestamp": datetime.now().isoformat(),
        "current_version": current_version,
        "target_version": target_version,
        "reason": reason or "Not specified",
        "target_metrics": target_metadata.get("metrics", {}),
        "rolled_back_by": os.environ.get("GITHUB_ACTOR", "unknown")
    }
    create_rollback_log(registry_dir, rollback_info)
    
    # Send notification
    try:
        subject = f"FrontShiftAI Model Rollback: {model_name} -> {target_version}"
        message = f"""
Model Rollback Executed

Model: {model_name}
Current Version: {current_version}
Target Version: {target_version}
Reason: {reason or 'Not specified'}
Timestamp: {rollback_info['timestamp']}

Target Version Metrics:
{json.dumps(target_metadata.get('metrics', {}), indent=2)}
"""
        send_email(subject, message)
        logger.info("Rollback notification sent")
    except Exception as e:
        logger.warning(f"Could not send rollback notification: {e}")
    
    logger.info(f"✅ Rollback completed: {model_name} -> {target_version}")
    
    return {
        "status": "success",
        "current_version": current_version,
        "target_version": target_version,
        "target_metrics": target_metadata.get("metrics", {})
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Rollback model to previous version")
    parser.add_argument(
        "--target-version",
        type=str,
        default=None,
        help="Target version to rollback to (e.g., 'v5')"
    )
    parser.add_argument(
        "--previous",
        action="store_true",
        help="Rollback to previous version"
    )
    parser.add_argument(
        "--reason",
        type=str,
        default=None,
        help="Reason for rollback (required for audit)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without actually rolling back"
    )
    parser.add_argument(
        "--list-versions",
        action="store_true",
        help="List available versions and exit"
    )
    args = parser.parse_args()
    
    try:
        config = load_pipeline_config()
        model_name = config.get("model", {}).get("name", "llama_3b_instruct")
        registry_dir = project_root / config.get("registry", {}).get("path", "models_registry")
        
        if args.list_versions:
            versions = get_available_versions(model_name, registry_dir)
            current = get_current_version(registry_dir, model_name)
            print(f"Available versions for {model_name}:")
            for v in versions:
                marker = " (current)" if v == current else ""
                print(f"  v{v}{marker}")
            sys.exit(0)
        
        if not args.reason and not args.dry_run:
            logger.warning("No reason specified for rollback. Use --reason for audit trail.")
            response = input("Continue without reason? (yes/no): ")
            if response.lower() != "yes":
                sys.exit(1)
        
        result = rollback_model(
            target_version=args.target_version,
            use_previous=args.previous,
            reason=args.reason,
            dry_run=args.dry_run
        )
        
        if args.dry_run:
            logger.info("Dry run completed successfully")
        else:
            logger.info(f"Rollback completed: {result['status']}")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()

