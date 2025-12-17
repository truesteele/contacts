#!/usr/bin/env python3
"""
Simple HTTP server for the donor prospect management frontend.

Usage:
    python3 server.py

Then open: http://localhost:8080
"""

import http.server
import socketserver
import os

PORT = 8080

# Change to frontend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"\n{'='*60}")
    print(f"🌲 Donor Prospect Management Frontend")
    print(f"{'='*60}")
    print(f"\n✅ Server running at: http://localhost:{PORT}")
    print(f"\n📂 Serving from: {os.getcwd()}")
    print(f"\n👉 Open http://localhost:{PORT} in your browser")
    print(f"\n{'='*60}\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✋ Server stopped")
