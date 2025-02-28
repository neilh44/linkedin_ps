from flask import Flask, request, Response, session
import requests
from urllib.parse import urljoin, urlparse
import os
import time
import logging
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Target URL
TARGET_URL = "https://www.linkedin.com"

# Get port from environment variable
port = int(os.environ.get("PORT", 5000))

# Store sessions keyed by session ID
SESSION_STORE = {}

# Common browser user agents
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
]

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return "Enhanced LinkedIn Proxy Server is running"

def get_session_object():
    """Get or create a requests session for the current user"""
    session_id = session.get('session_id')
    
    if not session_id or session_id not in SESSION_STORE:
        # Create new session
        session_id = os.urandom(16).hex()
        session['session_id'] = session_id
        
        # Create a new requests session
        s = requests.Session()
        
        # Set a random user agent
        s.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"'
        })
        
        # Store the session
        SESSION_STORE[session_id] = {
            'session': s,
            'last_used': time.time()
        }
    else:
        # Update last used time
        SESSION_STORE[session_id]['last_used'] = time.time()
    
    return SESSION_STORE[session_id]['session']

@app.route('/linkedin/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy(path):
    """Proxy requests to LinkedIn with session support"""
    try:
        # Build the complete URL
        target_url = urljoin(TARGET_URL, path)
        logger.info(f"Proxying request to: {target_url}")
        
        # Get the session for this user
        s = get_session_object()
        
        # Get query parameters from the request
        params = request.args.copy()
        
        # Get request headers
        headers = {}
        for key, value in request.headers:
            if key.lower() not in ('host', 'cookie', 'content-length'):
                headers[key] = value
        
        # Get cookies from request
        cookies = request.cookies
                
        # Make the request to LinkedIn
        resp = s.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=params,
            data=request.get_data(),
            cookies=cookies,
            allow_redirects=False,
            timeout=20
        )
        
        logger.info(f"Response status: {resp.status_code}")
        
        # Create the response object
        response = Response(resp.content, resp.status_code)
        
        # Copy headers from LinkedIn response
        excluded_headers = ('content-encoding', 'content-length', 'transfer-encoding', 'connection', 
                           'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 
                           'upgrade', 'content-security-policy')
        
        for key, value in resp.headers.items():
            if key.lower() not in excluded_headers:
                response.headers[key] = value
        
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        # Handle redirects
        if resp.status_code in (301, 302, 303, 307, 308) and 'Location' in resp.headers:
            redirect_url = resp.headers['Location']
            
            # If it's an absolute URL
            if redirect_url.startswith('http'):
                parsed = urlparse(redirect_url)
                # If it's a LinkedIn URL, keep it within our proxy
                if parsed.netloc.endswith('linkedin.com'):
                    response.headers['Location'] = f'/linkedin{parsed.path}'
                    if parsed.query:
                        response.headers['Location'] += f'?{parsed.query}'
            else:
                # Relative URL - prefix with /linkedin
                response.headers['Location'] = f'/linkedin{redirect_url}'
        
        # Clean up old sessions (simple periodic cleanup)
        cleanup_old_sessions()
        
        return response
        
    except Exception as e:
        logger.error(f"Error proxying request: {str(e)}", exc_info=True)
        return Response(f"Proxy error: {str(e)}", status=500)

@app.route('/linkedin/', defaults={'path': ''})
def proxy_root(path):
    """Handle requests to the root LinkedIn path"""
    return proxy(path)

def cleanup_old_sessions():
    """Clean up sessions that haven't been used for a while"""
    current_time = time.time()
    expired_sessions = []
    
    # Find expired sessions (unused for 30 minutes)
    for session_id, session_data in SESSION_STORE.items():
        if current_time - session_data['last_used'] > 1800:  # 30 minutes
            expired_sessions.append(session_id)
    
    # Remove expired sessions
    for session_id in expired_sessions:
        try:
            del SESSION_STORE[session_id]
            logger.info(f"Cleaned up session {session_id}")
        except KeyError:
            pass

@app.route('/')
def index():
    """Serve a simple HTML page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced LinkedIn Proxy</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #0077b5; }
            input { padding: 8px; width: 70%; margin-right: 10px; }
            button { padding: 8px 16px; background-color: #0077b5; color: white; border: none; border-radius: 4px; cursor: pointer; }
            iframe { width: 100%; height: 600px; border: 1px solid #ccc; margin-top: 20px; }
            .note { background-color: #f8f8f8; padding: 10px; border-left: 4px solid #0077b5; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>Enhanced LinkedIn Proxy</h1>
        <p>Enter a LinkedIn path to browse through the proxy</p>
        
        <div>
            <input type="text" id="path-input" placeholder="Enter LinkedIn path (e.g., /feed/)" value="/feed/">
            <button onclick="loadUrl()">Load</button>
        </div>
        
        <div class="note">
            <p><strong>Tips:</strong></p>
            <ul>
                <li>This proxy uses session cookies to maintain your browsing state</li>
                <li>Try simple paths first like <code>/feed/</code> or <code>/jobs/</code></li>
                <li>If you encounter errors, try refreshing the page</li>
            </ul>
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