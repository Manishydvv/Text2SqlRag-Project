"""AWS Lambda handler for FastAPI application."""
import os
from mangum import Mangum

# Set root path for API Gateway
# This tells FastAPI it's being served under /prod so OpenAPI JSON URLs are correct
os.environ["ROOT_PATH"] = "/prod"

# Create /tmp directories
os.makedirs("/tmp/uploads", exist_ok=True)
os.makedirs("/tmp/cached_chunks", exist_ok=True)

# Import app after directory creation
from app.main import app, initialize_services

# Lambda handler with lazy initialization
# API Gateway HTTP API (v2 payload format)
_handler = Mangum(app, lifespan="off", api_gateway_base_path="/prod")

# Flag to track if services have been initialized
_services_initialized = False

def handler(event, context):
    """
    Lambda handler with lazy service initialization.
    Services are initialized on first request to avoid 10-second init timeout.
    """
    global _services_initialized

    # Initialize services on first invocation (not at import time)
    if not _services_initialized:
        initialize_services()
        _services_initialized = True

    # Forward request to Mangum handler
    return _handler(event, context)
