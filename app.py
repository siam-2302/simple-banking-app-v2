import os
import datetime
import secrets
import pymysql
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_limiter.errors import RateLimitExceeded
from functools import wraps

# Extensions
from extensions import db, login_manager, bcrypt, limiter

# Load environment variables
load_dotenv()

# CSRF Protection
csrf = CSRFProtect()

# MySQL driver
pymysql.install_as_MySQLdb()

# Admin role check
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated

# App factory
def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)

    # Secure session config
    app.config.update({
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SECURE': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'REMEMBER_COOKIE_DURATION': datetime.timedelta(days=7),
        'PERMANENT_SESSION_LIFETIME': datetime.timedelta(minutes=30)
    })

    # CSRF
    csrf.init_app(app)

    # Database setup
    mysql_user = os.getenv('MYSQL_USER', '')
    mysql_password = os.getenv('MYSQL_PASSWORD', '')
    mysql_host = os.getenv('MYSQL_HOST', '')
    mysql_port = os.getenv('MYSQL_PORT', '3306')
    mysql_database = os.getenv('MYSQL_DATABASE', '')
    db_uri = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    # Rate limit error handler
    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_exceeded(e):
        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
            return jsonify({"error": "Rate limit exceeded", "message": str(e)}), 429
        return render_template('rate_limit_error.html', message=str(e)), 429

    # Generic error handlers
    @app.errorhandler(404)
    def not_found_error(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('500.html'), 500

    return app

app = create_app()

# Models
from models import User, Transaction

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
from routes import *

# Init DB
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                username="admin",
                email="admin@bankapp.com",
                account_number="0000000001",
                status="active",
                is_admin=True,
                balance=0.0
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Created default admin user.")

if __name__ == '__main__':
    print("Initializing app with environment variables:")
    print("MYSQL_HOST:", os.getenv('MYSQL_HOST'))
    print("MYSQL_USER:", os.getenv('MYSQL_USER'))
    print("MYSQL_DATABASE:", os.getenv('MYSQL_DATABASE'))

    with app.app_context():
        db.create_all()
    app.run(debug=True)
