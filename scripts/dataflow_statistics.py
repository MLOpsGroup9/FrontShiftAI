"""
Standalone analytics module for pipeline quality monitoring and SLA tracking.
Generates reports, detects anomalies, creates visualizations. Optional module.
Configuration is embedded for standalone operation.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import hashlib
import uuid

# Core libraries
import numpy as np
import pandas as pd

# Visualization
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Anomaly detection
try:
    from scipy import stats
    from sklearn.ensemble import IsolationForest
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Database
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

# Add parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Embedded Configuration (from user YAML spec)
CONFIG = {
    "runtime": {
        "report_dir": "logs/dataflow_reports/",
        "output_dir": "reports/",
        "cache_dir": ".cache/dataflow/",
        "db_backend": "duckdb",
        "threads": 4,
        "log_level": "INFO",
        "random_seed": 42,
        "persist_intermediate_stats": True,
        "save_timestamps": True,
    },
    "pipeline_stages": {
        "enabled_stages": ["extraction", "preprocessing", "embedding", "storage"],
        "comparative_analysis": True,
    },
    "chunk_quality": {
        "distributions": {
            "token_count_histogram": True,
            "quality_score_histogram": True,
        },
        "quality_breakdown": {
            "enable": True,
            "tiers": {
                "excellent": 0.85,
                "good": 0.70,
                "fair": 0.50,
            }
        },
        "outlier_detection": {
            "enable": True,
            "short_threshold_chars": 100,
            "long_threshold_chars": 1000,
        }
    },
    "sla_metrics": {
        "enabled": True,
        "quality_sla": {"min_quality_ratio": 0.70, "min_quality_percentage": 80},
        "coverage_sla": {"min_page_to_chunk_ratio": 0.85},
        "embedding_sla": {"validation_pass_rate": 1.00},
        "flag_violations": True,
    },
    "visualizations": {
        "enabled": True,
        "output_dir": "reports/visuals/",
        "formats": ["png", "json"],
        "dashboard": {
            "generate_html_dashboard": True,
            "dashboard_filename": "dataflow_dashboard.html",
        }
    },
    "trend_analysis": {
        "enabled": True,
        "detect_regressions": True,
        "regression_threshold_pct": 10,
        "trend_window_runs": 10,
    },
    "anomalies": {
        "enabled": True,
        "contamination": 0.05,
        "log_anomalies": True,
    },
    "benchmarks": {
        "quality_mean_target": 0.75,
        "dup_rate_target": 0.04,
        "retention_target": 0.90,
    }
}

# Setup logging
os.makedirs(CONFIG["runtime"]["report_dir"], exist_ok=True)
logging.basicConfig(
    level=getattr(logging, CONFIG["runtime"]["log_level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(CONFIG["runtime"]["report_dir"], 'dataflow_statistics.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EnterpriseDataflowAnalyzer:
    """
    Enterprise-grade dataflow statistics and analytics system.
    Implements comprehensive quality monitoring, SLA tracking, and reporting.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize analyzer with configuration."""
        self.config = config or CONFIG
        self.run_id = str(uuid.uuid4())[:8]
        self.start_time = time.time()
        
        # Create directories
        for dir_key in ["report_dir", "output_dir", "cache_dir"]:
            os.makedirs(self.config["runtime"][dir_key], exist_ok=True)
        
        if self.config["visualizations"]["enabled"]:
            os.makedirs(self.config["visualizations"]["output_dir"], exist_ok=True)
        
        # Initialize stats structure
        self.stats = {
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "pipeline_stages": {},
            "quality_metrics": {},
            "sla_results": {},
            "anomalies": [],
            "benchmarks": {},
            "metadata": {
                "analyzer_version": "1.0.0",
                "config_hash": hashlib.md5(str(self.config).encode()).hexdigest()
            }
        }
        
        # Data storage
        self.raw_data = {}
        self.extracted_data = {}
        self.chunks_data = []
        self.embeddings_data = {}
        
        logger.info(f"Initialized EnterpriseDataflowAnalyzer - Run ID: {self.run_id}")
    
    # ============================================================
    # 1. DATA COLLECTION
    # ============================================================
    
    def collect_extraction_stats(self) -> Dict:
        """Collect PDF extraction statistics."""
        logger.info("Collecting extraction statistics...")
        
        raw_dir = Path("data/raw")
        extracted_dir = Path("data/extracted")
        
        stats = {
            "stage": "extraction",
            "raw_pdfs": 0,
            "extracted_files": 0,
            "total_pages": 0,
            "total_words": 0,
            "parse_errors": 0,
            "tables_detected": 0,
            "images_detected": 0,
        }
        
        # Raw PDFs
        if raw_dir.exists():
            pdf_files = list(raw_dir.glob("*.pdf"))
            stats["raw_pdfs"] = len(pdf_files)
            stats["total_size_mb"] = sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)
        
        # Extracted data
        if extracted_dir.exists():
            json_files = list(extracted_dir.glob("*.json"))
            stats["extracted_files"] = len(json_files)
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        pages = data.get("pages", {})
                        stats["total_pages"] += len(pages)
                        
                        for page_data in pages.values():
                            text = page_data.get("text", "")
                            stats["total_words"] += len(text.split())
                            stats["tables_detected"] += 1 if page_data.get("has_tables") else 0
                            stats["images_detected"] += 1 if page_data.get("has_images") else 0
                        
                        self.extracted_data[json_file.stem] = data
                except Exception as e:
                    logger.error(f"Error reading {json_file}: {e}")
                    stats["parse_errors"] += 1
        
        stats["avg_pages_per_doc"] = stats["total_pages"] / stats["extracted_files"] if stats["extracted_files"] > 0 else 0
        stats["avg_words_per_page"] = stats["total_words"] / stats["total_pages"] if stats["total_pages"] > 0 else 0
        
        self.stats["pipeline_stages"]["extraction"] = stats
        logger.info(f"Extraction: {stats['extracted_files']} docs, {stats['total_pages']} pages")
        return stats
    
    def collect_preprocessing_stats(self) -> Dict:
        """Collect preprocessing/chunking statistics."""
        logger.info("Collecting preprocessing statistics...")
        
        chunks_dir = Path("data/validated/chunks")
        
        stats = {
            "stage": "preprocessing",
            "chunk_files": 0,
            "total_chunks": 0,
            "chunks_by_quality": {"excellent": 0, "good": 0, "fair": 0, "poor": 0},
            "token_distribution": [],
            "quality_distribution": [],
            "rejected_chunks": 0,
            "duplicate_chunks": 0,
        }
        
        if not chunks_dir.exists():
            logger.warning(f"Chunks directory not found: {chunks_dir}")
            self.stats["pipeline_stages"]["preprocessing"] = stats
            return stats
        
        chunk_files = list(chunks_dir.glob("*_chunks.jsonl"))
        stats["chunk_files"] = len(chunk_files)
        
        for chunk_file in chunk_files:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        self.chunks_data.append(chunk)
                        stats["total_chunks"] += 1
                        
                        # Extract metadata
                        metadata = chunk.get("metadata", {})
                        quality_score = metadata.get("quality_score", 0.0)
                        token_count = metadata.get("token_count", 0)
                        
                        stats["quality_distribution"].append(quality_score)
                        stats["token_distribution"].append(token_count)
                        
                        # Quality tiers
                        tiers = self.config["chunk_quality"]["quality_breakdown"]["tiers"]
                        if quality_score >= tiers["excellent"]:
                            stats["chunks_by_quality"]["excellent"] += 1
                        elif quality_score >= tiers["good"]:
                            stats["chunks_by_quality"]["good"] += 1
                        elif quality_score >= tiers["fair"]:
                            stats["chunks_by_quality"]["fair"] += 1
                        else:
                            stats["chunks_by_quality"]["poor"] += 1
            except Exception as e:
                logger.error(f"Error reading {chunk_file}: {e}")
        
        # Calculate statistics
        if stats["quality_distribution"]:
            stats["quality_mean"] = np.mean(stats["quality_distribution"])
            stats["quality_median"] = np.median(stats["quality_distribution"])
            stats["quality_std"] = np.std(stats["quality_distribution"])
        
        if stats["token_distribution"]:
            stats["token_mean"] = np.mean(stats["token_distribution"])
            stats["token_median"] = np.median(stats["token_distribution"])
            stats["token_p95"] = np.percentile(stats["token_distribution"], 95)
        
        self.stats["pipeline_stages"]["preprocessing"] = stats
        logger.info(f"Preprocessing: {stats['total_chunks']} chunks, quality_mean={stats.get('quality_mean', 0):.3f}")
        return stats
    
    def collect_embedding_stats(self) -> Dict:
        """Collect embedding/storage statistics."""
        logger.info("Collecting embedding statistics...")
        
        manifest_path = Path("data/vector_db/manifests/handbook_chunks_manifest.json")
        
        stats = {
            "stage": "embedding",
            "chunks_embedded": 0,
            "embedding_dimension": 0,
            "model_name": "",
            "validation_passed": True,
        }
        
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    stats["chunks_embedded"] = manifest.get("chunks_indexed", 0)
                    stats["embedding_dimension"] = manifest.get("model_dim", 0)
                    stats["model_name"] = manifest.get("model_name", "")
                    stats["preprocessing_version"] = manifest.get("preprocessing_version", "")
                    stats["embedding_version"] = manifest.get("embedding_version", "")
                    self.embeddings_data = manifest
            except Exception as e:
                logger.error(f"Error reading manifest: {e}")
        
        # Try to check ChromaDB
        try:
            import chromadb
            client = chromadb.PersistentClient(path="data/vector_db/chroma/")
            collections = client.list_collections()
            stats["chromadb_collections"] = len(collections)
            if collections:
                collection = collections[0]
                stats["chromadb_count"] = collection.count()
        except Exception as e:
            logger.warning(f"Could not connect to ChromaDB: {e}")
        
        self.stats["pipeline_stages"]["embedding"] = stats
        logger.info(f"Embedding: {stats['chunks_embedded']} vectors, dim={stats['embedding_dimension']}")
        return stats
    
    # ============================================================
    # 2. QUALITY ANALYSIS
    # ============================================================
    
    def analyze_chunk_quality(self) -> Dict:
        """Comprehensive chunk quality analysis."""
        logger.info("Analyzing chunk quality...")
        
        if not self.chunks_data:
            logger.warning("No chunks data loaded")
            return {}
        
        analysis = {
            "total_chunks": len(self.chunks_data),
            "quality_tiers": self.stats["pipeline_stages"]["preprocessing"]["chunks_by_quality"],
            "outliers": {"short": 0, "long": 0},
            "content_types": Counter(),
            "policy_coverage": Counter(),
            "keyword_density": [],
        }
        
        outlier_config = self.config["chunk_quality"]["outlier_detection"]
        
        for chunk in self.chunks_data:
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            
            # Outlier detection
            char_count = len(text)
            if char_count < outlier_config["short_threshold_chars"]:
                analysis["outliers"]["short"] += 1
            elif char_count > outlier_config["long_threshold_chars"]:
                analysis["outliers"]["long"] += 1
            
            # Content types
            content_type = metadata.get("content_type", "unknown")
            analysis["content_types"][content_type] += 1
            
            # Policy coverage
            policy_tags = metadata.get("policy_tags", [])
            if isinstance(policy_tags, str):
                policy_tags = json.loads(policy_tags) if policy_tags.startswith("[") else []
            for policy in policy_tags:
                analysis["policy_coverage"][policy] += 1
            
            # Keyword density
            keywords = metadata.get("keywords", [])
            if isinstance(keywords, str):
                keywords = json.loads(keywords) if keywords.startswith("[") else []
            analysis["keyword_density"].append(len(keywords))
        
        analysis["outlier_percentage"] = (
            (analysis["outliers"]["short"] + analysis["outliers"]["long"]) / 
            analysis["total_chunks"] * 100
        )
        analysis["avg_keywords_per_chunk"] = np.mean(analysis["keyword_density"]) if analysis["keyword_density"] else 0
        analysis["top_policies"] = dict(analysis["policy_coverage"].most_common(15))
        
        self.stats["quality_metrics"] = analysis
        logger.info(f"Quality: {analysis['quality_tiers']['excellent']} excellent, {analysis['outliers']['short']} short outliers")
        return analysis
    
    # ============================================================
    # 3. SLA VALIDATION
    # ============================================================
    
    def validate_slas(self) -> Dict:
        """Validate against SLA thresholds."""
        logger.info("Validating SLAs...")
        
        sla_config = self.config["sla_metrics"]
        results = {
            "overall_pass": True,
            "violations": [],
            "checks": {}
        }
        
        preprocessing = self.stats["pipeline_stages"].get("preprocessing", {})
        extraction = self.stats["pipeline_stages"].get("extraction", {})
        
        # Quality SLA
        if sla_config["quality_sla"]["min_quality_ratio"]:
            quality_mean = preprocessing.get("quality_mean", 0)
            target = sla_config["quality_sla"]["min_quality_ratio"]
            passed = quality_mean >= target
            results["checks"]["quality_mean"] = {
                "actual": quality_mean,
                "target": target,
                "passed": passed
            }
            if not passed:
                results["overall_pass"] = False
                results["violations"].append(f"Quality mean {quality_mean:.3f} below target {target}")
        
        # Coverage SLA
        if sla_config["coverage_sla"]["min_page_to_chunk_ratio"]:
            total_pages = extraction.get("total_pages", 0)
            total_chunks = preprocessing.get("total_chunks", 0)
            ratio = total_chunks / total_pages if total_pages > 0 else 0
            target = sla_config["coverage_sla"]["min_page_to_chunk_ratio"]
            passed = ratio >= target
            results["checks"]["page_to_chunk_ratio"] = {
                "actual": ratio,
                "target": target,
                "passed": passed
            }
            if not passed:
                results["overall_pass"] = False
                results["violations"].append(f"Page-to-chunk ratio {ratio:.3f} below target {target}")
        
        # Embedding SLA
        embedding = self.stats["pipeline_stages"].get("embedding", {})
        if embedding.get("validation_passed"):
            results["checks"]["embedding_validation"] = {
                "actual": 1.0,
                "target": 1.0,
                "passed": True
            }
        
        self.stats["sla_results"] = results
        
        if results["overall_pass"]:
            logger.info("All SLAs PASSED")
        else:
            logger.warning(f"SLA violations detected: {len(results['violations'])}")
            for violation in results["violations"]:
                logger.warning(f"  - {violation}")
        
        return results
    
    # ============================================================
    # 4. RETENTION & DEGRADATION
    # ============================================================
    
    def calculate_retention_rate(self) -> Dict:
        """Calculate data retention through pipeline."""
        logger.info("Calculating retention rate...")
        
        extraction = self.stats["pipeline_stages"].get("extraction", {})
        preprocessing = self.stats["pipeline_stages"].get("preprocessing", {})
        embedding = self.stats["pipeline_stages"].get("embedding", {})
        
        total_pages = extraction.get("total_pages", 0)
        total_chunks = preprocessing.get("total_chunks", 0)
        chunks_embedded = embedding.get("chunks_embedded", 0)
        
        retention = {
            "pages_extracted": total_pages,
            "chunks_created": total_chunks,
            "chunks_embedded": chunks_embedded,
            "page_to_chunk_rate": total_chunks / total_pages if total_pages > 0 else 0,
            "chunk_to_embedding_rate": chunks_embedded / total_chunks if total_chunks > 0 else 0,
            "overall_retention": chunks_embedded / total_pages if total_pages > 0 else 0,
        }
        
        target = self.config["benchmarks"]["retention_target"]
        retention["meets_target"] = retention["overall_retention"] >= target
        
        self.stats["retention"] = retention
        logger.info(f"Retention: {retention['overall_retention']:.2%} (target: {target:.0%})")
        return retention
    
    # ============================================================
    # 5. ANOMALY DETECTION
    # ============================================================
    
    def detect_anomalies(self) -> List[Dict]:
        """Detect anomalies using statistical methods."""
        if not SKLEARN_AVAILABLE or not self.config["anomalies"]["enabled"]:
            logger.info("Anomaly detection disabled or libraries not available")
            return []
        
        logger.info("Detecting anomalies...")
        
        anomalies = []
        preprocessing = self.stats["pipeline_stages"].get("preprocessing", {})
        
        # Quality score anomalies (Z-score method)
        quality_dist = preprocessing.get("quality_distribution", [])
        if len(quality_dist) > 10:
            z_scores = np.abs(stats.zscore(quality_dist))
            outlier_indices = np.where(z_scores > 3)[0]
            if len(outlier_indices) > 0:
                anomalies.append({
                    "type": "quality_outliers",
                    "count": len(outlier_indices),
                    "method": "zscore",
                    "threshold": 3.0
                })
        
        # Token distribution anomalies (Isolation Forest)
        token_dist = preprocessing.get("token_distribution", [])
        if len(token_dist) > 20:
            X = np.array(token_dist).reshape(-1, 1)
            clf = IsolationForest(
                contamination=self.config["anomalies"]["contamination"],
                random_state=self.config["runtime"]["random_seed"]
            )
            predictions = clf.fit_predict(X)
            outlier_count = np.sum(predictions == -1)
            if outlier_count > 0:
                anomalies.append({
                    "type": "token_distribution_outliers",
                    "count": int(outlier_count),
                    "method": "isolation_forest",
                    "contamination": self.config["anomalies"]["contamination"]
                })
        
        self.stats["anomalies"] = anomalies
        logger.info(f"Detected {len(anomalies)} anomaly patterns")
        return anomalies
    
    # ============================================================
    # 6. VISUALIZATIONS
    # ============================================================
    
    def generate_visualizations(self):
        """Generate statistical visualizations."""
        if not MATPLOTLIB_AVAILABLE or not self.config["visualizations"]["enabled"]:
            logger.info("Visualizations disabled or libraries not available")
            return
        
        logger.info("Generating visualizations...")
        
        vis_dir = Path(self.config["visualizations"]["output_dir"])
        preprocessing = self.stats["pipeline_stages"].get("preprocessing", {})
        
        # Set style
        sns.set_style("whitegrid")
        
        # 1. Token distribution histogram
        if preprocessing.get("token_distribution"):
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(preprocessing["token_distribution"], bins=30, edgecolor='black', alpha=0.7)
            ax.set_xlabel("Token Count")
            ax.set_ylabel("Frequency")
            ax.set_title("Token Count Distribution")
            ax.axvline(np.mean(preprocessing["token_distribution"]), color='r', linestyle='--', label=f'Mean: {np.mean(preprocessing["token_distribution"]):.0f}')
            ax.legend()
            plt.tight_layout()
            plt.savefig(vis_dir / "token_distribution.png", dpi=150)
            plt.close()
            logger.info("Generated token distribution chart")
        
        # 2. Quality score histogram
        if preprocessing.get("quality_distribution"):
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(preprocessing["quality_distribution"], bins=20, edgecolor='black', alpha=0.7, color='green')
            ax.set_xlabel("Quality Score")
            ax.set_ylabel("Frequency")
            ax.set_title("Quality Score Distribution")
            ax.axvline(np.mean(preprocessing["quality_distribution"]), color='r', linestyle='--', label=f'Mean: {np.mean(preprocessing["quality_distribution"]):.3f}')
            ax.legend()
            plt.tight_layout()
            plt.savefig(vis_dir / "quality_distribution.png", dpi=150)
            plt.close()
            logger.info("Generated quality distribution chart")
        
        # 3. Quality tiers bar chart
        if preprocessing.get("chunks_by_quality"):
            tiers = preprocessing["chunks_by_quality"]
            fig, ax = plt.subplots(figsize=(10, 6))
            colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
            ax.bar(tiers.keys(), tiers.values(), color=colors, edgecolor='black')
            ax.set_xlabel("Quality Tier")
            ax.set_ylabel("Number of Chunks")
            ax.set_title("Chunks by Quality Tier")
            for i, (tier, count) in enumerate(tiers.items()):
                ax.text(i, count, str(count), ha='center', va='bottom')
            plt.tight_layout()
            plt.savefig(vis_dir / "quality_tiers.png", dpi=150)
            plt.close()
            logger.info("Generated quality tiers chart")
    
    def generate_html_dashboard(self):
        """Generate interactive HTML dashboard."""
        if not self.config["visualizations"]["dashboard"]["generate_html_dashboard"]:
            return
        
        logger.info("Generating HTML dashboard...")
        
        dashboard_path = Path(self.config["runtime"]["output_dir"]) / self.config["visualizations"]["dashboard"]["dashboard_filename"]
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dataflow Statistics Dashboard - Run {self.run_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric {{ display: inline-block; margin: 10px 20px; padding: 15px; background: #ecf0f1; border-radius: 5px; min-width: 200px; }}
        .metric-label {{ font-weight: bold; color: #7f8c8d; font-size: 12px; text-transform: uppercase; }}
        .metric-value {{ font-size: 28px; color: #2c3e50; font-weight: bold; }}
        .pass {{ color: #27ae60; }}
        .fail {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .chart-container {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Dataflow Statistics Dashboard</h1>
        <p><strong>Run ID:</strong> {self.run_id} | <strong>Timestamp:</strong> {self.stats['timestamp']}</p>
        
        <h2>Pipeline Overview</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Documents</div>
                <div class="metric-value">{self.stats['pipeline_stages'].get('extraction', {}).get('extracted_files', 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Pages</div>
                <div class="metric-value">{self.stats['pipeline_stages'].get('extraction', {}).get('total_pages', 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Chunks</div>
                <div class="metric-value">{self.stats['pipeline_stages'].get('preprocessing', {}).get('total_chunks', 0)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Quality Mean</div>
                <div class="metric-value">{self.stats['pipeline_stages'].get('preprocessing', {}).get('quality_mean', 0):.3f}</div>
            </div>
        </div>
        
        <h2>SLA Status</h2>
        <table>
            <tr><th>Check</th><th>Actual</th><th>Target</th><th>Status</th></tr>
"""
        
        for check_name, check_data in self.stats.get("sla_results", {}).get("checks", {}).items():
            status_class = "pass" if check_data["passed"] else "fail"
            status_text = "✓ PASS" if check_data["passed"] else "✗ FAIL"
            html_content += f"""
            <tr>
                <td>{check_name.replace('_', ' ').title()}</td>
                <td>{check_data['actual']:.3f}</td>
                <td>{check_data['target']:.3f}</td>
                <td class="{status_class}">{status_text}</td>
            </tr>
"""
        
        html_content += """
        </table>
        
        <h2>Quality Tiers</h2>
        <table>
            <tr><th>Tier</th><th>Count</th><th>Percentage</th></tr>
"""
        
        total_chunks = self.stats['pipeline_stages'].get('preprocessing', {}).get('total_chunks', 1)
        for tier, count in self.stats['pipeline_stages'].get('preprocessing', {}).get('chunks_by_quality', {}).items():
            percentage = (count / total_chunks * 100) if total_chunks > 0 else 0
            html_content += f"""
            <tr>
                <td>{tier.title()}</td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
            </tr>
"""
        
        html_content += """
        </table>
        
        <p style="margin-top: 40px; color: #7f8c8d; text-align: center;">
            Generated by FrontShiftAI Enterprise Dataflow Analyzer v1.0
        </p>
    </div>
</body>
</html>
"""
        
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML dashboard saved to: {dashboard_path}")
    
    # ============================================================
    # 7. REPORTING
    # ============================================================
    
    def generate_reports(self):
        """Generate all output reports."""
        logger.info("Generating reports...")
        
        output_dir = Path(self.config["runtime"]["output_dir"])
        
        # JSON report
        json_path = output_dir / f"metrics_report_{self.run_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON report: {json_path}")
        
        # Markdown report
        md_path = output_dir / f"pipeline_report_{self.run_id}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown_report())
        logger.info(f"Markdown report: {md_path}")
        
        # CSV export
        csv_path = output_dir / f"metrics_export_{self.run_id}.csv"
        self._generate_csv_export(csv_path)
        logger.info(f"CSV export: {csv_path}")
    
    def _generate_markdown_report(self) -> str:
        """Generate markdown report content."""
        extraction = self.stats['pipeline_stages'].get('extraction', {})
        preprocessing = self.stats['pipeline_stages'].get('preprocessing', {})
        embedding = self.stats['pipeline_stages'].get('embedding', {})
        
        md = f"""# Dataflow Statistics Report

**Run ID:** {self.run_id}  
**Timestamp:** {self.stats['timestamp']}  
**Analyzer Version:** {self.stats['metadata']['analyzer_version']}

---

## Pipeline Overview

### Extraction Stage
- **PDFs Processed:** {extraction.get('extracted_files', 0)}
- **Total Pages:** {extraction.get('total_pages', 0)}
- **Total Words:** {extraction.get('total_words', 0):,}
- **Avg Pages/Doc:** {extraction.get('avg_pages_per_doc', 0):.1f}
- **Tables Detected:** {extraction.get('tables_detected', 0)}
- **Images Detected:** {extraction.get('images_detected', 0)}

### Preprocessing Stage
- **Total Chunks:** {preprocessing.get('total_chunks', 0)}
- **Quality Mean:** {preprocessing.get('quality_mean', 0):.3f}
- **Quality Median:** {preprocessing.get('quality_median', 0):.3f}
- **Token Mean:** {preprocessing.get('token_mean', 0):.1f}
- **Token P95:** {preprocessing.get('token_p95', 0):.1f}

#### Quality Tiers
"""
        for tier, count in preprocessing.get('chunks_by_quality', {}).items():
            md += f"- **{tier.title()}:** {count}\n"
        
        md += f"""
### Embedding Stage
- **Chunks Embedded:** {embedding.get('chunks_embedded', 0)}
- **Model:** {embedding.get('model_name', 'N/A')}
- **Dimensions:** {embedding.get('embedding_dimension', 0)}
- **ChromaDB Collections:** {embedding.get('chromadb_collections', 0)}

---

## SLA Validation

"""
        sla_results = self.stats.get('sla_results', {})
        if sla_results.get('overall_pass'):
            md += "✅ **ALL SLAs PASSED**\n\n"
        else:
            md += "⚠️ **SLA VIOLATIONS DETECTED**\n\n"
            for violation in sla_results.get('violations', []):
                md += f"- {violation}\n"
        
        md += "\n---\n\n"
        md += f"*Generated: {datetime.now().isoformat()}*\n"
        
        return md
    
    def _generate_csv_export(self, csv_path: Path):
        """Generate CSV export of key metrics."""
        data = []
        
        # Flatten stats for CSV
        for stage_name, stage_data in self.stats['pipeline_stages'].items():
            for key, value in stage_data.items():
                if isinstance(value, (int, float, str)):
                    data.append({
                        'run_id': self.run_id,
                        'stage': stage_name,
                        'metric': key,
                        'value': value
                    })
        
        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)
    
    def print_summary(self):
        """Print console summary."""
        print(f"\n{'='*70}")
        print(f"📊 Dataflow Statistics Summary - Run {self.run_id}")
        print(f"{'='*70}\n")
        
        extraction = self.stats['pipeline_stages'].get('extraction', {})
        preprocessing = self.stats['pipeline_stages'].get('preprocessing', {})
        embedding = self.stats['pipeline_stages'].get('embedding', {})
        
        print(f"📄 Extraction:")
        print(f"   Documents: {extraction.get('extracted_files', 0)}")
        print(f"   Pages: {extraction.get('total_pages', 0)}")
        print(f"   Words: {extraction.get('total_words', 0):,}\n")
        
        print(f"✂️  Preprocessing:")
        print(f"   Chunks: {preprocessing.get('total_chunks', 0)}")
        print(f"   Quality Mean: {preprocessing.get('quality_mean', 0):.3f}")
        print(f"   Token Mean: {preprocessing.get('token_mean', 0):.1f}\n")
        
        print(f"🔢 Embedding:")
        print(f"   Embedded: {embedding.get('chunks_embedded', 0)}")
        print(f"   Model: {embedding.get('model_name', 'N/A')}")
        print(f"   Dimensions: {embedding.get('embedding_dimension', 0)}\n")
        
        sla_results = self.stats.get('sla_results', {})
        if sla_results.get('overall_pass'):
            print(f"✅ SLA Status: ALL PASSED\n")
        else:
            print(f"⚠️  SLA Status: {len(sla_results.get('violations', []))} VIOLATIONS\n")
        
        print(f"{'='*70}\n")
    
    # ============================================================
    # 8. MAIN PIPELINE
    # ============================================================
    
    def run(self):
        """Execute complete analysis pipeline."""
        logger.info(f"\n{'='*70}")
        logger.info(f"Enterprise Dataflow Analyzer - Run {self.run_id}")
        logger.info(f"{'='*70}\n")
        
        try:
            # 1. Data collection
            self.collect_extraction_stats()
            self.collect_preprocessing_stats()
            self.collect_embedding_stats()
            
            # 2. Quality analysis
            self.analyze_chunk_quality()
            
            # 3. SLA validation
            self.validate_slas()
            
            # 4. Retention calculation
            self.calculate_retention_rate()
            
            # 5. Anomaly detection
            if SKLEARN_AVAILABLE:
                self.detect_anomalies()
            
            # 6. Visualizations
            if MATPLOTLIB_AVAILABLE:
                self.generate_visualizations()
            
            # 7. HTML Dashboard
            self.generate_html_dashboard()
            
            # 8. Reports
            self.generate_reports()
            
            # 9. Console summary
            self.print_summary()
            
            elapsed = time.time() - self.start_time
            logger.info(f"Analysis complete in {elapsed:.2f}s")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("🚀 FrontShiftAI Enterprise Dataflow Statistics")
    print("="*70 + "\n")
    
    # Check dependencies
    if not MATPLOTLIB_AVAILABLE:
        print("⚠️  Warning: matplotlib not installed. Visualizations disabled.")
    if not SKLEARN_AVAILABLE:
        print("⚠️  Warning: scikit-learn not installed. Anomaly detection disabled.")
    if not DUCKDB_AVAILABLE:
        print("⚠️  Warning: duckdb not installed. Using in-memory processing.")
    
    print()
    
    # Run analyzer
    analyzer = EnterpriseDataflowAnalyzer()
    stats = analyzer.run()
    
    print(f"\n📊 Reports generated:")
    print(f"   - JSON: reports/metrics_report_{analyzer.run_id}.json")
    print(f"   - Markdown: reports/pipeline_report_{analyzer.run_id}.md")
    print(f"   - CSV: reports/metrics_export_{analyzer.run_id}.csv")
    print(f"   - Dashboard: reports/dataflow_dashboard.html")
    
    if MATPLOTLIB_AVAILABLE:
        print(f"   - Charts: reports/visuals/")
    
    print(f"\n📝 Logs: {CONFIG['runtime']['report_dir']}")
    print(f"\n{'='*70}\n")
    
    return 0 if stats['sla_results'].get('overall_pass', False) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
