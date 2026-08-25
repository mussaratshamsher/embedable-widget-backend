import time
from fastapi import Request, HTTPException, status
from collections import defaultdict
import threading

class RateLimiter:
    """
    In-memory Rate Limiter using Token Bucket / Sliding Window logic.
    Note: On serverless environments like Vercel, this tracks state PER INSTANCE.
    It will prevent spamming a single instance, but it's not a strictly global limit.
    """
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
        self.history: dict[str, list[float]] = defaultdict(list)
        self.lock = threading.Lock()

    def __call__(self, request: Request):
        # Extract IP
        ip = request.client.host if request.client else "unknown"
        
        # Extract project/widget ID (Check headers, query params, or body depending on route)
        # For our case, it's often passed as a query param or in JSON.
        # But dependencies run before request parsing finishes easily, 
        # so let's rely on query params or just rate limit by IP if project ID is deep in body.
        
        project_api_key = request.query_params.get("project_api_key", "unknown")
        
        # Key combination
        key = f"{ip}:{project_api_key}"
        
        now = time.time()
        
        with self.lock:
            # Clean up old timestamps for this key
            self.history[key] = [t for t in self.history[key] if now - t < self.window]
            
            if len(self.history[key]) >= self.requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            self.history[key].append(now)
