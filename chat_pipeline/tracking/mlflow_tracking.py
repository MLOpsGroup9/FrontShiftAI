"""
MLflow tracking integration for FrontShiftAI RAG evaluation pipeline.

Provides experiment tracking, parameter logging, metric logging, and artifact management.
"""

import os
import mlflow
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MLflowTracker:
    """MLflow experiment tracking client"""
    
    def __init__(
        self,
        experiment_name: str = "FrontShiftAI-RAG-Evaluation",
        tracking_uri: Optional[str] = None
    ):
        """
        Initialize MLflow tracker
        
        Args:
            experiment_name: Name of MLflow experiment
            tracking_uri: MLflow tracking server URI (defaults to env var or local)
        """
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
        self.run = None
        self.enabled = True
        
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            logger.info(f"MLflow tracking URI: {self.tracking_uri}")
            
            try:
                mlflow.create_experiment(experiment_name)
                logger.info(f"Created MLflow experiment: {experiment_name}")
            except Exception:
                logger.info(f"Using existing MLflow experiment: {experiment_name}")
            
            mlflow.set_experiment(experiment_name)
            
        except Exception as e:
            logger.warning(f"MLflow initialization failed: {e}")
            self.enabled = False
    
    def start_run(self, run_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
        """Start a new MLflow run"""
        if not self.enabled:
            return
        
        try:
            if run_name is None:
                run_name = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.run = mlflow.start_run(run_name=run_name)
            
            if tags:
                mlflow.set_tags(tags)
            
            logger.info(f"Started MLflow run: {run_name} (ID: {self.run.info.run_id})")
            
        except Exception as e:
            logger.warning(f"Failed to start MLflow run: {e}")
            self.enabled = False
    
    def log_params(self, params: Dict[str, Any]):
        """Log parameters to MLflow"""
        if not self.enabled or self.run is None:
            return
        
        try:
            mlflow.log_params(params)
            logger.debug(f"Logged {len(params)} parameters to MLflow")
        except Exception as e:
            logger.warning(f"Failed to log parameters to MLflow: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """Log metrics to MLflow"""
        if not self.enabled or self.run is None:
            return
        
        try:
            numeric_metrics = {
                k: float(v) for k, v in metrics.items()
                if isinstance(v, (int, float))
            }
            
            if numeric_metrics:
                mlflow.log_metrics(numeric_metrics, step=step)
                logger.debug(f"Logged {len(numeric_metrics)} metrics to MLflow")
        except Exception as e:
            logger.warning(f"Failed to log metrics to MLflow: {e}")
    
    def log_artifact(self, file_path: str):
        """Log single artifact file to MLflow"""
        if not self.enabled or self.run is None:
            return
        
        try:
            if Path(file_path).exists():
                mlflow.log_artifact(file_path)
                logger.debug(f"Logged artifact to MLflow: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to log artifact to MLflow: {e}")
    
    def log_artifacts(self, artifact_dir: str):
        """Log directory of artifacts to MLflow"""
        if not self.enabled or self.run is None:
            return
        
        try:
            if Path(artifact_dir).exists():
                mlflow.log_artifacts(artifact_dir)
                logger.info(f"Logged artifacts from directory: {artifact_dir}")
        except Exception as e:
            logger.warning(f"Failed to log artifacts to MLflow: {e}")
    
    def set_tags(self, tags: Dict[str, str]):
        """Set tags on the current run"""
        if not self.enabled or self.run is None:
            return
        
        try:
            mlflow.set_tags(tags)
            logger.debug(f"Set {len(tags)} tags on MLflow run")
        except Exception as e:
            logger.warning(f"Failed to set tags on MLflow: {e}")
    
    def end_run(self, status: str = "FINISHED"):
        """End the current MLflow run"""
        if not self.enabled or self.run is None:
            return
        
        try:
            mlflow.end_run(status=status)
            logger.info(f"Ended MLflow run with status: {status}")
            self.run = None
        except Exception as e:
            logger.warning(f"Failed to end MLflow run: {e}")
    
    def get_run_id(self) -> Optional[str]:
        """Get the current run ID"""
        if self.run:
            return self.run.info.run_id
        return None

