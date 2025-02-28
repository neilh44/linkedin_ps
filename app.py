from flask import Flask, request, Response
import requests
from urllib.parse import urljoin
import os

app = Flask(__name__)

# Target URL (LinkedIn)
TARGET_URL = "https://www.linkedin.com"

# Get port from environment variable (for Render deployment)
port = int(os.environ.get("PORT", 5000))

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return "Python Proxy Server is running!"

@app.route('/linkedin/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy(path):
    """
    Main proxy function that forwards requests to LinkedIn
    and returns the response to the client
    """
    # Build the target URL
    target_url = urljoin(TARGET_URL, path)
    
    # Print for debugging
    print(f"Proxying request to: {target_url}")
    
    # Get headers from the request
    headers = {key: value for key, value in request.headers if key != 'Host'}
    
    # Add User-Agent to help avoid detection
    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    try:
        # Forward the request to LinkedIn
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=10
        )
        
        # Create a new response
        response = Response(resp.content, resp.status_code)
        
        # Copy response headers from LinkedIn
        for key, value in resp.headers.items():
            if key.lower() not in ('content-length', 'connection', 'transfer-encoding'):
                response.headers[key] = value
                
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
    
    except Exception as e:
        # Handle errors
        print(f"Error proxying request: {e}")
        return Response(f"Proxy error: {str(e)}", status=500)

@app.route('/linkedin/', defaults={'path': ''})
def proxy_root(path):
    """Handle requests to the root LinkedIn path"""
    return proxy(path)

@app.route('/')
def index():
    """Serve a simple HTML page for testing the proxy"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>LinkedIn Python Proxy</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #0077b5; }
            input { padding: 8px; width: 70%; margin-right: 10px; }
            button { padding: 8px 16px; background-color: #0077b5; color: white; border: none; border-radius: 4px; cursor: pointer; }
            iframe { width: 100%; height: 600px; border: 1px solid #ccc; margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>LinkedIn Python Proxy</h1>
        <p>Enter a LinkedIn path to browse through the proxy</p>
        
        <div>
            <input type="text" id="path-input" placeholder="Enter LinkedIn path (e.g., /feed/)" value="/feed/">
            <button onclick="loadUrl()">Load</button>
        </div>
        
        <iframe id="result-frame" src=""></iframe>
        
        <script>
            function loadUrl() {
                const path = document.getElementById('path-input').value;
                let cleanPath = path;
                
                // Handle full URLs
                if (path.startsWith('http')) {
                    try {
                        const url = new URL(path);
                        if (url.hostname.includes('linkedin.com')) {
                            cleanPath = url.pathname + url.search;
                        } else {
                            alert('Please enter a LinkedIn URL');
                            return;
                        }
                    } catch (e) {
                        alert('Invalid URL');
                        return;
                    }
                }
                
                // Ensure path starts with /
                if (!cleanPath.startsWith('/')) {
                    cleanPath = '/' + cleanPath;
                }
                
                document.getElementById('result-frame').src = '/linkedin' + cleanPath;
            }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=True)