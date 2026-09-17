"""
Vercel Flask entrypoint. Exposes the app from api_server for deployment.
"""
from api_server import app

# Re-exported for the serverless runtime to discover.
__all__ = ["app"]
