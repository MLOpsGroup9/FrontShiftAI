from chat_pipeline.rag.pipeline import RAGPipeline
from chat_pipeline.rag.generator import load_llm

def main():
    print("\n🔵 Interactive RAG CLI (Local LLaMA → Mercury Fallback)")
    print("Type 'exit' to quit.\n")
    
    # Try loading local LLaMA
    try:
        llm = load_llm()
        print("🦙 Using local LLaMA model\n")
    except Exception as e:
        print(f"⚠️ Local LLaMA unavailable: {e}")
        print("➡️  Falling back to Mercury.\n")
        llm = None
    
    pipeline = RAGPipeline()
    
    while True:
        try:
            query = input("You: ").strip()
            if not query or query.lower() == "exit":
                break
            
            # Use the public run() method
            result = pipeline.run(
                query=query,
                stream=False,
                top_k=5
            )
            
            print(f"\n✨ Answer:\n{result.answer}\n")
            
            # Show sources
            if result.metadata:
                print("📚 Sources:")
                for meta in result.metadata:
                    company = meta.get("company", "unknown")
                    filename = meta.get("filename", "unknown")
                    chunk_id = meta.get("chunk_id", "?")
                    print(f"  • {company} | {filename} (chunk {chunk_id})")
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()