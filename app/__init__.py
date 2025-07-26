import os
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
oauth = OAuth()
google = None

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_secure_secret_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///grouptrips.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # File Upload Configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')

    # Email Configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # SendGrid Configuration
    app.config['SENDGRID_API_KEY'] = os.environ.get('SENDGRID_API_KEY')
    app.config['USE_SENDGRID_API'] = os.environ.get('USE_SENDGRID_API', 'true').lower() in ['true', '1', 't']

    # Google OAuth Configuration
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
    app.config['GOOGLE_DISCOVERY_URL'] = "https://accounts.google.com/.well-known/openid-configuration"

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Initialize OAuth and Google client
    from .utils.oauth import init_oauth
    global google
    _, google = init_oauth(app)

    with app.app_context():
        from .main import routes as main_routes
        from .auth import routes as auth_routes
        from .admin import routes as admin_routes
        from .trips import routes as trip_routes

        app.register_blueprint(main_routes.main)
        app.register_blueprint(auth_routes.auth, url_prefix='/auth')
        app.register_blueprint(admin_routes.admin, url_prefix='/admin')
        app.register_blueprint(trip_routes.trips, url_prefix='/trips')

        # Add route to serve uploaded files
        @app.route('/static/uploads/<path:filename>')
        def uploaded_file(filename):
            from flask import send_from_directory
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

        # Create database tables for our models
        db.create_all()
        
        # Create admin user if it doesn't exist
        create_admin_user()

    return app

def create_admin_user():
    """Create admin user from environment variables if it doesn't exist."""
    from .models.models import User
    
    # Get admin user details from environment variables
    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_display_name = os.environ.get('ADMIN_DISPLAY_NAME')
    admin_password = os.environ.get('ADMIN_DEFAULT_PASSWORD')
    admin_timezone = os.environ.get('ADMIN_TIMEZONE', 'US/Central')
    
    # Only create admin if all required environment variables are set
    if not all([admin_username, admin_email, admin_display_name, admin_password]):
        print("Admin user environment variables not fully configured. Skipping admin user creation.")
        return
    
    # Check if admin user already exists
    existing_admin = User.query.filter_by(username=admin_username).first()
    if existing_admin:
        print(f"Admin user '{admin_username}' already exists.")
        return
    
    # Check if email is already in use
    existing_email = User.query.filter_by(email=admin_email).first()
    if existing_email:
        print(f"Email '{admin_email}' is already in use by another user.")
        return
    
    # Create the admin user
    admin_user = User(
        username=admin_username,
        email=admin_email,
        display_name=admin_display_name,
        is_admin=True,
        is_local_account=True,
        is_active=True,
        default_timezone=admin_timezone,
        created_at=datetime.utcnow()
    )
    
    # Set the password
    admin_user.set_password(admin_password)
    
    try:
        db.session.add(admin_user)
        db.session.commit()
        print(f"✅ Admin user '{admin_username}' created successfully!")
        print(f"   Email: {admin_email}")
        print(f"   Display Name: {admin_display_name}")
        print("   Please change the default password after first login for security.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
