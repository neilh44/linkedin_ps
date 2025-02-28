import requests
import os
import time
import random
from flask import session
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def get_session_object():
    """Get or create a requests session for the current user"""
    session_id = session.get('session_id')
    
    if not session_id or session_id not in SESSION_STORE:
        # Create new session
        session_id = os.urandom(16).hex()
        session['session_id'] = session_id
        
        logger.info(f"Creating new session with ID: {session_id}")
        
        # Create a new requests session
        s = requests.Session()
        
        # Choose a random user agent
        user_agent = random.choice(USER_AGENTS)
        
        # Set headers to mimic a real browser
        s.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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
            'last_used': time.time(),
            'user_agent': user_agent
        }
    else:
        # Update last used time
        SESSION_STORE[session_id]['last_used'] = time.time()
        logger.info(f"Using existing session with ID: {session_id}")
    
    return SESSION_STORE[session_id]['session']

def cleanup_old_sessions():
    """Clean up sessions that haven't been used for a while"""
    current_time = time.time()
    expired_sessions = []
    total_sessions = len(SESSION_STORE)
    
    # Find expired sessions (unused for 30 minutes)
    for session_id, session_data in SESSION_STORE.items():
        if current_time - session_data['last_used'] > 1800:  # 30 minutes
            expired_sessions.append(session_id)
    
    # Remove expired sessions
    for session_id in expired_sessions:
        try:
            del SESSION_STORE[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
        except KeyError:
            pass
    
    if expired_sessions:
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions. {total_sessions - len(expired_sessions)} sessions remaining.")
        
def get_active_session_count():
    """Get the count of active sessions"""
    return len(SESSION_STORE)

def get_session_info(session_id=None):
    """Get information about sessions
    
    Args:
        session_id (str, optional): Get info for a specific session. If None, returns info for all sessions.
    
    Returns:
        dict: Session information
    """
    current_time = time.time()
    
    if session_id:
        if session_id in SESSION_STORE:
            session_data = SESSION_STORE[session_id]
            return {
                'session_id': session_id,
                'user_agent': session_data.get('user_agent', 'Unknown'),
                'last_used': current_time - session_data['last_used'],
                'active': True
            }
        else:
            return {'session_id': session_id, 'active': False}
    
    # Return info for all sessions
    session_info = []
    for sess_id, sess_data in SESSION_STORE.items():
        session_info.append({
            'session_id': sess_id,
            'user_agent': sess_data.get('user_agent', 'Unknown'),
            'last_used_seconds_ago': int(current_time - sess_data['last_used']),
            'active': True
        })
    
    return {'total_sessions': len(session_info), 'sessions': session_info}