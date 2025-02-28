from flask import Flask, redirect, request, Response
import requests
from urllib.parse import urljoin
import os

from proxy_with_session import get_session_object

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
    
    # Add headers to appear more like a regular browser
    headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
    headers['Accept-Language'] = 'en-US,en;q=0.9'
    headers['Sec-Ch-Ua'] = '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"'
    headers['Sec-Ch-Ua-Mobile'] = '?0'
    headers['Sec-Ch-Ua-Platform'] = '"macOS"'
    headers['Sec-Fetch-Dest'] = 'document'
    headers['Sec-Fetch-Mode'] = 'navigate'
    headers['Sec-Fetch-Site'] = 'none'
    headers['Sec-Fetch-User'] = '?1'
    headers['Upgrade-Insecure-Requests'] = '1'
    
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
            if key.lower() not in ('content-length', 'connection', 'transfer-encoding', 'content-security-policy'):
                response.headers[key] = value
                
        # Handle redirects manually
        if resp.status_code in (301, 302, 303, 307, 308) and 'Location' in resp.headers:
            redirect_url = resp.headers['Location']
            # If it's an absolute URL
            if redirect_url.startswith('http'):
                # Convert back to our proxy path
                if redirect_url.startswith(TARGET_URL):
                    path = redirect_url[len(TARGET_URL):]
                    response.headers['Location'] = f'/linkedin{path}'
                else:
                    # External redirect - just keep it
                    pass
            else:
                # Relative URL - just prefix with /linkedin
                response.headers['Location'] = f'/linkedin{redirect_url}'
                
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


@app.route('/login', methods=['GET', 'POST'])
def direct_login():
    """Handle LinkedIn login directly"""
    if request.method == 'GET':
        # Show a simple login form
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkedIn Login</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 400px; margin: 0 auto; padding: 20px; }
                h1 { color: #0077b5; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; }
                input[type="text"], input[type="password"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
                button { padding: 10px 15px; background-color: #0077b5; color: white; border: none; border-radius: 4px; cursor: pointer; }
                .note { background-color: #f8f8f8; padding: 10px; border-left: 4px solid #0077b5; margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1>LinkedIn Login</h1>
            <p>Enter your LinkedIn credentials to log in through the proxy</p>
            
            <form method="POST" action="/login">
                <div class="form-group">
                    <label for="username">Email or Phone</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit">Log In</button>
            </form>
            
            <div class="note">
                <p><strong>Note:</strong> Your credentials are sent directly to LinkedIn through the proxy server. They are not stored on the proxy server itself.</p>
            </div>
        </body>
        </html>
        '''
    else:
        # Process login POST request
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return "Username and password are required", 400
            
        # Get the session for this user
        s = get_session_object()
        
        try:
            # First make a GET request to the login page to get the CSRF token
            login_page = s.get('https://www.linkedin.com/login')
            
            # Extract CSRF token from the page
            import re
            csrf_token = None
            match = re.search(r'name="loginCsrfParam"\s+value="([^"]+)"', login_page.text)
            if match:
                csrf_token = match.group(1)
            
            if not csrf_token:
                return "Could not extract CSRF token, try again", 400
                
            # Prepare login data
            login_data = {
                'session_key': username,
                'session_password': password,
                'loginCsrfParam': csrf_token
            }
            
            # Make the login request
            login_resp = s.post(
                'https://www.linkedin.com/checkpoint/lg/login-submit',
                data=login_data,
                headers={
                    'Referer': 'https://www.linkedin.com/login',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            # Check if login was successful
            if login_resp.url.startswith('https://www.linkedin.com/feed'):
                # If we're redirected to the feed page, login was successful
                return redirect('/linkedin/feed/')
            else:
                # Pass through LinkedIn's response which may have error messages
                return Response(login_resp.content, login_resp.status_code)
                
        except Exception as e:
            return f"Login error: {str(e)}", 500
        
if __name__ == '__main__':
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=True)