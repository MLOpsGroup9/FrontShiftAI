"""
Data Loader for ML-RAG Pipeline.
Loads chunks from data_pipeline and provides fast retrieval via ChromaDB.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chromadb
import pandas as pd
from chromadb.utils import embedding_functions

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "data_pipeline"))

from utils.logger import get_logger

logger = get_logger("ml_data_loader")


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
        chunks_dir: str = "data_pipeline/data/chunked",
        chromadb_path: str = "data_pipeline/data/vector_db",
        collection_name: str = "frontshift_handbooks"
    ):
        self.chunks_dir = Path(BASE_DIR) / chunks_dir
        self.chromadb_path = Path(BASE_DIR) / chromadb_path
        self.collection_name = collection_name
        
        if not self.chunks_dir.exists():
            raise FileNotFoundError(f"Chunks directory not found: {self.chunks_dir}")
        if not self.chromadb_path.exists():
            raise FileNotFoundError(f"ChromaDB path not found: {self.chromadb_path}")
        
        self._client = None
        self._collection = None
        
        logger.info(f"Initialized ChunkDataLoader")
        logger.info(f"  Chunks: {self.chunks_dir}")
        logger.info(f"  ChromaDB: {self.chromadb_path}")
        logger.info(f"  Collection: {self.collection_name}")
    
    @property
    def client(self) -> chromadb.ClientAPI:
        """Lazy load ChromaDB client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(path=str(self.chromadb_path))
            logger.info("Connected to ChromaDB")
        return self._client
    
    @property
    def collection(self) -> chromadb.Collection:
        """Lazy load ChromaDB collection."""
        if self._collection is None:
            self._collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded collection '{self.collection_name}' ({self._collection.count()} embeddings)")
        return self._collection
    
    def load_chunks(self, include_embeddings: bool = False) -> pd.DataFrame:
        """
        Load all chunks from JSONL files.
        
        Returns:
            DataFrame with columns: chunk_id, text, company, policy_tags, etc.
        """
        logger.info("Loading chunks...")
        
        chunk_files = sorted(self.chunks_dir.glob("*_chunks.jsonl"))
        if not chunk_files:
            raise FileNotFoundError(f"No chunk files in {self.chunks_dir}")
        
        logger.info(f"Found {len(chunk_files)} chunk files")
        
        all_chunks = []
        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        all_chunks.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        logger.info(f"Loaded {len(all_chunks)} chunks")
        
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
            logger.info("Fetching embeddings...")
            df['embedding'] = df['chunk_id'].apply(self._get_embedding)
        
        logger.info(f"Created DataFrame: {df.shape}")
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
    
    def get_embeddings(self, chunk_ids: List[str]) -> Dict[str, List[float]]:
        """Get embeddings for multiple chunks."""
        logger.info(f"Fetching embeddings for {len(chunk_ids)} chunks...")
        embeddings = {cid: emb for cid in chunk_ids if (emb := self._get_embedding(cid))}
        logger.info(f"Retrieved {len(embeddings)}/{len(chunk_ids)} embeddings")
        return embeddings
    
    def retrieve(
        self,
        query: str,
        company_name: Optional[str] = None,
        top_k: int = 5,
        include_distances: bool = False
    ) -> Tuple[List[str], List[Dict], Optional[List[float]]]:
        """
        Fast semantic search via ChromaDB.
        
        Args:
            query: Query text
            company_name: Optional company filter
            top_k: Number of results
            include_distances: Return distance scores
            
        Returns:
            (documents, metadatas, distances)
        """
        start_time = time.time()
        
        if not hasattr(self, '_emb_fn'):
            self._emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        
        collection = self.client.get_collection(
            name=self.collection_name,
            embedding_function=self._emb_fn
        )
        
        query_args = {
            "query_texts": [query],
            "n_results": top_k,
            "include": ["documents", "metadatas"]
        }
        
        if include_distances:
            query_args["include"].append("distances")
        if company_name:
            query_args["where"] = {"company": company_name}
        
        results = collection.query(**query_args)
        
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if include_distances else None
        
        latency = (time.time() - start_time) * 1000
        logger.info(f"Retrieved {len(docs)} chunks in {latency:.2f} ms")
        
        return docs, metas, distances
    
    def get_summary(self) -> Dict:
        """Get dataset statistics."""
        logger.info("Generating summary...")
        df = self.load_chunks(include_embeddings=False)
        
        return {
            'total_chunks': len(df),
            'unique_documents': df['doc_id'].nunique(),
            'unique_companies': df['company'].nunique(),
            'industries': df['industry'].value_counts().to_dict(),
            'doc_types': df['doc_type'].value_counts().to_dict(),
            'doc_years': df['doc_year'].value_counts().to_dict(),
            'avg_token_count': df['token_count'].mean(),
            'avg_quality_score': df['quality_score'].mean(),
            'chunks_with_policy_tags': (df['policy_tags'] != '').sum(),
            'chromadb_embedding_count': self.collection.count()
        }
    
    def print_summary(self):
        """Print formatted summary."""
        summary = self.get_summary()
        
        print("\n" + "="*70)
        print("Data Summary")
        print("="*70)
        print(f"Total Chunks:             {summary['total_chunks']:,}")
        print(f"Unique Documents:         {summary['unique_documents']}")
        print(f"Unique Companies:         {summary['unique_companies']}")
        print(f"ChromaDB Embeddings:      {summary['chromadb_embedding_count']:,}")
        print(f"Avg Token Count:          {summary['avg_token_count']:.1f}")
        print(f"Avg Quality Score:        {summary['avg_quality_score']:.3f}")
        print(f"Chunks with Policy Tags:  {summary['chunks_with_policy_tags']}")
        
        print("\nIndustries:")
        for industry, count in summary['industries'].items():
            print(f"  - {industry}: {count}")
        
        print("\nDocument Years:")
        for year, count in sorted(summary['doc_years'].items()):
            print(f"  - {year}: {count}")
        
        print("\n" + "="*70 + "\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Load chunks and query ChromaDB")
    parser.add_argument('--show-summary', action='store_true', help='Display data summary')
    parser.add_argument('--query', type=str, help='Query text')
    parser.add_argument('--top-k', type=int, default=5, help='Number of results (default: 5)')
    
    args = parser.parse_args()
    
    try:
        loader = ChunkDataLoader()
        
        if args.show_summary:
            loader.print_summary()
        
        if args.query:
            print(f"\nQuery: '{args.query}'")
            print("="*70)
            
            start_time = time.time()
            documents, metadatas, distances = loader.retrieve(
                query=args.query,
                top_k=args.top_k,
                include_distances=True
            )
            retrieval_time = (time.time() - start_time) * 1000
            
            print(f"Retrieved {len(documents)} chunks in {retrieval_time:.2f} ms")
            print("="*70)
            
            for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
                company = meta.get('company', 'N/A')
                section = meta.get('section_title', meta.get('section', 'Unknown'))
                
                print(f"\n[{i}] {company} - {section}")
                print(f"    Distance: {dist:.4f}")
                
                preview = doc[:120].encode('ascii', 'ignore').decode('ascii')
                preview = preview.replace('\n', ' ').strip()
                print(f"    {preview}...")
            
            print("\n" + "="*70)
        
        if not args.show_summary and not args.query:
            df = loader.load_chunks()
            print(f"\nLoaded {len(df)} chunks")
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print(f"\nFirst 3 rows:")
            print(df.head(3))
    
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
