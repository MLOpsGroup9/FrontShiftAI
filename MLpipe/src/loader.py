"""
Loads chunks from data_pipeline.
"""

import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Suppress TensorFlow and oneDNN logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Hardware optimization environment variables
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
os.environ.setdefault('CHROMADB_SEGMENT_CACHE_SIZE', '2G')

# Suppress all warnings including TensorFlow deprecation warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

import chromadb
import pandas as pd
from chromadb.utils import embedding_functions

# Additional TensorFlow warning suppression
try:
    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    import logging
    logging.getLogger('tensorflow').setLevel('ERROR')
    logging.getLogger('tf_keras').setLevel('ERROR')
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "data_pipeline"))

from utils.logger import get_logger

logger = get_logger("ml_data_loader")

# Global embedding function (loaded once)
_global_embedding_function = None

def get_embedding_function():
    """Get or create global embedding function with warm-up."""
    global _global_embedding_function
    if _global_embedding_function is None:
        logger.info("Initializing embedding function (all-MiniLM-L6-v2)...")
        _global_embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        # Warm-up: encode a dummy sentence to compile graph once
        try:
            _global_embedding_function(["warm-up sentence"])
            logger.info("Embedding function initialized and warmed up")
        except Exception as e:
            logger.warning(f"Embedding warm-up failed: {e}")
            logger.info("Embedding function initialized")
    return _global_embedding_function


class ChunkDataLoader:
    """
    Loads chunks and provides fast retrieval.
    
    Usage:
        loader = ChunkDataLoader()
        docs, metas, dists = loader.retrieve("What is PTO policy?", top_k=5)
        df = loader.load_chunks()
    """
    
    def __init__(
        self,
        chunks_dir: Optional[str] = None,
        chromadb_path: Optional[str] = None,
        collection_name: str = "frontshift_handbooks"
    ):
        # Use environment variables if available, otherwise use defaults
        self.chunks_dir = Path(
            os.getenv("CHUNKS_DIR", chunks_dir or "data_pipeline/data/chunked")
        )
        if not self.chunks_dir.is_absolute():
            self.chunks_dir = BASE_DIR / self.chunks_dir
        
        self.chromadb_path = Path(
            os.getenv("CHROMADB_PATH", chromadb_path or "data_pipeline/data/vector_db")
        )
        if not self.chromadb_path.is_absolute():
            self.chromadb_path = BASE_DIR / self.chromadb_path
        
        self.collection_name = collection_name
        
        if not self.chunks_dir.exists():
            raise FileNotFoundError(f"Chunks directory not found: {self.chunks_dir}")
        if not self.chromadb_path.exists():
            raise FileNotFoundError(f"ChromaDB path not found: {self.chromadb_path}")
        
        self._client = None
        self._collection = None
        
        # Initialize with retry
        self._initialize_with_retry()
    
    def _initialize_with_retry(self, max_retries: int = 1):
        """Initialize ChromaDB connection with retry logic and optimized settings."""
        for attempt in range(max_retries + 1):
            try:
                # Pre-initialize client (single connection, reused across queries)
                self._client = chromadb.PersistentClient(path=str(self.chromadb_path))
                logger.debug("Connected to ChromaDB")
                
                # Get embedding function (with warm-up) and collection
                emb_fn = get_embedding_function()
                self._collection = self._client.get_collection(
                    name=self.collection_name,
                    embedding_function=emb_fn
                )
                logger.debug(f"Loaded collection '{self.collection_name}'")
                return
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Initialization attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(1)
                else:
                    logger.error(f"Failed to initialize after {max_retries + 1} attempts: {e}")
                    raise
    
    @property
    def client(self) -> chromadb.ClientAPI:
        """Get ChromaDB client (pre-initialized)."""
        if self._client is None:
            raise RuntimeError("ChromaDB client not initialized. Call _initialize_with_retry first.")
        return self._client
    
    @property
    def collection(self) -> chromadb.Collection:
        """Get ChromaDB collection (pre-initialized and reused)."""
        if self._collection is None:
            raise RuntimeError("ChromaDB collection not initialized. Call _initialize_with_retry first.")
        return self._collection
    
    def load_chunks(self, include_embeddings: bool = False) -> pd.DataFrame:
        """
        Load all chunks from JSONL files.
        
        Returns:
            DataFrame with columns: chunk_id, text, company, policy_tags, etc.
        """
        chunk_files = sorted(self.chunks_dir.glob("*_chunks.jsonl"))
        if not chunk_files:
            raise FileNotFoundError(f"No chunk files in {self.chunks_dir}")
        
        all_chunks = []
        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        all_chunks.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        records = []
        for chunk in all_chunks:
            metadata = chunk.get('metadata', {})
            records.append({
                'chunk_id': chunk.get('chunk_id') or metadata.get('chunk_id'),
                'text': chunk.get('text', ''),
                'company': self._extract_company(metadata),
                'policy_tags': '|'.join(metadata.get('policy_tags', [])),
                'doc_id': metadata.get('doc_id', ''),
                'industry': metadata.get('industry', ''),
                'doc_type': metadata.get('doc_type', ''),
                'doc_year': metadata.get('doc_year', ''),
                'section_title': metadata.get('section_title', ''),
                'keywords': '|'.join(metadata.get('keywords', [])),
                'token_count': metadata.get('token_count', 0),
                'quality_score': metadata.get('quality_score', 0.0),
            })
        
        df = pd.DataFrame(records)
        
        if include_embeddings:
            df['embedding'] = df['chunk_id'].apply(self._get_embedding)
        
        return df
    
    def _extract_company(self, metadata: Dict) -> str:
        """Extract company name from metadata."""
        company = metadata.get('company', '')
        if company and company != 'Unknown Company':
            return company
        
        doc_id = metadata.get('doc_id', '')
        if doc_id:
            parts = doc_id.replace('_employee_manual', '').replace('_handbook', '').split('_')
            return ' '.join(p.capitalize() for p in parts if p and not p.isdigit())
        
        return 'Unknown'
    
    def _get_embedding(self, chunk_id: str) -> Optional[List[float]]:
        """Get embedding for a chunk."""
        try:
            results = self.collection.get(ids=[chunk_id], include=['embeddings'])
            return results['embeddings'][0] if results['embeddings'] else None
        except Exception as e:
            logger.warning(f"No embedding for {chunk_id}: {e}")
            return None
    
    def retrieve(
        self,
        query: str,
        company_name: Optional[str] = None,
        top_k: int = 5,
        include_distances: bool = True
    ) -> Tuple[List[str], List[Dict], Optional[List[float]]]:
        """
        Fast semantic search via ChromaDB with optimized performance and profiling.
        
        Args:
            query: Query text
            company_name: Optional company filter (case-insensitive)
            top_k: Number of results
            include_distances: Return distance scores (default: True for sorting)
            
        Returns:
            (documents, metadatas, distances) - already sorted by ChromaDB by similarity distance
        """
        total_start = time.time()
        
        # Use pre-initialized collection (reused across queries)
        collection = self.collection
        
        # Profile: Company filtering time
        company_filter_start = time.time()
        query_args = {
            "query_texts": [query],
            "n_results": top_k,
            "include": ["documents", "metadatas"]  # Reduced: only get what we need
        }
        
        if include_distances:
            query_args["include"].append("distances")
        
        # Optimized company filtering - cache company lookup if needed
        if company_name:
            # Use a more efficient lookup (only get metadata, not full chunks)
            if not hasattr(self, '_company_cache'):
                self._company_cache = {}
            
            cache_key = company_name.lower()
            if cache_key not in self._company_cache:
                # One-time lookup: get unique companies efficiently
                sample = collection.get(limit=1000, include=["metadatas"])
                company_map = {}
                for meta in sample.get('metadatas', []):
                    comp = meta.get('company', '').strip()
                    if comp:
                        company_map[comp.lower()] = comp
                self._company_cache = company_map
            
            matched_company = self._company_cache.get(cache_key)
            if matched_company:
                query_args["where"] = {"company": matched_company}
                logger.debug(f"Company filter: '{company_name}' -> '{matched_company}'")
            else:
                logger.warning(f"Company '{company_name}' not found, searching all companies")
        
        company_filter_time = (time.time() - company_filter_start) * 1000
        
        # Profile: ChromaDB query time (includes embedding creation)
        query_start = time.time()
        results = collection.query(**query_args)
        query_time = (time.time() - query_start) * 1000
        
        # Profile: Post-processing time
        postprocess_start = time.time()
        
        # ChromaDB already returns results sorted by distance, so no need to re-sort
        docs = results.get("documents", [[]])[0] or []
        metas = results.get("metadatas", [[]])[0] or []
        distances = results.get("distances", [[]])[0] if include_distances else None
        
        # Optimized metadata filtering using list comprehension (faster than loop)
        if metas:
            filtered_metas = [
                {
                    'company': m.get('company', ''),
                    'doc_id': m.get('filename', m.get('doc_id', '')),
                    'chunk_id': m.get('chunk_id', ''),
                    'section_title': m.get('section', m.get('section_title', ''))
                }
                for m in metas
            ]
        else:
            filtered_metas = []
        
        postprocess_time = (time.time() - postprocess_start) * 1000
        total_latency = (time.time() - total_start) * 1000
        
        logger.debug(
            f"Retrieved {len(docs)} chunks in {total_latency:.2f} ms "
            f"(filter: {company_filter_time:.2f}ms, query: {query_time:.2f}ms, postprocess: {postprocess_time:.2f}ms)"
        )
        
        return docs, filtered_metas, distances
    
