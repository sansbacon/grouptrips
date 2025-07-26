import os
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

        # Create database tables for our models
        db.create_all()

    return app
