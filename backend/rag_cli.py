from chat_pipeline.rag.pipeline import RAGPipeline
from chat_pipeline.rag.generator import load_llm, generation

def main():
    print("\n🔵 Interactive RAG CLI (Local LLaMA → Mercury Fallback)")
    print("Type 'exit' to quit.\n")

    pipeline = RAGPipeline()

    # Load LLaMA once
    try:
        llm = load_llm()
        print("🦙 Using local LLaMA model\n")
    except Exception as e:
        print(f"⚠️ Local LLaMA unavailable: {e}")
        print("➡️  Falling back to Mercury.\n")
        llm = None

    while True:
        query = input("You: ").strip()
        if query.lower() in {"exit", "quit"}:
            print("👋 Bye!")
            break

        # ---- STEP 1: Do retrieval only ----
        docs, metadatas = pipeline._run_retrieval_only(query=query)

        # ---- STEP 2: Use generator manually ----
        answer, sources = generation(
            query=query,
            documents=docs,
            metadatas=metadatas,
            llm=llm,     # <-- cached LLaMA or Mercury fallback
            stream=False
        )

        print("\nAssistant:\n", answer)
        print("\nSources:")
        for s in sources:
            print(f"- {s}")
        print("\n" + "-"*60 + "\n")

if __name__ == "__main__":
    main()
