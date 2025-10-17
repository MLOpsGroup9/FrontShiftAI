"""
Master Pipeline Runner
Orchestrates the complete data processing pipeline
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

def print_banner(text):
    """Print a formatted banner."""
    print(f"\n{'='*70}")
    print(f" {text}")
    print(f"{'='*70}\n")

def run_step(script_name, description):
    """Run a pipeline step."""
    print_banner(f"Step: {description}")
    print(f"Running: {script_name}\n")
    
    result = subprocess.run(
        [sys.executable, f"scripts/{script_name}"],
        capture_output=False,
        text=True
    )
    
    if result.returncode != 0:
        print(f"\n[ERROR] Error in {description}")
        return False
    
    print(f"\n[SUCCESS] {description} completed successfully!")
    return True

def main():
    parser = argparse.ArgumentParser(description="Run the complete data pipeline")
    parser.add_argument("--extract", action="store_true", help="Run data extraction from PDFs")
    parser.add_argument("--preprocess", action="store_true", help="Run preprocessing and chunking")
    parser.add_argument("--embed", action="store_true", help="Run embedding and ChromaDB storage")
    parser.add_argument("--stats", action="store_true", help="Generate dataflow statistics")
    parser.add_argument("--test", action="store_true", help="Test RAG pipeline")
    parser.add_argument("--all", action="store_true", help="Run all pipeline steps")
    
    args = parser.parse_args()
    
    # If no specific steps selected, run all
    if not any([args.extract, args.preprocess, args.embed, args.stats, args.test, args.all]):
        args.all = True
    
    print_banner("FrontShiftAI Data Pipeline")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    success = True
    
    # Step 1: Data Extraction
    if args.all or args.extract:
        if not run_step("data_extraction.py", "Data Extraction"):
            success = False
            if not args.all:
                return
    
    # Step 2: Preprocessing
    if args.all or args.preprocess:
        if not run_step("preprocess.py", "Preprocessing & Chunking"):
            success = False
            if not args.all:
                return
    
    # Step 3: Embedding
    if args.all or args.embed:
        if not run_step("store_in_chromadb.py", "Embedding & ChromaDB Storage"):
            success = False
            if not args.all:
                return
    
    # Step 4: Statistics
    if args.all or args.stats:
        if not run_step("dataflow_statistics.py", "Dataflow Statistics"):
            success = False
            if not args.all:
                return
    
    # Step 5: Testing (optional, interactive)
    if args.test:
        print_banner("RAG Pipeline Testing")
        print("Running interactive test mode...")
        print("You can test queries manually.\n")
        subprocess.run([sys.executable, "scripts/test_rag.py"])
    
    # Final summary
    print_banner("Pipeline Summary")
    if success:
        print("[SUCCESS] All pipeline steps completed successfully!")
    else:
        print("[WARNING] Some pipeline steps encountered errors.")
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nLogs are available in: logs/")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()

