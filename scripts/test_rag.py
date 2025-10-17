"""
RAG evaluation and interactive testing with retrieval metrics and latency benchmarking.
Supports interactive Q&A mode and automated evaluation with hybrid search.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from collections import defaultdict, Counter
import statistics
import numpy as np

# ChromaDB & Embeddings
import chromadb
from sentence_transformers import SentenceTransformer

# BM25 for hybrid search
try:
    from rank_bm25 import BM25Okapi
    import pickle
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

# LLM
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

# Add parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import time_block, print_banner
from utils.metrics import calculate_all_metrics, calculate_batch_metrics

# Embedded Configuration (from YAML)
CONFIG = {
    "runtime": {
        "mode": "test",
        "random_seed": 42,
        "log_level": "INFO",
        "output_dir": "reports/rag_eval_reports/",
        "device": "auto",
        "threads": 4,
    },
    "evaluation_scope": {
        "evaluate_retrieval": True,
        "evaluate_latency": True,
        "evaluate_embeddings": True,
        "evaluate_hybrid_search": True,
        "use_synthetic_queries": False,
    },
    "retrieval": {
        "top_k_values": [3, 5, 10],
        "collections": ["handbook_chunks"],
        "metrics": ["recall_at_k", "precision_at_k", "hit_rate", "mrr"],
        "thresholds": {
            "recall@5_min": 0.75,
            "mrr_min": 0.60,
        },
        "hybrid_search": {
            "enabled": True,
            "bm25_index_path": "data/vector_db/bm25/handbook_chunks",
            "semantic_weight": 0.7,
            "keyword_weight": 0.3,
            "compare_with_semantic": True,
        }
    },
    "latency": {
        "measure_retrieval_latency": True,
        "measure_llm_latency": True,
        "metrics": ["mean_ms", "p50_ms", "p95_ms", "p99_ms"],
        "thresholds": {
            "retrieval_p95_max_ms": 1000,
            "llm_p95_max_ms": 3000,
        }
    },
    "embeddings": {
        "evaluate_intra_doc_similarity": True,
        "evaluate_inter_doc_separation": True,
        "sample_docs": 5,
        "sample_chunks_per_doc": 20,
        "thresholds": {
            "intra_doc_mean_min": 0.70,
            "inter_doc_mean_max": 0.50,
        }
    },
    "reporting": {
        "enabled": True,
        "formats": ["json", "markdown"],
        "console_summary": True,
    }
}

# Setup logging
os.makedirs(CONFIG["runtime"]["output_dir"], exist_ok=True)
logging.basicConfig(
    level=getattr(logging, CONFIG["runtime"]["log_level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(CONFIG["runtime"]["output_dir"], 'rag_eval.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RAGEvaluator:
    """
    Comprehensive RAG evaluation and testing system.
    Supports both interactive testing and automated evaluation.
    """
    
    def __init__(
        self,
        chroma_path: str = "data/vector_db/chroma/",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        llm_model_path: Optional[str] = None,
        config: Optional[Dict] = None
    ):
        """Initialize RAG evaluator."""
        self.config = config or CONFIG
        self.chroma_path = chroma_path
        self.embedding_model_name = embedding_model
        self.llm_model_path = llm_model_path
        
        # Initialize components
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        
        logger.info(f"Connecting to ChromaDB at: {chroma_path}")
        self.client = chromadb.PersistentClient(path=chroma_path)
        
        # Load BM25 if hybrid search enabled
        self.bm25_index = None
        self.doc_ids = []
        if self.config["retrieval"]["hybrid_search"]["enabled"] and BM25_AVAILABLE:
            self._load_bm25_index()
        
        # Initialize LLM if path provided
        self.llm = None
        if llm_model_path and LLAMA_AVAILABLE:
            self._init_llm(llm_model_path)
        
        # Metrics storage
        self.metrics = defaultdict(list)
        self.latencies = defaultdict(list)
        
        logger.info("RAGEvaluator initialized successfully")
    
    def _load_bm25_index(self):
        """Load BM25 index for hybrid search."""
        bm25_path = Path(self.config["retrieval"]["hybrid_search"]["bm25_index_path"])
        index_file = bm25_path / "bm25_index.pkl"
        ids_file = bm25_path / "document_ids.json"
        
        if index_file.exists() and ids_file.exists():
            try:
                with open(index_file, 'rb') as f:
                    self.bm25_index = pickle.load(f)
                with open(ids_file, 'r') as f:
                    self.doc_ids = json.load(f)
                logger.info(f"Loaded BM25 index with {len(self.doc_ids)} documents")
            except Exception as e:
                logger.warning(f"Failed to load BM25 index: {e}")
        else:
            logger.warning(f"BM25 index not found at {bm25_path}")
    
    def _init_llm(self, model_path: str):
        """Initialize LLM for answer generation."""
        if not os.path.exists(model_path):
            logger.warning(f"LLM model not found at {model_path}")
            return
        
        try:
            logger.info(f"Loading LLM from {model_path}")
            self.llm = Llama(
                model_path=model_path,
                n_ctx=8192,
                n_threads=self.config["runtime"]["threads"],
                temperature=0.6,
                top_p=0.9,
                max_tokens=2048,
                verbose=False
            )
            logger.info("LLM loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
    
    # ============================================================
    # RETRIEVAL
    # ============================================================
    
    def semantic_search(
        self,
        query: str,
        collection_name: str = "handbook_chunks",
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> Tuple[List[Dict], float]:
        """Perform semantic search with latency tracking."""
        start_time = time.time()
        
        try:
            collection = self.client.get_collection(collection_name)
        except Exception as e:
            logger.error(f"Collection {collection_name} not found: {e}")
            return [], 0.0
        
        # Generate query embedding
        query_embedding = self.embedder.encode(query, convert_to_numpy=True, normalize_embeddings=True).tolist()
        
        # Query
        query_args = {"query_embeddings": [query_embedding], "n_results": top_k}
        if filters:
            query_args["where"] = filters
        
        results = collection.query(**query_args)
        
        latency = (time.time() - start_time) * 1000  # ms
        
        # Format results
        formatted_results = []
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'text': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None,
                    'score': 1 - results['distances'][0][i] if results['distances'] else None,
                    'id': results['ids'][0][i] if results['ids'] else None
                })
        
        return formatted_results, latency
    
    def hybrid_search(
        self,
        query: str,
        collection_name: str = "handbook_chunks",
        top_k: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> Tuple[List[Dict], float]:
        """Perform hybrid search (BM25 + Semantic)."""
        if not self.bm25_index:
            logger.warning("BM25 index not available, falling back to semantic search")
            return self.semantic_search(query, collection_name, top_k)
        
        start_time = time.time()
        
        # BM25 scores
        query_tokens = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(query_tokens)
        bm25_scores_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-9)
        
        # Semantic scores
        semantic_results, _ = self.semantic_search(query, collection_name, len(self.doc_ids))
        semantic_scores = {r['id']: r['score'] for r in semantic_results}
        
        # Combine scores
        combined_scores = []
        for i, doc_id in enumerate(self.doc_ids):
            semantic_score = semantic_scores.get(doc_id, 0.0)
            bm25_score = bm25_scores_norm[i]
            hybrid_score = (semantic_weight * semantic_score) + (keyword_weight * bm25_score)
            combined_scores.append((doc_id, hybrid_score))
        
        # Sort and get top-k
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        top_ids = [doc_id for doc_id, _ in combined_scores[:top_k]]
        
        # Get full results
        results = []
        for doc_id in top_ids:
            matching_result = next((r for r in semantic_results if r['id'] == doc_id), None)
            if matching_result:
                results.append(matching_result)
        
        latency = (time.time() - start_time) * 1000  # ms
        
        return results, latency
    
    # ============================================================
    # EVALUATION METRICS
    # ============================================================
    
    def calculate_recall_at_k(self, retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
        """Calculate Recall@K."""
        if not relevant_ids:
            return 0.0
        retrieved_k = set(retrieved_ids[:k])
        relevant_set = set(relevant_ids)
        return len(retrieved_k & relevant_set) / len(relevant_set)
    
    def calculate_precision_at_k(self, retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
        """Calculate Precision@K."""
        if k == 0:
            return 0.0
        retrieved_k = set(retrieved_ids[:k])
        relevant_set = set(relevant_ids)
        return len(retrieved_k & relevant_set) / k
    
    def calculate_mrr(self, retrieved_ids: List[str], relevant_ids: List[str]) -> float:
        """Calculate Mean Reciprocal Rank."""
        relevant_set = set(relevant_ids)
        for i, doc_id in enumerate(retrieved_ids, 1):
            if doc_id in relevant_set:
                return 1.0 / i
        return 0.0
    
    def calculate_hit_rate(self, retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
        """Calculate Hit Rate@K (binary: did we retrieve any relevant doc?)."""
        retrieved_k = set(retrieved_ids[:k])
        relevant_set = set(relevant_ids)
        return 1.0 if len(retrieved_k & relevant_set) > 0 else 0.0
    
    # ============================================================
    # EMBEDDING HEALTH
    # ============================================================
    
    def evaluate_embedding_health(self, collection_name: str = "handbook_chunks") -> Dict:
        """Evaluate embedding quality (intra-doc similarity, inter-doc separation)."""
        logger.info("Evaluating embedding health...")
        
        collection = self.client.get_collection(collection_name)
        
        # Sample documents
        all_results = collection.get(include=["embeddings", "metadatas"])
        embeddings = np.array(all_results['embeddings'])
        metadatas = all_results['metadatas']
        
        # Group by document
        doc_embeddings = defaultdict(list)
        for i, meta in enumerate(metadatas):
            doc_id = meta.get('doc_id', 'unknown')
            doc_embeddings[doc_id].append(embeddings[i])
        
        # Sample docs
        sample_size = min(self.config["embeddings"]["sample_docs"], len(doc_embeddings))
        sampled_docs = list(doc_embeddings.keys())[:sample_size]
        
        # Intra-document similarity
        intra_similarities = []
        for doc_id in sampled_docs:
            doc_vecs = np.array(doc_embeddings[doc_id])
            if len(doc_vecs) > 1:
                # Pairwise cosine similarity
                from sklearn.metrics.pairwise import cosine_similarity
                sim_matrix = cosine_similarity(doc_vecs)
                # Get upper triangle (excluding diagonal)
                triu_indices = np.triu_indices_from(sim_matrix, k=1)
                sims = sim_matrix[triu_indices]
                intra_similarities.extend(sims)
        
        # Inter-document similarity
        inter_similarities = []
        for i, doc1 in enumerate(sampled_docs):
            for doc2 in sampled_docs[i+1:]:
                vecs1 = np.array(doc_embeddings[doc1])
                vecs2 = np.array(doc_embeddings[doc2])
                # Sample pairs
                for v1 in vecs1[:5]:
                    for v2 in vecs2[:5]:
                        sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                        inter_similarities.append(sim)
        
        results = {
            "intra_doc_mean": np.mean(intra_similarities) if intra_similarities else 0.0,
            "intra_doc_std": np.std(intra_similarities) if intra_similarities else 0.0,
            "inter_doc_mean": np.mean(inter_similarities) if inter_similarities else 0.0,
            "inter_doc_std": np.std(inter_similarities) if inter_similarities else 0.0,
            "sampled_docs": sample_size,
            "intra_samples": len(intra_similarities),
            "inter_samples": len(inter_similarities)
        }
        
        # Check thresholds
        thresholds = self.config["embeddings"]["thresholds"]
        results["intra_doc_pass"] = results["intra_doc_mean"] >= thresholds["intra_doc_mean_min"]
        results["inter_doc_pass"] = results["inter_doc_mean"] <= thresholds["inter_doc_mean_max"]
        
        logger.info(f"Embedding health: intra={results['intra_doc_mean']:.3f}, inter={results['inter_doc_mean']:.3f}")
        return results
    
    # ============================================================
    # LLM GENERATION
    # ============================================================
    
    def generate_answer(self, query: str, context: str) -> Tuple[str, float]:
        """Generate answer with LLM."""
        if not self.llm:
            return "LLM not available", 0.0
        
        system_prompt = """You are an HR assistant. Answer questions based on the provided context.
If the answer is not in the context, say "I don't have enough information to answer that."
Keep answers concise and professional."""
        
        prompt = f"""{system_prompt}

CONTEXT:
{context[:6000]}

QUESTION: {query}

ANSWER:"""
        
        start_time = time.time()
        
        try:
            response = self.llm(prompt, max_tokens=512, temperature=0.6)
            answer = response["choices"][0]["text"].strip()
            latency = (time.time() - start_time) * 1000
            return answer, latency
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Error: {e}", 0.0
    
    # ============================================================
    # EVALUATION PIPELINE
    # ============================================================
    
    def run_evaluation(
        self,
        test_queries: List[Dict],
        collection_name: str = "handbook_chunks"
    ) -> Dict:
        """Run comprehensive evaluation.
        
        Args:
            test_queries: List of dicts with 'query' and 'relevant_ids' keys
        """
        logger.info(f"Running evaluation on {len(test_queries)} queries...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "num_queries": len(test_queries),
            "retrieval_metrics": {},
            "latency_metrics": {},
            "embedding_health": {},
            "hybrid_comparison": {},
        }
        
        # Per-query results
        semantic_metrics = defaultdict(list)
        hybrid_metrics = defaultdict(list)
        semantic_latencies = []
        hybrid_latencies = []
        
        for query_data in test_queries:
            query = query_data['query']
            relevant_ids = query_data.get('relevant_ids', [])
            
            # Semantic search
            semantic_results, semantic_lat = self.semantic_search(query, collection_name, top_k=10)
            retrieved_ids = [r['id'] for r in semantic_results]
            semantic_latencies.append(semantic_lat)
            
            # Calculate metrics
            for k in self.config["retrieval"]["top_k_values"]:
                semantic_metrics[f"recall@{k}"].append(self.calculate_recall_at_k(retrieved_ids, relevant_ids, k))
                semantic_metrics[f"precision@{k}"].append(self.calculate_precision_at_k(retrieved_ids, relevant_ids, k))
                semantic_metrics[f"hit_rate@{k}"].append(self.calculate_hit_rate(retrieved_ids, relevant_ids, k))
            
            semantic_metrics["mrr"].append(self.calculate_mrr(retrieved_ids, relevant_ids))
            
            # Hybrid search (if enabled)
            if self.config["retrieval"]["hybrid_search"]["enabled"] and self.bm25_index:
                hybrid_results, hybrid_lat = self.hybrid_search(query, collection_name, top_k=10)
                hybrid_ids = [r['id'] for r in hybrid_results]
                hybrid_latencies.append(hybrid_lat)
                
                for k in self.config["retrieval"]["top_k_values"]:
                    hybrid_metrics[f"recall@{k}"].append(self.calculate_recall_at_k(hybrid_ids, relevant_ids, k))
                    hybrid_metrics[f"precision@{k}"].append(self.calculate_precision_at_k(hybrid_ids, relevant_ids, k))
                
                hybrid_metrics["mrr"].append(self.calculate_mrr(hybrid_ids, relevant_ids))
        
        # Aggregate metrics
        results["retrieval_metrics"]["semantic"] = {
            metric: {
                "mean": np.mean(values),
                "std": np.std(values),
                "min": np.min(values),
                "max": np.max(values)
            }
            for metric, values in semantic_metrics.items()
        }
        
        if hybrid_metrics:
            results["retrieval_metrics"]["hybrid"] = {
                metric: {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values)
                }
                for metric, values in hybrid_metrics.items()
            }
            
            # Comparison
            results["hybrid_comparison"] = {
                "semantic_recall@5": results["retrieval_metrics"]["semantic"]["recall@5"]["mean"],
                "hybrid_recall@5": results["retrieval_metrics"]["hybrid"]["recall@5"]["mean"],
                "delta": results["retrieval_metrics"]["hybrid"]["recall@5"]["mean"] - results["retrieval_metrics"]["semantic"]["recall@5"]["mean"]
            }
        
        # Latency metrics
        results["latency_metrics"]["semantic"] = {
            "mean_ms": np.mean(semantic_latencies),
            "p50_ms": np.percentile(semantic_latencies, 50),
            "p95_ms": np.percentile(semantic_latencies, 95),
            "p99_ms": np.percentile(semantic_latencies, 99)
        }
        
        if hybrid_latencies:
            results["latency_metrics"]["hybrid"] = {
                "mean_ms": np.mean(hybrid_latencies),
                "p50_ms": np.percentile(hybrid_latencies, 50),
                "p95_ms": np.percentile(hybrid_latencies, 95),
                "p99_ms": np.percentile(hybrid_latencies, 99)
            }
        
        # Embedding health
        if self.config["evaluation_scope"]["evaluate_embeddings"]:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                results["embedding_health"] = self.evaluate_embedding_health(collection_name)
            except ImportError:
                logger.warning("scikit-learn not available, skipping embedding health evaluation")
        
        logger.info("Evaluation complete")
        return results
    
    # ============================================================
    # INTERACTIVE TESTING
    # ============================================================
    
    def test_query(
        self,
        query: str,
        collection_name: str = "handbook_chunks",
        top_k: int = 5,
        use_hybrid: bool = False,
        generate_answer: bool = False
    ):
        """Interactive query testing."""
        print(f"\n{'='*70}")
        print(f"Query: {query}")
        print(f"{'='*70}\n")
        
        # Retrieve
        if use_hybrid and self.bm25_index:
            results, latency = self.hybrid_search(query, collection_name, top_k)
            print(f"[HYBRID SEARCH] Latency: {latency:.2f}ms\n")
        else:
            results, latency = self.semantic_search(query, collection_name, top_k)
            print(f"[SEMANTIC SEARCH] Latency: {latency:.2f}ms\n")
        
        # Display results
        if results:
            for i, result in enumerate(results, 1):
                print(f"[{i}] Score: {result['score']:.4f}")
                metadata = result['metadata']
                print(f"    Doc: {metadata.get('doc_id', 'N/A')}")
                print(f"    Section: {metadata.get('section_path', 'N/A')}")
                print(f"    Page: {metadata.get('page_number', 'N/A')}")
                print(f"    Text: {result['text'][:200]}...")
                print()
        else:
            print("No results found.\n")
        
        # Generate answer
        if generate_answer and self.llm and results:
            context = "\n\n".join([r['text'] for r in results])
            answer, llm_lat = self.generate_answer(query, context)
            print(f"{'='*70}")
            print(f"Generated Answer (Latency: {llm_lat:.2f}ms):")
            print(f"{'='*70}")
            print(answer)
            print()
        
        print(f"{'='*70}\n")
    
    # ============================================================
    # REPORTING
    # ============================================================
    
    def generate_report(self, eval_results: Dict):
        """Generate evaluation reports."""
        if not self.config["reporting"]["enabled"]:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(self.config["runtime"]["output_dir"])
        
        # JSON report
        json_path = output_dir / f"rag_eval_report_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(eval_results, f, indent=2)
        logger.info(f"JSON report: {json_path}")
        
        # Markdown report
        md_path = output_dir / f"rag_eval_summary_{timestamp}.md"
        with open(md_path, 'w') as f:
            f.write(self._generate_markdown(eval_results))
        logger.info(f"Markdown report: {md_path}")
        
        # Console summary
        if self.config["reporting"]["console_summary"]:
            self._print_summary(eval_results)
    
    def _generate_markdown(self, results: Dict) -> str:
        """Generate markdown report."""
        md = f"""# RAG Evaluation Report

**Timestamp:** {results['timestamp']}  
**Queries:** {results['num_queries']}

## Retrieval Metrics

### Semantic Search
"""
        for metric, stats in results['retrieval_metrics'].get('semantic', {}).items():
            md += f"- **{metric}:** {stats['mean']:.4f} (±{stats['std']:.4f})\n"
        
        if 'hybrid' in results['retrieval_metrics']:
            md += "\n### Hybrid Search\n"
            for metric, stats in results['retrieval_metrics']['hybrid'].items():
                md += f"- **{metric}:** {stats['mean']:.4f} (±{stats['std']:.4f})\n"
        
        if results.get('hybrid_comparison'):
            comp = results['hybrid_comparison']
            md += f"\n### Hybrid vs Semantic\n"
            md += f"- **Semantic Recall@5:** {comp['semantic_recall@5']:.4f}\n"
            md += f"- **Hybrid Recall@5:** {comp['hybrid_recall@5']:.4f}\n"
            md += f"- **Delta:** {comp['delta']:+.4f}\n"
        
        md += "\n## Latency\n\n"
        for search_type, metrics in results['latency_metrics'].items():
            md += f"### {search_type.title()}\n"
            for metric, value in metrics.items():
                md += f"- **{metric}:** {value:.2f}ms\n"
        
        if results.get('embedding_health'):
            health = results['embedding_health']
            md += "\n## Embedding Health\n\n"
            md += f"- **Intra-doc Mean:** {health['intra_doc_mean']:.4f} {'✓' if health['intra_doc_pass'] else '✗'}\n"
            md += f"- **Inter-doc Mean:** {health['inter_doc_mean']:.4f} {'✓' if health['inter_doc_pass'] else '✗'}\n"
        
        return md
    
    def _print_summary(self, results: Dict):
        """Print console summary."""
        print(f"\n{'='*70}")
        print(f"RAG Evaluation Summary")
        print(f"{'='*70}\n")
        
        print(f"Queries: {results['num_queries']}\n")
        
        print("Retrieval (Semantic):")
        semantic = results['retrieval_metrics'].get('semantic', {})
        if 'recall@5' in semantic:
            print(f"  Recall@5: {semantic['recall@5']['mean']:.4f}")
        if 'mrr' in semantic:
            print(f"  MRR: {semantic['mrr']['mean']:.4f}")
        
        if 'hybrid' in results['retrieval_metrics']:
            print("\nRetrieval (Hybrid):")
            hybrid = results['retrieval_metrics']['hybrid']
            if 'recall@5' in hybrid:
                print(f"  Recall@5: {hybrid['recall@5']['mean']:.4f}")
            if 'mrr' in hybrid:
                print(f"  MRR: {hybrid['mrr']['mean']:.4f}")
        
        print(f"\nLatency:")
        for search_type, metrics in results['latency_metrics'].items():
            print(f"  {search_type.title()} p95: {metrics['p95_ms']:.2f}ms")
        
        if results.get('embedding_health'):
            health = results['embedding_health']
            print(f"\nEmbedding Health:")
            print(f"  Intra-doc: {health['intra_doc_mean']:.4f} {'✓' if health['intra_doc_pass'] else '✗'}")
            print(f"  Inter-doc: {health['inter_doc_mean']:.4f} {'✓' if health['inter_doc_pass'] else '✗'}")
        
        print(f"\n{'='*70}\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Evaluation & Testing")
    parser.add_argument("query", nargs="*", help="Query to test (interactive mode)")
    parser.add_argument("--eval", action="store_true", help="Run evaluation mode")
    parser.add_argument("--test-file", type=str, help="Path to test queries JSON file")
    parser.add_argument("--hybrid", action="store_true", help="Use hybrid search")
    parser.add_argument("--llm", type=str, help="Path to LLM model")
    parser.add_argument("--generate", action="store_true", help="Generate LLM answers")
    parser.add_argument("--collection", type=str, default="handbook_chunks", help="Collection name")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    
    args = parser.parse_args()
    
    # Initialize evaluator
    evaluator = RAGEvaluator(llm_model_path=args.llm)
    
    # Evaluation mode
    if args.eval:
        if not args.test_file:
            logger.error("--test-file required for evaluation mode")
            return 1
        
        # Load test queries
        with open(args.test_file, 'r') as f:
            test_queries = [json.loads(line) for line in f]
        
        # Run evaluation
        results = evaluator.run_evaluation(test_queries, args.collection)
        evaluator.generate_report(results)
        
        return 0
    
    # Interactive mode
    if args.query:
        query = " ".join(args.query)
        evaluator.test_query(
            query,
            collection_name=args.collection,
            top_k=args.top_k,
            use_hybrid=args.hybrid,
            generate_answer=args.generate
        )
    else:
        # Interactive loop
        print("\nRAG Interactive Testing")
        print("Commands: 'quit' to exit, 'hybrid' to toggle hybrid search\n")
        
        use_hybrid = args.hybrid
        
        while True:
            query = input("Query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            elif query.lower() == 'hybrid':
                use_hybrid = not use_hybrid
                print(f"Hybrid search: {'ON' if use_hybrid else 'OFF'}\n")
                continue
            
            if query:
                evaluator.test_query(
                    query,
                    collection_name=args.collection,
                    top_k=args.top_k,
                    use_hybrid=use_hybrid,
                    generate_answer=args.generate
                )
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
