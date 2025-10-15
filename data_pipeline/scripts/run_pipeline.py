import os
import subprocess

scripts = [
    "data_extraction.py",
    "preprocess.py",
    "validate_data.py",
    "store_in_chromadb.py",
    "test_rag_llama.py",
]

for script in scripts:
    print(f"\n🚀 Running {script} ...")
    subprocess.run(["python", script], check=True)

print("\n✅ Pipeline complete!")
