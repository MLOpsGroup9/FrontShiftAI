import sys
from pathlib import Path
import subprocess
import time
from datetime import datetime

# --- Ensure FrontShiftAI root is on sys.path BEFORE importing ml_pipeline ---
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]  # /Users/sriks/Documents/Projects/FrontShiftAI
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"✅ Added to sys.path: {project_root}")

# --- Now safe to import from ml_pipeline ---
from ml_pipeline.utils.logger import get_logger

# --- Initialize logger ---
logger = get_logger("eval_pipeline_runner")

PROJECT_ROOT = project_root
EVAL_DIR = PROJECT_ROOT / "evaluation" / "eval_results"

# --- Pipeline Stages ---
STAGES = [
    {
        "name": "RAG Evaluation",
        "script": PROJECT_ROOT / "evaluation" / "rag_eval_metrics.py",
        "expected_output": EVAL_DIR / "rag_eval_results.csv",
    },
    {
        "name": "Bias Detection",
        "script": PROJECT_ROOT / "evaluation" / "bias_detection.py",
        "expected_output": EVAL_DIR / "bias_report.csv",
    },
    {
        "name": "Sensitivity Analysis",
        "script": PROJECT_ROOT / "evaluation" / "sensitivity_analysis.py",
        "expected_output": EVAL_DIR / "sensitivity_report.csv",
    },
]

def run_stage(stage):
    """Run a single pipeline stage and log its result."""
    name = stage["name"]
    script = stage["script"]
    output = stage["expected_output"]

    logger.info(f"🚀 Starting stage: {name}")
    start_time = time.time()

    try:
        subprocess.run(["python", str(script)], check=True)
        duration = round(time.time() - start_time, 2)

        if output.exists():
            logger.info(f"✅ {name} completed successfully in {duration}s | Output: {output.name}")
        else:
            logger.warning(f"⚠️ {name} ran but expected output not found at {output}")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Stage '{name}' failed: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error in stage '{name}': {e}")

def main():
    logger.info("🧩 ===== FrontShiftAI ML Pipeline Runner =====")
    logger.info(f"📅 Run started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Running {len(STAGES)} stages sequentially...\n")

    for stage in STAGES:
        run_stage(stage)

    logger.info("\n🏁 Pipeline run complete.")
    logger.info("====================================================\n")

if __name__ == "__main__":
    main()
