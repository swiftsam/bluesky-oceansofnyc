#!/usr/bin/env python3
"""
Simple HTTP server to serve images from Modal volume for local development.

This script provides a basic image serving endpoint that can be used
to test the static site locally before deploying to production.
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ImageHandler(SimpleHTTPRequestHandler):
    """Custom handler to serve images from Modal volume path."""

    def do_GET(self):  # noqa: N802
        """Handle GET requests for images."""
        if self.path.startswith("/data/images/"):
            # For local development, you would need to:
            # 1. Mount the Modal volume locally, OR
            # 2. Copy images to a local directory, OR
            # 3. Use Modal's web endpoint to serve images

            # For now, return 404 with helpful message
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(
                b"Image storage not configured. See web/README.md for setup instructions."
            )
        else:
            # Serve other files normally
            super().do_GET()


def run_server(port=8000):
    """Run the development server."""
    # Change to web directory
    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)

    server = HTTPServer(("localhost", port), ImageHandler)
    print(f"Server running at http://localhost:{port}/")
    print(f"Serving files from: {web_dir}")
    print("\nNote: Images from Modal volume will show placeholders")
    print("See README.md for image configuration options\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
