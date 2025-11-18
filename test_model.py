from llama_cpp import Llama
import sys

print("Loading model...")
try:
    llm = Llama(
        model_path="./models/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        n_ctx=2048,
        n_threads=8,
        n_gpu_layers=35,
        verbose=False
    )
    print("✅ Model loaded successfully!")
    
    print("\nTesting generation...")
    output = llm(
        "What is 2+2?",
        max_tokens=50,
        temperature=0.7,
        stop=["</s>", "\n\n"]
    )
    
    print("✅ Generation successful!")
    print(f"\nResponse: {output['choices'][0]['text']}")
    print(f"\nTokens used: {output['usage']['total_tokens']}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
