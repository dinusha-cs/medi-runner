#!/usr/bin/env python3
"""
Simple HTTP server for serving the 3D robot viewer
"""

import http.server
import socketserver
import webbrowser
import os
import sys

# Change to the correct directory
os.chdir(r'd:\DIPS-AS\Workbench\medi-runner')

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

def serve_3d_viewer():
    print(f"🌐 Starting HTTP server on port {PORT}")
    print(f"📁 Serving from: {os.getcwd()}")
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"✅ Server running at http://localhost:{PORT}")
        print(f"🎮 3D Robot Viewer: http://localhost:{PORT}/robot_3d_viewer.html")
        print("\nPress Ctrl+C to stop the server")
        
        # Automatically open browser
        try:
            webbrowser.open(f'http://localhost:{PORT}/robot_3d_viewer.html')
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")

if __name__ == "__main__":
    serve_3d_viewer()