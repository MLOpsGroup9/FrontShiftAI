#!/usr/bin/env python3
"""
Environment Validation Script for FrontShiftAI ML Pipeline

Validates that all prerequisites are met before running the ML pipeline:
- Python version
- Required packages
- ChromaDB accessibility
- Model files
- Environment variables
- System resources

Usage:
    python ml_pipeline/ci_cd/validate_environment.py
    python ml_pipeline/ci_cd/validate_environment.py --verbose
"""

import sys
import os
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

# Ensure project root is on sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ml_pipeline.utils.logger import get_logger

logger = get_logger("validate_environment")

# Load pipeline config
try:
    import yaml
    config_path = project_root / "ml_pipeline" / "configs" / "pipeline_config.yml"
    if config_path.exists():
        with open(config_path, "r") as f:
            pipeline_config = yaml.safe_load(f)
    else:
        pipeline_config = {}
except ImportError:
    logger.warning("PyYAML not installed, using default config")
    pipeline_config = {}
except Exception as e:
    logger.warning(f"Could not load pipeline config: {e}")
    pipeline_config = {}


class ValidationResult:
    """Container for validation check results"""
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message


def check_python_version() -> ValidationResult:
    """Check Python version is 3.12"""
    version = sys.version_info
    if version.major == 3 and version.minor == 12:
        return ValidationResult("Python Version", True, f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        return ValidationResult(
            "Python Version", 
            False, 
            f"Python {version.major}.{version.minor}.{version.micro} found, but 3.12 is required"
        )


def check_required_packages() -> ValidationResult:
    """Check all required packages from requirements.txt are installed"""
    requirements_file = project_root / "requirements.txt"
    if not requirements_file.exists():
        return ValidationResult("Required Packages", False, f"requirements.txt not found at {requirements_file}")
    
    missing_packages = []
    try:
        with open(requirements_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before == or >=)
                    package_name = line.split("==")[0].split(">=")[0].split(" ")[0].strip()
                    if package_name:
                        try:
                            __import__(package_name.replace("-", "_"))
                        except ImportError:
                            missing_packages.append(package_name)
    except Exception as e:
        return ValidationResult("Required Packages", False, f"Error reading requirements.txt: {e}")
    
    if missing_packages:
        return ValidationResult(
            "Required Packages", 
            False, 
            f"Missing packages: {', '.join(missing_packages)}"
        )
    else:
        return ValidationResult("Required Packages", True, "All required packages installed")


def check_chromadb() -> ValidationResult:
    """Check ChromaDB is accessible"""
    try:
        import chromadb
        vector_db_path = project_root / pipeline_config.get("vector_db", {}).get("path", "data_pipeline/data/vector_db")
        
        if not vector_db_path.exists():
            return ValidationResult(
                "ChromaDB Accessibility", 
                False, 
                f"Vector DB path does not exist: {vector_db_path}"
            )
        
        # Try to connect
        client = chromadb.PersistentClient(path=str(vector_db_path))
        collection_name = pipeline_config.get("vector_db", {}).get("collection_name", "frontshift_handbooks")
        
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            return ValidationResult(
                "ChromaDB Accessibility", 
                True, 
                f"Connected to collection '{collection_name}' with {count} documents"
            )
        except Exception as e:
            return ValidationResult(
                "ChromaDB Accessibility", 
                False, 
                f"Collection '{collection_name}' not found or error: {e}"
            )
    except ImportError:
        return ValidationResult("ChromaDB Accessibility", False, "chromadb package not installed")
    except Exception as e:
        return ValidationResult("ChromaDB Accessibility", False, f"Error connecting to ChromaDB: {e}")


def check_model_file() -> ValidationResult:
    """Check model file exists"""
    model_path = project_root / pipeline_config.get("model", {}).get("path", "models/Llama-3.2-3B-Instruct-Q4_K_S.gguf")
    
    if not model_path.exists():
        return ValidationResult(
            "Model File", 
            False, 
            f"Model file not found: {model_path}"
        )
    
    size_mb = model_path.stat().st_size / (1024 * 1024)
    return ValidationResult(
        "Model File", 
        True, 
        f"Model file found: {model_path.name} ({size_mb:.2f} MB)"
    )


def check_environment_variables() -> ValidationResult:
    """Check required environment variables are set"""
    required_vars = pipeline_config.get("required_env_vars", [])
    missing_vars = []
    placeholder_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        elif value.startswith("PLACEHOLDER_") or "placeholder" in value.lower():
            placeholder_vars.append(var)
            logger.warning(f"  {var} is set to placeholder value")
    
    if missing_vars:
        message = f"Missing environment variables: {', '.join(missing_vars)}"
        message += "\n  See ml_pipeline/ci_cd/docs/SECRETS_SETUP.md for setup instructions"
        return ValidationResult(
            "Environment Variables", 
            False, 
            message
        )
    
    if placeholder_vars:
        message = f"Placeholder values detected: {', '.join(placeholder_vars)}"
        message += "\n  Workflows will fail until real secrets are configured"
        message += "\n  This is fine for review, but needs to be fixed before running on main"
        logger.warning(message)
        return ValidationResult(
            "Environment Variables", 
            True,  # Don't fail, just warn
            f"All required environment variables set (with placeholders: {', '.join(placeholder_vars)})"
        )
    else:
        return ValidationResult(
            "Environment Variables", 
            True, 
            f"All required environment variables set: {', '.join(required_vars)}"
        )


def check_disk_space() -> ValidationResult:
    """Check sufficient disk space (at least 5GB free)"""
    try:
        if platform.system() == "Windows":
            import shutil
            total, used, free = shutil.disk_usage(project_root)
        else:
            stat = os.statvfs(project_root)
            free = stat.f_bavail * stat.f_frsize
        
        free_gb = free / (1024 ** 3)
        min_required_gb = 5
        
        if free_gb >= min_required_gb:
            return ValidationResult(
                "Disk Space", 
                True, 
                f"Sufficient disk space: {free_gb:.2f} GB free (required: {min_required_gb} GB)"
            )
        else:
            return ValidationResult(
                "Disk Space", 
                False, 
                f"Insufficient disk space: {free_gb:.2f} GB free (required: {min_required_gb} GB)"
            )
    except Exception as e:
        return ValidationResult("Disk Space", False, f"Error checking disk space: {e}")


def check_memory() -> ValidationResult:
    """Check system memory (at least 8GB recommended)"""
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_kb = int(line.split()[1])
                        total_gb = total_kb / (1024 ** 2)
                        if total_gb >= 8:
                            return ValidationResult(
                                "Memory", 
                                True, 
                                f"Sufficient memory: {total_gb:.2f} GB total"
                            )
                        else:
                            return ValidationResult(
                                "Memory", 
                                False, 
                                f"Low memory: {total_gb:.2f} GB total (8 GB recommended)"
                            )
        # For Windows/macOS, just report as warning
        return ValidationResult(
            "Memory", 
            True, 
            "Memory check skipped (platform-specific implementation needed)"
        )
    except Exception as e:
        return ValidationResult("Memory", True, f"Memory check skipped: {e}")


def check_pythonpath() -> ValidationResult:
    """Check PYTHONPATH includes project root"""
    pythonpath = os.environ.get("PYTHONPATH", "")
    project_root_str = str(project_root)
    
    if project_root_str in pythonpath or str(project_root) in sys.path:
        return ValidationResult(
            "PYTHONPATH", 
            True, 
            f"Project root in PYTHONPATH or sys.path"
        )
    else:
        return ValidationResult(
            "PYTHONPATH", 
            False, 
            f"Project root not in PYTHONPATH. Set: export PYTHONPATH={project_root_str}"
        )


def run_all_checks(verbose: bool = False) -> Tuple[List[ValidationResult], bool]:
    """Run all validation checks"""
    checks = [
        check_python_version(),
        check_required_packages(),
        check_chromadb(),
        check_model_file(),
        check_environment_variables(),
        check_disk_space(),
        check_memory(),
        check_pythonpath(),
    ]
    
    all_passed = all(check.passed for check in checks)
    
    if verbose:
        logger.info("=" * 60)
        logger.info("Environment Validation Report")
        logger.info("=" * 60)
        for check in checks:
            status = "[PASS]" if check.passed else "[FAIL]"
            logger.info(f"{status}: {check.name}")
            if check.message:
                logger.info(f"   {check.message}")
        logger.info("=" * 60)
        logger.info(f"Overall Status: {'[PASS] ALL CHECKS PASSED' if all_passed else '[FAIL] SOME CHECKS FAILED'}")
    
    return checks, all_passed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate ML pipeline environment")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    logger.info("Starting environment validation...")
    checks, all_passed = run_all_checks(verbose=args.verbose or True)
    
    if all_passed:
        logger.info("[PASS] Environment validation passed")
        sys.exit(0)
    else:
        logger.error("[FAIL] Environment validation failed")
        failed_checks = [c for c in checks if not c.passed]
        for check in failed_checks:
            logger.error(f"  - {check.name}: {check.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()

