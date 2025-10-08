import os
from langchain_community.llms import LlamaCpp # type: ignore
from langchain.prompts import PromptTemplate # type: ignore
from langchain.chains import RetrievalQA # type: ignore
import chromadb # type: ignore
from langchain.vectorstores import Chroma # type: ignore
from langchain.embeddings import HuggingFaceEmbeddings # type: ignore

# Paths
CHROMA_PATH = "data/chroma_db"
MODEL_PATH = "models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"

def run_query(query: str):
    # 🔹 Embeddings (for query encoding)
    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 🔹 Load Chroma
    vectordb = Chroma(
        collection_name="handbook_qna",
        persist_directory=CHROMA_PATH,
        embedding_function=embedder
    )

    retriever = vectordb.as_retriever(search_kwargs={"k": 3})

    # 🔹 LLaMA model
    llm = LlamaCpp(
        model_path=MODEL_PATH,
        n_ctx=4096,
        n_threads=4,     # adjust based on your MacBook
        n_batch=128,
        f16_kv=True,
        verbose=False
    )

    # 🔹 Prompt Template
    template = """You are an HR assistant.
Use the retrieved context below to answer the question.
If you don’t know, say "I don't know."

Context:
{context}

Question: {question}
Answer:"""

    QA_PROMPT = PromptTemplate(
        input_variables=["context", "question"],
        template=template,
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": QA_PROMPT},
        return_source_documents=True
    )

    result = qa(query)

    print("\n🔹 Question:", query)
    print("💡 Answer:", result["result"])

    print("\n📖 Retrieved Contexts:")
    for i, doc in enumerate(result["source_documents"]):
        print(f"\n--- Context {i+1} ---")
        print(doc.page_content)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_query(query)
    else:
        print("⚠️ Please provide a query. Example:")
        print("python -m src.rag.qa_pipeline 'What is the overtime pay rate?'")
