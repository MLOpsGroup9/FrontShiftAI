import os
import subprocess
from datetime import datetime

# --- Directory setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /data_pipeline
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# --- Pipeline script order ---
DEFAULT_SCRIPTS = [
    "download_data.py",
    "pdf_parser.py",
    "preprocess.py",
    "chunker.py",
    "validate_data.py",
    "store_in_chromadb.py",
]


def run_pipeline(script_names=None):
    """Run the pipeline scripts sequentially and return the log file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOGS_DIR, f"pipeline_run_{timestamp}.log")
    scripts = script_names or DEFAULT_SCRIPTS

    with open(log_file, "w", encoding="utf-8") as log:
        for script in scripts:
            script_path = os.path.join(SCRIPTS_DIR, script)
            print(f"\n🚀 Running {script} ...")
            log.write(f"\n🚀 Running {script} ...\n")
            log.flush()

            try:
                subprocess.run(["python", script_path], check=True, stdout=log, stderr=log)
                print(f"✅ {script} completed successfully.")
                log.write(f"✅ {script} completed successfully.\n")
            except subprocess.CalledProcessError as e:
                print(f"❌ {script} failed. Check {log_file} for details.")
                log.write(f"❌ {script} failed with error code {e.returncode}\n")
                break

    print(f"\n📘 Pipeline execution finished. Logs saved to: {log_file}")
    return log_file


if __name__ == "__main__":
    run_pipeline()
