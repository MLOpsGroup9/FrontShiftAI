"""
Generates embeddings and stores in ChromaDB with BM25 hybrid search support.
Includes fault tolerance, deduplication, QnA export, and audit logging.
"""

import os
import sys
import json
import logging
import time
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
import numpy as np
from tqdm import tqdm
import yaml

# Embedding & Vector DB
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import torch

# BM25 for hybrid search
try:
    from rank_bm25 import BM25Okapi
    import pickle
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logging.warning("rank-bm25 not installed. Hybrid search will be disabled.")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
os.makedirs("logs/embeddings", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/embeddings/embedding_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class EmbeddingStats:
    """Statistics for embedding pipeline."""
    run_id: str
    model_name: str
    items_processed: int = 0
    items_indexed: int = 0
    items_skipped_quality: int = 0
    items_skipped_dedup: int = 0
    time_elapsed_sec: float = 0.0
    throughput_items_per_sec: float = 0.0
    avg_embedding_time_ms: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


class EmbeddingPipeline:
    """Production embedding pipeline with ChromaDB, BM25, and QnA export."""
    
    def __init__(self, config_path: str = "config/embedding_config.yaml"):
        """Initialize pipeline with configuration."""
        # Load config
        self.config = self._load_config(config_path)
        self.run_id = str(uuid.uuid4())
        
        # Set seed
        seed = self.config['runtime']['seed']
        torch.manual_seed(seed)
        np.random.seed(seed)
        
        # Device detection
        self.device = self._detect_device()
        logger.info(f"Using device: {self.device}")
        
        # Initialize model
        self.model = self._init_model()
        
        # Initialize ChromaDB
        self.chroma_client = self._init_chromadb()
        
        # Initialize BM25 if enabled
        self.bm25_index = None
        if self.config['collections']['handbook_chunks']['hybrid_search']['enabled']:
            if BM25_AVAILABLE:
                self.bm25_enabled = True
            else:
                logger.warning("BM25 not available, falling back to semantic-only search")
                self.bm25_enabled = False
        else:
            self.bm25_enabled = False
        
        # Statistics
        self.stats = EmbeddingStats(
            run_id=self.run_id,
            model_name=self.config['defaults']['active_chunk_model_name']
        )
        
        # Checkpoint state
        self.checkpoint_dir = Path(self.config['runtime']['tmp_dir']) / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Deduplication tracking
        self.seen_hashes: Set[str] = set()
        
        # Create necessary directories
        self._create_directories()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    
    def _detect_device(self) -> str:
        """Auto-detect compute device."""
        device_config = self.config['runtime']['device']
        if device_config == 'auto':
            return 'cuda' if torch.cuda.is_available() else 'cpu'
        return device_config
    
    def _init_model(self) -> SentenceTransformer:
        """Initialize embedding model."""
        model_config = self.config['models']['default']
        model_name = model_config['name']
        
        logger.info(f"Loading embedding model: {model_name}")
        model = SentenceTransformer(model_name, device=self.device)
        
        # Store normalize flag for use in encode calls
        self.normalize_embeddings = model_config.get('normalize_embeddings', True)
        
        logger.info(f"Model loaded. Dimension: {model_config['dim']}")
        return model
    
    def _init_chromadb(self) -> chromadb.Client:
        """Initialize ChromaDB client."""
        persist_dir = self.config['chromadb']['persist_directory']
        os.makedirs(persist_dir, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
        
        logger.info(f"ChromaDB initialized at {persist_dir}")
        return client
    
    def _create_directories(self):
        """Create all necessary directories."""
        dirs = [
            self.config['chromadb']['persist_directory'],
            self.config['collections']['handbook_chunks']['hybrid_search']['bm25_index_dir'],
            self.config['collections']['handbook_qna_finetune']['export']['out_dir'],
            Path(self.config['versioning']['manifest_path']).parent,
            self.config['audit']['log_dir'],
            self.config['runtime']['tmp_dir']
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def load_chunks(self, source_dir: str) -> List[Dict]:
        """Load all chunks from JSONL files in directory."""
        chunks = []
        source_path = Path(source_dir)
        
        if not source_path.exists():
            logger.error(f"Source directory not found: {source_dir}")
            return chunks
        
        jsonl_files = list(source_path.glob("*.jsonl"))
        logger.info(f"Found {len(jsonl_files)} JSONL files in {source_dir}")
        
        for jsonl_file in tqdm(jsonl_files, desc="Loading chunks"):
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            chunks.append(chunk)
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSON decode error in {jsonl_file.name}:{line_num}: {e}")
            except Exception as e:
                logger.error(f"Error loading {jsonl_file}: {e}")
        
        logger.info(f"Loaded {len(chunks)} total chunks")
        return chunks
    
    def filter_chunks(self, chunks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Filter chunks by quality gate and deduplication."""
        quality_config = self.config['collections']['handbook_chunks']['quality_gate']
        dedup_config = self.config['collections']['handbook_chunks']['deduplicate_before_index']
        
        valid_chunks = []
        skipped_chunks = []
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            
            # Quality gate
            quality_score = metadata.get('quality_score', 0.0)
            token_count = metadata.get('token_count', 0)
            
            if quality_score < quality_config['min_quality_score']:
                skipped_chunks.append(('quality', chunk))
                self.stats.items_skipped_quality += 1
                continue
            
            if token_count > quality_config['max_tokens']:
                skipped_chunks.append(('tokens', chunk))
                self.stats.items_skipped_quality += 1
                continue
            
            # Deduplication
            if dedup_config['enabled']:
                simhash = metadata.get(dedup_config['simhash_field'], '')
                if simhash in self.seen_hashes:
                    skipped_chunks.append(('duplicate', chunk))
                    self.stats.items_skipped_dedup += 1
                    continue
                self.seen_hashes.add(simhash)
            
            valid_chunks.append(chunk)
        
        logger.info(f"Filtered: {len(valid_chunks)} valid, {len(skipped_chunks)} skipped")
        logger.info(f"  - Quality: {self.stats.items_skipped_quality}")
        logger.info(f"  - Duplicates: {self.stats.items_skipped_dedup}")
        
        return valid_chunks, skipped_chunks
    
    def generate_embeddings(self, chunks: List[Dict], batch_size: Optional[int] = None) -> List[np.ndarray]:
        """Generate and validate embeddings in batches."""
        if batch_size is None:
            batch_size = self.config['embedding']['batch_size']
        
        text_field = self.config['collections']['handbook_chunks']['text_field']
        texts = [chunk.get(text_field, '') for chunk in chunks]
        
        # Sanitize texts
        if self.config['embedding']['strip_whitespace']:
            texts = [t.strip() for t in texts]
        
        if self.config['embedding']['sanitize_control_chars']:
            texts = [self._sanitize_text(t) for t in texts]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        start_time = time.time()
        
        embeddings = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
            batch_texts = texts[i:i + batch_size]
            
            batch_embeddings = self.model.encode(
                batch_texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=self.normalize_embeddings,
                device=self.device
            )
            
            embeddings.extend(batch_embeddings)
        
        embeddings = np.array(embeddings)
        
        elapsed = time.time() - start_time
        self.stats.avg_embedding_time_ms = (elapsed / len(texts)) * 1000
        
        logger.info(f"Generated {len(embeddings)} embeddings in {elapsed:.2f}s")
        logger.info(f"Average: {self.stats.avg_embedding_time_ms:.2f}ms per item")
        
        # Validate embeddings
        embeddings = self._validate_embeddings(embeddings)
        
        return embeddings
    
    def _sanitize_text(self, text: str) -> str:
        """Remove control characters."""
        return ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    def _validate_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """Validate embedding dimensions and values."""
        cfg = self.config['validation']
        issues = []
        
        # Dimension check
        if cfg['dim_check']:
            expected = self.config['defaults']['active_chunk_model_dim']
            actual = embeddings.shape[1] if len(embeddings.shape) > 1 else embeddings.shape[0]
            if actual != expected:
                raise ValueError(f"Dimension mismatch: expected {expected}, got {actual}")
        
        # Collect all issues
        if cfg['null_check'] and (nan_count := np.isnan(embeddings).sum()):
            issues.append(f"{nan_count} NaN values")
        if cfg['nan_inf_check'] and (inf_count := np.isinf(embeddings).sum()):
            issues.append(f"{inf_count} Inf values")
        if cfg['norm_check'] and self.config['models']['default']['normalize_embeddings']:
            if (non_unit := (np.abs(np.linalg.norm(embeddings, axis=1) - 1.0) > 0.01).sum()):
                issues.append(f"{non_unit} non-unit norms")
        
        if issues:
            logger.warning(f"Embedding issues: {', '.join(issues)}")
        logger.info("Embeddings passed validation")
        return embeddings
    
    def store_in_chromadb(self, chunks: List[Dict], embeddings: np.ndarray):
        """Store chunks and embeddings in ChromaDB with streaming."""
        collection_name = self.config['chromadb']['collection_name']
        
        # Get or create collection
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            logger.info(f"Using existing collection: {collection_name}")
        except:
            # Create new collection
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": self.config['chromadb']['hnsw']['space'],
                    "hnsw:construction_ef": self.config['chromadb']['hnsw']['ef_construction'],
                    "hnsw:M": self.config['chromadb']['hnsw']['M'],
                    "hnsw:search_ef": self.config['chromadb']['hnsw']['ef_search'],
                }
            )
            logger.info(f"Created new collection: {collection_name}")
        
        # Prepare data in single pass
        id_field = self.config['collections']['handbook_chunks']['id_field']
        text_field = self.config['collections']['handbook_chunks']['text_field']
        metadata_fields = set(self.config['metadata']['fields_for_index'])
        
        def filter_metadata(meta):
            return {
                k: (json.dumps(v) if isinstance(v, list) else v)
                for k, v in meta.items()
                if k in metadata_fields and v is not None and isinstance(v, (str, int, float, bool, list))
            }
        
        result = zip(*[
            (
                chunk.get(id_field, f"chunk_{i}"),
                chunk.get(text_field, ''),
                filter_metadata(chunk.get('metadata', {})),
                embeddings[i].tolist()
            )
            for i, chunk in enumerate(chunks)
        ]) if chunks else ([], [], [], [])
        
        # Convert tuples to lists for ChromaDB compatibility
        ids, documents, metadatas, embeddings_list = (list(x) for x in result) if chunks else ([], [], [], [])
        
        # Streaming ingest
        if self.config['performance']['streaming_ingest']['enabled']:
            commit_interval = self.config['performance']['streaming_ingest']['commit_interval']
            
            for i in tqdm(range(0, len(ids), commit_interval), desc="Storing in ChromaDB"):
                batch_ids = ids[i:i + commit_interval]
                batch_docs = documents[i:i + commit_interval]
                batch_meta = metadatas[i:i + commit_interval]
                batch_emb = embeddings_list[i:i + commit_interval]
                
                collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_meta,
                    embeddings=batch_emb
                )
                
                self.stats.items_indexed += len(batch_ids)
        else:
            # Add all at once
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings_list
            )
            self.stats.items_indexed = len(ids)
        
        logger.info(f"Stored {self.stats.items_indexed} chunks in ChromaDB")
    
    def build_bm25_index(self, chunks: List[Dict]):
        """Build and save BM25 index for keyword search."""
        if not self.bm25_enabled:
            logger.info("BM25 disabled, skipping index build")
            return
        
        logger.info("Building BM25 index...")
        text_field = self.config['collections']['handbook_chunks']['text_field']
        
        # Tokenize documents
        corpus = [chunk.get(text_field, '').lower().split() for chunk in chunks]
        
        # Build BM25 index
        self.bm25_index = BM25Okapi(corpus)
        
        # Save index
        bm25_dir = self.config['collections']['handbook_chunks']['hybrid_search']['bm25_index_dir']
        os.makedirs(bm25_dir, exist_ok=True)
        
        index_path = Path(bm25_dir) / "bm25_index.pkl"
        with open(index_path, 'wb') as f:
            pickle.dump(self.bm25_index, f)
        
        # Save document IDs
        id_field = self.config['collections']['handbook_chunks']['id_field']
        doc_ids = [chunk.get(id_field) for chunk in chunks]
        
        ids_path = Path(bm25_dir) / "document_ids.json"
        with open(ids_path, 'w') as f:
            json.dump(doc_ids, f)
        
        logger.info(f"BM25 index saved to {index_path}")
    
    def export_qna_for_finetuning(self):
        """Export QnA pairs split into train/val sets."""
        qna_config = self.config['collections']['handbook_qna_finetune']
        
        if not qna_config.get('export'):
            logger.info("QnA export disabled, skipping")
            return
        
        logger.info("Exporting QnA for fine-tuning...")
        
        # Load QnA files
        all_qna = []
        for qna_file in qna_config['source_files']:
            if not os.path.exists(qna_file):
                logger.warning(f"QnA file not found: {qna_file}")
                continue
            
            with open(qna_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        all_qna.append(json.loads(line))
        
        logger.info(f"Loaded {len(all_qna)} QnA pairs")
        
        # Split train/val
        split_ratio = qna_config['export']['split_ratio']
        split_idx = int(len(all_qna) * split_ratio)
        
        train_qna = all_qna[:split_idx]
        val_qna = all_qna[split_idx:]
        
        # Export
        export_config = qna_config['export']
        out_dir = export_config['out_dir']
        os.makedirs(out_dir, exist_ok=True)
        
        train_path = Path(out_dir) / export_config['train_filename']
        val_path = Path(out_dir) / export_config['val_filename']
        
        with open(train_path, 'w', encoding='utf-8') as f:
            for item in train_qna:
                f.write(json.dumps(item) + '\n')
        
        with open(val_path, 'w', encoding='utf-8') as f:
            for item in val_qna:
                f.write(json.dumps(item) + '\n')
        
        logger.info(f"Exported {len(train_qna)} train, {len(val_qna)} val QnA pairs")
        logger.info(f"  Train: {train_path}")
        logger.info(f"  Val: {val_path}")
    
    def save_checkpoint(self, chunk_ids: List[str]):
        """Save checkpoint for resuming after failure."""
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{self.run_id}.json"
        
        checkpoint_data = {
            'run_id': self.run_id,
            'processed_ids': chunk_ids,
            'stats': self.stats.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logger.debug(f"Checkpoint saved: {len(chunk_ids)} items")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """Load latest checkpoint if exists."""
        checkpoints = list(self.checkpoint_dir.glob("checkpoint_*.json"))
        
        if not checkpoints:
            return None
        
        latest_checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)
        
        with open(latest_checkpoint, 'r') as f:
            checkpoint_data = json.load(f)
        
        logger.info(f"Loaded checkpoint: {len(checkpoint_data['processed_ids'])} items already processed")
        return checkpoint_data
    
    def write_manifest(self):
        """Write version manifest with run metadata."""
        if not self.config['versioning']['write_manifest']:
            return
        
        manifest_path = self.config['versioning']['manifest_path']
        os.makedirs(Path(manifest_path).parent, exist_ok=True)
        
        manifest = {
            'run_id': self.run_id,
            'preprocessing_version': self.config['versioning']['preprocessing_version'],
            'embedding_version': self.config['versioning']['embedding_version'],
            'model_name': self.stats.model_name,
            'model_dim': self.config['defaults']['active_chunk_model_dim'],
            'created_at': datetime.now().isoformat(),
            'chunks_indexed': self.stats.items_indexed,
            'collection_name': self.config['chromadb']['collection_name'],
            'config': self.config
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Manifest written to {manifest_path}")
    
    def write_audit_log(self):
        """Write audit log."""
        if not self.config['audit']['enabled']:
            return
        
        log_dir = Path(self.config['audit']['log_dir'])
        log_file = log_dir / f"run_{self.run_id}.json"
        
        audit_data = {}
        for field in self.config['audit']['log_fields']:
            audit_data[field] = getattr(self.stats, field, None)
        
        with open(log_file, 'w') as f:
            json.dump(audit_data, f, indent=2)
        
        logger.info(f"Audit log written to {log_file}")
    
    def run(self):
        """Execute complete embedding pipeline."""
        logger.info("\n" + "="*70)
        logger.info("Embedding & Storage Pipeline")
        logger.info("="*70 + "\n")
        logger.info(f"Run ID: {self.run_id}")
        
        start_time = time.time()
        
        try:
            # 1. Load chunks
            source_dir = self.config['collections']['handbook_chunks']['source_dir']
            chunks = self.load_chunks(source_dir)
            self.stats.items_processed = len(chunks)
            
            if not chunks:
                logger.error("No chunks loaded. Exiting.")
                return
            
            # 2. Filter chunks
            valid_chunks, skipped_chunks = self.filter_chunks(chunks)
            
            if not valid_chunks:
                logger.error("No valid chunks after filtering. Exiting.")
                return
            
            # 3. Generate embeddings
            embeddings = self.generate_embeddings(valid_chunks)
            
            # 4. Store in ChromaDB
            self.store_in_chromadb(valid_chunks, embeddings)
            
            # 5. Build BM25 index
            self.build_bm25_index(valid_chunks)
            
            # 6. Export QnA
            self.export_qna_for_finetuning()
            
            # 7. Write manifest & audit
            self.write_manifest()
            
            # Calculate final stats
            self.stats.time_elapsed_sec = time.time() - start_time
            self.stats.throughput_items_per_sec = (
                self.stats.items_indexed / self.stats.time_elapsed_sec
                if self.stats.time_elapsed_sec > 0 else 0
            )
            
            self.write_audit_log()
            
            # Summary
            logger.info("\n" + "="*70)
            logger.info("Pipeline Complete")
            logger.info("="*70)
            logger.info(f"Items processed: {self.stats.items_processed}")
            logger.info(f"Items indexed: {self.stats.items_indexed}")
            logger.info(f"Items skipped (quality): {self.stats.items_skipped_quality}")
            logger.info(f"Items skipped (dedup): {self.stats.items_skipped_dedup}")
            logger.info(f"Time elapsed: {self.stats.time_elapsed_sec:.2f}s")
            logger.info(f"Throughput: {self.stats.throughput_items_per_sec:.2f} items/sec")
            logger.info(f"Avg embedding time: {self.stats.avg_embedding_time_ms:.2f}ms")
            logger.info(f"\nOutput: {self.config['chromadb']['persist_directory']}")
            logger.info(f"Logs: {self.config['audit']['log_dir']}")
            logger.info("="*70 + "\n")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.stats.errors.append(str(e))
            raise


def main():
    """Main entry point."""
    pipeline = EmbeddingPipeline(config_path="config/embedding_config.yaml")
    pipeline.run()
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
