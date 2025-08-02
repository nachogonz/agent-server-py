"""
Simple health check server for the LiveKit Python agent.
This runs a basic HTTP server to provide health check endpoints.
"""

import asyncio
import logging
import os
from aiohttp import web, ClientSession

logger = logging.getLogger(__name__)


async def health_check(request):
    """Health check endpoint."""
    return web.json_response({"status": "ok", "service": "livekit-python-agent"})


async def start_health_server():
    """Start the health check server."""
    port = int(os.getenv("PORT", 8080))
    
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/healthz", health_check)  # Alternative health check endpoint
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Try to start on the specified port, fallback to a random port if busy
    try:
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Health check server started on port {port}")
    except OSError as e:
        if "address already in use" in str(e):
            # Try a random port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            random_port = sock.getsockname()[1]
            sock.close()
            
            site = web.TCPSite(runner, "0.0.0.0", random_port)
            await site.start()
            logger.info(f"Health check server started on random port {random_port} (port {port} was busy)")
        else:
            raise
    
    return runner


async def stop_health_server(runner):
    """Stop the health check server."""
    await runner.cleanup()
    logger.info("Health check server stopped")