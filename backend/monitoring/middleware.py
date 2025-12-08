"""
FastAPI middleware for automatic request monitoring
Tracks all API requests to production endpoints
"""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from .production_logger import production_monitor


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to track all API requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()
        
        # Extract request info
        endpoint = request.url.path
        method = request.method
        
        # Extract company_id and user_id from request if available
        company_id = None
        user_id = None
        
        # Try to get from headers
        if hasattr(request.state, 'company_id'):
            company_id = request.state.company_id
        if hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        
        # Process request
        error_message = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            error_message = str(e)
            raise
        finally:
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log to WANDB
            production_monitor.log_request(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                latency_ms=latency_ms,
                company_id=company_id,
                user_id=user_id,
                error=error_message
            )
        
        return response