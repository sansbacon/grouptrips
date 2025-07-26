"""OAuth utility functions for Google authentication."""
import json
import requests
from authlib.integrations.flask_client import OAuth
from flask import current_app, url_for
from app import db
from app.models.models import User


def init_oauth(app):
    """Initialize OAuth with the Flask app.
    
    Args:
        app: Flask application instance
        
    Returns:
        OAuth: Configured OAuth instance
    """
    oauth = OAuth(app)
    
    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    return oauth, google


def get_google_provider_cfg():
    """Get Google's provider configuration.
    
    Returns:
        dict: Google's OpenID Connect configuration
    """
    return requests.get(current_app.config['GOOGLE_DISCOVERY_URL']).json()


def create_or_update_google_user(google_user_info):
    """Create or update user from Google OAuth information.
    
    Args:
        google_user_info (dict): User information from Google
        
    Returns:
        User: Created or updated user instance
    """
    google_id = google_user_info['sub']
    email = google_user_info['email']
    display_name = google_user_info.get('name', '')
    avatar_url = google_user_info.get('picture', '')
    
    # Check if user exists by Google ID
    user = User.query.filter_by(google_id=google_id).first()
    
    if user:
        # Update existing user's Google information
        user.email = email
        user.display_name = display_name
        user.avatar_url = avatar_url
        user.last_login = db.func.now()
        
        db.session.commit()
        return user
    
    # Check if user exists by email
    user = User.query.filter_by(email=email).first()
    
    if user:
        # Link existing email user to Google account
        user.google_id = google_id
        user.display_name = display_name
        user.avatar_url = avatar_url
        user.last_login = db.func.now()
        
        db.session.commit()
        return user
    
    # Create new user
    username = email.split('@')[0]
    
    # Ensure username is unique
    base_username = username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1
        
    user = User(
        username=username,
        email=email,
        display_name=display_name,
        google_id=google_id,
        avatar_url=avatar_url,
    )
    
    db.session.add(user)
    db.session.commit()
    
    return user


def get_google_auth_url(google_client):
    """Get Google OAuth authorization URL.
    
    Args:
        google_client: Google OAuth client
        
    Returns:
        str: Authorization URL
    """
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google_client.authorize_redirect(redirect_uri)


def handle_google_callback(google_client, request):
    """Handle Google OAuth callback.
    
    Args:
        google_client: Google OAuth client
        request: Flask request object
        
    Returns:
        tuple: (success, user_or_error_message)
    """
    try:
        # Get authorization code from callback
        token = google_client.authorize_access_token()
        
        # Get user info from Google
        user_info = token.get('userinfo')
        
        if not user_info:
            # Fallback: get user info from Google's userinfo endpoint
            resp = google_client.get('userinfo')
            user_info = resp.json()
        
        # Verify that the user's email is verified
        if not user_info.get('email_verified'):
            return False, "Google account email not verified"
        
        # Create or update user
        user = create_or_update_google_user(user_info)
        
        return True, user
        
    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        return False, f"Authentication failed: {str(e)}"
